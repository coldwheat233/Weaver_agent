"""Critical Mass Trigger (V3) —— 概念簇临界质量检测

当某个概念簇达到预设阈值时，自动触发设计提案。
"""

from typing import List, Optional
from datetime import datetime
from src.core.models import ConceptCluster, IdeaNode, WeaverSession, DesignDocument
from src.storage.database import get_async_session
from src.storage.session_repo import SessionRepo
from src.storage.idea_repo import IdeaRepo
from src.storage.design_repo import DesignRepo
from src.utils.logging_config import logger


class CriticalMassDetector:
    """检测概念簇是否达到临界质量"""

    # 阈值配置
    MIN_NODES = 5                    # 最少想法数
    MIN_CROSS_DOMAINS = 2            # 最少跨领域数
    MIN_INNOVATION_SCORE = 0.5       # 最低创新度
    MIN_TIMESPAN_HOURS = 1           # 最少时间跨度（小时）

    def __init__(self):
        self._triggered_clusters: set[str] = set()  # 已触发的簇（防重复）

    def should_trigger(self, cluster: ConceptCluster,
                       nodes: List[IdeaNode]) -> bool:
        """判定是否应该触发设计提案"""
        if str(cluster.id) in self._triggered_clusters:
            return False

        # 检查节点数
        if len(cluster.member_node_ids) < self.MIN_NODES:
            return False

        # 检查跨领域数
        if cluster.cross_domain_count < self.MIN_CROSS_DOMAINS:
            return False

        # 检查创新度
        if cluster.innovation_score < self.MIN_INNOVATION_SCORE:
            return False

        # 检查时间跨度（至少有新旧想法的混合）
        cluster_nodes = [n for n in nodes if n.id in cluster.member_node_ids]
        if cluster_nodes:
            times = [n.created_at for n in cluster_nodes if n.created_at]
            if times:
                timespan = (max(times) - min(times)).total_seconds() / 3600
                if timespan < self.MIN_TIMESPAN_HOURS:
                    return False

        return True

    def mark_triggered(self, cluster_id: str):
        self._triggered_clusters.add(cluster_id)

    def reset(self, cluster_id: str):
        self._triggered_clusters.discard(cluster_id)


class AutoProposalEngine:
    """自动提案引擎 —— 检测临界质量 → 触发编织 → 推送通知"""

    def __init__(self, detector: CriticalMassDetector | None = None):
        self.detector = detector or CriticalMassDetector()
        self._proposals: List[dict] = []  # 内存中的提案列表

    async def scan_and_propose(self) -> List[dict]:
        """扫描所有活跃簇，触发符合条件的自动提案"""
        async with await get_async_session() as db:
            from src.storage.cluster_repo import ClusterRepo
            cluster_repo = ClusterRepo(db)
            idea_repo = IdeaRepo(db)

            clusters = await cluster_repo.list_active()
            active_nodes = await idea_repo.list_active()

        new_proposals = []
        for cluster in clusters:
            if self.detector.should_trigger(cluster, active_nodes):
                proposal = await self._create_proposal(cluster, active_nodes)
                if proposal:
                    new_proposals.append(proposal)
                    self.detector.mark_triggered(str(cluster.id))

        self._proposals.extend(new_proposals)
        return new_proposals

    async def _create_proposal(self, cluster: ConceptCluster,
                               nodes: List[IdeaNode]) -> Optional[dict]:
        """为一个临界质量簇创建设计提案"""
        try:
            # 创建编织会话
            session = WeaverSession(
                north_star=f"[自动提案] {cluster.name}",
                divergence_degree=2,
            )
            session.input_idea_ids = cluster.member_node_ids

            async with await get_async_session() as db:
                session_repo = SessionRepo(db)
                await session_repo.create(session)

            # 触发编织
            from src.core.workflow import execute_weave_workflow
            result = await execute_weave_workflow(str(session.id))

            proposal = {
                "session_id": str(session.id),
                "cluster_name": cluster.name,
                "cluster_id": str(cluster.id),
                "node_count": len(cluster.member_node_ids),
                "cross_domains": cluster.cross_domain_count,
                "innovation_score": cluster.innovation_score,
                "status": result.get("status", "unknown"),
                "design_id": result.get("design_id"),
                "created_at": datetime.utcnow().isoformat(),
            }

            logger.bind(component="trigger").info(
                f"Auto-proposal created for cluster {cluster.name}"
            )
            return proposal

        except Exception as e:
            logger.error(f"Failed to create auto-proposal: {e}")
            return None

    async def get_proposals(self, limit: int = 20) -> List[dict]:
        return sorted(
            self._proposals,
            key=lambda p: p.get("created_at", ""),
            reverse=True,
        )[:limit]

    def get_pending_count(self) -> int:
        """待处理提案数"""
        return sum(1 for p in self._proposals if p.get("status") == "complete")


# 全局单例
auto_proposal_engine = AutoProposalEngine()
