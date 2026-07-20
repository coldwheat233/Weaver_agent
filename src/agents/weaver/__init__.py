"""Weaver 组件包 —— DESIGN.md 第 17 章解耦
外观模式：对外只暴露 weave() 函数，内部由 4 个子组件协作。
"""

from typing import List, Optional
from src.core.models import IdeaNode, ConceptCluster, Relationship, ConflictInfo
from src.core.llm_service import LLMService
from src.agents.weaver.clusterer import Clusterer
from src.agents.weaver.relationship_builder import RelationshipBuilder
from src.agents.weaver.bridge_finder import BridgeFinder
from src.agents.weaver.conflict_detector import ConflictDetector


class WeaverAgent:
    """语义编织者 —— 外观模式协调 4 个子组件"""

    def __init__(self, llm: LLMService):
        self.clusterer = Clusterer(llm)
        self.rel_builder = RelationshipBuilder(llm)
        self.bridge_finder = BridgeFinder(llm)
        self.conflict_detector = ConflictDetector(llm)

    async def weave(self, nodes: List[IdeaNode], north_star: str,
                    feedback: Optional[dict] = None,
                    max_input_tokens: int = 8000) -> dict:
        """执行完整编织流程"""
        # Step 1: 聚类
        cluster_result = await self.clusterer.cluster(nodes, north_star)
        clusters_data = cluster_result.get("clusters", [])

        # Step 2: 关系发现
        rel_result = await self.rel_builder.discover(nodes, clusters_data, north_star)

        # Step 3: 跨域桥梁
        bridge_result = await self.bridge_finder.find(
            nodes, clusters_data,
            rel_result.get("relationships", []),
        )

        # Step 4: 冲突检测
        conflict_result = await self.conflict_detector.detect(
            nodes, rel_result.get("relationships", []),
        )

        # 汇总
        return {
            "clusters": clusters_data,
            "relationships": rel_result.get("relationships", []),
            "cross_domain_bridges": bridge_result.get("cross_domain_bridges", []),
            "conflicts": conflict_result.get("conflicts", []),
        }

    # 保持向后兼容的静态方法
    @staticmethod
    def build_clusters_from_result(data: dict, nodes: List[IdeaNode]) -> List[ConceptCluster]:
        from uuid import uuid4
        clusters = []
        for item in data.get("clusters", []):
            indices = item.get("member_indices", [])
            member_ids = [nodes[i].id for i in indices if 0 <= i < len(nodes)]
            if not member_ids:
                continue
            clusters.append(ConceptCluster(
                id=uuid4(), name=item.get("name", ""),
                description=item.get("description", ""),
                member_node_ids=member_ids,
                summary=item.get("description", "")[:300],
                cross_domain_count=len(set(tuple(nodes[i].context_tags) for i in indices if 0 <= i < len(nodes))),
            ))
        return clusters

    @staticmethod
    def build_relationships(data: dict, nodes: List[IdeaNode]) -> List[Relationship]:
        from uuid import uuid4
        from src.core.models import RelationshipType
        rels = []
        for item in data.get("relationships", []):
            si, ti = item.get("source_idx", -1), item.get("target_idx", -1)
            if si < 0 or si >= len(nodes) or ti < 0 or ti >= len(nodes):
                continue
            rtype = item.get("type", "supports")
            try:
                rtype = RelationshipType(rtype)
            except ValueError:
                rtype = RelationshipType.SUPPORTS
            rels.append(Relationship(
                id=uuid4(), source_node_id=nodes[si].id, target_node_id=nodes[ti].id,
                relationship_type=rtype, strength=item.get("strength", 0.5),
                explanation=item.get("explanation", ""),
            ))
        return rels

    @staticmethod
    def build_conflicts(data: dict, nodes: List[IdeaNode]) -> List[ConflictInfo]:
        from uuid import uuid4
        from src.core.models import ConflictType
        conflicts = []
        for item in data.get("conflicts", []):
            ia, ib = item.get("idx_a", -1), item.get("idx_b", -1)
            if ia < 0 or ia >= len(nodes) or ib < 0 or ib >= len(nodes):
                continue
            ctype = item.get("type", "tension")
            try:
                ctype = ConflictType(ctype)
            except ValueError:
                ctype = ConflictType.TENSION
            conflicts.append(ConflictInfo(
                id=uuid4(), node_a=nodes[ia].id, node_b=nodes[ib].id,
                conflict_type=ctype, description=item.get("description", ""),
                resolution_strategy=item.get("suggested_strategy", "flag_for_user"),
            ))
        return conflicts
