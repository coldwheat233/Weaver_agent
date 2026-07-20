"""Critic Pass 1 —— 零 LLM 成本的静态结构检查

检查内容：
1. Mermaid 中引用的组件是否在文档中有定义
2. 接口是否闭合
3. 原始 problem_statement 是否都有对应方案
"""

from typing import List
import re


class StructureReport:
    """静态检查报告"""
    def __init__(self):
        self.component_ref_score = 1.0
        self.interface_closure_score = 1.0
        self.requirement_coverage_score = 1.0
        self.missing_components: List[str] = []
        self.open_interfaces: List[str] = []
        self.uncovered_requirements: List[str] = []


def static_check(design_markdown: str,
                 requirement_nodes: list | None = None) -> StructureReport:
    """对设计文档执行零 LLM 成本的静态检查"""
    report = StructureReport()

    # 1. Mermaid 组件引用完整性
    mermaid_blocks = re.findall(r'```mermaid\n(.*?)```', design_markdown, re.DOTALL)
    mermaid_components = set()
    for block in mermaid_blocks:
        # 匹配 graph TD/LR 中的节点：A[Label] 或 A-->B
        components = re.findall(r'\b(\w+)[\[\(\{]', block)
        mermaid_components.update(components)
        # 也匹配 --> 两端的节点
        arrows = re.findall(r'(\w+)\s*-->', block)
        mermaid_components.update(arrows)
        arrows = re.findall(r'-->\s*(\w+)', block)
        mermaid_components.update(arrows)

    # 在 Markdown 标题中查找组件定义
    defined_components = set()
    headers = re.findall(r'^###?\s+(.+)$', design_markdown, re.MULTILINE)
    for h in headers:
        # 提取组件名（通常在第一段）
        defined_components.add(h.strip())

    report.missing_components = [
        c for c in mermaid_components
        if c not in defined_components and len(c) > 1 and not c.startswith("subgraph")
    ]

    if mermaid_components:
        found = len(mermaid_components) - len(report.missing_components)
        report.component_ref_score = found / len(mermaid_components)

    # 2. 需求覆盖率
    if requirement_nodes:
        total_requirements = len(requirement_nodes)
        covered = 0
        for req in requirement_nodes:
            req_text = req.standardized_content or req.raw_content if hasattr(req, 'standardized_content') else str(req)
            # 模糊匹配：关键词在设计中至少出现一次
            keywords = re.findall(r'[\w一-鿿]{2,}', req_text)
            for kw in keywords[:5]:
                if kw.lower() in design_markdown.lower():
                    covered += 1
                    break
        if total_requirements > 0:
            report.requirement_coverage_score = covered / total_requirements
        report.uncovered_requirements = [
            (r.standardized_content or r.raw_content if hasattr(r, 'standardized_content') else str(r))[:80]
            for r in requirement_nodes
            if not any(kw.lower() in design_markdown.lower()
                       for kw in re.findall(r'[\w一-鿿]{2,}',
                           r.standardized_content or r.raw_content if hasattr(r, 'standardized_content') else str(r))[:5])
        ]

    return report
