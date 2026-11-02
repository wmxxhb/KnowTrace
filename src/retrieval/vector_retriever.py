from contextlib import nullcontext
from typing import List, Optional
from src.retrieval.base_retriever import BaseRetriever
from src.database.vector_db import MilvusClient
from src.embedding import get_embedding_service
from src.models.vector import SearchResult
from src.services.execution_trace import document_snapshots
from src.settings import settings


class VectorRetriever(BaseRetriever):
    def __init__(self):
        self.milvus_client = MilvusClient()
        self.embedding_service = get_embedding_service()

    def retrieve(self, query: str, top_k: int = 10, kb_id: Optional[int] = None,
                 kb_ids: Optional[List[int]] = None, trace=None) -> List[SearchResult]:
        scope = trace.step("embedding", "问题向量化", {"query": query, "model": settings.EMBEDDING_MODEL,
                           "dimension": settings.MILVUS_DIMENSION}) if trace else nullcontext({})
        with scope as step:
            vector = self.embedding_service.embed_query(query)
            if not vector:
                raise RuntimeError("问题向量化未返回向量")
            step["output"] = {"dimension": len(vector)}
        expr = f"kb_id in {kb_ids}" if kb_ids else (f"kb_id == {kb_id}" if kb_id is not None else None)
        scope = trace.step("retrieval", "向量检索", {"query": query, "method": "向量检索（L2 距离）",
                           "storage": "本地向量库" if settings.LOCAL_MODE else "Milvus",
                           "kb_ids": kb_ids or ([kb_id] if kb_id is not None else []), "top_k": top_k}) if trace else nullcontext({})
        with scope as step:
            results = self.milvus_client.search(vector, top_k=top_k, expr=expr)
            step["output"] = {"count": len(results), "candidates": document_snapshots(results)}
            return results
