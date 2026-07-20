"""核心数据模型 —— 全部 Pydantic 实体定义

这是整个系统的基础层（被 18 个模块依赖）。
所有字段、枚举、关系在此集中定义，不可分散到其他文件。
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


# ═══════════════════════════════════════════
# 枚举
# ═══════════════════════════════════════════

class SourceType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"


class NodeStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    MERGED = "merged"
    ARCHIVED = "archived"


class RelationshipType(str, Enum):
    CAUSAL = "causal"           # A 导致 B
    CONTRADICTS = "contradicts"  # A 与 B 逻辑矛盾
    ANALOGY = "analogy"          # A 类比于 B
    PREREQUISITE = "prerequisite" # A 是 B 的前提
    REFINES = "refines"          # B 是 A 的具体化
    GENERALIZES = "generalizes"  # B 是 A 的泛化
    SUPPORTS = "supports"        # A 支撑 B
    TRANSFORMS = "transforms"    # A 变形为 B


class IntentTag(str, Enum):
    PROBLEM_STATEMENT = "problem_statement"
    SOLUTION_HYPOTHESIS = "solution_hypothesis"
    CONSTRAINT = "constraint"
    QUESTION = "question"
    OBSERVATION = "observation"
    ANALOGY = "analogy"
    GOAL = "goal"
    FEATURE_IDEA = "feature_idea"
    RISK = "risk"
    ASSUMPTION = "assumption"


class ConflictType(str, Enum):
    CONTRADICTION = "contradiction"
    TENSION = "tension"
    INCOMPATIBILITY = "incompatibility"
    MISUNDERSTANDING = "misunderstanding"


class ResolutionStrategy(str, Enum):
    FLAG_FOR_USER = "flag_for_user"
    PRESERVE_AS_TENSION = "preserve_as_tension"
    GENERATE_ALTERNATIVES = "generate_alternatives"
    MERGE_NODES = "merge_nodes"


class DesignType(str, Enum):
    ARCHITECTURE = "architecture"
    PRD = "prd"
    FLOW_DIAGRAM = "flow_diagram"
    TECHNICAL_SPEC = "technical_spec"


class SessionStatus(str, Enum):
    COLLECTING = "collecting"
    WEAVING = "weaving"
    ARCHITECTING = "architecting"
    CRITIQUING = "critiquing"
    COMPLETE = "complete"
    FAILED = "failed"


class ClusterStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class EmbeddingStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


DiscoveryMethod = Literal[
    "semantic_similarity", "llm_inferred", "structural_match", "user_specified"
]

ConflictClass = Literal["contradiction", "tension", "incompatibility", "misunderstanding"]


# ═══════════════════════════════════════════
# 核心实体
# ═══════════════════════════════════════════

class IdeaNode(BaseModel):
    """想法节点 —— 系统最基本的认知单元"""

    id: UUID = Field(default_factory=uuid4)
    source_type: SourceType = SourceType.TEXT
    raw_content: str = ""
    raw_asset_path: Optional[str] = None          # 相对路径
    standardized_content: Optional[str] = None    # LLM 精炼后的描述（用于 embedding）
    embedding: Optional[List[float]] = None       # 仅在 ChromaDB 中，Pydantic 序列化时排除
    embedding_status: EmbeddingStatus = EmbeddingStatus.PENDING

    intent_tags: List[IntentTag] = Field(default_factory=list)
    context_tags: List[str] = Field(default_factory=list)   # 领域关键词

    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    completeness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    actionability_score: float = Field(default=0.5, ge=0.0, le=1.0)

    status: NodeStatus = NodeStatus.ACTIVE
    merged_into: Optional[UUID] = None
    north_star_relevance: float = Field(default=0.5, ge=0.0, le=1.0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None

    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})


class Relationship(BaseModel):
    """有向的、带类型的关系边"""

    id: UUID = Field(default_factory=uuid4)
    source_node_id: UUID
    target_node_id: UUID
    relationship_type: RelationshipType
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    explanation: Optional[str] = None
    discovery_method: DiscoveryMethod = "llm_inferred"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})


class ConflictInfo(BaseModel):
    """两个想法节点之间的冲突"""

    id: UUID = Field(default_factory=uuid4)
    cluster_id: Optional[UUID] = None
    node_a: UUID
    node_b: UUID
    conflict_type: ConflictType = ConflictType.TENSION
    description: str = ""
    resolution_strategy: ResolutionStrategy = ResolutionStrategy.FLAG_FOR_USER
    resolved: bool = False

    model_config = ConfigDict(json_encoders={UUID: str})


class ConceptCluster(BaseModel):
    """一组相关想法形成的概念簇"""

    id: UUID = Field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    member_node_ids: List[UUID] = Field(default_factory=list)
    centroid_embedding: Optional[List[float]] = None
    summary: str = ""                              # 压缩版（放入上下文窗口）
    innovation_score: float = Field(default=0.5, ge=0.0, le=1.0)
    coherence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    conflicts: List[ConflictInfo] = Field(default_factory=list)
    cross_domain_count: int = 0
    status: ClusterStatus = ClusterStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})


class DesignDocument(BaseModel):
    """Architect 生成的结构化设计文档"""

    id: UUID = Field(default_factory=uuid4)
    title: str = ""
    type: DesignType = DesignType.ARCHITECTURE
    source_cluster_ids: List[UUID] = Field(default_factory=list)
    content_markdown: str = ""
    innovation_score: float = Field(default=0.5, ge=0.0, le=1.0)
    coherence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    feasibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    critic_approval: bool = False
    critic_feedback: Optional[str] = None
    version: int = 1
    parent_design_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})


class UserProfile(BaseModel):
    """学习到的用户偏好与思维模式"""

    id: int = 1  # 单例表
    frequent_domains: List[str] = Field(default_factory=list)
    preferred_output_formats: List[str] = Field(default_factory=lambda: ["architecture"])
    idea_transition_matrix: dict = Field(default_factory=dict)  # domain -> domain 计数
    recurring_constraints: List[str] = Field(default_factory=list)
    interaction_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})


class WeaverSession(BaseModel):
    """一次编织会话"""

    id: UUID = Field(default_factory=uuid4)
    north_star: str = ""
    divergence_degree: int = 2
    status: SessionStatus = SessionStatus.COLLECTING
    input_idea_ids: List[UUID] = Field(default_factory=list)
    output_design_id: Optional[UUID] = None
    errors: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})


# ═══════════════════════════════════════════
# Critic 反馈协议（第 16 章补充-3）
# ═══════════════════════════════════════════

class CriticScores(BaseModel):
    coherence: float = Field(default=0.5, ge=0.0, le=1.0)
    innovation: float = Field(default=0.5, ge=0.0, le=1.0)
    feasibility: float = Field(default=0.5, ge=0.0, le=1.0)


class BlockingIssue(BaseModel):
    severity: Literal["critical", "major"]
    category: str  # "missing_component" | "broken_interface" | "contradiction" | "uncovered_requirement"
    description: str
    affected_component: Optional[str] = None
    affected_requirement_id: Optional[UUID] = None
    suggestion: str


class Suggestion(BaseModel):
    severity: Literal["minor", "enhancement"]
    aspect: str  # "scalability" | "security" | "maintainability" | "cost" | "simplicity"
    suggestion: str


class CriticFeedback(BaseModel):
    """Critic -> Weaver 的结构化反馈"""
    approved: bool = False
    iteration: int = 1
    max_iterations: int = 3
    blocking_issues: List[BlockingIssue] = Field(default_factory=list)
    suggestions: List[Suggestion] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    conflict_resolutions: List[dict] = Field(default_factory=list)
    scores: CriticScores = Field(default_factory=CriticScores)


# ═══════════════════════════════════════════
# LangGraph 工作流状态（第 7 章）
# ═══════════════════════════════════════════

from typing import TypedDict as TypedDictType

class WeaverState(TypedDictType, total=False):
    """LangGraph 工作流的全局状态。

    注意：按照第 17 章耦合分析的解耦方案，WeaverState 已从
    14 个字段精简为 6 个顶层字段 + 1 个嵌套 phases dict。
    各节点的输入/输出由独立的 Pydantic 模型约束（见 node_contracts.py）。
    """
    session_id: str
    north_star: str
    iteration: int
    max_iterations: int
    status: str
    errors: List[str]
    phases: dict  # {"collect": {...}, "cluster": {...}, "design": {...}, ...}
