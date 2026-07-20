"""Prompt 加载器 —— 从 YAML 读取 + 运行时组装
DESIGN.md 第 9 章 + 第 16 章补充-4
"""

from pathlib import Path
from typing import List, Dict, Optional
import yaml

_PROMPT_DIR = Path(__file__).parent
_CACHE: Dict[str, dict] = {}


def _load_yaml(name: str) -> dict:
    if name not in _CACHE:
        path = _PROMPT_DIR / f"{name}.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _CACHE[name] = yaml.safe_load(f)
        else:
            _CACHE[name] = {}
    return _CACHE[name]


def get_system_prompt(agent: str) -> str:
    """获取 Agent 的 system prompt"""
    data = _load_yaml(agent)
    return data.get("system", "")


class PromptBuilder:
    """运行时组装 Prompt —— 替代硬编码在 Agent .py 中的字符串"""

    def __init__(self):
        self.skill_dir = Path("skills")

    def build_collector(self, user_input: str,
                        user_profile: Optional[dict] = None) -> List[Dict[str, str]]:
        data = _load_yaml("collector")
        messages = [{"role": "system", "content": data.get("system", "")}]
        if user_profile and user_profile.get("recurring_constraints"):
            constraints = "\n".join(f"- {c}" for c in user_profile["recurring_constraints"])
            messages.append({"role": "system", "content": f"用户历史约束偏好：\n{constraints}"})
        for shot in data.get("few_shots", [])[:2]:
            messages.append({"role": "user", "content": shot.get("input", "")})
            messages.append({"role": "assistant", "content": shot.get("output", "")})
        messages.append({"role": "user", "content": user_input})
        return messages

    def build_weaver(self, north_star: str, nodes_text: str,
                     feedback: Optional[dict] = None) -> List[Dict[str, str]]:
        data = _load_yaml("weaver")
        messages = [{"role": "system", "content": data.get("system", "")}]
        context = f"北极星目标：{north_star}\n\n想法节点列表：\n{nodes_text}"
        if feedback:
            import json
            context += f"\n\n上一轮 Critique 反馈：\n{json.dumps(feedback, ensure_ascii=False, indent=2)}"
        messages.append({"role": "user", "content": context})
        return messages

    def build_architect(self, north_star: str, context: str) -> List[Dict[str, str]]:
        data = _load_yaml("architect")
        return [
            {"role": "system", "content": data.get("system", "")},
            {"role": "user", "content": f"设计目标：{north_star}\n\n{context}\n\n请生成完整的设计文档。"},
        ]

    def build_critic(self, design_content: str,
                     requirements: str = "") -> List[Dict[str, str]]:
        data = _load_yaml("critic")
        context = f"设计文档：\n\n{design_content}"
        if requirements:
            context += f"\n\n原始需求：\n{requirements}"
        return [
            {"role": "system", "content": data.get("system", "")},
            {"role": "user", "content": f"{context}\n\n请评估。"},
        ]

    def build_inquisitor(self, north_star: str, nodes_text: str,
                         clusters_text: str) -> List[Dict[str, str]]:
        data = _load_yaml("inquisitor")
        return [
            {"role": "system", "content": data.get("system", "")},
            {"role": "user", "content": f"北极星：{north_star}\n\n想法：\n{nodes_text}\n\n概念簇：\n{clusters_text}"},
        ]

    def build_monitor(self, content: str, source: str) -> List[Dict[str, str]]:
        data = _load_yaml("monitor")
        return [
            {"role": "system", "content": data.get("system", "")},
            {"role": "user", "content": f"来源：{source}\n\n内容：{content[:3000]}"},
        ]
