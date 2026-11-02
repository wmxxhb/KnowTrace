from typing import List
from http import HTTPStatus
from dashscope import TextEmbedding
from src.settings import settings
from src.embedding.base import BaseEmbedding


class DashScopeEmbeddingService(BaseEmbedding):
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.MILVUS_DIMENSION

    def _embed(self, texts: List[str], text_type: str) -> List[List[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise ValueError("请先配置 DASHSCOPE_API_KEY")
        batch_size = min(settings.EMBEDDING_BATCH_SIZE, settings.EMBEDDING_MAX_BATCH_SIZE, 20)
        if batch_size < 1:
            raise ValueError("嵌入批量大小必须大于 0")
        embeddings = []
        for offset in range(0, len(texts), batch_size):
            batch = texts[offset:offset + batch_size]
            response = TextEmbedding.call(
                model=self.model,
                input=batch,
                api_key=self.api_key,
                dimension=self.dimension,
                text_type=text_type,
                output_type="dense",
                base_address=settings.DASHSCOPE_HTTP_BASE_URL,
                workspace=settings.DASHSCOPE_WORKSPACE_ID,
            )
            if response.status_code != HTTPStatus.OK:
                raise RuntimeError(f"嵌入模型调用失败：{response.code} - {response.message}")
            items = sorted(response.output["embeddings"], key=lambda item: item["text_index"])
            if len(items) != len(batch):
                raise RuntimeError("嵌入模型返回数量与输入数量不一致")
            for item in items:
                vector = item["embedding"]
                if len(vector) != self.dimension:
                    raise RuntimeError("嵌入模型返回维度与配置不一致")
                embeddings.append(vector)
        return embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts, "document")

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text], "query")[0]
