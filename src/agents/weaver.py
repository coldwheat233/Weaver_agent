"""Weaver Agent —— 语义聚类 + 关系发现 + 跨域桥梁 + 冲突检测"""

from typing import List, Dict, Optional
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import IdeaNode, ConceptCluster, Relationship, RelationshipType, ConflictInfo, ConflictType
from src.utils.logging_config import logger
import json
from uuid import uuid4


WEAVER_SYSTEM = """你是 Idea Weaving 系统中的 Weaver Agent（语义编织者）。
你接收一组想法节点，完成四项任务：

1. 语义聚类：基于共同主题、互补视角或结构相似性，分组为概念簇。
2. 关系发现：对相关节点对，判断关系类型（causal/contradicts/analogy/prerequisite/refines/generalizes/supports/transforms）和强度。
3. 跨域桥梁：识别来自不同领域但共享结构模式的节点对——创新潜力最高的连接。
4. 冲突检测：识别逻辑矛盾或创造性张力的节点对。

输出 JSON：
{
  "clusters": [{"name": "簇名", "description": "描述", "member_indices": [0,1,3]}],
  "relationships": [{"source_idx": 0, "target_idx": 1, "type": "causal", "strength": 0.8, "explanation": "说明"}],
  "cross_domain_bridges": [{"idx_a": 0, "idx_b": 5, "domain_a": "...", "domain_b": "...", "shared_structure": "..."}],
  "conflicts": [{"idx_a": 2, "idx_b": 3, "type": "contradiction", "description": "说明", "suggested_strategy": "flag_for_user"}]
}

重要：
- 不要强行连接不相关的想法
- 跨域连接质量优先于数量
- 冲突是创造性张力，不是坏事
- member_indices / source_idx 等均为 nodes 数组中的索引 (0-based)"""


class WeaverAgent:
    """语义编织——最核心的 Agent"""

    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(
            llm=llm,
            model="",  # 从 settings 读取
            temperature=0.7,
            max_tokens=6000,
        )

    async def weave(self, nodes: List[IdeaNode], north_star: str,
                    feedback: Optional[dict] = None,
                    max_input_tokens: int = 8000) -> dict:
        """执行编织（含 Token 截断保护）"""

        # Token 截断保护（DESIGN.md 第 16 章补充-5）
        nodes_dicts = [self._node_to_dict(n) for n in nodes]
        rels_for_truncation = []  # 首轮无关系，后续轮次来自 feedback
        from src.core.retrieval import TruncationPolicy
        nodes_dicts, _ = TruncationPolicy.truncate(
            nodes_dicts, rels_for_truncation, max_input_tokens,
        )

        # 构建节点列表文本（截断后）
        nodes_text = self._format_nodes_from_dicts(nodes_dicts)
        feedback_text = ""
        if feedback:
            feedback_text = (
                f"\n\n上一轮的 Critique 反馈：\n"
                f"{json.dumps(feedback, ensure_ascii=False, indent=2)}\n"
                f"请针对反馈中的 blocking_issues 修正。"
            )

        messages = [
            {"role": "system", "content": WEAVER_SYSTEM},
            {"role": "user", "content": f"北极星目标：{north_star}\n\n想法节点列表：\n{nodes_text}{feedback_text}\n\n请完成四项编织任务。"},
        ]

        data = await self.agent.call_llm_json(messages)

        if data.get("_parse_error"):
            logger.error(f"Weaver JSON parse failed")
            return {"clusters": [], "relationships": [], "cross_domain_bridges": [], "conflicts": []}

        logger.bind(component="weaver").info(
            f"Weave complete: {len(data.get('clusters',[]))} clusters, "
            f"{len(data.get('relationships',[]))} relationships"
        )
        return data

    def _format_nodes(self, nodes: List[IdeaNode]) -> str:
        lines = []
        for i, node in enumerate(nodes):
            content = node.standardized_content or node.raw_content
            tags = [t.value if hasattr(t, 'value') else str(t) for t in node.intent_tags]
            lines.append(
                f"[{i}] ID={node.id}\n"
                f"    内容: {content}\n"
                f"    意图: {', '.join(tags)}\n"
                f"    领域: {', '.join(node.context_tags)}\n"
            )
        return "\n".join(lines)

    @staticmethod
    def _node_to_dict(node: IdeaNode) -> dict:
        return {
            "id": str(node.id),
            "standardized_content": node.standardized_content or "",
            "raw_content": node.raw_content,
            "intent_tags": [t.value if hasattr(t, 'value') else t for t in node.intent_tags],
            "context_tags": node.context_tags,
            "relevance_score": node.north_star_relevance,
        }

    @staticmethod
    def _format_nodes_from_dicts(nodes: List[dict]) -> str:
        lines = []
        for i, n in enumerate(nodes):
            content = n.get("standardized_content") or n.get("raw_content", "")
            lines.append(
                f"[{i}] {n.get('id','?')[:8]}\n"
                f"    内容: {content}\n"
                f"    领域: {', '.join(n.get('context_tags', []))}\n"
            )
        return "\n".join(lines)

    @staticmethod
    def build_clusters_from_result(data: dict, nodes: List[IdeaNode]) -> List[ConceptCluster]:
        """从 Weaver 输出构建 ConceptCluster 对象"""
        clusters = []
        for item in data.get("clusters", []):
            indices = item.get("member_indices", [])
            member_ids = [nodes[i].id for i in indices if 0 <= i < len(nodes)]
            if not member_ids:
                continue
            cluster = ConceptCluster(
                id=uuid4(),
                name=item.get("name", ""),
                description=item.get("description", ""),
                member_node_ids=member_ids,
                summary=item.get("description", "")[:300],
                cross_domain_count=len(set(
                    tuple(nodes[i].context_tags) for i in indices if 0 <= i < len(nodes)
                )),
            )
            clusters.append(cluster)
        return clusters

    @staticmethod
    def build_relationships(data: dict, nodes: List[IdeaNode]) -> List[Relationship]:
        """从 Weaver 输出构建 Relationship 对象"""
        rels = []
        valid_types = {rt.value for rt in RelationshipType}
        for item in data.get("relationships", []):
            si, ti = item.get("source_idx", -1), item.get("target_idx", -1)
            if si < 0 or si >= len(nodes) or ti < 0 or ti >= len(nodes):
                continue
            rtype = item.get("type", "supports")
            if isinstance(rtype, str):
                try:
                    rtype = RelationshipType(rtype)
                except ValueError:
                    rtype = RelationshipType.SUPPORTS
            rel = Relationship(
                id=uuid4(),
                source_node_id=nodes[si].id,
                target_node_id=nodes[ti].id,
                relationship_type=rtype,
                strength=item.get("strength", 0.5),
                explanation=item.get("explanation", ""),
            )
            rels.append(rel)
        return rels

    @staticmethod
    def build_conflicts(data: dict, nodes: List[IdeaNode]) -> List[ConflictInfo]:
        """从 Weaver 输出构建 ConflictInfo 对象"""
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
                id=uuid4(),
                node_a=nodes[ia].id,
                node_b=nodes[ib].id,
                conflict_type=ctype,
                description=item.get("description", ""),
                resolution_strategy=item.get("suggested_strategy", "flag_for_user"),
            ))
        return conflicts
