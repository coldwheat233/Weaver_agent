"""NetworkX 图操作 —— 构建、查询、分析"""

from typing import List, Tuple
import networkx as nx
from src.core.models import IdeaNode, Relationship, ConceptCluster


class GraphOps:
    """想法关系图的操作封装"""

    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, nodes: List[IdeaNode], relationships: List[Relationship]):
        """从节点和关系构建有向图"""
        self.graph.clear()
        for node in nodes:
            self.graph.add_node(
                str(node.id),
                tags=node.intent_tags,
                domains=node.context_tags,
                relevance=node.north_star_relevance,
            )
        for rel in relationships:
            self.graph.add_edge(
                str(rel.source_node_id),
                str(rel.target_node_id),
                type=rel.relationship_type.value,
                strength=rel.strength,
            )

    def expand_neighbors(self, seed_ids: List[str], hops: int = 1) -> List[str]:
        """沿图扩展 K 跳邻居"""
        visited = set(seed_ids)
        frontier = set(seed_ids)
        for _ in range(hops):
            neighbors = set()
            for nid in frontier:
                if nid in self.graph:
                    neighbors.update(self.graph.successors(nid))
                    neighbors.update(self.graph.predecessors(nid))
            frontier = neighbors - visited
            visited.update(frontier)
        return list(visited)

    def betweenness_centrality(self) -> dict:
        """计算介数中心性——发现桥梁节点"""
        if self.graph.number_of_nodes() == 0:
            return {}
        return nx.betweenness_centrality(self.graph, weight="strength")

    def find_bridge_nodes(self, threshold: float = 0.1) -> List[str]:
        """找到高介数但不属于任何簇核心的节点"""
        bc = self.betweenness_centrality()
        return [nid for nid, score in bc.items() if score > threshold]

    def subgraph_for_nodes(self, node_ids: List[str]) -> "GraphOps":
        """提取子图"""
        sub = GraphOps()
        sub.graph = self.graph.subgraph([str(nid) for nid in node_ids]).copy()
        return sub

    def to_dict(self) -> dict:
        """导出为 D3.js 可消费的 JSON"""
        nodes = []
        for nid, data in self.graph.nodes(data=True):
            nodes.append({
                "id": nid,
                "tags": [str(t) for t in data.get("tags", [])],
                "domains": data.get("domains", []),
            })
        edges = []
        for src, dst, data in self.graph.edges(data=True):
            edges.append({
                "source": src,
                "target": dst,
                "type": data.get("type", ""),
                "strength": data.get("strength", 0.5),
            })
        return {"nodes": nodes, "edges": edges}

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()
