import time
from http import HTTPStatus
from typing import Optional, Tuple

from dashscope import Generation, MultiModalConversation
from src.settings import settings
from src.utils.logger import logger


class LLMClient:
    def __init__(self, model_name: Optional[str] = None, temperature: float = 0.7):
        self.model_name = model_name or settings.LLM_MODEL
        self.api_key = settings.DASHSCOPE_API_KEY
        self.temperature = temperature

    def generate_response_with_metrics(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Tuple[str, float, float]:
        if not self.api_key:
            raise RuntimeError("请先配置 DASHSCOPE_API_KEY")

        # Qwen 3.7 Plus requires the multimodal endpoint even for text-only input.
        multimodal = self.model_name.startswith("qwen3.7-plus")
        messages = [
            {"role": "system", "content": system_prompt or "你是一名知识库问答助手，请使用中文回答。"},
            {"role": "user", "content": prompt},
        ]
        if multimodal:
            messages = [
                {"role": message["role"], "content": [{"text": message["content"]}]}
                for message in messages
            ]

        parameters = {
            "model": self.model_name,
            "messages": messages,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "top_p": 0.8,
            "stream": True,
            "incremental_output": True,
            "base_address": settings.DASHSCOPE_HTTP_BASE_URL,
            "workspace": settings.DASHSCOPE_WORKSPACE_ID,
        }
        if self.model_name.startswith("qwen3"):
            parameters["enable_thinking"] = settings.LLM_ENABLE_THINKING
        if not multimodal:
            parameters["result_format"] = "message"
        client = MultiModalConversation if multimodal else Generation
        started = time.perf_counter()
        first_token = None
        chunks = []
        try:
            for response in client.call(**parameters):
                if response.status_code != HTTPStatus.OK:
                    raise RuntimeError(
                        f"模型调用失败（{response.code}）：{response.message}"
                    )
                choices = response.output.get("choices", [])
                if not choices:
                    continue
                content = choices[0]["message"].get("content", []) if multimodal else choices[0]["message"].get("content", "")
                text = "".join(part.get("text", "") for part in content) if multimodal else content
                if text:
                    if first_token is None:
                        first_token = time.perf_counter()
                    chunks.append(text)
        except Exception as error:
            logger.error(f"模型 {self.model_name} 调用失败：{error}")
            if isinstance(error, RuntimeError):
                raise
            raise RuntimeError(f"模型请求失败：{error}") from error

        if not chunks:
            raise RuntimeError("模型未返回回答内容")
        ended = time.perf_counter()
        return "".join(chunks), first_token - started, ended - started

    def generate_response(self, query: str, context: str, system_prompt: Optional[str] = None) -> str:
        prompt = f"""基于以下上下文信息回答问题。

上下文：
{context}

问题：{query}

要求：
1. 基于上下文回答，不添加外部知识。
2. 如上下文无相关信息，明确说明“根据提供的信息无法回答”。
3. 引用相关段落编号。
4. 保持回答准确、简洁。
"""
        return self.generate_custom_response(prompt, system_prompt)

    def generate_general_response(self, query: str, context: str = "") -> str:
        prompt = f"{context}\n\n用户问题：{query}"
        return self.generate_custom_response(prompt)

    def generate_custom_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        answer, _, _ = self.generate_response_with_metrics(prompt, system_prompt)
        return answer
