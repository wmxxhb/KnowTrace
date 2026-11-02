from src.retrieval.vector_retriever import VectorRetriever
from src.retrieval.reranker import DashScopeReranker
from src.llm.llm_client import LLMClient
from src.settings import settings
from src.services.question_analyzer import QuestionAnalyzer
from src.services.memory_service import MemorySystem
from src.services.execution_trace import ExecutionTrace, TracedExecutionError, document_snapshots


class RAGService:
    def __init__(self):
        self.retriever = VectorRetriever()
        self.reranker = DashScopeReranker()
        self.memory = MemorySystem()

    def query(self, query_text, top_k=5, session_id="default", kb_ids=None,
              assistant_config=None, on_event=None):
        trace = ExecutionTrace(on_event)
        try:
            config = assistant_config or {}
            rag_config = config.get("rag_config") or {}
            with trace.step("configuration", "确定问答配置", {"query": query_text}) as step:
                top_k = int(rag_config.get("top_k", top_k))
                rerank_enabled = bool(rag_config.get("enable_rerank", settings.ENABLE_RERANK))
                top_n = int(rag_config.get("rerank_top_n", settings.RERANK_TOP_N))
                if top_k < 1 or top_n < 1:
                    raise ValueError("召回数量和重排保留数量必须大于 0")
                model = config.get("llm_model") or settings.LLM_MODEL
                llm = LLMClient(model, config.get("temperature", 0.7))
                step["output"] = dict(mode="知识库问答" if kb_ids else "通用问答", model=model,
                    kb_ids=kb_ids or [], top_k=top_k, rerank_enabled=rerank_enabled,
                    rerank_top_n=top_n, method="向量检索" if kb_ids else "无检索")
            memory_config = config.get("memory_config") or {}
            memory_enabled = memory_config.get("enable_short_term", True)
            with trace.step("memory", "读取对话历史") as step:
                try:
                    history = self.memory.get_short_term_memory(session_id, memory_config.get("window_size", 10)) if memory_enabled else []
                except Exception as error:
                    history = []
                    step.update(status="degraded", message="历史读取失败，本次不使用历史", error=str(error))
                step["output"] = {"count": len(history), "messages": history}
                if not memory_enabled:
                    step.update(status="skipped", message="未启用短期记忆")
            history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history)
            if memory_config.get("enable_long_term") or config.get("agent_ids"):
                with trace.step("extensions", "扩展能力") as step:
                    step.update(status="skipped", message="长期记忆与智能体执行尚未实现，本次未执行")
            selected = []
            if kb_ids:
                contextual_query = f"历史对话：\n{history_text}\n当前问题：{query_text}" if history_text else query_text
                with trace.step("analysis", "分析问题", {"query": contextual_query, "model": model}) as step:
                    analysis = QuestionAnalyzer(llm).analyze(contextual_query) if settings.ENABLE_MULTI_HOP else {}
                    sub_queries = analysis.get("sub_queries") or []
                    use_multi = bool(analysis.get("is_multi_hop") and isinstance(sub_queries, list) and sub_queries)
                    queries = [q for q in sub_queries if isinstance(q, str) and q.strip()][:settings.MAX_HOP] if use_multi else [query_text]
                    queries = queries or [query_text]
                    step["output"] = {"mode": "多跳检索" if len(queries) > 1 else "单次检索", "queries": queries, "reason": analysis.get("reason", "未启用多跳问题分析")}
                    if analysis.get("fallback"):
                        step.update(status="degraded", message="问题分析失败，按原问题检索", error=analysis.get("reason"))
                    elif not settings.ENABLE_MULTI_HOP:
                        step.update(status="skipped", message="未启用多跳问题分析")
                candidates = []
                for query in queries:
                    initial_k = top_k * 2 if rerank_enabled and len(queries) == 1 else top_k
                    candidates.extend(self.retriever.retrieve(query, top_k=initial_k, kb_ids=kb_ids, trace=trace))
                if len(queries) > 1:
                    with trace.step("deduplicate", "合并并去重", {"count": len(candidates)}) as step:
                        unique = {}
                        for doc in candidates:
                            if doc.id not in unique or doc.score < unique[doc.id].score:
                                unique[doc.id] = doc
                        candidates = sorted(unique.values(), key=lambda doc: doc.score)
                        step["output"] = {"count": len(candidates), "candidates": document_snapshots(candidates)}
                selected = self.reranker.rerank(query_text, candidates, trace=trace,
                                               enabled=rerank_enabled, top_n=top_n if rerank_enabled else top_k)
            else:
                with trace.step("retrieval", "知识库检索") as step:
                    step.update(status="skipped", message="未选择知识库，直接进行通用问答")
            with trace.step("context", "组装模型输入") as step:
                context = "\n\n".join(f"段落 {index} (ID: {doc.id}):\n{doc.text}" for index, doc in enumerate(selected, 1))
                if history_text:
                    context = f"历史对话：\n{history_text}\n\n检索资料：\n{context}"
                if kb_ids:
                    prompt = f"基于以下上下文回答问题。\n\n上下文：\n{context}\n\n问题：{query_text}\n\n要求：只根据上下文回答；无相关信息时明确说明无法回答；引用段落编号；保持准确、简洁。"
                else:
                    prompt = f"{context}\n\n用户问题：{query_text}"
                step["output"] = {"context": context, "count": len(selected), "source_ids": [doc.id for doc in selected]}
            system_prompt = config.get("system_prompt") or "你是一名知识库问答助手，请使用中文回答。"
            with trace.step("generation", "生成回答", {"model": model, "temperature": llm.temperature,
                            "thinking": settings.LLM_ENABLE_THINKING, "system_prompt": system_prompt, "prompt": prompt}) as step:
                answer, first_token, duration = llm.generate_response_with_metrics(prompt, system_prompt)
                metrics = {"first_token_latency": first_token, "total_latency": duration}
                step["output"] = {"answer": answer, "characters": len(answer), **metrics}
            if memory_enabled:
                with trace.step("memory_write", "保存对话记忆") as step:
                    try:
                        self.memory.add_short_term_memory(session_id, "user", query_text)
                        self.memory.add_short_term_memory(session_id, "assistant", answer)
                        step["output"] = {"count": 2}
                    except Exception as error:
                        step.update(status="degraded", message="短期记忆写入失败，本次未完整更新记忆", error=str(error))
            return {"query": query_text, "answer": answer,
                    "source_documents": [{"id": doc.id, "text": doc.text, "score": doc.score, "metadata": doc.metadata} for doc in selected],
                    "metrics": metrics, "execution_trace": trace.finish()}
        except Exception as error:
            raise TracedExecutionError(str(error), trace.finish("failed", str(error))) from error
