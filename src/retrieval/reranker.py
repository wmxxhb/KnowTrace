from contextlib import nullcontext
from typing import List
from http import HTTPStatus
from dashscope import TextReRank
from src.settings import settings
from src.utils.logger import logger
from src.models.vector import SearchResult
from src.services.execution_trace import document_snapshots


class DashScopeReranker:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.RERANK_MODEL
        self.top_n = settings.RERANK_TOP_N

    def rerank(self, query: str, documents: List[SearchResult], trace=None,
               enabled=None, top_n=None) -> List[SearchResult]:
        enabled = settings.ENABLE_RERANK if enabled is None else enabled
        top_n = self.top_n if top_n is None else top_n
        scope = trace.step("rerank", "重排序", {"query": query, "model": self.model,
                           "top_n": top_n, "count": len(documents)}) if trace else nullcontext({})
        with scope as step:
            success = False
            if not documents or not enabled:
                step.update(status="skipped", message="未召回片段" if not documents else "未启用重排序")
                results = documents[:top_n]
            else:
                try:
                    response = TextReRank.call(
                        model=self.model, query=query, documents=[doc.text for doc in documents],
                        top_n=min(top_n, len(documents)), api_key=self.api_key,
                        base_address=settings.DASHSCOPE_HTTP_BASE_URL, workspace=settings.DASHSCOPE_WORKSPACE_ID)
                    if response.status_code != HTTPStatus.OK:
                        raise RuntimeError(f"{response.code} - {response.message}")
                    results = [documents[item["index"]].model_copy(update={"score": item["relevance_score"]})
                               for item in response.output["results"]]
                    success = True
                except Exception as error:
                    logger.error(f"重排模型 {self.model} 调用失败，使用原始检索结果：{error}")
                    step.update(status="degraded", message="重排序失败，沿用原始检索顺序", error=str(error))
                    results = documents[:top_n]
            after = {doc.id: (rank, doc.score) for rank, doc in enumerate(results, 1)}
            comparison = []
            for rank, doc in enumerate(documents, 1):
                selected = after.get(doc.id)
                comparison.append(dict(id=doc.id, text=doc.text, metadata=doc.metadata,
                    rank_before=rank, rank_after=selected[0] if selected else None, distance=doc.score,
                    relevance=selected[1] if selected and success else None, selected=selected is not None))
            step["output"] = {"count": len(results), "comparison": comparison,
                "candidates": document_snapshots(results, "relevance" if success else "distance")}
            return results
