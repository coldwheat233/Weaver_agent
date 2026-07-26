"""Embedding 生成服务 —— 通过 OpenAICompatibleService"""

from typing import List


class EmbeddingService:
    def __init__(self, model: str = "qwen3.7-text-embedding"):
        self.model = model
        self._service = None

    @property
    def service(self):
        if self._service is None:
            from src.core.deepseek_service import OpenAICompatibleService
            from src.utils.runtime_config import RuntimeConfig
            # embedding 独立供应商——不跟 chat 走同一个 API
            cfg = RuntimeConfig.load()
            emb_key = cfg.get("embedding_api_key", cfg.get("api_key", ""))
            emb_base = cfg.get("embedding_base_url", "https://dashscope.aliyuncs.com/compatible-mode")
            self._service = OpenAICompatibleService(api_key=emb_key, base_url=emb_base)
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
