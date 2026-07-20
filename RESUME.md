# Idea Weaver — AI 想法编织工具

> **GitHub**: https://github.com/coldwheat233/Weaver_agent  
> **一句话**: 将碎片化想法自动转化为结构化工程设计文档的 AI 桌面应用

## 技术栈

`Python` `FastAPI` `Tauri 2` `React 18` `Rust` `TypeScript` `SQLite` `DeepSeek API` `PyInstaller` `GitHub Actions`

## 项目亮点

- **自研四 Agent 流水线**: Collector(标准化) → Weaver(语义聚类+关系发现+冲突检测) → Architect(生成含Mermaid架构图的设计文档) → Critic(闭环评分+反馈迭代), 7 次 LLM 调用串行编排, 不依赖 LangChain 等框架
- **Tauri 2 + React 桌面壳**: Rust 原生窗口 (~5MB) + WebView2 渲染, 真圆角无边框设计, 全局热键 (Win32 RegisterHotKey), 系统托盘, 白/灰/青设计令牌系统
- **多供应商 LLM 配置器**: 用户级运行时配置 (~/.weaver/config.json), 支持 DeepSeek / OpenAI / Ollama / 自定义 OpenAI 兼容, 保存后热生效无需重启, API Key 脱敏返回
- **OpenAI 兼容协议抽象**: `LLMService` ABC → `OpenAICompatibleService` 统一接口, httpx 直连不依赖 litellm/litechain 等第三方, 任意兼容 API 即可替换
- **双运行时打包**: PyInstaller 将 Python 后端打包为 41.6MB sidecar, Tauri NSIS 打包为 44MB 安装器, 用户双击即可使用无需安装 Python/Node/Rust
- **V2 交互追问**: Inquisitor Agent 分析想法缺口, 自动生成追问 (如 "缓存一致性最大容忍延迟是多少?"), 浮窗内快速回复形成多轮细化
- **V3 自治演进**: 外部数据源监听 (RSS/Webhook), 概念簇临界质量检测, 自动触发设计提案
- **白/灰/青轻质美学**: DESIGN.md 5420 行设计文档, CSS Design Tokens 全局统一, 弹簧动画+毛玻璃效果+圆角无边框

## 架构设计

```
用户想法 → Ctrl+Alt+[ 浮窗 → Collector标准化 → Weaver编织
                                                    ↓
设计文档 ← 浏览器渲染 ← Architect生成 ← Critic评分反馈
                         ↑
                   V2 Inquisitor追问 ──→ 多轮细化
                   V3 Monitor监听 ──→ 自治提案
```

**分层**:
- **表示层** (Tauri 2 / React / TypeScript): 捕获浮窗, 用户后台, 模型配置器
- **应用层** (FastAPI / Python): 路由编排, Agent 流水线, V2/V3 业务逻辑
- **领域层** (四 Agent + 14 个 Pydantic 实体): Collector, Weaver(4 子组件), Architect, Critic, Inquisitor, Monitor
- **基础设施层**: SQLite + ChromaDB, 文件存储, LLM 服务抽象, 检索器 (HybridRetriever + Token 截断)

**关键设计决策**:
| 决策 | 为什么 |
|---|---|
| Agent 串行编排而非 LangGraph | 稳定优先——生产路径直接调用 Agent, LangGraph 仅作为可选扩展 |
| DeepSeek 直连而非 litellm | 减少依赖故障面, httpx 3 行代码完成调用 |
| Tauri 而非 Electron | 5MB vs 200MB, 系统 WebView2, 真原生窗口 |
| 用户级配置而非 .env | 打包后程序目录不可写, ~/.weaver/ 统一管理 |
| Node Registry 解耦 | Agent 自注册工作流节点, workflow.py 零 import Agent |

## 量化成果

- **代码**: 110+ 源文件, Python + Rust + TypeScript 混合架构
- **测试**: 21 个单元/集成/E2E 测试, 全通过
- **设计文档**: 5420 行 DESIGN.md + 484 行 TRACEABILITY.md 设计→代码对照
- **打包体积**: 安装器 44MB (含 Python 运行时)
- **API 延迟**: Collector 2.5s / Weaver 1.4s / Architect 18s / Critic 4.5s (DeepSeek V4)

## 自我介绍 (简历话术)

> "独立设计并实现了一款 AI 驱动的想法编织工具, 可将碎片化灵感自动转化为包含架构图、组件详规和权衡分析的结构化设计文档。项目采用四 Agent 串行流水线架构 (Collector→Weaver→Architect→Critic), 使用 Python/FastAPI 构建后端, Tauri 2/React 构建桌面壳, Rust 实现全局热键和系统托盘。LLM 调用层通过自定义 OpenAI 兼容协议抽象, 不依赖第三方框架, 支持 DeepSeek/OpenAI/Ollama 运行时切换。实现 V2 交互追问和 V3 自治演进功能, 并通过 PyInstaller + NSIS 打包为 44MB 独立安装器。"
