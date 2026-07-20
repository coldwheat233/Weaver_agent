"""Embedding 生成服务 —— 通过 LiteLLM 调用"""

from typing import List
from src.utils.config import get_settings

settings = get_settings()


class EmbeddingService:
    """生成文本 embedding 向量"""

    def __init__(self, model: str | None = None):
        self.model = model or settings.EMBEDDING_MODEL

    async def generate(self, text: str) -> List[float]:
        """为单条文本生成 embedding"""
        embeddings = await self.batch_generate([text])
        return embeddings[0]

    async def batch_generate(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding"""
        import litellm

        # 过滤空文本
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if not non_empty:
            return [[0.0] for _ in texts]

        try:
            resp = await litellm.aembedding(
                model=self.model,
                input=[t for _, t in non_empty],
            )
            # 重建结果数组（保持与输入索引一致）
            result = [[0.0] for _ in texts]
            for idx, (orig_idx, _) in enumerate(non_empty):
                result[orig_idx] = resp.data[idx]["embedding"]
            return result
        except Exception as e:
            # 降级：返回零向量
            return [[0.0] for _ in texts]
