"""评分计算器 —— 创新度/自洽性/可行性"""

from src.core.models import ConceptCluster, DesignDocument


def compute_innovation(cluster: ConceptCluster, llm_surprise: float = 5.0) -> float:
    """计算创新度"""
    cross_domain_score = min(cluster.cross_domain_count / 5.0, 1.0)
    novelty_score = cluster.innovation_score  # Weaver 已计算
    surprise_score = llm_surprise / 10.0
    return (
        cross_domain_score * 0.30
        + novelty_score * 0.45
        + surprise_score * 0.25
    )


def compute_coherence(cluster: ConceptCluster) -> float:
    """计算自洽性"""
    conflict_penalty = min(len(cluster.conflicts) * 0.1, 0.5)
    return max(0.0, cluster.coherence_score - conflict_penalty)


def compute_feasibility(design: DesignDocument) -> float:
    """计算可行性"""
    content = design.content_markdown

    # 组件具体性：统计含括号技术名的组件数
    import re
    tech_mentions = len(re.findall(r'(?:PostgreSQL|Redis|Kafka|RabbitMQ|MySQL|MongoDB|Elasticsearch|'
                                     r'Nginx|Kubernetes|Docker|AWS|GCP|Azure|Prometheus|Grafana)', content))
    total_components = max(len(re.findall(r'^###\s', content, re.MULTILINE)), 1)
    specificity = min(tech_mentions / total_components, 1.0)

    # 接口完整度：统计含 "API" / "接口" / "协议" 的段落
    interface_mentions = len(re.findall(r'(?:API|接口|协议|endpoint|gRPC|REST|GraphQL)', content))
    interface_score = min(interface_mentions / max(total_components, 1), 1.0)

    return (
        specificity * 0.4
        + interface_score * 0.3
        + design.feasibility_score * 0.3
    )
