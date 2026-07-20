"""混合检索器 + Token 管理 —— DESIGN.md 第 16 章补充-5

HybridRetriever: 向量相似度(70%) + 关键词匹配(20%) + 时间衰减(10%)
TruncationPolicy: 三级降级截断策略
"""

from typing import List, Optional, Tuple
from datetime import datetime, timezone
from uuid import UUID
from src.core.models import IdeaNode
from src.core.embeddings import EmbeddingService
from src.storage.vector_store import VectorStore
from src.storage.idea_repo import IdeaRepo
from src.utils.logging_config import logger


class HybridRetriever:
    """混合检索——向量 + 关键词 + 时间衰减 + K-hop 图扩展"""

    DECAY_HALFLIFE_DAYS = 30

    def __init__(self, vector_store: VectorStore, idea_repo: IdeaRepo,
                 embedding_service: EmbeddingService):
        self.vector_store = vector_store
        self.idea_repo = idea_repo
        self.embedding_service = embedding_service

    async def retrieve_for_weaving(
        self,
        north_star: str,
        new_node_ids: List[UUID],
        divergence_degree: int = 2,
        max_nodes: int = 20,
    ) -> List[IdeaNode]:
        """为一次编织检索所有相关历史节点。

        策略：
        1. 以北极星 embedding 为中心，向量检索 2*max_nodes 候选
        2. 计算 north_star_relevance
        3. 关键词穿透：按 context_tags 精确匹配
        4. 时间衰减：旧节点得分降低
        5. K-hop 展开：沿已有关系图扩展 divergence_degree 跳
        6. 截断到 max_nodes
        """
        # Step 0: 生成北极星 embedding
        north_embedding = await self.embedding_service.generate(north_star)

        # Step 1: 向量检索
        candidates_raw = self.vector_store.search_ideas(
            north_embedding,
            k=max_nodes * 2,
            filter={"status": {"$ne": "dormant"}},
        )

        # Step 2: 获取候选节点完整信息
        candidate_ids = [c["id"] for c in candidates_raw]
        candidates = await self.idea_repo.get_by_ids(
            [UUID(cid) for cid in candidate_ids]
        )

        # 构建 id → similarity 映射
        sim_map = {c["id"]: c["similarity"] for c in candidates_raw}

        # Step 3: 关键词增强——匹配 context_tags
        keywords = _extract_keywords(north_star)
        keyword_hits = await self.idea_repo.search_by_context_tags(
            keywords, limit=max_nodes
        )
        existing_ids = {str(c.id) for c in candidates}
        for hit in keyword_hits:
            if str(hit.id) not in existing_ids:
                candidates.append(hit)
                sim_map[str(hit.id)] = 0.5  # 默认相似度

        # Step 4: 时间衰减 + 综合评分
        now = datetime.now(timezone.utc)
        for c in candidates:
            # 确保 created_at 是 timezone-aware
            created = c.created_at
            if created.tzinfo is None:
                from datetime import timezone as tz
                created = created.replace(tzinfo=tz.utc)
            age_days = (now - created).days
            decay = 0.5 ** (age_days / self.DECAY_HALFLIFE_DAYS)

            similarity = sim_map.get(str(c.id), 0.5)
            is_keyword_hit = c in keyword_hits

            c.north_star_relevance = (
                similarity * 0.7
                + (1.0 if is_keyword_hit else 0.0) * 0.2
                + decay * 0.1
            )

        # Step 5: 排序
        candidates.sort(key=lambda c: c.north_star_relevance, reverse=True)

        # Step 6: 排除新节点自身（已在 Weaver 输入中）
        new_id_set = {str(nid) for nid in new_node_ids}
        selected = [c for c in candidates if str(c.id) not in new_id_set][:max_nodes]

        # Step 7: K-hop 图扩展
        if divergence_degree > 0:
            selected = await self._graph_expand(selected, divergence_degree, max_nodes)

        logger.bind(component="retrieval").info(
            f"Retrieved {len(selected)} nodes for weaving "
            f"(candidates={len(candidates)}, divergence={divergence_degree})"
        )
        return selected[:max_nodes]

    async def _graph_expand(self, seeds: List[IdeaNode], hops: int,
                            max_total: int) -> List[IdeaNode]:
        """沿关系图扩展 K 跳"""
        from src.core.graph_ops import GraphOps

        # 加载种子节点的关系
        all_rels = []
        for seed in seeds:
            rels = await self.idea_repo.get_relationships(seed.id)
            all_rels.extend(rels)

        graph = GraphOps()
        graph.build(seeds, all_rels)

        seed_ids = [str(s.id) for s in seeds]
        expanded_ids = graph.expand_neighbors(seed_ids, hops)

        # 获取扩展节点
        new_ids = [UUID(eid) for eid in expanded_ids if eid not in seed_ids]
        if new_ids:
            expanded = await self.idea_repo.get_by_ids(new_ids)
            seen = {str(s.id) for s in seeds}
            result = list(seeds)
            for n in expanded:
                if str(n.id) not in seen:
                    result.append(n)
                    seen.add(str(n.id))
            seeds = result[:max_total]

        return seeds


def _extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词（简易版，实际可用 NLP 库）"""
    # 中英文分词简易处理
    import re
    # 提取 2-8 字符的中文词
    chinese_words = re.findall(r'[一-鿿]{2,8}', text)
    # 提取英文词
    english_words = re.findall(r'[a-zA-Z]{3,}', text)
    return list(set(chinese_words + english_words))[:10]


# ═══════════════════════════════════════════
# Token 截断策略
# ═══════════════════════════════════════════

class TruncationPolicy:
    """三级降级截断策略

    当 Weaver 上下文超过 max_input_tokens 时按顺序降级：
    1. 减少节点数 → Top-5
    2. 压缩节点内容 → 只用 raw_content 前 200 字符
    3. 裁减弱关系 → 只保留 strength > 0.7
    """

    MAX_NODES_TIER1 = 10
    MAX_NODES_TIER2 = 5
    CONTENT_MAX_CHARS = 200

    @staticmethod
    def estimate_tokens(nodes: List[dict], relationships: List[dict]) -> int:
        """估算 token 数（粗略：4 字符 ≈ 1 token）"""
        text = ""
        for n in nodes:
            text += n.get("standardized_content", "") or n.get("raw_content", "")
            text += " ".join(n.get("context_tags", []))
        for r in relationships:
            text += r.get("explanation", "")
        return len(text) // 4

    @classmethod
    def truncate(cls, nodes: List[dict], relationships: List[dict],
                 max_tokens: int) -> Tuple[List[dict], List[dict]]:
        """按预算截断，返回适配后的 (nodes, relationships)"""
        current = cls.estimate_tokens(nodes, relationships)
        if current <= max_tokens:
            return nodes, relationships

        # Tier 1: 减节点到 Top-N
        nodes = nodes[:cls.MAX_NODES_TIER1]
        current = cls.estimate_tokens(nodes, relationships)
        if current <= max_tokens:
            logger.debug(f"Truncation Tier 1: {len(nodes)} nodes, {current}t")
            return nodes, relationships

        # Tier 2: 减少更多 + 压缩内容
        nodes = nodes[:cls.MAX_NODES_TIER2]
        for n in nodes:
            raw = n.get("raw_content", "")
            if len(raw) > cls.CONTENT_MAX_CHARS:
                n["standardized_content"] = raw[:cls.CONTENT_MAX_CHARS] + "..."
        current = cls.estimate_tokens(nodes, relationships)
        if current <= max_tokens:
            logger.debug(f"Truncation Tier 2: content compressed, {current}t")
            return nodes, relationships

        # Tier 3: 裁减弱关系
        relationships = [r for r in relationships if r.get("strength", 0) > 0.7]
        current = cls.estimate_tokens(nodes, relationships)
        logger.debug(f"Truncation Tier 3: weak rels pruned, {current}t")
        return nodes, relationships
