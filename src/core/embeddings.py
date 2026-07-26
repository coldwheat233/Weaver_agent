"""Embedding 生成服务 —— 通过 OpenAICompatibleService"""

from typing import List


class EmbeddingService:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self._service = None

    @property
    def service(self):
        if self._service is None:
            from src.core.deepseek_service import OpenAICompatibleService
            self._service = OpenAICompatibleService()
        return self._service

    async def generate(self, text: str) -> List[float]:
        embeddings = await self.batch_generate([text])
        return embeddings[0]

    async def batch_generate(self, texts: List[str]) -> List[List[float]]:
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if not non_empty:
            return [[0.0] for _ in texts]

        result = await self.service.embed(
            texts=[t for _, t in non_empty],
            model=self.model,
        )
        # 重建结果数组，保持与输入索引一致
        output = [[0.0] for _ in texts]
        for idx, (orig_idx, _) in enumerate(non_empty):
            output[orig_idx] = result[idx] if idx < len(result) else [0.0]
        return output
