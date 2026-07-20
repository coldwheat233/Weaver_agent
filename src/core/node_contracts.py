"""节点级输入/输出契约 —— 第 17 章耦合分析解耦方案

每个 LangGraph 节点有精确的 Pydantic 输入/输出模型，
不再依赖全局 WeaverState TypedDict 的隐式字段约定。
"""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from src.core.models import (
    IntentTag,
    ConceptCluster,
    Relationship,
    ConflictInfo,
    DesignDocument,
    CriticFeedback,
)


# ═══════════════════════════════════════════
# collect_and_prepare 节点
# ═══════════════════════════════════════════

class IdeaNodeSummary(BaseModel):
    """工作流节点间的轻量级想法表示（不含 embedding）"""
    id: UUID
    source_type: str = "text"
    standardized_content: str = ""
    raw_content: str = ""
    intent_tags: List[str] = Field(default_factory=list)
    context_tags: List[str] = Field(default_factory=list)
    relevance_score: float = 0.5
    completeness_score: float = 0.5
    actionability_score: float = 0.5
    status: str = "active"


class CollectOutput(BaseModel):
    """collect_and_prepare 节点的输出"""
    new_nodes: List[IdeaNodeSummary] = Field(default_factory=list)
    all_relevant_nodes: List[IdeaNodeSummary] = Field(default_factory=list)
    status: str = "collected"


# ═══════════════════════════════════════════
# semantic_cluster 节点
# ═══════════════════════════════════════════

class ClusterInput(BaseModel):
    session_id: str
    north_star: str
    new_nodes: List[IdeaNodeSummary] = Field(default_factory=list)
    all_relevant_nodes: List[IdeaNodeSummary] = Field(default_factory=list)
    divergence_degree: int = 2


class ClusterOutput(BaseModel):
    clusters: List[dict] = Field(default_factory=list)    # ConceptCluster 的 dict 表示
    status: str = "clustered"


# ═══════════════════════════════════════════
# build_relationships 节点
# ═══════════════════════════════════════════

class RelationshipInput(BaseModel):
    session_id: str
    clusters: List[dict] = Field(default_factory=list)
    nodes: List[IdeaNodeSummary] = Field(default_factory=list)
    critic_feedback: Optional[dict] = None
    iteration: int = 1


class RelationshipOutput(BaseModel):
    relationships: List[dict] = Field(default_factory=list)
    cross_domain_bridges: List[dict] = Field(default_factory=list)
    conflicts: List[dict] = Field(default_factory=list)
    status: str = "relationships_built"


# ═══════════════════════════════════════════
# generate_design 节点
# ═══════════════════════════════════════════

class DesignInput(BaseModel):
    session_id: str
    north_star: str
    clusters: List[dict] = Field(default_factory=list)
    relationships: List[dict] = Field(default_factory=list)
    cross_domain_bridges: List[dict] = Field(default_factory=list)
    conflicts: List[dict] = Field(default_factory=list)


class DesignOutput(BaseModel):
    design_draft: dict = Field(default_factory=dict)
    status: str = "design_generated"


# ═══════════════════════════════════════════
# critique 节点
# ═══════════════════════════════════════════

class CritiqueInput(BaseModel):
    session_id: str
    design_draft: dict = Field(default_factory=dict)
    requirement_node_ids: List[UUID] = Field(default_factory=list)


class CritiqueOutput(BaseModel):
    critic_feedback: dict = Field(default_factory=dict)
    critic_scores: dict = Field(default_factory=dict)  # {coherence, innovation, feasibility}
    status: str = "critiqued"
