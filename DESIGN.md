# Idea Weaving Agent — 设计文档

> 将零散想法转化为结构化工程设计的智能助手
>
> **快捷键唤起 | 多模态输入 | Python 实现 | Windows 11**

---

## 目录

1. [项目概述](#1-项目概述)
2. [原设计评审](#2-原设计评审)
3. [10 个关键问题的回答](#3-10-个关键问题的回答)
4. [技术栈选型](#4-技术栈选型)
5. [数据模型](#5-数据模型)
6. [系统架构](#6-系统架构)
7. [LangGraph 工作流](#7-langgraph-工作流)
8. [API 契约](#8-api-契约)
9. [Prompt 架构](#9-prompt-架构)
10. [UI 设计](#10-ui-设计)
11. [文件结构](#11-文件结构)
12. [实施计划](#12-实施计划)
13. [验证策略](#13-验证策略)
14. [风险评估](#14-风险评估)
15. [决策记录](#15-决策记录)
16. [设计补充：8 项不足的工程级方案](#16-设计补充针对-22-节-8-项不足的工程级方案)
17. [模块耦合度分析](#17-模块耦合度分析)
18. [部署方案：Docker 一键部署 & 阿里云 FC](#18-部署方案docker-一键部署--阿里云-fc-serverless)
19. [FC 部署对已设计结构的冲击逐文件分析](#19-fc-部署对已设计结构的冲击逐文件分析)

---

## 1. 项目概述

### 1.1 核心目标

构建一个"想法编织 Agent"——将碎片化、非结构化的想法（文字、图片、语音）转化为结构化工程设计文档（系统架构图、PRD、流程图）。

### 1.2 产品形态

| 维度 | 方案 |
|---|---|
| 唤起方式 | 全局快捷键 `Ctrl+Alt+I` |
| 输入 | 文字输入 / 剪贴板粘贴图片 / 麦克风录音 |
| UI 风格 | 极简浮窗（500×400），Windows 11 亚克力模糊，类似 uTools/Raycast |
| 输出 | 自包含 HTML（Mermaid 架构图 + D3.js 交互概念图 + 渐进式文档） |
| 运行方式 | 系统托盘常驻后台 |

### 1.3 演化路线

- **V1（被动响应）**：用户输入一堆想法 → Agent 一次性总结、归类、输出静态设计文档
- **V2（交互式编织）**：Agent 主动提问，多轮细化，版本回滚与差异对比
- **V3（自治式演进）**：持续监听外部数据源，概念簇达临界质量时主动推送设计提案

---

## 2. 原设计评审

### 2.1 优点

| 设计点 | 评价 |
|---|---|
| 四 Agent 流水线（Collector→Weaver→Architect→Critic） | ✅ 映射认知过程（发散→收敛），职责边界清晰，与 ETL 流水线模式一致 |
| 状态外置为文件系统 | ✅ 支持崩溃恢复、跨天续跑、人工审查、版本控制 |
| 闭环 Think→Act→Observe | ✅ Critic→Weaver 反馈形成迭代精炼，而非单次通过 |
| 动态技能注入（Markdown 说明书） | ✅ 轻量、低仪式感、非程序员可贡献领域知识 |
| V1→V2→V3 渐进演化 | ✅ 每一步有清晰边界，不过度设计也不欠设计 |

### 2.2 不足与缺失

| 问题 | 严重度 | 说明 |
|---|---|---|
| 无具体数据模型 | 🔴 高 | "想法节点""概念簇"只有名字，没有 Schema、字段、关系 |
| 10 个探索性问题未答 | 🔴 高 | 信噪比过滤、冲突消解、多模态编码等全部悬空 |
| Critic Agent 欠定义 | 🔴 高 | "逻辑自洽"只是标签——没有输出格式、评分标准、反馈路由机制 |
| 无 Prompt 工程策略 | 🟡 中 | 多 Agent LLM 系统的核心是 Prompt，但完全没涉及 System Message / Few-shot / 输出格式 |
| Token 窗口管理空泛 | 🟡 中 | "上下文压缩"没有具体策略、预算分配、检索层级 |
| UI 层完全缺失 | 🔴 高 | 快捷键浮窗决定了进程模型、通信协议、资产处理——是架构级约束 |
| 无并发模型 | 🟡 中 | "持续状态演化"但没说谁写、何时锁、编织中新提交怎么排队 |
| 无可观测性 | 🟡 中 | 进度在哪看、失败了为什么、两个想法为什么被关联——全部黑盒 |

---

## 3. 10 个关键问题的回答

### Q1: 如何过滤低信噪比的碎片化信息？

**三层过滤，在采集时即完成：**

```
┌─────────────────────────────────────────────────┐
│ L1: 启发式规则（零 LLM 成本）                      │
│   · 最小字符数 > 15                                │
│   · 与已有节点余弦相似度 > 0.92 → 标记合并，不丢弃     │
├─────────────────────────────────────────────────┤
│ L2: LLM 三轴评分（单次廉价调用）                     │
│   · relevance_score:   与已知领域的相关度            │
│   · completeness_score: 想法的完整程度               │
│   · actionability_score: 可操作性                   │
│   · 综合 < 0.3 → 标记 dormant，排除在编织之外        │
├─────────────────────────────────────────────────┤
│ L3: 用户反馈训练（积累后生效）                       │
│   · 结果页有 "✓ 有用" / "✗ 噪音" 按钮              │
│   · 标签训练轻量逻辑回归分类器（基于 embedding）       │
│   · 模型越用越准，预过滤后续输入                      │
└─────────────────────────────────────────────────┘
```

### Q2: 如何平衡用户意图约束与发散探索？

**北极星锚定机制：**

- 每场编织会话设定 `north_star`（用户明确目标）
- Weaver 探索距北极星 **N 度关联**（默认 N=2，可配置）
  - 0 度 = 直接相关
  - 1 度 = 一跳关联
  - 2 度 = 两跳关联
- N 度之外的关联 → 记录但放入"🫧 探索分支"折叠区
- 用户可通过 UI 滑块实时调整 N，或手动将探索分支提升到主编织

### Q3: 如何发现表面上不相关的隐性连接？

**四种互补机制：**

| 机制 | 原理 |
|---|---|
| **多向量编码** | 每个节点生成 3 个向量：语义向量（什么意思）+ 结构向量（什么角色：问题/方案/约束/类比）+ 上下文向量（领域标签/情感）。跨空间查询找到"不同领域+相同结构"的节点对 |
| **类比生成 Prompt** | 显式指令："给定领域 X 中有结构 S 的想法 A，在领域 Y 中找到或生成同构结构" |
| **强制偶遇采样** | 随机配对低语义相似度 + 匹配结构角色的节点，抛给 LLM："找到合理但非显而易见的连接" |
| **图介数中心性** | 构建关系图后计算介数中心性——高介数但不属于任何簇的节点是"桥梁想法"，连接原本隔离的区域 |

### Q4: 想法冲突时如何处理？

**先分类，再行动：**

| 冲突类型 | 检测方式 | 处理策略 |
|---|---|---|
| **矛盾**（A 断言 X，B 断言非X） | LLM 逻辑分析 + 图中有 `contradicts` 边 | 🔴 标记用户，双方呈现证据，**不自动消解** |
| **张力**（如"简洁"vs"完整"——可共存但对冲） | 不同维度上 `refines` + `contradicts` 并存 | 🟡 保留为"创造性张力"，在设计文档中列为**多维度权衡表** |
| **不兼容**（A 和 B 不能在同一设计中共存） | Architect 无法生成同时包含二者的自洽结构 | 🟠 生成分支方案：Design-A / Design-B / Hybrid-C，用户选择 |
| **误解**（A 和 B 说的是同一件事） | 高语义相似度 + 低结构相似度 | 🟢 合并为一个澄清节点，原始表述作为注释保留 |

### Q5: Token 窗口有限，如何压缩"想法状态"？

**五级渐进式信息披露：**

```
Level 0  ▓▓ 北极星 + 会话目标                       ~100 tokens    始终在上下文中
Level 1  ▓▓ 所有簇的压缩摘要（每簇 1 段）              ~200×5=1000   按需展开
Level 2  ▓▓ Top-K 相关节点（向量检索，含标准化内容）    ~300×10=3000  相似度排序
Level 3  ▓▓ 这些节点的关系子图（邻接表形式）            ~500          结构上下文
Level 4  ▓▓ 上一轮 Critic 反馈                        ~200          迭代记忆
─────────────────────────────────────────────────────────────────────
总计     ▓▓ ~5000 tokens 状态，留 6000-11000 给 Prompt + 输出
```

**压缩层级：**
- 想法节点 → `node_summary`（1-2 句）
- 多个节点 → `cluster_summary`（1 段）
- 多个簇 → `meta_cluster_summary`
- 编织时按需加载对应层级

### Q6: 如何防止新想法"淹没"长期目标？

**三管齐下：**

1. **目标锚定**：长期目标存独立 `goals` 表（`persistence: permanent`），每场会话全量注入上下文（体积极小）
2. **衰减加权检索，不删除**：旧想法余弦相似度 × 时间衰减因子 → 排名靠后但不消失。提供"恢复休眠想法"搜索
3. **定期合并**：每 N 个新想法触发后台合并——去重近重复簇、清理用户明确驳回的节点、重新生成簇摘要。由系统提议、用户确认

### Q7: 能否学习用户思维模式并预判？

**可以，但保守且本地化：**

- 存储 `UserProfile`：
  - `frequent_domains`：高频探索领域
  - `preferred_output_formats`：偏好的输出类型
  - `idea_transition_matrix`：领域→领域的 Markov 转移计数
  - `recurring_constraints`：重复出现的约束条件
- **输入补全**：用户输入时提示"基于你之前对微服务模式的探索，你可能还想考虑：熔断器设计"
- 存为 `data/user_profile.yaml`，可检查/编辑/删除，**永不出本地**

### Q8: 多模态输入如何统一编码？

**流水线汇聚，而非统一嵌入：**

```
┌─────────┐
│  图片    │ → Vision LLM (Claude Sonnet) → 结构化描述
│PNG/JPG  │    { type, description, extracted_elements, mermaid_representation }
└─────────┘
┌─────────┐
│  语音    │ → openai-whisper (本地) → 转录文本 + 元数据
│WAV/MP3  │    { transcript, speaker_emotion, confidence }
└─────────┘
┌─────────┐
│  文字    │ → 原样保留
└─────────┘
         ↓
┌─────────────────────────────────────────────────┐
│ 统一为 IdeaNode                                   │
│   · source_type: "text" | "image" | "voice"      │
│   · standardized_content: 统一文本（用于 embedding） │
│   · raw_asset_path: 原始文件路径（永不丢失）         │
│   · source_metadata: 模态特有字段                   │
└─────────────────────────────────────────────────┘
```

关键：所有模态最终进入**同一文本嵌入空间**。图片产生的"分布式任务队列"和语音产生的"作业调度模式"会有相似的 embedding，自动聚类。

### Q9: 如何量化评估"创新度 / 自洽性 / 可行性"？

**多维度评分，编织后自动计算：**

| 指标 | 子维度 | 计算方式 |
|---|---|---|
| **创新度** | 新颖率 | 簇内节点嵌入的平均两两余弦距离（越高=来源越多样），以同领域簇为基线归一化 |
| | 跨领域数 | 簇内不同领域的数量。>3 = 高创新 |
| | 惊讶商数 | LLM 评估："这些连接的意外/惊喜程度 1-10"，归一化 |
| **自洽性** | 图密度 | 边数 / 可能边数。过稀=不连贯，过密=琐碎 |
| | 矛盾数 | 检测到的矛盾数取反归一化 |
| | 一致性三问 | LLM 以不同温度跑 3 次找逻辑漏洞，严重度均值取反 |
| **可行性** | 组件具体性 | "PostgreSQL with read replicas" 而非 "某种数据库" 的组件占比 |
| | 接口完整度 | 已定义接口的组件间交互占比 |
| | 可实施路径 | LLM 评估："合格工程师能否在合理时间内实现？1-10" |

三项评分以**雷达图**展示在结果页。

### Q10: 如何直观呈现复杂创意架构？

**三种自动生成的呈现模式：**

1. **Mermaid.js 图表（嵌入 Markdown）**
   - `graph TD` 架构图
   - `sequenceDiagram` 时序图
   - `erDiagram` 实体关系图
   - `mindmap` 思维导图
   - 文本即图表、diff 友好、任何浏览器渲染

2. **D3.js 力导向交互图**
   - 节点 = 想法（大小 = 相关性，颜色 = 领域）
   - 凸包 = 概念簇
   - 边 = 关系（实线 = 因果，虚线 = 类比，红色 = 冲突）
   - 点击展开详情，拖拽重排，按领域/时间/相关性过滤

3. **渐进式文档**
   - L1 折叠 → 执行摘要（1 段）
   - L2 展开 → 架构概览（图 + 组件列表）
   - L3 展开 → 组件详规
   - L4 展开 → 原始想法溯源（哪个输入产生了这个组件）

所有输出为**自包含 HTML**（无需服务器）或带 Mermaid 的 Markdown（可 GitHub 渲染）。

---

## 4. 技术栈选型

| 组件 | 选型 | 版本 | 为什么 |
|---|---|---|---|
| 语言 | Python | 3.11+ | Windows 生态成熟 |
| Web 框架 | FastAPI | 0.111+ | 原生 async、WebSocket 内置、自动 OpenAPI 文档、Pydantic 集成 |
| ASGI | uvicorn | 0.30+ | FastAPI 标准搭配 |
| Agent 编排 | **LangGraph** | 0.2+ | 有状态图工作流、SQLite checkpoint 内置、条件边、可视化 |
| LLM 抽象 | **LiteLLM** | 1.40+ | 提供商无关（Claude/GPT/本地），成本追踪，内置重试 |
| 结构化存储 | SQLAlchemy + aiosqlite | 2.0+ | 异步 SQLite ORM，单文件零配置 |
| 向量存储 | **ChromaDB** | 0.5+ | 本地进程内运行，零网络依赖，免费 |
| Embedding | OpenAI `text-embedding-3-small` | — | 1536d，$0.02/1M tokens 或 Voyage `voyage-3-lite` 1024d |
| 图分析 | NetworkX | 3.3+ | 事实标准 |
| 语音转写 | **openai-whisper** (本地) | 20231117 | 离线、隐私、零 API 费用 |
| 图片理解 | Claude Sonnet (via LiteLLM) | — | 当前最强视觉能力 |
| 桌面壳 | **Tauri 2 + React 18** | 2.x | Rust 原生壳 (~5MB), WebView2 渲染, 真圆角/GPU/毛玻璃 |
| 前端 UI | React 18 + Vite + TypeScript | — | 组件化, DESIGN.md CSS 令牌直出 |
| 全局热键 | Tauri Rust (RegisterHotKey) | — | Ctrl+Alt+[ 输入 / Ctrl+Alt+] 后台 |
| 系统托盘 | Tauri tray-icon 内置 | — | 左键→后台, 右键→菜单 |
| HTTP 客户端 | httpx | 0.27+ | 异步 HTTP |
| 数据校验 | Pydantic | 2.7+ | 模型校验、序列化 |
| 配置管理 | python-dotenv + PyYAML | — | .env 密钥、YAML Prompt |
| 日志 | loguru | 0.7+ | 结构化、彩色、简洁 |
| 打包 | PyInstaller | 6.5+ | 单 .exe 分发 |
| 图表 | Mermaid.js + D3.js v7 | — | 浏览器内渲染 |

### 未选用方案及原因

| 未选用 | 为什么不用 |
|---|---|
| CrewAI / AutoGen | 高层抽象，不够灵活——LangGraph 给我们精确的状态机控制 |
| Pinecone / Weaviate | 云托管 = 延迟 + 费用 + 网络依赖。ChromaDB 本地进程内，单用户桌面工具首选 |
| Electron | 一个 500×400 浮窗不需要 200MB+ 的 Chromium。WebView2 系统自带 |
| LangChain | 高层抽象难以调试。只用它的 `RecursiveCharacterTextSplitter`，编排交给 LangGraph |
| Flask | 不支持原生 async，没有 WebSocket，没有自动文档 |
| 直接 Anthropic SDK | 锁定供应商。LiteLLM 一行配置切换 Claude/GPT/本地模型 |

---

## 5. 数据模型

### 5.1 IdeaNode（想法节点）

```python
class SourceType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"

class NodeStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    MERGED = "merged"
    ARCHIVED = "archived"

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

class IdeaNode(BaseModel):
    id: UUID
    source_type: SourceType
    raw_content: str                          # 原始文本或语音转写
    raw_asset_path: Optional[str] = None      # 图片/音频文件路径
    standardized_content: Optional[str] = None # LLM 精炼后的描述（用于 embedding）
    embedding: Optional[List[float]] = None   # 向量
    intent_tags: List[IntentTag] = []         # 意图标签
    context_tags: List[str] = []              # 领域关键词
    relevance_score: float = 0.5              # 0-1
    completeness_score: float = 0.5           # 0-1
    actionability_score: float = 0.5          # 0-1
    status: NodeStatus = ACTIVE
    merged_into: Optional[UUID] = None
    north_star_relevance: float = 0.5         # 与当前北极星的相关度
    created_at: datetime
    updated_at: datetime
    session_id: Optional[str] = None
```

### 5.2 Relationship（关系边）

```python
class RelationshipType(str, Enum):
    CAUSAL = "causal"           # A 导致 B
    CONTRADICTS = "contradicts"  # A 与 B 逻辑矛盾
    ANALOGY = "analogy"          # A 类比于 B
    PREREQUISITE = "prerequisite" # A 是 B 的前提
    REFINES = "refines"          # B 是 A 的具体化
    GENERALIZES = "generalizes"  # B 是 A 的泛化
    SUPPORTS = "supports"        # A 支撑 B
    TRANSFORMS = "transforms"    # A 变形为 B

class Relationship(BaseModel):
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    relationship_type: RelationshipType
    strength: float = 0.5            # 0-1
    explanation: Optional[str] = None # LLM 生成的解释
    discovery_method: Literal["semantic_similarity", "llm_inferred",
                               "structural_match", "user_specified"] = "llm_inferred"
    created_at: datetime
```

### 5.3 ConflictInfo（冲突信息）

```python
class ConflictInfo(BaseModel):
    node_a: UUID
    node_b: UUID
    conflict_type: Literal["contradiction", "tension", "incompatibility", "misunderstanding"]
    description: str
    resolution_strategy: Literal["flag_for_user", "preserve_as_tension",
                                  "generate_alternatives", "merge_nodes"]
    resolved: bool = False
```

### 5.4 ConceptCluster（概念簇）

```python
class ConceptCluster(BaseModel):
    id: UUID
    name: str                                 # 人读标签
    description: str                          # 合成摘要
    member_node_ids: List[UUID] = []          # 成员节点
    centroid_embedding: Optional[List[float]] = None
    summary: str                              # 压缩版（放入上下文窗口）
    innovation_score: float = 0.5             # 0-1
    coherence_score: float = 0.5              # 0-1
    conflicts: List[ConflictInfo] = []
    cross_domain_count: int = 0
    status: Literal["active", "resolved", "archived"] = "active"
    created_at: datetime
    updated_at: datetime
```

### 5.5 DesignDocument（设计文档）

```python
class DesignDocument(BaseModel):
    id: UUID
    title: str
    type: Literal["architecture", "prd", "flow_diagram", "technical_spec"]
    source_cluster_ids: List[UUID] = []
    content_markdown: str                     # 完整 Markdown（含 Mermaid 图表）
    innovation_score: float = 0.5
    coherence_score: float = 0.5
    feasibility_score: float = 0.5
    critic_approval: bool = False
    critic_feedback: Optional[str] = None
    version: int = 1
    parent_design_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
```

### 5.6 UserProfile（用户画像）

```python
class UserProfile(BaseModel):
    frequent_domains: List[str] = []
    preferred_output_formats: List[str] = ["architecture"]
    idea_transition_matrix: dict = {}         # domain → domain 计数的 Markov 链
    recurring_constraints: List[str] = []
    interaction_count: int = 0
    last_updated: datetime
```

### 5.7 WeaverSession（编织会话）

```python
class WeaverSession(BaseModel):
    id: UUID
    north_star: str                           # 用户明确目标
    divergence_degree: int = 2                # 探索度数
    status: Literal["collecting", "weaving", "architecting",
                     "critiquing", "complete", "failed"] = "collecting"
    input_idea_ids: List[UUID] = []
    output_design_id: Optional[UUID] = None
    errors: List[str] = []
    started_at: datetime
    completed_at: Optional[datetime] = None
```

### 5.8 实体关系图

```
UserProfile (1) ──────────────────────────────────────────
     │                                                     │
     │ learns from                                         │
     ▼                                                     │
WeaverSession (N) ─── contains ─── IdeaNode (N)            │
     │                               │                     │
     │ produces                      │ related via          │
     ▼                               ▼                     │
DesignDocument (N) ◀── from ─── ConceptCluster (N) ◀── Relationship (N)
     │                               │
     │ references                    │ contains
     └───────────────────────────────┘
                                  ConflictInfo (N)
```

---

## 6. 系统架构

### 6.1 整体架构图

```
┌──────────────────────────────────────────────────────────────┐
│                    WINDOWS 11 DESKTOP                         │
│                                                               │
│  ┌──────────────┐      Global Hotkey (Ctrl+Alt+I)            │
│  │ System Tray  │◄────────────────────────────────┐          │
│  │  (pystray)   │                                 │          │
│  └──────┬───────┘                          ┌──────┴──────┐  │
│         │ shows/hides                       │  Keyboard   │  │
│         ▼                                   │  Listener   │  │
│  ┌──────────────┐                           │  (pynput)   │  │
│  │   Overlay    │                           └─────────────┘  │
│  │  (pywebview  │                                             │
│  │  + WebView2) │                                             │
│  │              │                                             │
│  │ [Text Area]  │                                             │
│  │ [Paste Img]  │                                             │
│  │ [Record Mic] │                                             │
│  └──────┬───────┘                                             │
│         │ POST /api/ideas (localhost:8765)                    │
└─────────┼─────────────────────────────────────────────────────┘
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                     FASTAPI SERVER (localhost:8765)            │
│                                                                │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐  │
│  │Collector │──▶│ Weaver   │──▶│ Architect │──▶│  Critic  │  │
│  │  Agent   │   │  Agent   │   │   Agent   │   │  Agent   │  │
│  └────┬─────┘   └────┬─────┘   └─────┬─────┘   └────┬─────┘  │
│       │               │               │              │        │
│       │          ┌────▼────┐          │              │        │
│       │          │LangGraph│◄─────────┘   feedback   │        │
│       │          │Workflow │─────────────────────────┘        │
│       │          └────┬────┘                                  │
│       │               │                                       │
│  ┌────▼───────────────▼──────────────┐                        │
│  │          STORAGE LAYER            │                        │
│  │  ┌─────────┐  ┌──────────────┐   │                        │
│  │  │ SQLite  │  │   ChromaDB   │   │                        │
│  │  │(struct) │  │  (vectors)   │   │                        │
│  │  └─────────┘  └──────────────┘   │                        │
│  │  ┌────────────────────────────┐  │                        │
│  │  │ Filesystem (assets/exports)│  │                        │
│  │  └────────────────────────────┘  │                        │
│  └──────────────────────────────────┘                        │
│                                                                │
│  ┌──────────────────────────────────┐                         │
│  │  LiteLLM (LLM Provider Layer)    │                         │
│  │  → Claude, GPT-4o, local models  │                         │
│  └──────────────────────────────────┘                         │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 并发模型

```
┌───────────────────────────────────────┐
│            MAIN THREAD                 │
│  · System tray (pystray)               │
│  · Global hotkey listener (pynput)     │
│  · pywebview window management         │
│  · FastAPI server (daemon thread)      │
└──────────────┬────────────────────────┘
               │ dispatches to
┌──────────────▼────────────────────────┐
│        PROCESSING THREAD               │
│  · Single-threaded state mutation queue│
│  · LangGraph workflow executor         │
│  · All agent runs are sequential       │
│  · Async LLM calls via asyncio loop    │
└──────────────┬────────────────────────┘
               │ writes to
┌──────────────▼────────────────────────┐
│     STORAGE (SQLite + ChromaDB)        │
│  · SQLite built-in write serialization │
│  · ChromaDB document-level locking     │
│  · No concurrent writes possible       │
└────────────────────────────────────────┘
```

**编织期间收到新想法**：排队，当前编织完成后处理。浮窗提示"编织中——你的想法将在下一轮处理"。

### 6.3 可观测性

| 层面 | 机制 |
|---|---|
| 进度 | WebSocket 推送编织阶段变化（collecting → clustering → building_relations → designing → critiquing） |
| 流式 | 簇形成时即推送摘要，不等全部完成 |
| 错误 | loguru 结构化日志 + 会话 `errors` 字段 + 浮窗 toast 通知 |
| 追溯 | 每条 Relationship 有 `discovery_method` 和 `explanation`——为什么这两个想法被关联 |

---

## 7. LangGraph 工作流

### 7.1 状态定义

```python
from typing import TypedDict, List, Optional

class WeaverState(TypedDict):
    session_id: str
    north_star: str
    divergence_degree: int
    new_nodes: List[dict]              # 待编织的 IdeaNode
    all_relevant_nodes: List[dict]     # 从向量库检索的相关历史节点
    clusters: List[dict]              # Weaver 输出的 ConceptCluster
    relationships: List[dict]         # Weaver 输出的 Relationship
    design_draft: Optional[dict]      # Architect 输出的 DesignDocument
    critic_feedback: Optional[str]    # Critic 反馈文本
    critic_scores: Optional[dict]     # {innovation, coherence, feasibility}
    iteration: int
    max_iterations: int
    status: str
    errors: List[str]
```

### 7.2 工作流图

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

def build_weaving_workflow() -> StateGraph:
    workflow = StateGraph(WeaverState)

    # 6 个节点
    workflow.add_node("collect_and_prepare", collect_and_prepare_node)
    workflow.add_node("semantic_cluster", semantic_cluster_node)
    workflow.add_node("build_relationships", build_relationships_node)
    workflow.add_node("generate_design", generate_design_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("finalize", finalize_node)

    # 主流程边
    workflow.add_edge("collect_and_prepare", "semantic_cluster")
    workflow.add_edge("semantic_cluster", "build_relationships")
    workflow.add_edge("build_relationships", "generate_design")
    workflow.add_edge("generate_design", "critique")

    # 条件边：迭代或结束
    workflow.add_conditional_edges(
        "critique",
        should_iterate,
        {
            "iterate": "build_relationships",   # 带着反馈重新编织
            "finalize": "finalize",
            "error": END,
        }
    )

    workflow.add_edge("finalize", END)
    workflow.set_entry_point("collect_and_prepare")
    return workflow


def should_iterate(state: WeaverState) -> str:
    if state["errors"]:
        return "error"
    scores = state.get("critic_scores", {})
    # 自洽性 >= 0.6 且 可行性 >= 0.5 = 通过
    if (scores.get("coherence_score", 0) >= 0.6
            and scores.get("feasibility_score", 0) >= 0.5):
        return "finalize"
    if state["iteration"] >= state["max_iterations"]:
        return "finalize"
    return "iterate"

# SQLite checkpoint 支持暂停/恢复：
checkpointer = SqliteSaver.from_conn_string("data/weaver_checkpoints.db")
app = workflow.compile(checkpointer=checkpointer)
```

### 7.3 各节点职责

| 节点 | 对应 Agent | 输入 | 输出 |
|---|---|---|---|
| `collect_and_prepare` | Collector | raw 想法 | 标准化 IdeaNode + embedding 存入 SQLite/ChromaDB |
| `semantic_cluster` | Weaver | 新节点 + 向量检索的历史节点 | ConceptCluster 列表 |
| `build_relationships` | Weaver | 簇内节点 + Critic 反馈（如有） | Relationship 列表 + 跨领域桥梁 + ConflictInfo |
| `generate_design` | Architect | 概念簇 + 领域技能说明书 | DesignDocument（Markdown + Mermaid） |
| `critique` | Critic | DesignDocument | 评分 + 反馈文本 + 通过/驳回 |
| `finalize` | — | 通过的 DesignDocument | 保存、生成 HTML、推送给用户 |

---

## 8. API 契约

### 8.1 想法提交

```
POST /api/ideas
Content-Type: multipart/form-data

Fields:
  content:     string   (必填，若无文件)
  file:        binary   (可选，图片或音频)
  source_type: "text" | "image" | "voice"  (省略时自动检测)
  session_id:  string   (可选，关联已有会话)

Response 201:
{
  "idea_id": "uuid",
  "standardized_content": "...",
  "intent_tags": ["problem_statement", "constraint"],
  "status": "active"
}
```

### 8.2 会话管理

```
POST /api/sessions
Body: {
  "north_star": "设计一个支持分布式部署的 API 网关限流系统",
  "divergence_degree": 2
}

Response 201:
{
  "session_id": "uuid",
  "status": "collecting"
}

GET /api/sessions/{id}
Response 200:
{
  "session_id": "uuid",
  "north_star": "...",
  "status": "complete",
  "input_idea_ids": [...],
  "output_design_id": "uuid",
  "started_at": "...",
  "completed_at": "..."
}
```

### 8.3 编织触发

```
POST /api/sessions/{session_id}/weave
Body: { "divergence_degree": 2 }   // 可选，覆盖会话设置

Response 202:
{
  "session_id": "uuid",
  "status": "weaving",
  "progress_ws": "ws://localhost:8765/ws/progress/{session_id}"
}
```

### 8.4 设计文档获取

```
GET /api/designs/{id}
Response 200:
{
  "design_id": "uuid",
  "title": "API Gateway Rate Limiting Architecture",
  "type": "architecture",
  "content_markdown": "...",
  "innovation_score": 0.72,
  "coherence_score": 0.85,
  "feasibility_score": 0.68,
  "critic_approval": true,
  "version": 1
}

GET /api/designs/{id}/html
Response 200: text/html
(自包含 HTML：Mermaid 图表 + D3.js 交互图 + 渐进式文档 + 评分雷达图)
```

### 8.5 WebSocket 进度

```
WS /ws/progress/{session_id}

Server → Client messages:
  {"phase": "collecting", "message": "正在标准化 3 条想法...", "progress": 0.1}
  {"phase": "clustering", "message": "发现 2 个概念簇", "progress": 0.3, "clusters": [...]}
  {"phase": "building_relations", "message": "找到 5 条关联", "progress": 0.5}
  {"phase": "designing", "message": "正在生成架构设计...", "progress": 0.7}
  {"phase": "critiquing", "message": "正在验证设计...", "progress": 0.9}
  {"phase": "complete", "design_id": "uuid", "progress": 1.0}
  {"phase": "error", "message": "...", "progress": null}
```

### 8.6 健康检查

```
GET /api/health
Response 200: {"status": "ok", "llm_provider": "connected", "db": "ok", "chromadb": "ok"}
```

---

## 9. Prompt 架构

### 9.1 Collector Agent

```yaml
# src/agents/prompts/collector.yaml

system: |
  你是 Idea Weaving 系统中的 Collector Agent（想法捕获者）。
  你的职责：接收原始的非结构化输入（文本、图片描述、语音转写），
  产出一个标准化的"想法节点"（IdeaNode），供下游 Weaver Agent 使用。

  对每条输入，你必须输出一个 JSON 对象，包含以下字段：
  - standardized_content: 经过澄清和扩展的想法描述（2-4 句）
  - intent_tags: 从以下标签中选择 1-3 个：
    [problem_statement, solution_hypothesis, constraint, question,
     observation, analogy, goal, feature_idea, risk, assumption]
  - context_tags: 领域关键词数组（如 ["distributed_systems", "rate_limiting"]）
  - relevance_score: 0.0-1.0，与工程设计的相关度
  - completeness_score: 0.0-1.0，想法是否完整/成形
  - actionability_score: 0.0-1.0，能否立即据此行动

  质量过滤规则：
  - 三项评分均低于 0.3 → 标记为 dormant（休眠），暂不纳入编织
  - 三项评分均高于 0.7 → 标记为高优先级
  - 明显垃圾、空内容、无意义文本 → 标记为 noise（噪声）

  只输出有效 JSON。不要前言、不要解释。

few_shots:
  - input: "微服务之间调用太慢了，需要加缓存"
    output: |
      {
        "standardized_content": "微服务架构中存在服务间调用的延迟问题，需要通过引入缓存层来降低响应时间。这可能涉及本地缓存（如 Caffeine）、分布式缓存（如 Redis）或多级缓存策略的选型。需要考虑缓存失效策略、数据一致性保证和缓存穿透防护。",
        "intent_tags": ["problem_statement", "solution_hypothesis"],
        "context_tags": ["microservices", "caching", "latency", "distributed_systems"],
        "relevance_score": 0.85,
        "completeness_score": 0.6,
        "actionability_score": 0.5
      }

  - input: "就像高速公路有快车道和慢车道一样"
    output: |
      {
        "standardized_content": "用高速公路的分道设计类比系统架构中的流量分级——快车道（高优先级请求）和慢车道（批量处理、后台任务）分离，避免相互阻塞。这暗示了优先级队列或 QoS 分级的架构模式。",
        "intent_tags": ["analogy"],
        "context_tags": ["traffic_management", "qos", "priority_queueing", "system_design"],
        "relevance_score": 0.7,
        "completeness_score": 0.5,
        "actionability_score": 0.4
      }
```

### 9.2 Weaver Agent

```yaml
# src/agents/prompts/weaver.yaml

system: |
  你是 Idea Weaving 系统中的 Weaver Agent（语义编织者）。
  你接收一组标准化后的想法节点，需要完成四项任务：

  1. 语义聚类 (SEMANTIC CLUSTERING)：
     基于共同主题、互补视角或结构相似性，将想法分组为 ConceptCluster。
     每个簇输出 name、description 和 member_node_ids。
     对于跨领域的簇，标记为高创新潜力。

  2. 关系发现 (RELATIONSHIP DISCOVERY)：
     对簇内的每对节点，判断是否存在有意义的关系：
     - causal (因果), contradicts (矛盾), analogy (类比), prerequisite (前提),
       refines (细化), generalizes (泛化), supports (支撑), transforms (转化)
     输出关系类型、强度 (0-1) 和简短解释。

  3. 跨领域桥梁 (CROSS-DOMAIN BRIDGES)：
     识别来自不同领域但共享结构模式的节点对。
     这些是创新潜力最高的连接，单独列出。

  4. 冲突检测 (CONFLICT DETECTION)：
     识别逻辑矛盾或创造性张力的节点对。
     按类型分类：contradiction / tension / incompatibility / misunderstanding
     为每个冲突建议处理策略。

  输出格式：JSON，包含 "clusters", "relationships", "cross_domain_bridges", "conflicts" 四个键。

  重要约束：
  - 不要强行连接不相关的想法。如果没有真的关联，就说不存在。
  - 跨领域连接的质量优先于数量。
  - 冲突不是坏事——创造性张力可以驱动创新。

output_schema:
  type: object
  properties:
    clusters:
      type: array
      items:
        type: object
        properties:
          name: { type: string }
          description: { type: string }
          member_node_ids: { type: array, items: { type: string } }
          innovation_potential: { type: string, enum: [low, medium, high] }
        required: [name, description, member_node_ids]
    relationships:
      type: array
      items:
        type: object
        properties:
          source_node_id: { type: string }
          target_node_id: { type: string }
          relationship_type: { type: string }
          strength: { type: number, minimum: 0, maximum: 1 }
          explanation: { type: string }
    cross_domain_bridges:
      type: array
      items:
        type: object
        properties:
          node_a: { type: string }
          node_b: { type: string }
          domain_a: { type: string }
          domain_b: { type: string }
          shared_structure: { type: string }
    conflicts:
      type: array
      items:
        type: object
        properties:
          node_a: { type: string }
          node_b: { type: string }
          conflict_type: { type: string }
          description: { type: string }
          suggested_strategy: { type: string }
```

### 9.3 Architect Agent

```yaml
# src/agents/prompts/architect.yaml

system: |
  你是 Idea Weaving 系统中的 Architect Agent（设计架构师）。
  你接收概念簇和关系图，将其收敛为结构化的工程设计文档。

  你的输出必须是完整的 Markdown 文档，包含：

  1. 执行摘要（Executive Summary）
     - 1 段话概括设计目标与核心方案

  2. 架构概览（Architecture Overview）
     - 用 Mermaid graph TD 绘制系统架构图
     - 列出所有组件及其职责
     - 标明组件间的数据流方向

  3. 组件详规（Component Specifications）
     - 每个组件的具体技术选型与配置
     - 接口定义（输入/输出/协议）
     - 非功能性需求（性能、可靠性、可扩展性）

  4. 关键决策与权衡（Key Decisions & Trade-offs）
     - 表格形式：决策 | 备选 | 选择理由 | 代价
     - 对 Weaver 识别的冲突/张力给出明确回应

  5. 实施路径（Implementation Roadmap）
     - 分阶段的实施建议
     - 每阶段的目标与里程碑

  约束：
  - 技术选型要具体（"PostgreSQL with read replicas" 而非 "数据库"）
  - Mermaid 图表必须语法正确
  - 对识别到的冲突不能回避——要么选择一方，要么设计折中方案

output_format: |
  # {设计标题}

  ## 1. 执行摘要
  ...

  ## 2. 架构概览
  ```mermaid
  graph TD
      ...
```

  ## 3. 组件详规
  ### 3.1 {组件名}
  ...

  ## 4. 关键决策与权衡
  | 决策 | 备选方案 | 选择理由 | 代价 |
  |---|---|---|---|
  | ... | ... | ... | ... |

  ## 5. 实施路径
  ### Phase 1: ...
  ### Phase 2: ...
```

### 9.4 Critic Agent

```yaml
# src/agents/prompts/critic.yaml

system: |
  你是 Idea Weaving 系统中的 Critic Agent（设计审计员）。
  你对 Architect 生成的设计文档进行闭环验证。

  评估维度：

  1. 逻辑自洽性（Logical Coherence）：
     - 组件之间的数据流是否闭合？有没有引用了不存在的组件？
     - 是否有自相矛盾的设计决策？
     - 时序/因果链是否完整？

  2. 需求覆盖率（Requirement Coverage）：
     - 原始想法中的每个 problem_statement 是否都有对应的解决方案？
     - 原始想法中的每个 constraint 是否在设计中被满足或明确拒绝？
     - 有没有遗漏的想法被忽视？

  3. 风险扫描（Risk Scanning）：
     - 单点故障（SPOF）
     - 未指定的错误处理
     - 安全漏洞（未提鉴权、加密、审计）
     - 可扩展性瓶颈
     - 数据一致性隐患

  评分（0.0-1.0）：
  - coherence_score: 逻辑自洽性
  - innovation_score: 对原始想法创新性的保留程度
  - feasibility_score: 实际可实施性

  输出格式：JSON
  {
    "approved": true/false,
    "scores": { "coherence": 0.0-1.0, "innovation": 0.0-1.0, "feasibility": 0.0-1.0 },
    "feedback": "具体的、可操作的反馈文本，直接传达给 Weaver 用于重新编织",
    "issues": [
      { "severity": "critical|major|minor", "category": "...", "description": "..." }
    ],
    "strengths": ["做得好的方面..."]
  }

  通过标准：coherence >= 0.6 且 feasibility >= 0.5
  不通过时，feedback 必须具体到 Weaver 可以据此行动的程度。
```

---

## 10. UI 设计

> **设计方向**：白/灰/青配色 · 无边框 · 大圆角 · 柔阴影 · 弹簧动画 · 轻质感
>
> **实现方案**：Tauri 2 (Rust 壳, WebView2 渲染) + React 18 (TypeScript, Vite)
>   — 真圆角 (CSS border-radius + transparent window)
>   — GPU 加速 60fps CSS 动画
>   — backdrop-filter 毛玻璃效果
>   — Ctrl+Alt+[ 输入浮窗 / Ctrl+Alt+] 用户后台
>   — 系统托盘 (左键→后台, 右键→菜单)
>
> 参考审美：Linear, Raycast, Arc Browser, Things 3 — 留白大胆、层级用灰阶区分、
> 青色作为唯一强调色、无分割线、一切过渡都是圆滑的。

---

### 10.1 设计令牌 (Design Tokens)

所有视觉值收敛为 CSS 自定义属性，全局统一，不许硬编码。

```css
:root {
  /* ═══ 色彩 ═══ */
  --color-bg:            #FBFBFB;   /* 浮窗底色——微暖白，不是纯白 */
  --color-surface:       #F3F3F5;   /* 卡片/输入区底色——浅灰 */
  --color-surface-hover: #EBEBED;   /* hover 态 */
  --color-border:        transparent; /* 无边框设计 */
  --color-separator:     #E5E5E8;   /* 极少使用的分割线 */

  --color-text-primary:   #1A1A2E;  /* 主文字——近黑但非纯黑 */
  --color-text-secondary: #6E6E7C;  /* 辅助文字 */
  --color-text-tertiary:  #A0A0AC;  /* placeholder / disabled */

  --color-accent:         #0891B2;  /* 青色主调 */
  --color-accent-light:   #06B6D4;  /* hover / 高亮 */
  --color-accent-subtle:  #ECFEFF;  /* 极淡青底 */
  --color-accent-muted:   #CFFAFE;  /* 淡青底 */

  --color-danger:         #EF4444;  /* 录音中 / 删除 */
  --color-success:        #10B981;  /* 完成态 */

  --color-shadow-sm: rgba(0,0,0,0.04);
  --color-shadow-md: rgba(0,0,0,0.06);
  --color-shadow-lg: rgba(0,0,0,0.08);

  /* ═══ 圆角 ═══ */
  --radius-sm:   8px;
  --radius-md:   12px;
  --radius-lg:   16px;
  --radius-xl:   20px;
  --radius-full: 9999px;  /* 药丸 */

  /* ═══ 间距 ═══ */
  --space-xs:  4px;
  --space-sm:  8px;
  --space-md:  12px;
  --space-lg:  16px;
  --space-xl:  24px;
  --space-2xl: 32px;

  /* ═══ 字体 ═══ */
  --font-sans: "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif;
  --font-mono: "Cascadia Code", "Fira Code", "JetBrains Mono", monospace;

  --text-xs:   11px;
  --text-sm:   13px;
  --text-base: 15px;
  --text-lg:   18px;
  --text-xl:   22px;
  --text-2xl:  28px;

  --leading-tight:  1.2;
  --leading-normal: 1.5;
  --leading-relaxed: 1.7;

  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;

  /* ═══ 阴影 ═══ */
  --shadow-xs:  0 1px 2px  var(--color-shadow-sm);
  --shadow-sm:  0 1px 3px  var(--color-shadow-sm), 0 1px 2px var(--color-shadow-md);
  --shadow-md:  0 4px 12px var(--color-shadow-md), 0 1px 4px var(--color-shadow-sm);
  --shadow-lg:  0 8px 24px var(--color-shadow-lg), 0 2px 8px var(--color-shadow-md);
  --shadow-xl:  0 16px 48px var(--color-shadow-lg), 0 4px 16px var(--color-shadow-md);

  /* ═══ 动画 ═══ */
  --ease-spring:  cubic-bezier(0.22, 0.61, 0.36, 1);     /* 弹性收尾 */
  --ease-out:     cubic-bezier(0.16, 0.84, 0.44, 1);     /* 标准缓出 */
  --ease-in:      cubic-bezier(0.55, 0.06, 0.68, 0.19);  /* 缓入（消失用） */
  --ease-smooth:  cubic-bezier(0.4, 0, 0.2, 1);          /* Material 标准 */

  --duration-fast:   150ms;
  --duration-normal: 250ms;
  --duration-slow:   400ms;
  --duration-spring: 500ms;
}
```

### 10.2 捕获浮窗 —— 像素级规格

#### 10.2.1 视觉呈现

```
╭───────────────────────────────────────────╮  ← 无边框 · radius-xl (20px)
│                                           │  ← 白底 #FBFBFB + shadow-xl
│                                           │
│     ┌─────────────────────────────────┐   │
│     │                                 │   │  ← 输入区：浅灰底 #F3F3F5
│     │  写下你的想法……                  │   │     radius-lg (16px)
│     │                                 │   │     placeholder 灰色
│     │  文字自动撑高，最多可见 6 行      │   │     有内容时文字 #1A1A2E
│     │                                 │   │
│     └─────────────────────────────────┘   │
│                                           │
│     ┌──────┐ ┌──────┐                    │  ← 已粘贴的图片/音频缩略图
│     │ 🖼   │ │ 🎵   │                    │     radius-md (12px)
│     │ pic1 │ │ rec1 │                    │     青色细边框 + 右上角 ✕ 按钮
│     └──────┘ └──────┘                    │
│                                           │
│     ● REC  00:08                         │  ← 录音中状态条（仅录音时显示）
│                                           │     红色呼吸点 + 时长
│                                           │
│            ╭─────────────────╮            │
│            │   捕捉想法 →    │            │  ← 提交按钮：青色药丸
│            ╰─────────────────╯            │     radius-full · accent bg
│                                           │     hover 时提亮
│                                           │
╰───────────────────────────────────────────╯
       ↑ 浮窗宽 480px，高度自适应内容
```

#### 10.2.2 完整 HTML 结构

```html
<!-- src/ui/static/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Idea Weaver</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>

  <!-- 浮窗容器：所有动画作用于此 -->
  <div id="overlay" class="overlay visible">

    <!-- 输入区 -->
    <textarea
      id="idea-input"
      class="input-area"
      placeholder="写下你的想法……"
      rows="3"
      autofocus
    ></textarea>

    <!-- 附件缩略图列表（无附件时不渲染） -->
    <div id="attachments" class="attachments">
      <!-- JS 动态生成：
      <div class="attachment-thumb">
        <img src="..." alt="screenshot">
        <button class="remove-attachment" aria-label="移除">×</button>
      </div>
      -->
    </div>

    <!-- 录音状态条（闲置时不渲染） -->
    <div id="recording-bar" class="recording-bar hidden">
      <span class="recording-dot"></span>
      <span id="recording-time" class="recording-time">00:00</span>
    </div>

    <!-- 微提示 -->
    <p class="hint">Ctrl+↵ 提交 &nbsp;·&nbsp; Esc 取消 &nbsp;·&nbsp; Ctrl+V 粘贴图片</p>

    <!-- 提交按钮 -->
    <button id="submit-btn" class="submit-btn" disabled>
      <span class="btn-text">捕捉想法</span>
      <span class="btn-arrow">→</span>
    </button>

  </div>

  <script src="app.js"></script>
</body>
</html>
```

#### 10.2.3 完整 CSS

```css
/* src/ui/static/styles.css */

/* ═══════════════════════════════════
   RESET & BASE
   ═══════════════════════════════════ */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  height: 100%;
  overflow: hidden;
  background: transparent;  /* WebView2 透明底 */
  font-family: var(--font-sans);
  font-size: var(--text-base);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  user-select: none;
}

/* ═══════════════════════════════════
   OVERLAY — 无边框白底浮窗
   ═══════════════════════════════════ */
.overlay {
  width: 480px;
  max-height: 540px;
  margin: 0 auto;
  padding: var(--space-xl);
  background: var(--color-bg);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);

  display: flex;
  flex-direction: column;
  gap: var(--space-md);

  /* GPU 加速 */
  transform: translateZ(0);
  will-change: transform, opacity;

  /* 显示/隐藏动画 */
  opacity: 0;
  transform: translateY(12px) scale(0.97);
  transition:
    opacity var(--duration-spring) var(--ease-spring),
    transform var(--duration-spring) var(--ease-spring);
}

.overlay.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* ═══════════════════════════════════
   INPUT AREA
   ═══════════════════════════════════ */
.input-area {
  width: 100%;
  min-height: 100px;
  max-height: 240px;
  padding: var(--space-lg);
  background: var(--color-surface);
  border: none;
  border-radius: var(--radius-lg);
  outline: none;
  resize: none;

  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--color-text-primary);

  transition:
    background var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out);
}

.input-area::placeholder {
  color: var(--color-text-tertiary);
}

/* focus ring: 不破坏无边框美学——极淡的青色光晕 */
.input-area:focus {
  background: #FFFFFF;
  box-shadow:
    0 0 0 3px var(--color-accent-subtle),
    0 0 0 1px var(--color-accent-light);
}

/* ═══════════════════════════════════
   ATTACHMENTS
   ═══════════════════════════════════ */
.attachments {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.attachments:empty {
  display: none;
}

.attachment-thumb {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface);
  transition: transform var(--duration-fast) var(--ease-out);
}

.attachment-thumb:hover {
  transform: scale(1.05);
}

.attachment-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 音频附件样式 */
.attachment-thumb.audio {
  display: flex;
  align-items: center;
  justify-content: center;
  /* 青色微底 + 波形 icon（CSS 绘制简化版） */
  background: var(--color-accent-subtle);
  color: var(--color-accent);
  font-size: var(--text-sm);
  font-weight: var(--font-weight-medium);
}

.remove-attachment {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: var(--radius-full);
  background: rgba(0,0,0,0.45);
  color: #FFF;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-out);
}

.attachment-thumb:hover .remove-attachment {
  opacity: 1;
}

/* ═══════════════════════════════════
   RECORDING BAR
   ═══════════════════════════════════ */
.recording-bar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: #FEF2F2;    /* 极淡红底 */
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  color: var(--color-danger);

  transition:
    opacity var(--duration-normal) var(--ease-out),
    transform var(--duration-normal) var(--ease-out);
}

.recording-bar.hidden {
  display: none;
}

.recording-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-danger);
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.4; transform: scale(0.75); }
}

/* ═══════════════════════════════════
   HINT TEXT
   ═══════════════════════════════════ */
.hint {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  line-height: var(--leading-normal);
  /* 小字不要显得太拥挤 */
}

/* ═══════════════════════════════════
   SUBMIT BUTTON — 青色药丸
   ═══════════════════════════════════ */
.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  width: 100%;
  padding: var(--space-md) var(--space-xl);
  border: none;
  border-radius: var(--radius-full);
  background: var(--color-accent);
  color: #FFFFFF;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;

  /* 过渡 */
  transition:
    background var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out);

  /* 禁止选中 */
  user-select: none;
  -webkit-user-select: none;
}

.submit-btn:hover:not(:disabled) {
  background: var(--color-accent-light);
  transform: translateY(-1px);
  box-shadow:
    0 4px 12px rgba(8, 145, 178, 0.25),
    0 2px 4px rgba(8, 145, 178, 0.12);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
  transition-duration: 50ms;
}

.submit-btn:disabled {
  background: var(--color-surface);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

/* 按钮内箭头 */
.btn-arrow {
  display: inline-block;
  transition: transform var(--duration-fast) var(--ease-out);
}

.submit-btn:hover:not(:disabled) .btn-arrow {
  transform: translateX(3px);
}

/* 提交中状态 */
.submit-btn.loading {
  background: var(--color-accent-light);
  pointer-events: none;
}

.submit-btn.loading .btn-text::after {
  content: "...";
  animation: ellipsis 1.2s steps(3, end) infinite;
}

@keyframes ellipsis {
  0%   { content: "."; }
  33%  { content: ".."; }
  66%  { content: "..."; }
}
```

#### 10.2.4 动画时间线

```
按下 Ctrl+Alt+I：

 0ms   ─── pynput 捕获热键，通知 Python
 ~50ms ─── Python 创建 webview window，定位到活动显示器中央
 50ms  ─── HTML 加载完成，.overlay 的 transition 启动
         从 opacity:0 + translateY(12px) + scale(0.97)
 200ms ─── 到达 opacity:1 + translateY(0) + scale(1)
         动画曲线：cubic-bezier(0.22, 0.61, 0.36, 1) (弹簧感)
 200ms ─── input 获得焦点，光标闪烁
         ★ 用户可开始输入

按下 Esc：

 0ms   ─── .overlay 移除 .visible
         过渡到 opacity:0 + translateY(-8px) + scale(0.98)
         动画曲线：cubic-bezier(0.55, 0.06, 0.68, 0.19) (缓入)
 200ms ─── 动画结束，Python 关闭 webview window

提交瞬间：

 0ms   ─── 按钮文字变为 "捕捉中..."
         按钮背景变亮，箭头消失
 50ms  ─── .overlay 开始淡出 (opacity → 0, 100ms)
 150ms ─── webview 隐藏
         toast（系统托盘气泡）："✓ 已捕捉"
```

#### 10.2.5 交互细节规范

| 交互 | 触发 | 视觉反馈 | 持续时间 |
|---|---|---|---|
| **浮窗出现** | Ctrl+Alt+I | scale 0.97→1 + 上移 + 淡入 | 250ms spring |
| **浮窗消失** | Esc / 提交后 | scale 1→0.98 + 上移 + 淡出 | 200ms ease-in |
| **输入聚焦** | 点击 / 自动 | 白色底 + 青色光晕 (3px spread) | 150ms |
| **输入失焦** | 点击外部 | 光晕消失，底变回 #F3F3F5 | 150ms |
| **图片缩略图出现** | Ctrl+V | scale 0.8→1 + 淡入 | 200ms spring |
| **缩略图 hover** | 鼠标悬停 | scale 1→1.05 | 150ms |
| **移除按钮出现** | 悬停缩略图 | opacity 0→1 | 150ms |
| **提交按钮 hover** | 鼠标悬停 | 上浮 1px + 青阴影 + 箭头右移 3px | 150ms |
| **提交按钮 press** | 鼠标按下 | scale 1→0.98 | 50ms（极快反馈） |
| **录音开始** | 点击 🎤 | 录音条滑入 + 红点呼吸动画 | 200ms + 持续 |
| **录音结束** | 再次点击 | 录音条滑出 → 显示音频缩略图 | 200ms |
| **提交成功** | API 返 201 | 按钮 → "✓" + 浮窗淡出 | 200ms + 100ms 消失 |
| **提交失败** | API 报错 | 按钮短暂变红 → 恢复为"重试" | 300ms |

#### 10.2.6 无边框窗口配置

```python
# src/ui/overlay_window.py —— 关键配置

import webview

def create_overlay():
    window = webview.create_window(
        title="",
        url=str(Path("src/ui/static/index.html").resolve()),
        width=480,
        height=400,
        min_size=(360, 200),

        # === 无边框美学 ===
        frameless=True,          # 去掉 Windows 标题栏
        on_top=True,             # 始终置顶（类似 Spotlight）
        easy_drag=False,         # 浮窗不可拖动（居中固定）

        # === 透明底 ===
        # WebView2 默认白底，需注入 CSS 让 body 透明
        background_color="#00000000",

        # === 阴影由 CSS box-shadow 负责，不用系统阴影 ===
        transparent=True,
    )

    # 注入 CSS 透明背景
    window.evaluate_js("""
        document.documentElement.style.background = 'transparent';
        document.body.style.background = 'transparent';
    """)

    return window
```

---

### 10.3 结果页 —— 轻质设计

#### 10.3.1 整体布局

```
╭─────────────────────────────────────────────────────────────╮
│                                                              │
│              API Gateway 限流架构设计                         │
│              2026-07-18 · 来自 7 条想法                       │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │  创新度  │  │  自洽性  │  │  可行性  │                   │
│  │          │  │          │  │          │                   │
│  │  ● 0.72 │  │  ● 0.85 │  │  ● 0.68 │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ## 架构概览                                         │   │
│  │                                                      │   │
│  │  [Mermaid 渲染区域——浅灰底卡片]                       │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ## 概念关联图                                       │   │
│  │                                                      │   │
│  │  [D3.js 力导向图——节点青色系，边浅灰]                  │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ▼ 执行摘要                                                  │
│  ▼ 组件详规                                                  │
│  ▼ 关键决策与权衡                                             │
│  ▼ 探索分支                                                  │
│                                                              │
╰─────────────────────────────────────────────────────────────╯
```

#### 10.3.2 配色与排版

```css
/* 结果页专属令牌 */
:root {
  --result-max-width: 780px;       /* 正文不无限宽 */
  --result-bg: #FCFCFD;            /* 极淡灰白底 */
  --card-bg: #F5F5F7;             /* 卡片底 */
  --card-radius: 14px;
  --score-ring-size: 56px;        /* 评分圆环直径 */
  --score-ring-width: 4px;        /* 圆环线宽 */
}
```

**评分卡设计 —— 环形进度替代进度条：**

```html
<!-- 评分卡 HTML 片段 -->
<div class="score-cards">
  <div class="score-card">
    <svg class="score-ring" viewBox="0 0 56 56">
      <circle class="ring-bg"   cx="28" cy="28" r="24" />
      <circle class="ring-fill" cx="28" cy="28" r="24"
              stroke-dasharray="150.8"
              stroke-dashoffset="42.2" />  <!-- offset = 150.8 * (1 - 0.72) -->
    </svg>
    <span class="score-value">0.72</span>
    <span class="score-label">创新度</span>
  </div>
  <!-- ... 自洽性和可行性同理 -->
</div>
```

```css
/* 评分卡样式 */
.score-cards {
  display: flex;
  gap: var(--space-lg);
  justify-content: center;
}

.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xl) var(--space-2xl);
  background: #FFFFFF;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.score-ring {
  width: var(--score-ring-size);
  height: var(--score-ring-size);
  transform: rotate(-90deg);  /* 从 12 点方向开始 */
}

.ring-bg {
  fill: none;
  stroke: var(--color-surface);
  stroke-width: var(--score-ring-width);
}

.ring-fill {
  fill: none;
  stroke: var(--color-accent);
  stroke-width: var(--score-ring-width);
  stroke-linecap: round;
  /* stroke-dashoffset 由 JS 动态设置，实现动画 */
  transition: stroke-dashoffset 1s var(--ease-spring);
}

.score-value {
  font-size: var(--text-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.score-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
```

#### 10.3.3 Mermaid 图表——融入轻质风格

图表不花哨——统一的青色/灰色调，无边框，浅灰底卡片包裹。

```javascript
// src/ui/static/results.js

mermaid.initialize({
  startOnLoad: true,
  theme: 'base',
  themeVariables: {
    primaryColor: '#ECFEFF',       // 节点填充——极淡青
    primaryBorderColor: '#0891B2', // 节点边框——青色
    primaryTextColor: '#1A1A2E',   // 文字
    lineColor: '#A0A0AC',         // 连线——浅灰
    secondaryColor: '#F3F3F5',     // 次级节点
    tertiaryColor: '#FBFBFB',      // 三级节点
    fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif',
    fontSize: '14px',
  },
});
```

#### 10.3.4 D3.js 概念图 —— 轻质感力导向图

```javascript
// D3.js 力导向图配色与配置

const GRAPH_COLORS = {
  // 节点颜色——按领域分（低饱和度，融入白底）
  domains: {
    distributed_systems: '#CFFAFE',  // 极淡青
    frontend:           '#EDE9FE',   // 极淡紫
    database:           '#DCFCE7',   // 极淡绿
    devops:             '#FEF3C7',   // 极淡黄
    security:           '#FEE2E2',   // 极淡红
    default:            '#F3F3F5',   // 浅灰
  },
  domainStroke: '#0891B2',  // 选中节点的描边

  // 边
  edge: '#E5E5E8',         // 默认浅灰
  edgeHover: '#0891B2',    // hover 时变青
  edgeConflict: '#FCA5A5', // 冲突边——淡红

  // 节点文字
  label: '#6E6E7C',
  labelHover: '#1A1A2E',

  // 凸包（概念簇边界）
  hull: '#F3F3F5',
  hullStroke: '#E5E5E8',
};

const forceSimulation = d3.forceSimulation()
  .force('link', d3.forceLink().distance(80))
  .force('charge', d3.forceManyBody().strength(-200))   // 轻微排斥
  .force('center', d3.forceCenter())
  .force('collision', d3.forceCollide().radius(30))      // 防重叠
  .alphaDecay(0.02)                                      // 慢衰减——柔和"落定"
  .velocityDecay(0.3);                                   // 有阻尼——不抖
```

#### 10.3.5 结果页整体交互

| 元素 | 行为 |
|---|---|
| **页面加载** | 标题 + 评分卡先行渲染，Mermaid 和 D3 图依次淡入（各间隔 200ms） |
| **评分圆环** | 加载后 0→目标值 的 stroke-dashoffset 动画（1s spring） |
| **折叠区域** | 点击标题展开/收起，箭头旋转 180°，内容区 max-height 动画（300ms） |
| **概念图节点** | hover：放大 1.1x + 描边变青。click：居中固定 + 展开详情面板 |
| **概念图边** | hover：变青 + 线宽加粗。click：高亮两端节点 + 显示 relationship 说明 |
| **探索分支** | 默认折叠，标题旁灰色数字表示分支数。hover 时淡青色提示 |

---

### 10.4 性能预算

> UI 的所有动画集中在 `transform` 和 `opacity` 两个属性——它们只触发 GPU 合成，
> 不触发 layout 或 paint，保证 60fps。

| 指标 | 预算 | 验证方式 |
|---|---|---|
| 浮窗 HTML | < 8 KB | 文件大小 |
| 浮窗 CSS | < 5 KB | 文件大小 |
| 浮窗 JS (app.js) | < 10 KB | 文件大小（不含 D3/Mermaid） |
| 结果页总大小 | < 200 KB | 含 Mermaid.js + D3.js CDN |
| CSS 动画属性 | 只用 transform + opacity | 审查 styles.css |
| 浮窗首帧 (FCP) | < 200ms | Chrome DevTools Performance |
| 浮窗可交互 (TTI) | < 300ms | Chrome DevTools Performance |
| 动画帧率 | 60fps 无掉帧 | Chrome DevTools FPS meter |
| WebView2 内存 | < 80 MB（浮窗）/< 200 MB（结果页） | Windows 任务管理器 |

**禁止事项：**
- ❌ 禁止在动画中使用 `width` / `height` / `left` / `top` / `margin` / `padding`
- ❌ 禁止 `box-shadow` 在动画中变化（触发 paint）
- ❌ 禁止引入 CSS 框架（Bootstrap / Tailwind CDN）——手写 CSS 控制在 5KB
- ❌ 禁止 JS 动画（`setInterval` 做动画）——全部用 CSS transition / animation
- ❌ 禁止大图 base64 内嵌——缩略图保持 < 200×200，用 blob URL

---

## 11. 文件结构

```
D:\PY_PROJ\WEAVE\
├── pyproject.toml                    # Python 后端元数据
├── README.md
├── .env.example
├── .gitignore
├── run.py                            # 一键启动脚本
│
├── desktop/                          # ★ Tauri 2 + React 桌面壳
│   ├── package.json                  # React 依赖 + Tauri CLI
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src-tauri/                    # Rust 壳
│   │   ├── Cargo.toml
│   │   ├── tauri.conf.json           # 无边框/透明/托盘/热键
│   │   ├── capabilities/default.json
│   │   └── src/main.rs               # 启动 Python + 托盘 + 热键
│   └── src/                          # React 前端
│       ├── App.tsx                   # 窗口 label 检测 + 热键
│       ├── main.tsx
│       ├── components/
│       │   ├── CaptureOverlay.tsx     # Ctrl+Alt+[ 输入浮窗
│       │   └── Dashboard.tsx         # Ctrl+Alt+] 用户后台
│       ├── styles/globals.css        # DESIGN.md 设计令牌直出
│       └── lib/api.ts                # API 类型 + HTTP 封装
│
├── src/                              # Python 后端
│   ├── __init__.py
│   ├── main.py                       # 入口：系统托盘 + 热键 + 服务器启动
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py                 # FastAPI 应用定义、lifespan 事件
│   │   ├── dependencies.py           # 依赖注入（DB session、config）
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ideas.py             # POST /api/ideas, GET /api/ideas, DELETE
│   │   │   ├── sessions.py          # POST /api/sessions, GET /api/sessions/{id}
│   │   │   ├── weaving.py           # POST /api/sessions/{id}/weave
│   │   │   ├── designs.py           # GET /api/designs/{id}, /api/designs/{id}/html
│   │   │   └── health.py            # GET /api/health
│   │   └── websocket_manager.py     # WebSocket 连接管理与进度推送
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseAgent: LLM 调用封装、重试、结构化输出解析
│   │   ├── collector.py              # CollectorAgent: 多模态归一化
│   │   ├── weaver.py                 # WeaverAgent: 语义聚类 + 关系发现 + 冲突检测
│   │   ├── architect.py              # ArchitectAgent: 结构化设计文档生成
│   │   ├── critic.py                 # CriticAgent: 验证 + 评分 + 反馈
│   │   └── prompts/
│   │       ├── __init__.py           # Prompt 加载器（读取 YAML）
│   │       ├── collector.yaml        # Collector system message + few-shot
│   │       ├── weaver.yaml           # Weaver system message + 输出 schema
│   │       ├── architect.yaml        # Architect system message + 设计模板
│   │       └── critic.yaml           # Critic system message + 评估量规
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py                 # 所有 Pydantic 模型
│   │   ├── graph_ops.py              # NetworkX 图构建、查询、序列化
│   │   ├── embeddings.py             # Embedding 生成、批处理
│   │   ├── state_manager.py          # WeaverSession 状态序列化/反序列化
│   │   └── workflow.py               # LangGraph 工作流定义 + 各节点实现
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── tray_app.py               # pystray 系统托盘图标与菜单
│   │   ├── hotkey_listener.py        # pynput 全局热键监听
│   │   ├── overlay_window.py         # pywebview 浮窗管理
│   │   ├── static/
│   │   │   ├── index.html            # 捕获浮窗 HTML
│   │   │   ├── styles.css            # 浮窗样式（暗色主题、Win11 亚克力效果）
│   │   │   ├── app.js                # 前端逻辑（剪贴板、麦克风、API 调用）
│   │   │   ├── results.html          # 结果查看器模板
│   │   │   └── results.js            # D3.js 概念图 + Mermaid 渲染
│   │   └── templates/
│   │       └── design_report.html    # Jinja2 模板：最终设计文档
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py               # SQLAlchemy async engine + session factory
│   │   ├── idea_repo.py              # IdeaNode CRUD
│   │   ├── cluster_repo.py           # ConceptCluster CRUD
│   │   ├── design_repo.py            # DesignDocument CRUD
│   │   ├── session_repo.py           # WeaverSession CRUD
│   │   ├── vector_store.py           # ChromaDB 集合管理
│   │   └── file_store.py             # 资产文件 I/O（图片、音频、导出）
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py                  # pydantic-settings 配置管理
│       ├── logging_config.py          # loguru 配置
│       ├── whisper_transcriber.py     # 本地 Whisper 封装
│       └── metrics.py                # 创新度/自洽性/可行性计算器
│
├── skills/                            # 领域技能说明书（Markdown，运行时注入）
│   ├── software_architecture.md       # 微服务、单体、事件驱动等模式
│   ├── product_requirements.md        # PRD 模板与最佳实践
│   ├── system_design.md               # 系统设计面试框架
│   └── business_model_canvas.md       # 商业模式画布
│
├── data/                              # 运行时数据（.gitignored）
│   ├── weaver.db                      # SQLite 主数据库
│   ├── weaver_checkpoints.db          # LangGraph checkpoint 数据库
│   ├── chroma/                        # ChromaDB 持久化目录
│   └── assets/
│       ├── images/                    # 粘贴/截图的图片
│       └── audio/                     # 语音录音
│
├── exports/                           # 用户输出（.gitignored）
│   └── design_{date}_{title}.md
│
└── tests/
    ├── __init__.py
    ├── conftest.py                    # Pytest fixtures（测试 DB、mock LLM）
    ├── test_models.py                 # 模型序列化/校验
    ├── test_collector.py              # Collector 单元测试
    ├── test_weaver.py                 # Weaver 单元测试
    ├── test_architect.py              # Architect 单元测试
    ├── test_critic.py                 # Critic 单元测试
    ├── test_workflow.py               # LangGraph 全流水线测试
    ├── test_storage.py                # 数据库 + 向量存储测试
    ├── test_api.py                    # FastAPI 路由测试（TestClient）
    ├── test_ui.py                     # 浮窗行为测试
    ├── test_e2e.py                    # 端到端冒烟测试
    └── fixtures/
        ├── sample_ideas.json          # 10 条精心构造的想法片段
        ├── sample_image.png           # 测试用图片
        └── sample_audio.wav           # 测试用音频
```

---

## 12. 实施计划

### 总览：8 周

```
Week 1  ████████  Foundation
Week 2  ████████  Embeddings & Vector Store
Week 3  ████████  Agents: Collector + Weaver
Week 4  ████████  Agents: Architect + Critic + Workflow
Week 5  ████████  API Layer
Week 6  ████████  UI Layer
Week 7  ████████  Integration & Polish
Week 8  ████████  Packaging & Docs
```

### Week 1: Foundation（基础）

- 创建项目骨架、pyproject.toml、.env.example
- 实现 `src/core/models.py`（所有 Pydantic 模型）
- 实现 `src/storage/database.py`（SQLAlchemy + aiosqlite）
- 实现 `src/storage/idea_repo.py`、`cluster_repo.py`、`design_repo.py`、`session_repo.py`
- 实现 `src/utils/config.py`（pydantic-settings）
- 编写模型校验测试和存储测试

**可交付**：所有实体 CRUD 可操作，测试通过

### Week 2: Embeddings & Vector Store（向量存储）

- 实现 `src/core/embeddings.py`（LiteLLM embedding 集成）
- 实现 `src/storage/vector_store.py`（ChromaDB 设置、增/搜/删）
- 实现 `src/core/graph_ops.py`（NetworkX 从节点+关系构建图）
- 已有节点批量生成 embedding

**可交付**：语义搜索可用，图查询可用

### Week 3: Agents — Collector + Weaver

- 实现 `src/agents/base.py`（LLM 调用 + 重试 + 结构化输出解析）
- 实现 `src/agents/collector.py`（多模态归一化）
- 实现 `src/agents/prompts/collector.yaml`、`weaver.yaml`
- 实现 `src/utils/whisper_transcriber.py`
- 实现 `src/agents/weaver.py`（聚类 + 关系发现 + 冲突检测）

**可交付**：Collector 将文字/图片/语音转为 IdeaNode；Weaver 产出簇和关系

### Week 4: Agents — Architect + Critic + Workflow

- 实现 `src/agents/architect.py`（含 Mermaid 图表的设计文档生成）
- 实现 `src/agents/critic.py`（评估 + 反馈）
- 实现 `src/agents/prompts/architect.yaml`、`critic.yaml`
- 实现 `src/core/workflow.py`（LangGraph 编排）
- 实现 `src/core/state_manager.py`（checkpoint 序列化）

**可交付**：端到端流水线跑通（想法 → 设计文档 → 批判反馈循环）

### Week 5: API Layer（接口层）

- 实现 `src/api/server.py`（FastAPI 应用）
- 实现全部路由处理器
- 实现 `src/api/websocket_manager.py`（进度推送）
- 实现 `src/utils/metrics.py`（创新/自洽/可行性评分）

**可交付**：完整 REST API + WebSocket + Swagger 文档

### Week 6: UI Layer（界面层）

- 实现 `src/ui/overlay_window.py`（pywebview，无边框、置顶）
- 实现 `src/ui/static/`（HTML/CSS/JS 捕获浮窗）
- 实现 `src/ui/tray_app.py`（pystray + 菜单）
- 实现 `src/ui/hotkey_listener.py`（pynput，Ctrl+Alt+I）
- 实现 `src/ui/static/results.html` + `results.js`（D3.js + Mermaid）

**可交付**：热键浮窗可捕获文字/图片/语音，结果页正常渲染

### Week 7: Integration & Polish（集成打磨）

- 实现 `src/main.py`（全部组件连线）
- 接入真实 LLM 端到端测试
- 错误处理与边界情况
- 性能优化（batch embedding、连接池）

**可交付**：从热键到设计输出的可用产品

### Week 8: Packaging & Documentation（打包发布）

- PyInstaller 配置，Windows .exe
- 开机自启（Windows 注册表 `HKCU\...\Run`）
- README.md 含安装/使用/架构说明
- skills 目录填充领域说明书

**可交付**：可分发的 .exe + 完整文档

---

## 13. 验证策略

### 13.1 测试金字塔

```
         ┌─────────┐
         │  E2E    │  4 个测试（冒烟、多模态、持久化、冲突检测）
         ├─────────┤
         │ 集成测试 │  8 个测试（工作流、API、WebSocket、存储）
         ├─────────┤
         │ 单元测试 │  30+ 个测试（每个 Agent、每个模型、每个工具）
         └─────────┘
```

### 13.2 关键集成测试

**Collector → Storage 流水线：**
```
Given: 原始文本 "We need horizontal scaling for the API layer"
When:  Collector 处理
Then:  创建 IdeaNode，standardized_content 正确，intent_tags=["problem_statement", "constraint"]
And:  持久化到 SQLite
And:  Embedding 生成并存入 ChromaDB
```

**Weaver → Architect 流水线：**
```
Given: 5 条关于分布式系统的关联 IdeaNode
When:  Weaver 处理
Then:  至少创建 1 个 ConceptCluster（含 member_node_ids）
And:  发现节点间关系
And:  Architect 生成含 Mermaid 图表的 DesignDocument
```

**Critic 反馈循环：**
```
Given: 一份已知缺陷的 DesignDocument（多用户系统缺少鉴权）
When:  Critic 评估
Then:  critic_approval = False
And:  critic_feedback 提及缺失的鉴权
And:  工作流迭代（Weaver 接收反馈重新编织）
```

### 13.3 E2E 测试

**E2E-1: 文字到设计冒烟测试**
```
1. 启动应用（main.py）
2. 验证系统托盘图标出现
3. 按 Ctrl+Alt+I
4. 验证浮窗在 500ms 内出现
5. 输入："需要设计一个 API 网关限流系统，支持分布式部署，
   使用 Redis 计数器，采用滑动窗口算法"
6. Ctrl+Enter
7. 验证浮窗关闭
8. 60 秒内浏览器打开结果 HTML
9. 验证文档包含：标题含"限流"、Mermaid 架构图、具名组件、至少 1 个权衡分析
10. 验证创新/自洽/可行性评分均已显示
```

**E2E-2: 多模态输入测试**
```
1. Ctrl+Alt+I
2. 输入文字："这是一个用户仪表盘的 mockup"
3. 从剪贴板粘贴仪表盘截图
4. 验证浮窗中显示缩略图
5. 点击麦克风："仪表盘需要 WebSocket 实时更新通知计数，活动流延迟加载"
6. 提交
7. 验证三种输入均产生不同 source_type 的 IdeaNode
8. 编织后验证设计文档引用了所有三个输入
```

**E2E-3: 冲突检测测试**
```
1. 提交想法 A："系统必须对所有读操作保证强一致性"
2. 提交想法 B："系统必须优先保障可用性和分区容错，而非一致性"
3. 触发编织
4. 验证 Critic 检测到 CAP 定理张力
5. 验证设计文档包含 CP vs AP 的权衡讨论
6. 验证冲突被标记，而非静默消解
```

**E2E-4: 持久化与崩溃恢复**
```
1. 提交 3 条想法
2. 强制结束进程（taskkill）
3. 重启应用
4. Ctrl+Alt+I 输入第 4 条想法
5. 触发编织
6. 验证全部 4 条想法参与编织
```

### 13.4 V1 完成标准

| 指标 | 阈值 | 验证方式 |
|---|---|---|
| 热键响应 | < 500ms | 测试计时 |
| 想法提交延迟 | < 2s（含 embedding） | API 响应计时 |
| 单次编织（5-10 条想法） | < 60s | 工作流计时 |
| 设计文档完整性 | 含标题、概述、Mermaid 图、组件列表、权衡分析 | 结构校验 |
| Critic 检出率 | 能发现：缺失鉴权、CAP 冲突、未指定的错误处理 | 对抗测试集 |
| 重启数据恢复 | 100% 节点可恢复 | 持久化 E2E |
| 多模态支持 | 文字/图片/语音均生成正确类型的 IdeaNode | 多模态 E2E |
| 零静默丢失 | 随机 kill 后 0 数据丢失 | Fuzz 测试 |
| 打包 | 单 .exe < 100MB | PyInstaller 构建 |
| 文档 | README 含安装/使用/架构概述 | 可读性审查 |

---

## 14. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| WebView2 不可用 | 低（Win11 自带） | 高（无 UI） | 降级：在默认浏览器打开捕获页面 |
| ChromaDB 持久化损坏 | 低 | 高（丢失全部 embedding） | embedding 是派生数据，可从 SQLite 重建 |
| LLM 结构化输出解析失败 | 中 | 中 | 重试（低温度）→ 正则提取 → 记录原始输出供调试 |
| LLM 延迟影响体验 | 中 | 中 | 流式输出，渐进式 UI 更新（簇形成即推送） |
| 全局热键与其他应用冲突 | 中 | 低 | 可配置热键，检测注册失败提示替代键 |
| pywebview 多显示器定位 | 中 | 低 | 通过 Windows API 检测活动显示器，居中 |
| PyInstaller .exe 被杀软误报 | 中 | 中 | 代码签名（如可行），文档化误报处理 |

---

## 15. 决策记录

| 决策 | 备选方案 | 选择理由 |
|---|---|---|
| ChromaDB 本地 vs Pinecone 云 | Pinecone：托管、可扩展 | ChromaDB：零网络依赖、免费、数据在用户机器上 |
| LangGraph vs 自定义状态机 | 自定义：更多控制 | LangGraph：内置 checkpoint、条件边、可视化 |
| Tauri 2 + React vs Electron | Electron：更强大 | Tauri 2：~5MB vs Electron 200MB+, WebView2 + Rust, 真圆角/GPU/毛玻璃 |
| pywebview vs Electron (旧决策) | Electron：更强大 | pywebview：5MB vs 200MB——已被 Tauri 2 取代 |
| pynput vs ctypes Win32 API | ctypes：零依赖 | pynput：跨平台、API 更简洁 |
| openai-whisper 本地 vs 云 STT | 云 STT：更高准确率 | 本地 Whisper：离线、隐私、零费用 |
| SQLite vs PostgreSQL | PostgreSQL：更强大 | SQLite：单用户桌面应用、零配置、单文件备份 |
| FastAPI vs Flask | Flask：更简单 | FastAPI：原生 async、WebSocket、自动文档、Pydantic |
| LiteLLM vs 直接 Anthropic SDK | 直接 SDK：更少抽象 | LiteLLM：一行配置换模型、成本追踪、内置重试 |

---

## 16. 设计补充：针对 2.2 节 8 项不足的工程级方案

> 以下逐条回应 2.2 节「不足与缺失」表格中的每一项，
> 提供可直接落地的工程设计。

---

### 补充-1: 数据模型 —— 从 Pydantic 到物理存储

> 对应不足：**「无具体数据模型」**

Section 5 已给出各实体的 Pydantic 定义。本节补全：SQL DDL、索引策略、迁移方案。

#### 16.1.1 SQLite 物理表结构

```sql
-- 想法节点
CREATE TABLE idea_nodes (
    id TEXT PRIMARY KEY,                          -- UUID
    source_type TEXT NOT NULL CHECK(source_type IN ('text','image','voice')),
    raw_content TEXT NOT NULL,
    raw_asset_path TEXT,                          -- 相对路径，如 'assets/images/abc123.png'
    standardized_content TEXT,
    -- embedding 不存 SQLite，仅在 ChromaDB 中
    intent_tags TEXT NOT NULL DEFAULT '[]',        -- JSON 数组
    context_tags TEXT NOT NULL DEFAULT '[]',       -- JSON 数组
    relevance_score REAL NOT NULL DEFAULT 0.5,
    completeness_score REAL NOT NULL DEFAULT 0.5,
    actionability_score REAL NOT NULL DEFAULT 0.5,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','dormant','merged','archived')),
    merged_into TEXT,
    north_star_relevance REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    session_id TEXT,
    FOREIGN KEY(merged_into) REFERENCES idea_nodes(id) ON DELETE SET NULL
);

CREATE INDEX idx_ideas_status ON idea_nodes(status);
CREATE INDEX idx_ideas_session ON idea_nodes(session_id);
CREATE INDEX idx_ideas_created ON idea_nodes(created_at);
CREATE INDEX idx_ideas_source ON idea_nodes(source_type);

-- 关系边
CREATE TABLE relationships (
    id TEXT PRIMARY KEY,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL CHECK(relationship_type IN (
        'causal','contradicts','analogy','prerequisite',
        'refines','generalizes','supports','transforms')),
    strength REAL NOT NULL DEFAULT 0.5 CHECK(strength >= 0 AND strength <= 1),
    explanation TEXT,
    discovery_method TEXT NOT NULL DEFAULT 'llm_inferred',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(source_node_id) REFERENCES idea_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY(target_node_id) REFERENCES idea_nodes(id) ON DELETE CASCADE
);

CREATE INDEX idx_rel_source ON relationships(source_node_id);
CREATE INDEX idx_rel_target ON relationships(target_node_id);
CREATE INDEX idx_rel_type ON relationships(relationship_type);

-- 概念簇
CREATE TABLE concept_clusters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    member_node_ids TEXT NOT NULL DEFAULT '[]',   -- JSON 数组
    summary TEXT NOT NULL DEFAULT '',
    innovation_score REAL NOT NULL DEFAULT 0.5,
    coherence_score REAL NOT NULL DEFAULT 0.5,
    cross_domain_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','resolved','archived')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_clusters_status ON concept_clusters(status);

-- 簇-节点 多对多关系表（比 JSON 数组更利于查询）
CREATE TABLE cluster_members (
    cluster_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    PRIMARY KEY(cluster_id, node_id),
    FOREIGN KEY(cluster_id) REFERENCES concept_clusters(id) ON DELETE CASCADE,
    FOREIGN KEY(node_id) REFERENCES idea_nodes(id) ON DELETE CASCADE
);

-- 冲突信息
CREATE TABLE conflicts (
    id TEXT PRIMARY KEY,
    cluster_id TEXT NOT NULL,
    node_a TEXT NOT NULL,
    node_b TEXT NOT NULL,
    conflict_type TEXT NOT NULL CHECK(conflict_type IN (
        'contradiction','tension','incompatibility','misunderstanding')),
    description TEXT NOT NULL DEFAULT '',
    resolution_strategy TEXT NOT NULL DEFAULT 'flag_for_user',
    resolved INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(cluster_id) REFERENCES concept_clusters(id) ON DELETE CASCADE,
    FOREIGN KEY(node_a) REFERENCES idea_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY(node_b) REFERENCES idea_nodes(id) ON DELETE CASCADE
);

-- 设计文档
CREATE TABLE design_documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('architecture','prd','flow_diagram','technical_spec')),
    source_cluster_ids TEXT NOT NULL DEFAULT '[]',
    content_markdown TEXT NOT NULL DEFAULT '',
    innovation_score REAL NOT NULL DEFAULT 0.5,
    coherence_score REAL NOT NULL DEFAULT 0.5,
    feasibility_score REAL NOT NULL DEFAULT 0.5,
    critic_approval INTEGER NOT NULL DEFAULT 0,
    critic_feedback TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    parent_design_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(parent_design_id) REFERENCES design_documents(id) ON DELETE SET NULL
);

-- 编织会话
CREATE TABLE weaver_sessions (
    id TEXT PRIMARY KEY,
    north_star TEXT NOT NULL,
    divergence_degree INTEGER NOT NULL DEFAULT 2,
    status TEXT NOT NULL DEFAULT 'collecting' CHECK(status IN (
        'collecting','weaving','architecting','critiquing','complete','failed')),
    input_idea_ids TEXT NOT NULL DEFAULT '[]',
    output_design_id TEXT,
    errors TEXT NOT NULL DEFAULT '[]',
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY(output_design_id) REFERENCES design_documents(id) ON DELETE SET NULL
);

-- 用户画像（单例表，始终只有 1 行）
CREATE TABLE user_profile (
    id INTEGER PRIMARY KEY CHECK(id = 1),  -- 强制单例
    frequent_domains TEXT NOT NULL DEFAULT '[]',
    preferred_output_formats TEXT NOT NULL DEFAULT '["architecture"]',
    idea_transition_matrix TEXT NOT NULL DEFAULT '{}',
    recurring_constraints TEXT NOT NULL DEFAULT '[]',
    interaction_count INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT NOT NULL DEFAULT (datetime('now'))
);
```

#### 16.1.2 ChromaDB 集合设计

```python
# 主想法集合
idea_collection = chroma_client.get_or_create_collection(
    name="idea_nodes",
    metadata={"hnsw:space": "cosine"},  # 余弦距离
    embedding_function=litellm_embedding_function,
)

# 元数据结构：每条 ChromaDB 记录
# {
#     "id": "<idea_node_uuid>",
#     "embedding": [0.123, -0.456, ...],  # 1536-d
#     "document": "<standardized_content>",  # 用于全文搜索
#     "metadata": {
#         "intent_tags": "problem_statement,constraint",
#         "context_tags": "distributed_systems,rate_limiting",
#         "status": "active",
#         "source_type": "text",
#         "relevance_score": 0.85,
#         "north_star_relevance": 0.72,
#         "session_id": "uuid",
#         "created_at": "2026-07-18T10:30:00"
#     }
# }

# 簇质心集合（独立集合，加速簇级搜索）
cluster_collection = chroma_client.get_or_create_collection(
    name="cluster_centroids",
    metadata={"hnsw:space": "cosine"},
    embedding_function=litellm_embedding_function,
)
```

#### 16.1.3 迁移策略

```
版本管理：data/.schema_version 文件记录当前 DB schema 版本号。
启动时检查，若版本不匹配则按序执行迁移脚本。

迁移目录：src/storage/migrations/
├── 001_initial_schema.sql     ← 上述完整 DDL
├── 002_add_goals_table.sql    ← V2 需求
└── ...

执行方式：SQLAlchemy + aiosqlite 原生 SQL，不引入 Alembic（单用户本地 DB 不需要复杂的迁移链）。
每次都从 .schema_version 读取当前版本，缺哪个执行哪个，最后更新版本号。
```

---

### 补充-2: 10 个探索性问题 —— 工程实现要点

> 对应不足：**「10 个探索性问题未答」**

Section 3 已给出完整回答。此处补全关键实现细节：

#### 16.2.1 信噪比三层过滤的实现

```python
# src/agents/collector.py 中的过滤管线

class SignalFilter:
    """采集时的三阶段过滤器"""

    # L1 参数
    MIN_CONTENT_LENGTH = 15
    DUPLICATE_SIMILARITY_THRESHOLD = 0.92
    DUPLICATE_MAX_RESULTS = 5  # 只检查最相似的 5 个已有节点

    # L2 参数
    DORMANT_COMPOSITE_THRESHOLD = 0.3  # 三项评分均值低于此 → dormant
    HIGH_PRIORITY_COMPOSITE_THRESHOLD = 0.7  # 三项评分均值高于此 → high_priority

    async def filter(self, raw_input: RawInput, vector_store: VectorStore) -> FilterResult:
        # L1: 启发式
        if len(raw_input.content) < self.MIN_CONTENT_LENGTH:
            return FilterResult(action="reject", reason="too_short")

        # L1: 近似去重（需先有 embedding）
        embedding = await self._embed(raw_input)
        nearest = await vector_store.search(embedding, k=self.DUPLICATE_MAX_RESULTS)
        if nearest and nearest[0].similarity > self.DUPLICATE_SIMILARITY_THRESHOLD:
            return FilterResult(
                action="merge_candidate",
                reason=f"near_duplicate_of_{nearest[0].id}",
                merge_target_id=nearest[0].id,
            )

        # L2: LLM 三轴评分（Collector prompt 内置）
        scores = await self._llm_triage(raw_input)
        composite = (scores.relevance + scores.completeness + scores.actionability) / 3

        if composite < self.DORMANT_COMPOSITE_THRESHOLD:
            return FilterResult(action="accept_dormant", scores=scores)
        elif composite >= self.HIGH_PRIORITY_COMPOSITE_THRESHOLD:
            return FilterResult(action="accept_priority", scores=scores)
        return FilterResult(action="accept_active", scores=scores)

    # L3 在 results.js 中由用户触发，调用 POST /api/feedback {node_id, label}
```

#### 16.2.2 冲突检测的完整判定树

```python
# src/agents/weaver.py 中的冲突分类逻辑

def classify_conflict(node_a: IdeaNode, node_b: IdeaNode,
                      relationship: Relationship) -> str:
    """根据节点标签和关系类型，判定冲突类别"""
    a_tags = set(node_a.intent_tags)
    b_tags = set(node_b.intent_tags)

    # 矛盾：相同维度上互斥的断言
    if (relationship.relationship_type == RelationshipType.CONTRADICTS
            and a_tags.intersection(b_tags)):
        return "contradiction"

    # 误解：高语义相似度 但 结构标签完全不同
    if (relationship.strength > 0.85
            and relationship.relationship_type == RelationshipType.REFINES
            and not a_tags.intersection(b_tags)):
        return "misunderstanding"

    # 不兼容：Architect 尝试合并失败（在 workflow 迭代中由 Architect 标记）
    # 张力：低语义相似度 + 不同维度 + 有 connection
    if (relationship.strength < 0.4
            and relationship.discovery_method == "structural_match"
            and a_tags != b_tags):
        return "tension"

    return "tension"  # default
```

#### 16.2.3 跨域发现的"强制偶遇"实现

```python
# src/agents/weaver.py

async def forced_serendipity_sample(
    nodes: List[IdeaNode],
    embeddings: List[List[float]],
    sample_size: int = 5,
) -> List[Tuple[IdeaNode, IdeaNode]]:
    """
    随机采样低语义相似度 + 结构角色匹配的节点对，
    抛给 LLM 寻找非显而易见的连接。
    """
    pairs = []
    all_tags = [set(n.intent_tags) for n in nodes]

    # 分组：按语义聚类分桶
    semantic_buckets = cluster_by_cosine(embeddings, threshold=0.5)

    # 跨桶配对
    for i, bucket_a in enumerate(semantic_buckets):
        for bucket_b in semantic_buckets[i+1:]:
            # 从不同桶中找共享 intent_tag 的节点
            for idx_a in bucket_a:
                for idx_b in bucket_b:
                    if all_tags[idx_a].intersection(all_tags[idx_b]):
                        pairs.append((nodes[idx_a], nodes[idx_b]))

    # 随机采样
    import random
    return random.sample(pairs, min(sample_size, len(pairs)))
```

---

### 补充-3: Critic Agent —— 完整评估管线

> 对应不足：**「Critic Agent 欠定义」**

Section 9.4 已给出 Prompt YAML。本节补全：评估算法、反馈路由、迭代决策。

#### 16.3.1 评估流程

```
┌──────────────────────────────────────────────────────────────┐
│                   CRITIC 评估管线                              │
│                                                               │
│  DesignDocument ─┬─ Pass 1: 结构静态检查 (零 LLM)              │
│                  │   · 组件引用完整性：Mermaid 中提到的每个组件   │
│                  │     是否在组件详规中有定义？                  │
│                  │   · 接口闭合性：每个输出端口是否连接到某组件？  │
│                  │   · 需求回溯：每个 problem_statement IdeaNode │
│                  │     是否在设计中有对应方案？                  │
│                  │   → 产出 StructureReport                     │
│                  │                                             │
│                  ├─ Pass 2: LLM 逻辑审查 (Claude Sonnet)       │
│                  │   · 因果链完整性                             │
│                  │   · 自相矛盾检测                             │
│                  │   · 边界条件处理                             │
│                  │   → 产出 LogicReport                         │
│                  │                                             │
│                  ├─ Pass 3: LLM 风险扫描 (Claude Sonnet)       │
│                  │   · SPOF 检测                               │
│                  │   · 安全缺口（鉴权、加密、审计）               │
│                  │   · 可扩展性瓶颈                             │
│                  │   · 数据一致性隐患                           │
│                  │   → 产出 RiskReport                          │
│                  │                                             │
│                  └─ Pass 4: 评分聚合                            │
│                      · 综合 Pass 1-3 计算三维分数               │
│                      · 生成结构化 Feedback                      │
│                      · 决策：approved / iterate / error         │
│                      → 产出 CriticVerdict                       │
└──────────────────────────────────────────────────────────────┘
```

#### 16.3.2 评分算法

```python
# src/utils/metrics.py

class CriticScorer:
    """Critic 评分计算器"""

    # 权重配置（可从 user_profile 学习调整）
    COHERENCE_WEIGHTS = {
        "component_reference_integrity": 0.20,   # Pass 1
        "interface_closure": 0.20,               # Pass 1
        "requirement_coverage": 0.25,             # Pass 1
        "causal_chain_completeness": 0.20,        # Pass 2
        "contradiction_free": 0.15,               # Pass 2
    }

    INNOVATION_WEIGHTS = {
        "cross_domain_density": 0.30,
        "structural_novelty": 0.25,
        "idea_diversity_index": 0.25,
        "surprise_quotient": 0.20,                # Pass 2 + 3 的 LLM 评分
    }

    FEASIBILITY_WEIGHTS = {
        "component_specificity": 0.30,
        "interface_completeness": 0.25,
        "implementation_path_exists": 0.25,
        "risk_severity_inverted": 0.20,           # Pass 3 风险等级取反
    }

    def compute_coherence(self, structure: StructureReport,
                          logic: LogicReport) -> float:
        scores = {
            "component_reference_integrity": structure.component_ref_score,
            "interface_closure": structure.interface_closure_score,
            "requirement_coverage": structure.requirement_coverage_score,
            "causal_chain_completeness": logic.causal_chain_score,
            "contradiction_free": 1.0 - logic.contradiction_count * 0.1,
        }
        return sum(scores[k] * self.COHERENCE_WEIGHTS[k] for k in scores)

    def compute_innovation(self, cluster: ConceptCluster,
                           llm_surprise: float) -> float:
        # novelty_ratio: 簇内节点 embedding 的平均两两余弦距离
        # 以所有活跃簇的均值作为基线归一化
        scores = {
            "cross_domain_density": min(cluster.cross_domain_count / 5.0, 1.0),
            "structural_novelty": cluster.innovation_score,  # Weaver 已计算
            "idea_diversity_index": cluster.innovation_score,
            "surprise_quotient": llm_surprise / 10.0,
        }
        return sum(scores[k] * self.INNOVATION_WEIGHTS[k] for k in scores)

    def compute_feasibility(self, design: DesignDocument,
                            risk: RiskReport) -> float:
        # component_specificity: 使用了具体技术名的组件占比
        specific_count = count_specific_components(design.content_markdown)
        total_count = count_all_components(design.content_markdown)
        spec_score = specific_count / max(total_count, 1)

        risk_score = 1.0 - min(risk.severity_sum / 10.0, 1.0)

        return (
            spec_score * 0.30
            + design.feasibility_score * 0.50  # Architect 自评 + LLM 评分
            + risk_score * 0.20
        )
```

#### 16.3.3 Feedback 结构化协议

```python
# Critic 输出给 Weaver 的反馈格式
# 这决定了 Weaver 能否有效"重新编织"

class CriticFeedback(BaseModel):
    """Critic → Weaver 的结构化反馈"""
    approved: bool
    iteration: int
    max_iterations: int

    # === 必须处理的问题（blocking）===
    blocking_issues: List[BlockingIssue] = []
    # 例：{"component": "RateLimiter", "issue": "缺少与 Redis 的连接定义",
    #       "suggestion": "补充 RateLimiter → Redis 的数据流和协议"}

    # === 建议改进（non-blocking）===
    suggestions: List[Suggestion] = []
    # 例：{"aspect": "scalability", "suggestion": "考虑增加分片策略应对单 Redis 瓶颈"}

    # === 做得好的方面（Weaver 应保留）===
    strengths: List[str] = []
    # 例："跨域类比（高速车道 → 优先级队列）有创新性，保留"

    # === 冲突处理建议 ===
    conflict_resolutions: List[ConflictResolution] = []
    # 例：{"conflict_id": "uuid", "recommendation": "preserve_as_tension",
    #       "tradeoff_dimensions": ["consistency", "availability"]}

    scores: CriticScores

class BlockingIssue(BaseModel):
    severity: Literal["critical", "major"]
    category: str  # "missing_component", "broken_interface", "contradiction", "uncovered_requirement"
    description: str
    affected_component: Optional[str] = None
    affected_requirement_id: Optional[UUID] = None
    suggestion: str  # 具体的、可操作的建议


class Suggestion(BaseModel):
    severity: Literal["minor", "enhancement"]
    aspect: str  # "scalability", "security", "maintainability", "cost", "simplicity"
    suggestion: str
```

#### 16.3.4 迭代决策逻辑

```python
# src/agents/critic.py

def make_verdict(feedback: CriticFeedback) -> str:
    """
    返回: "approved" | "iterate" | "error"
    """
    # 红线：critical 级别的 blocking issue
    if any(i.severity == "critical" for i in feedback.blocking_issues):
        if feedback.iteration >= feedback.max_iterations:
            return "approved"  # 达到最大迭代次数，强制通过但标注 unresolved
        return "iterate"

    # 阈值判定
    scores = feedback.scores
    if scores.coherence >= 0.6 and scores.feasibility >= 0.5:
        return "approved"

    if feedback.iteration >= feedback.max_iterations:
        return "approved"  # 强制通过

    return "iterate"
```

---

### 补充-4: Prompt 工程策略 —— 运行时组合与预算管理

> 对应不足：**「无 Prompt 工程策略」**

Section 9 已给出 4 个 Agent 的 YAML Prompt 模板。本节补全：运行时组装、预算分配、Few-shot 选择。

#### 16.4.1 Prompt 运行时组装管线

```python
# src/agents/prompts/__init__.py

class PromptBuilder:
    """从 YAML 模板 + 运行时状态 → 最终发送给 LLM 的 messages"""

    def __init__(self, yaml_dir: Path):
        self.templates = {
            "collector":  load_yaml(yaml_dir / "collector.yaml"),
            "weaver":     load_yaml(yaml_dir / "weaver.yaml"),
            "architect":  load_yaml(yaml_dir / "architect.yaml"),
            "critic":     load_yaml(yaml_dir / "critic.yaml"),
        }
        self.skill_loader = SkillLoader(Path("skills/"))

    async def build_collector_prompt(
        self, raw_input: RawInput, user_profile: UserProfile
    ) -> List[Dict[str, str]]:
        """
        组装 Collector 的完整 prompt。

        预算：~1500 tokens
        结构：
          1. system message (from YAML, ~800 tokens)
          2. user profile context (~100 tokens)    ← 动态注入
          3. few-shot examples (2-3, ~400 tokens)  ← 按领域匹配
          4. current input (~200 tokens)
        """
        template = self.templates["collector"]

        # 动态选择 few-shot：匹配用户高频领域
        few_shots = self._select_few_shots(
            template["few_shots"],
            user_profile.frequent_domains,
            k=2,
        )

        messages = [
            {"role": "system", "content": template["system"]},
        ]
        # 注入用户偏好上下文
        if user_profile.recurring_constraints:
            constraints = "\n".join(f"- {c}" for c in user_profile.recurring_constraints)
            messages.append({
                "role": "system",
                "content": f"用户的历史约束偏好：\n{constraints}"
            })

        for shot in few_shots:
            messages.append({"role": "user", "content": shot["input"]})
            messages.append({"role": "assistant", "content": shot["output"]})

        messages.append({"role": "user", "content": raw_input.content})
        return messages

    async def build_weaver_prompt(
        self, state: WeaverState, feedback: Optional[CriticFeedback]
    ) -> List[Dict[str, str]]:
        """
        组装 Weaver 的完整 prompt。

        预算：~8000 tokens（最大，因为 Weaver 是核心引擎）
        结构：
          1. system message (~1500 tokens)
          2. 北极星上下文 (~200 tokens)
          3. 簇摘要 (Level 1 压缩, ~1000 tokens)
          4. Top-K 节点详情 (Level 2 展开, ~3000 tokens)
          5. 关系子图邻接表 (Level 3, ~500 tokens)
          6. Critic 反馈 (如有迭代, ~300 tokens)
          7. 技能领域知识 (按需注入, ~1500 tokens)
        """
        template = self.templates["weaver"]

        # 检索相关领域技能
        skill_context = await self.skill_loader.load_relevant(
            domains=extract_domains(state["clusters"]),
            max_tokens=1500,
        )

        # 构建上下文的渐进式压缩
        context = self._build_progressive_context(state, feedback)

        messages = [
            {"role": "system", "content": template["system"]},
            {"role": "system", "content": skill_context},
            {"role": "user", "content": context},
        ]

        if feedback and feedback.blocking_issues:
            messages.append({
                "role": "user",
                "content": f"上一轮设计有以下问题需要修复：\n{format_feedback(feedback)}"
            })

        return messages

    def _select_few_shots(self, all_shots: List[dict],
                          domains: List[str], k: int) -> List[dict]:
        """按领域关键词匹配度选择最相关的 few-shot 示例"""
        if not domains:
            return all_shots[:k]
        scored = []
        for shot in all_shots:
            if isinstance(shot.get("output"), str):
                try:
                    output = json.loads(shot["output"])
                except json.JSONDecodeError:
                    continue
                shot_domains = set(output.get("context_tags", []))
                score = len(shot_domains.intersection(set(domains)))
                scored.append((score, shot))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:k]] or all_shots[:k]

    def _build_progressive_context(self, state: WeaverState,
                                   feedback: Optional[CriticFeedback]) -> str:
        """渐进式上下文组装（见补充-5 Token 管理）"""
        parts = []

        # Level 0: 北极星
        parts.append(f"## 北极星目标\n{state['north_star']}")
        parts.append(f"探索度数: {state.get('divergence_degree', 2)}")

        # Level 1: 簇摘要
        parts.append("## 已有概念簇")
        for c in state.get("clusters", []):
            parts.append(f"- **{c['name']}**: {c.get('summary', c.get('description', ''))}")

        # Level 2: 节点详情
        parts.append("## 待编织的想法节点")
        for i, node in enumerate(state.get("new_nodes", state.get("all_relevant_nodes", []))):
            parts.append(
                f"### 节点 {i+1}: {node.get('id', 'unknown')}\n"
                f"- 类型: {node.get('source_type', 'text')}\n"
                f"- 内容: {node.get('standardized_content', node.get('raw_content', ''))}\n"
                f"- 意图标签: {', '.join(node.get('intent_tags', []))}\n"
                f"- 领域标签: {', '.join(node.get('context_tags', []))}"
            )

        # Level 3: 关系图
        if state.get("relationships"):
            parts.append("## 已有关系（邻接表）")
            for r in state["relationships"]:
                parts.append(
                    f"- {r['source_node_id'][:8]} --[{r['relationship_type']}]--> "
                    f"{r['target_node_id'][:8]} (strength={r.get('strength', 0.5):.2f})"
                )

        return "\n\n".join(parts)
```

#### 16.4.2 各 Agent 的 Token 预算与模型选择

```python
# src/utils/config.py

class AgentProfile:
    """每个 Agent 的运行配置"""

AGENT_PROFILES = {
    "collector": {
        "model": "claude-haiku-4-5-20251001",  # 轻量任务用小模型
        "max_input_tokens": 2000,
        "max_output_tokens": 500,
        "temperature": 0.3,                     # 低温度：标准化输出
        "retry_count": 2,
    },
    "weaver": {
        "model": "claude-sonnet-5",             # 核心引擎用最强模型
        "max_input_tokens": 8000,
        "max_output_tokens": 4000,
        "temperature": 0.7,                     # 较高温度：鼓励创造性关联
        "retry_count": 2,
    },
    "architect": {
        "model": "claude-sonnet-5",
        "max_input_tokens": 6000,
        "max_output_tokens": 6000,              # 输出完整设计文档需要较多 token
        "temperature": 0.4,
        "retry_count": 1,
    },
    "critic": {
        "model": "claude-sonnet-5",             # 批判也需要强推理
        "max_input_tokens": 6000,
        "max_output_tokens": 2000,
        "temperature": 0.2,                     # 低温度：评估需要一致性
        "retry_count": 1,
    },
}
```

---

### 补充-5: Token 窗口管理 —— 压缩算法与检索策略

> 对应不足：**「Token 窗口管理空泛」**

#### 16.5.1 五级渐进式表示（完整定义）

```
┌─────────────────────────────────────────────────────────────┐
│ Level 0  北极星 + 会话元数据                                  │
│           内容: north_star, divergence_degree, session_status │
│           大小: ~100 tokens                                   │
│           时机: 始终在上下文中                                  │
│           更新: 会话创建/修改时                                 │
├─────────────────────────────────────────────────────────────┤
│ Level 1  簇摘要索引                                           │
│           内容: 每个 ConceptCluster 的 name + summary (1 段)   │
│           大小: ~200 tokens/簇 × max 5 簇 = ~1000 tokens      │
│           时机: Weaver 和 Architect 的上下文中                  │
│           更新: 每次编织完成后重新生成 summary                   │
│           生成: LLM 压缩 "用 1 段话概括该簇的核心洞见"          │
├─────────────────────────────────────────────────────────────┤
│ Level 2  活跃节点详情                                         │
│           内容: standardized_content + intent_tags +           │
│                 context_tags + 三项评分                        │
│           大小: ~300 tokens/节点 × max 10 节点 = ~3000 tokens  │
│           时机: 仅 Weaver 的上下文中                            │
│           选择: Top-K 向量相似度 + 衰减加权                     │
├─────────────────────────────────────────────────────────────┤
│ Level 3  关系结构子图                                         │
│           内容: 邻接表格式的图结构                              │
│                   "A --[causal]--> B"                         │
│           大小: ~500 tokens                                    │
│           选择: Level 2 选中节点的 1 跳邻域                     │
├─────────────────────────────────────────────────────────────┤
│ Level 4  迭代记忆                                             │
│           内容: 上一轮 CriticFeedback (blocking_issues +        │
│                 suggestions)                                  │
│           大小: ~300 tokens                                    │
│           时机: 仅迭代编织时（第二轮及以后）                     │
└─────────────────────────────────────────────────────────────┘
```

#### 16.5.2 检索策略：混合搜索

```python
# src/core/retrieval.py

class HybridRetriever:
    """
    向量相似度 (70%) + 关键词匹配 (20%) + 时间衰减 (10%)
    """

    def __init__(self, vector_store: VectorStore, idea_repo: IdeaRepo):
        self.vector_store = vector_store
        self.idea_repo = idea_repo
        self.decay_halflife_days = 30  # 30 天半衰期

    async def retrieve_for_weaving(
        self,
        north_star: str,
        north_star_embedding: List[float],
        new_node_ids: List[UUID],
        divergence_degree: int,
        max_nodes: int = 20,
    ) -> List[IdeaNode]:
        """
        为一次编织检索所有相关历史节点。

        策略：
        1. 以北极星为中心，向量检索 2*max_nodes 候选
        2. 计算每个节点的 north_star_relevance
        3. 关键词穿透：按 context_tags 精确匹配
        4. 时间衰减：旧节点得分降低
        5. K-hop 扩展：沿已有关系图展开 divergence_degree 跳
        6. 截断到 max_nodes
        """
        # Step 1: 向量检索
        candidates = await self.vector_store.search(
            north_star_embedding,
            k=max_nodes * 2,
            filter={"status": {"$ne": "dormant"}},  # 排除休眠节点
        )

        # Step 2: 计算相关性
        for c in candidates:
            c.north_star_relevance = c.similarity  # cosine similarity to north_star

        # Step 3: 关键词增强
        keyword_hits = await self.idea_repo.search_by_context_tags(
            tags=extract_keywords(north_star),
            limit=max_nodes,
        )
        for hit in keyword_hits:
            if hit.id not in [c.id for c in candidates]:
                candidates.append(hit)

        # Step 4: 时间衰减
        now = datetime.utcnow()
        for c in candidates:
            age_days = (now - c.created_at).days
            decay = 0.5 ** (age_days / self.decay_halflife_days)
            c.final_score = (
                c.north_star_relevance * 0.7
                + (1.0 if c in keyword_hits else 0.0) * 0.2
                + decay * 0.1
            )

        # Step 5: 排序截断
        candidates.sort(key=lambda c: c.final_score, reverse=True)
        selected = candidates[:max_nodes]

        # Step 6: K-hop 图扩展
        if divergence_degree > 0:
            expanded = await self._graph_expand(selected, divergence_degree)
            selected = list({n.id: n for n in selected + expanded}.values())[:max_nodes]

        return selected

    async def _graph_expand(self, seeds: List[IdeaNode], hops: int) -> List[IdeaNode]:
        """沿关系图扩展 K 跳"""
        visited = {n.id for n in seeds}
        frontier = set(visited)
        for _ in range(hops):
            neighbors = set()
            for nid in frontier:
                rels = await self.idea_repo.get_relationships(nid)
                for r in rels:
                    neighbor_id = r.target_node_id if r.source_node_id == nid else r.source_node_id
                    if neighbor_id not in visited:
                        neighbors.add(neighbor_id)
                        visited.add(neighbor_id)
            frontier = neighbors
        expanded = await self.idea_repo.get_by_ids(list(visited - {n.id for n in seeds}))
        return expanded
```

#### 16.5.3 截断策略

```python
# 当组装后的 prompt 仍超过 max_input_tokens 时的降级策略

def truncate_weaver_context(nodes: List[dict], relationships: List[dict],
                            max_tokens: int) -> Tuple[List[dict], List[dict]]:
    """
    降级顺序：
    1. 先减少节点数（保留高 relevance 的）
    2. 再压缩节点内容（只用 raw_content，丢弃 standardized_content）
    3. 最后裁减关系（只保留 strength > 0.7 的）
    """
    current_tokens = estimate_tokens(nodes, relationships)

    if current_tokens <= max_tokens:
        return nodes, relationships

    # Tier 1: 减少节点到 Top-5
    nodes = nodes[:5]
    current_tokens = estimate_tokens(nodes, relationships)
    if current_tokens <= max_tokens:
        return nodes, relationships

    # Tier 2: 使用短版内容
    for n in nodes:
        n["standardized_content"] = n.get("raw_content", "")[:200]  # 截断到 200 字符
    current_tokens = estimate_tokens(nodes, relationships)
    if current_tokens <= max_tokens:
        return nodes, relationships

    # Tier 3: 裁减弱关系
    relationships = [r for r in relationships if r.get("strength", 0) > 0.7]
    return nodes, relationships
```

---

### 补充-6: UI 层完整设计 —— WebView2 桥接与资产流

> 对应不足：**「UI 层完全缺失」**

Section 10 已给出浮窗和结果页的视觉设计。本节补全：Python ↔ JS 通信、剪贴板处理、录音管线。

#### 16.6.1 Python ↔ WebView2 双向通信

```python
# src/ui/overlay_window.py

import webview

class CaptureOverlay:
    """快捷键唤起的捕获浮窗"""

    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 400
    API_PORT = 8765

    def __init__(self):
        self.window = None
        self._api = OverlayAPI()  # 暴露给 JS 的 Python 对象

    def show(self):
        """显示浮窗（在主线程中调用）"""
        if self.window is None:
            self.window = webview.create_window(
                title="Idea Weaver",
                url=str(Path("src/ui/static/index.html").resolve()),
                width=self.WINDOW_WIDTH,
                height=self.WINDOW_HEIGHT,
                frameless=True,          # 无边框
                on_top=True,             # 置顶
                easy_drag=False,         # 禁止拖拽（固定居中）
                background_color="#1e1e2e",  # 暗色背景
            )
            # 暴露 Python 方法给 JS
            self.window.expose(self._api)
        else:
            self.window.show()
            self.window.restore()

    def hide(self):
        if self.window:
            self.window.hide()

    def center_on_active_monitor(self):
        """在活动显示器上居中"""
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        # 获取前台窗口所在显示器的 work area
        hwnd = user32.GetForegroundWindow()
        monitor = user32.MonitorFromWindow(hwnd, 0x00000002)  # MONITOR_DEFAULTTONEAREST

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(monitor, ctypes.byref(mi))

        work_width = mi.rcWork.right - mi.rcWork.left
        work_height = mi.rcWork.bottom - mi.rcWork.top
        x = mi.rcWork.left + (work_width - self.WINDOW_WIDTH) // 2
        y = mi.rcWork.top + (work_height - self.WINDOW_HEIGHT) // 2

        self.window.move(x, y)


class OverlayAPI:
    """暴露给 JavaScript 的 API 对象"""

    def submit_idea(self, content: str, source_type: str = "text",
                    file_path: str = None) -> dict:
        """
        JS 调用: window.pywebview.api.submit_idea(...)
        将想法提交给后端 FastAPI。
        """
        import httpx

        data = {"content": content, "source_type": source_type}
        if file_path:
            with open(file_path, "rb") as f:
                files = {"file": f}
                resp = httpx.post(
                    f"http://localhost:{CaptureOverlay.API_PORT}/api/ideas",
                    data=data, files=files, timeout=10,
                )
        else:
            resp = httpx.post(
                f"http://localhost:{CaptureOverlay.API_PORT}/api/ideas",
                data=data, timeout=10,
            )
        return resp.json()

    def get_sessions(self) -> list:
        """获取活跃会话列表"""
        import httpx
        resp = httpx.get(
            f"http://localhost:{CaptureOverlay.API_PORT}/api/sessions",
            timeout=5,
        )
        return resp.json()

    def start_weave(self, session_id: str) -> dict:
        """触发编织"""
        import httpx
        resp = httpx.post(
            f"http://localhost:{CaptureOverlay.API_PORT}/api/sessions/{session_id}/weave",
            timeout=5,
        )
        return resp.json()

    def notify(self, title: str, message: str):
        """系统通知（通过 pystray）"""
        # 调用主线程的 tray 对象
        pass
```

#### 16.6.2 前端剪贴板处理

```javascript
// src/ui/static/app.js

class CaptureApp {
    constructor() {
        this.textArea = document.getElementById('idea-input');
        this.pasteZone = document.getElementById('paste-zone');
        this.audioBtn = document.getElementById('mic-btn');
        this.submitBtn = document.getElementById('submit-btn');
        this.pastedFiles = [];  // {name, dataUrl, blob}
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;

        this.init();
    }

    init() {
        // 自动聚焦
        this.textArea.focus();

        // 全局粘贴事件
        document.addEventListener('paste', (e) => this.handlePaste(e));

        // Ctrl+Enter 提交
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') this.submit();
            if (e.key === 'Escape') this.dismiss();
        });

        // 麦克风按钮
        this.audioBtn.addEventListener('click', () => this.toggleRecording());
    }

    async handlePaste(e) {
        const items = e.clipboardData?.items;
        if (!items) return;

        for (const item of items) {
            if (item.type.startsWith('image/')) {
                e.preventDefault();
                const blob = item.getAsFile();
                const dataUrl = await this.blobToDataUrl(blob);
                this.pastedFiles.push({
                    name: `clipboard-${Date.now()}.png`,
                    dataUrl: dataUrl,
                    blob: blob,
                });
                this.renderThumbnails();
            }
        }
    }

    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        this.audioChunks = [];

        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) this.audioChunks.push(e.data);
        };

        this.mediaRecorder.onstop = async () => {
            const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
            const dataUrl = await this.blobToDataUrl(blob);
            this.pastedFiles.push({
                name: `recording-${Date.now()}.webm`,
                dataUrl: dataUrl,
                blob: blob,
            });
            this.renderThumbnails();
            stream.getTracks().forEach(t => t.stop());
        };

        this.mediaRecorder.start();
        this.isRecording = true;
        this.audioBtn.classList.add('recording');
        this.audioBtn.textContent = '⏹ 停止';
    }

    stopRecording() {
        this.mediaRecorder?.stop();
        this.isRecording = false;
        this.audioBtn.classList.remove('recording');
        this.audioBtn.textContent = '🎤 录音';
    }

    async submit() {
        const text = this.textArea.value.trim();

        if (!text && this.pastedFiles.length === 0) return;

        this.submitBtn.disabled = true;
        this.submitBtn.textContent = '提交中...';

        try {
            // Step 1: 上传文件（如有），获取临时路径
            const uploadedPaths = [];
            for (const file of this.pastedFiles) {
                const formData = new FormData();
                formData.append('file', file.blob, file.name);
                const resp = await fetch('http://localhost:8765/api/assets/upload', {
                    method: 'POST',
                    body: formData,
                });
                const result = await resp.json();
                uploadedPaths.push(result.path);
            }

            // Step 2: 提交想法
            const ideaResp = await fetch('http://localhost:8765/api/ideas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: text || '(图片/语音输入)',
                    source_type: uploadedPaths.length > 0 ? 'image' : 'text',
                    asset_paths: uploadedPaths,
                }),
            });

            if (ideaResp.ok) {
                // Step 3: 通知 Python 侧关闭浮窗
                window.pywebview?.api?.notify('已捕获', '想法已保存');
                this.reset();
                // 关闭浮窗
                window.close();
            }
        } catch (err) {
            console.error('提交失败:', err);
            this.submitBtn.textContent = '重试';
            this.submitBtn.disabled = false;
        }
    }

    dismiss() {
        this.reset();
        window.close();
    }

    reset() {
        this.textArea.value = '';
        this.pastedFiles = [];
        this.renderThumbnails();
        this.submitBtn.disabled = false;
        this.submitBtn.textContent = 'Ctrl+↵ 提交';
    }

    renderThumbnails() {
        this.pasteZone.innerHTML = this.pastedFiles.map((f, i) => `
            <div class="thumbnail">
                ${f.dataUrl.startsWith('data:image')
                    ? `<img src="${f.dataUrl}" alt="${f.name}">`
                    : `<span class="audio-icon">🎵 ${f.name}</span>`}
                <button class="remove-btn" data-index="${i}">✕</button>
            </div>
        `).join('');

        // 绑定删除按钮
        this.pasteZone.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.target.dataset.index);
                this.pastedFiles.splice(idx, 1);
                this.renderThumbnails();
            });
        });
    }

    blobToDataUrl(blob) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.readAsDataURL(blob);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new CaptureApp());
```

#### 16.6.3 资产上传路由

```python
# src/api/routes/assets.py

from fastapi import APIRouter, UploadFile, File
from pathlib import Path

router = APIRouter(prefix="/api/assets", tags=["assets"])

ASSETS_DIR = Path("data/assets")

@router.post("/upload")
async def upload_asset(file: UploadFile = File(...)):
    """上传图片/音频文件，返回本地路径"""
    import uuid
    suffix = Path(file.filename).suffix if file.filename else ".bin"
    asset_id = str(uuid.uuid4())
    subdir = "images" if file.content_type.startswith("image") else "audio"
    target_dir = ASSETS_DIR / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{asset_id}{suffix}"
    content = await file.read()
    target_path.write_bytes(content)

    return {
        "path": str(target_path.relative_to(Path.cwd())),
        "asset_id": asset_id,
        "content_type": file.content_type,
        "size": len(content),
    }
```

---

### 补充-7: 并发模型 —— 会话生命周期与状态机

> 对应不足：**「无并发模型」**

#### 16.7.1 会话状态机

```
                    ┌─────────────┐
                    │ collecting  │ ← 创建会话 / 提交新想法
                    └──────┬──────┘
                           │ POST /sessions/{id}/weave
                           ▼
                    ┌─────────────┐
                    │  weaving    │ ← Weaver Agent 运行中
                    └──────┬──────┘
                           │ Weaver 完成
                           ▼
                    ┌─────────────┐
                    │architecting │ ← Architect Agent 运行中
                    └──────┬──────┘
                           │ Architect 完成
                           ▼
                    ┌─────────────┐
               ┌───│ critiquing  │ ← Critic Agent 运行中
               │   └──────┬──────┘
               │          │ Critic 判定
               │          ▼
               │   ╔══════════════╗
               │   ║  iterate?    ║── Yes ──→ weaving (带着 feedback)
               │   ╚══════════════╝
               │          │ No
               │          ▼
               │   ┌─────────────┐
               └───│  complete   │ ← 设计文档已通过，等待用户查看
                   └─────────────┘

    任意阶段可进入 ──→ ┌─────────────┐
                      │   failed    │ ← 不可恢复的错误
                      └─────────────┘
```

#### 16.7.2 并发控制实现

```python
# src/core/concurrency.py

import asyncio
from enum import Enum
from collections import deque

class SessionState(str, Enum):
    COLLECTING = "collecting"
    WEAVING = "weaving"
    ARCHITECTING = "architecting"
    CRITIQUING = "critiquing"
    COMPLETE = "complete"
    FAILED = "failed"

class SessionManager:
    """
    管理所有活跃编织会话的并发。

    约束：
    - 同一时刻只有 1 个会话处于处理中（weaving/architecting/critiquing）
    - 其他会话的编织请求排队
    - 新想法可以在任意时刻提交（不阻塞）
    """

    def __init__(self):
        self.sessions: Dict[str, WeaverSession] = {}
        self._processing_queue: deque[str] = deque()  # 排队中的 session_id
        self._active_session_id: Optional[str] = None
        self._lock = asyncio.Lock()
        self._processing_event = asyncio.Event()

    async def submit_idea(self, idea: IdeaNode,
                          session_id: Optional[str] = None) -> WeaverSession:
        """提交想法——永不阻塞"""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
        else:
            session = await self._create_session()
        session.input_idea_ids.append(idea.id)
        await self._save_session(session)
        return session

    async def request_weave(self, session_id: str) -> str:
        """
        请求编织——可能排队。

        返回: "started" | "queued"
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            if self._active_session_id is not None:
                # 已有编织在运行，排队
                self._processing_queue.append(session_id)
                return "queued"

            # 立即开始
            self._active_session_id = session_id
            asyncio.create_task(self._run_workflow(session_id))
            return "started"

    async def _run_workflow(self, session_id: str):
        """运行编织工作流（后台任务）"""
        try:
            session = self.sessions[session_id]
            session.status = SessionState.WEAVING
            await self._save_session(session)

            # 调用 LangGraph workflow
            result = await self._workflow_executor.run(session)

            session.status = SessionState.COMPLETE
            session.output_design_id = result.design_id
            session.completed_at = datetime.utcnow()
            await self._save_session(session)

        except Exception as e:
            session.status = SessionState.FAILED
            session.errors.append(str(e))
            await self._save_session(session)

        finally:
            async with self._lock:
                self._active_session_id = None
                # 处理排队的下一个
                if self._processing_queue:
                    next_id = self._processing_queue.popleft()
                    self._active_session_id = next_id
                    asyncio.create_task(self._run_workflow(next_id))

    def get_queue_position(self, session_id: str) -> int:
        """查询在队列中的位置"""
        try:
            return list(self._processing_queue).index(session_id)
        except ValueError:
            return -1  # 不在队列中
```

#### 16.7.3 并发场景处理矩阵

| 场景 | 处理方式 |
|---|---|
| 编织中提交新想法到同一会话 | 想法立即持久化，但不影响正在运行的工作流。需要用户手动再次触发编织 |
| 编织中提交新想法到新会话 | 新会话创建为 collecting 状态，等当前编织完成后排队 |
| 编织中再次请求同一会话编织 | 返回 `{"status": "already_running"}` |
| 多个会话同时请求编织 | 第一个立即执行，其余按 FIFO 排队 |
| 编织中进程被 kill | 重启后 LangGraph checkpoint 恢复，从中断点继续 |
| Critic 判定 iterate | 同一会话状态回退到 weaving，不释放锁 |

---

### 补充-8: 可观测性 —— 日志、追踪与调试工具

> 对应不足：**「无可观测性」**

#### 16.8.1 结构化日志 Schema

```python
# src/utils/logging_config.py

import loguru
import sys
from pathlib import Path

# 日志格式
LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{extra[component]: <15} | "
    "{extra[trace_id]: <8} | "
    "{message}"
)

def setup_logging():
    loguru.logger.remove()  # 移除默认 handler

    # 控制台输出（开发时）
    loguru.logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level="DEBUG",
        colorize=True,
    )

    # 文件输出（始终）
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    loguru.logger.add(
        "data/logs/weaver_{time:YYYY-MM-DD}.log",
        format=LOG_FORMAT,
        level="INFO",
        rotation="00:00",       # 每天轮转
        retention="30 days",    # 保留 30 天
        compression="gz",       # 压缩归档
    )

    # 错误单独文件
    loguru.logger.add(
        "data/logs/errors_{time:YYYY-MM-DD}.log",
        format=LOG_FORMAT,
        level="ERROR",
        rotation="00:00",
        retention="90 days",
    )

    return loguru.logger

# 使用示例
# logger.bind(component="collector", trace_id="abc123").info("idea normalized", idea_id="uuid")
```

#### 16.8.2 追踪上下文

```python
# src/utils/tracing.py

import uuid
from contextvars import ContextVar
from contextlib import contextmanager

# 协程安全的上下文变量
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_id: ContextVar[str] = ContextVar("span_id", default="")
_component: ContextVar[str] = ContextVar("component", default="system")

def new_trace() -> str:
    """生成新的 trace_id（每个编织会话一个）"""
    tid = str(uuid.uuid4())[:8]
    _trace_id.set(tid)
    return tid

@contextmanager
def span(component: str, operation: str):
    """
    创建一个追踪 span。

    Usage:
        with span("weaver", "semantic_cluster"):
            ...
    """
    sid = str(uuid.uuid4())[:8]
    prev_span = _span_id.get()
    prev_comp = _component.get()
    _span_id.set(sid)
    _component.set(component)

    logger.bind(
        trace_id=_trace_id.get(),
        span_id=sid,
        component=component,
    ).info(f"[SPAN START] {operation}")

    import time
    start = time.monotonic()
    try:
        yield
    except Exception as e:
        logger.bind(
            trace_id=_trace_id.get(),
            span_id=sid,
            component=component,
        ).error(f"[SPAN ERROR] {operation}: {e}")
        raise
    finally:
        elapsed = time.monotonic() - start
        logger.bind(
            trace_id=_trace_id.get(),
            span_id=sid,
            component=component,
        ).info(f"[SPAN END] {operation} ({elapsed:.2f}s)")
        _span_id.set(prev_span)
        _component.set(prev_comp)
```

#### 16.8.3 LLM 调用追踪

```python
# src/agents/base.py

class LLMTracer:
    """记录每次 LLM 调用的详细信息"""

    def __init__(self):
        self.calls: List[LLMCallRecord] = []

    def record(self, agent_name: str, model: str,
               input_tokens: int, output_tokens: int,
               latency_ms: float, cost_usd: float,
               success: bool, error: Optional[str] = None):
        self.calls.append(LLMCallRecord(
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            error=error,
            trace_id=_trace_id.get(),
            timestamp=datetime.utcnow(),
        ))

    def summary(self) -> dict:
        """返回当前会话的 LLM 调用摘要"""
        total_cost = sum(c.cost_usd for c in self.calls)
        total_latency = sum(c.latency_ms for c in self.calls)
        return {
            "total_calls": len(self.calls),
            "by_agent": {
                name: len([c for c in self.calls if c.agent_name == name])
                for name in set(c.agent_name for c in self.calls)
            },
            "total_cost_usd": round(total_cost, 4),
            "total_latency_ms": total_latency,
            "failures": [c for c in self.calls if not c.success],
        }


class LLMCallRecord(BaseModel):
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    success: bool
    error: Optional[str] = None
    trace_id: str
    timestamp: datetime
```

#### 16.8.4 WebSocket 进度协议（完整定义）

```python
# src/api/websocket_manager.py

class ProgressMessage(BaseModel):
    """推送给前端的进度消息"""
    trace_id: str
    session_id: str
    phase: Literal[
        "collecting",        # 正在收集和准备节点
        "semantic_search",   # 向量检索历史相关想法
        "clustering",        # 语义聚类中
        "building_relations",# 构建关系图
        "designing",         # 生成设计文档
        "critiquing",        # 批判评估中
        "iterating",         # 进入下一轮迭代
        "complete",          # 完成
        "error",             # 出错
    ]
    progress: float         # 0.0 - 1.0
    message: str            # 人类可读的描述
    detail: Optional[dict] = None  # 阶段特定的负载

    # 示例：
    # {"phase": "clustering", "progress": 0.35,
    #  "message": "发现 3 个概念簇", "detail": {"cluster_count": 3, "cluster_names": [...]}}
    # {"phase": "building_relations", "progress": 0.55,
    #  "message": "找到 2 条跨领域桥梁",
    #  "detail": {"bridges": [{"from": "高速公路类比", "to": "优先级队列", "domains": ["交通", "CS"]}]}}
```

#### 16.8.5 调试端点

```python
# src/api/routes/debug.py  (仅开发环境启用)

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/sessions/{session_id}/trace")
async def get_trace(session_id: str):
    """获取某次编织的完整执行追踪"""
    # 返回: LLM调用链、各阶段耗时、中间状态快照

@router.get("/sessions/{session_id}/state-snapshot")
async def get_state_snapshot(session_id: str):
    """获取 LangGraph checkpoint 的当前状态快照"""
    # 返回: 完整的 WeaverState dict

@router.get("/graph/{session_id}")
async def get_idea_graph(session_id: str):
    """导出当前想法图谱为 JSON（用于调试可视化）"""
    # 返回: nodes + edges JSON，可直接加载到 D3.js

@router.get("/llm-calls")
async def get_llm_calls(hours: int = 24):
    """查看最近 N 小时的 LLM 调用统计"""
    # 返回: 按 Agent/模型分组的调用次数、费用、延迟

@router.get("/prompts/{agent_name}")
async def preview_prompt(agent_name: str, session_id: str):
    """预览某 Agent 在当前会话状态下的完整组装 prompt（调试用）"""
    # 返回: 完整的 messages 数组——帮助理解 LLM 实际收到了什么
```

---

## 17. 模块耦合度分析

> 对整个系统（11 个文件结构目录 × 30+ 源文件）进行静态依赖分析，
> 识别耦合热点，量化耦合级别，提出解耦方案。

### 17.1 模块依赖矩阵

下表中 **→** 表示"行依赖列"（编译时 import 或运行时调用）。

```
         被依赖方:   models  base  coll  weav  arch  crit  wf   grph  embd  stmgr  api  tray  ovly  hotk  db  i-rep  c-rep  d-rep  s-rep  v-sto  f-sto  cfg  log  whsp  metr  skills
依赖方:
models      ·       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
base        ✓       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
collector   ✓       ✓     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ✓      ·      ·      ·      ✓      ✓     ·    ·    ✓     ·      ·
weaver      ✓       ✓     ·     ·     ·     ·     ·    ✓     ✓     ·     ·    ·     ·     ·    ·    ✓      ✓      ·      ·      ✓      ·     ·    ·    ·     ·      ·
architect   ✓       ✓     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ·      ✓      ·      ✓      ·      ·     ·    ·    ·     ·      ✓
critic      ✓       ✓     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ✓      ·      ·      ✓      ·      ·     ·    ·    ·     ✓      ·
workflow    ✓       ·     ✓     ✓     ✓     ✓     ·    ·     ·     ✓     ·    ·     ·     ·    ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ✓      ·
graph_ops   ✓       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
embeddings  ✓       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
state_mgr   ✓       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ·      ·      ·      ·      ✓      ·     ·    ·    ·     ·      ·
api/ideas   ✓       ·     ✓     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ✓      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
api/weave   ✓       ·     ·     ·     ·     ·     ✓    ·     ·     ·     ·    ·     ·     ·    ·    ·      ·      ·      ·      ✓      ·     ·    ·    ·     ·      ·
api/designs ✓       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·    ·    ·      ·      ·      ✓      ·      ·     ·    ·    ·     ·      ·
tray_app    ·       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ✓     ·     ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
hotkey_lst  ·       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ✓     ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
overlay_win ·       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·     ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
db          ✓       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·     ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
idea_repo   ✓       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ✓     ·     ·     ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
v_store     ✓       ·     ·     ·     ·     ·     ·    ·     ✓     ·     ·    ·     ·     ·     ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
whisper_tr  ·       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·     ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·
metrics     ✓       ·     ·     ·     ·     ·     ·    ·     ·     ·     ·    ·     ·     ·     ·    ·      ·      ·      ·      ·      ·     ·    ·    ·     ·      ·

图例:
  ✓ = 存在编译时/运行时依赖
  · = 无直接依赖
  灰底 = 高频被依赖项（热点）
```

### 17.2 耦合热点排名

按被依赖次数排序，识别系统中最"重"的模块：

| 排名 | 模块 | 被依赖次数 | 耦合类型 | 风险 |
|---|---|---|---|---|
| 🔴 **P0** | **`core/models.py`** | 18 | 内容耦合（共享数据结构） | 改一个字段，18 个模块受影响 |
| 🔴 **P0** | **`core/workflow.py`** | 5 (输入) + 4 (输出) | 控制耦合（编排所有 Agent） | God Module——任何 Agent 接口变化都要求改 workflow |
| 🔴 **P0** | **`WeaverState` (TypedDict)** | 6 个节点 + 3 个工具 | 公共耦合（共享全局状态） | 字段改名 → 6 个 LangGraph 节点全部崩溃 |
| 🟡 **P1** | **`agents/base.py`** | 4 | 内容耦合（Agent 都继承同一个基类） | 基类修改重试逻辑 → 4 个 Agent 行为全部改变 |
| 🟡 **P1** | **`storage/database.py`** | 4 (repo) + 1 (cli) | 公共耦合（共享 DB 连接） | 连接池参数改动影响所有 repo |
| 🟡 **P1** | **`agents/weaver.py`** | 2 (workflow + 自身) | 内聚度低（承担 4 项任务） | 最复杂的 Agent，但输入依赖多达 5 个外部模块 |
| 🟢 **P2** | **`utils/metrics.py`** | 2 (critic + workflow) | 数据耦合 | 评分公式变更影响两个模块，但有明确契约 |
| 🟢 **P2** | **`ui/overlay_window.py`** | 2 (tray + hotkey) | 控制耦合 | UI 层的自然依赖，可接受 |

### 17.3 六大致命耦合问题

#### 问题 1: `workflow.py` 是 God Module

```
workflow.py
├── from agents.collector import CollectorAgent    ← 直接 import
├── from agents.weaver import WeaverAgent
├── from agents.architect import ArchitectAgent
├── from agents.critic import CriticAgent
├── from core.models import *
├── from utils.metrics import *
└── 6 个 LangGraph 节点函数全部定义在此文件

影响:
  · 任何 Agent 的 __init__ 签名改变 → workflow.py 必须改
  · 无法单独测试 workflow graph 结构（与 Agent 实现强绑定）
  · 新增 Agent 类型需要修改 workflow.py（违反开闭原则）
```

**解耦方案 —— Node Registry 模式：**

```python
# 当前（紧耦合）：
# workflow.py 直接 import 并实例化每个 Agent

# 改进后（松耦合）：
# src/core/node_registry.py

from typing import Protocol, Callable, Dict

class WorkflowNode(Protocol):
    """每个 Agent 用 @register_node 注册自己的节点"""
    node_name: str
    def execute(self, state: WeaverState) -> WeaverState: ...

_NODE_REGISTRY: Dict[str, Callable] = {}

def register_node(name: str):
    """装饰器：Agent 自注册工作流节点"""
    def decorator(func):
        _NODE_REGISTRY[name] = func
        return func
    return decorator

def get_node(name: str) -> Callable:
    return _NODE_REGISTRY[name]

# === 使用 ===
# src/agents/collector.py
from core.node_registry import register_node

@register_node("collect_and_prepare")
async def collect_and_prepare_node(state: WeaverState) -> WeaverState:
    """Collector 自己负责注册和实现"""
    ...

# src/core/workflow.py  —— 现在只负责编排，不负责实现
def build_weaving_workflow() -> StateGraph:
    workflow = StateGraph(WeaverState)
    for node_name in ["collect_and_prepare", "semantic_cluster", ...]:
        workflow.add_node(node_name, get_node(node_name))  # 从 registry 获取
    # ... 剩下的边定义
```

#### 问题 2: `WeaverState` TypedDict 是公共耦合

```python
# 当前问题：
# 6 个节点函数 + 3 个工具函数全部读写同一个 TypedDict
# TypedDict 无运行时校验，字段名拼错 → 运行时 KeyError
# 一个节点向 state 中塞入了下游不需要的字段 → 隐式契约

class WeaverState(TypedDict):
    session_id: str
    north_star: str
    new_nodes: List[dict]        # ← dict 无结构保证，可能缺失字段
    all_relevant_nodes: List[dict]
    clusters: List[dict]
    relationships: List[dict]
    design_draft: Optional[dict]
    critic_feedback: Optional[str]  # ← 为什么是 str 但别处期望 dict?
    critic_scores: Optional[dict]
    iteration: int
    max_iterations: int
    status: str                    # ← 为什么不是 Literal?
    errors: List[str]
```

**解耦方案 —— 节点级输入/输出契约：**

```python
# src/core/node_contracts.py

from pydantic import BaseModel
from typing import List, Optional

class ClusterInput(BaseModel):
    """semantic_cluster 节点的精确输入"""
    session_id: str
    north_star: str
    new_nodes: List[IdeaNodeSummary]    # ← 强类型，不再是 dict
    all_relevant_nodes: List[IdeaNodeSummary]
    divergence_degree: int = 2

class ClusterOutput(BaseModel):
    """semantic_cluster 节点的精确输出"""
    clusters: List[ConceptCluster]
    status: str = "clustered"

class RelationshipInput(BaseModel):
    """build_relationships 节点的精确输入"""
    session_id: str
    clusters: List[ConceptCluster]
    critic_feedback: Optional[CriticFeedback] = None   # ← 强类型
    iteration: int = 1

class RelationshipOutput(BaseModel):
    relationships: List[Relationship]
    cross_domain_bridges: List[CrossDomainBridge]
    conflicts: List[ConflictInfo]

# 全局 WeaverState 从 14 个字段降为 6 个：
class WeaverState(TypedDict, total=False):
    """仅保留跨节点共享的最小状态"""
    session_id: str
    north_star: str
    iteration: int
    max_iterations: int
    status: str
    errors: List[str]
    # 阶段产物不再混在顶层，改为嵌套在 phases 下：
    phases: dict  # {"collect": {...}, "cluster": ClusterOutput, "design": DesignOutput, ...}
```

#### 问题 3: Weaver Agent 输入扇入过大 + 职责过载

```
weaver.py 的依赖扇入（5 个外部模块）:
  ├── storage/idea_repo.py       → 读想法
  ├── storage/cluster_repo.py    → 写概念簇
  ├── storage/vector_store.py    → 语义搜索
  ├── core/graph_ops.py          → 图计算
  ├── core/embeddings.py         → 生成 embedding
  └── 同时承担 4 项职责:
      ① 语义聚类         ② 关系发现
      ③ 跨域桥梁识别      ④ 冲突检测

问题:
  · 5 个依赖中任一接口变化 → weaver.py 必须改
  · 4 项职责无法独立测试、独立部署
  · 单文件过大（预计 500+ 行），难以维护
```

**解耦方案 —— Weaver 内部组件化：**

```python
# src/agents/weaver/  (从单文件变为包)
# ├── __init__.py       # 外观模式：对外只暴露 weave()
# ├── clusterer.py      # 职责①: 语义聚类
# ├── relationship_builder.py  # 职责②: 关系发现
# ├── bridge_finder.py  # 职责③: 跨域桥梁
# └── conflict_detector.py     # 职责④: 冲突检测

# 每个子组件有窄接口：
class Clusterer:
    """只依赖 vector_store + embeddings"""
    def __init__(self, vector_store: VectorStore, embeddings: EmbeddingService):
        ...
    async def cluster(self, nodes: List[IdeaNode]) -> List[ConceptCluster]:
        ...

class RelationshipBuilder:
    """只依赖 graph_ops"""
    def __init__(self, graph_ops: GraphOps):
        ...
    async def discover(self, nodes: List[IdeaNode],
                       clusters: List[ConceptCluster]) -> List[Relationship]:
        ...

class ConflictDetector:
    """无外部依赖（纯 LLM + 逻辑）"""
    async def detect(self, nodes: List[IdeaNode],
                     relationships: List[Relationship]) -> List[ConflictInfo]:
        ...

# __init__.py 中组装：
async def weave(nodes, north_star, feedback=None):
    clusters = await clusterer.cluster(nodes)
    relationships = await rel_builder.discover(nodes, clusters)
    bridges = await bridge_finder.find(clusters, relationships)
    conflicts = await conflict_detector.detect(nodes, relationships)
    return clusters, relationships, bridges, conflicts
```

#### 问题 4: Agent 直接依赖 LiteLLM（缺少抽象层）

```python
# 当前（紧耦合）:
# src/agents/base.py
import litellm  # ← 硬依赖外部库

class BaseAgent:
    async def call_llm(self, messages):
        response = await litellm.acompletion(  # ← 直接调用
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return response

# 问题:
#   · 每个 Agent 通过 base.py 间接绑定了 LiteLLM
#   · 测试时必须 mock LiteLLM（重）
#   · 如果要切换为本地模型（如 Ollama HTTP API），需要改动 BaseAgent
#   · 如果需要 A/B 测试两个 LLM provider，当前架构不支持
```

**解耦方案 —— LLM Service 抽象：**

```python
# src/core/llm_service.py

from abc import ABC, abstractmethod

class LLMService(ABC):
    """与 LLM 供应商无关的抽象接口"""

    @abstractmethod
    async def complete(self,
                       messages: List[Dict[str, str]],
                       model: str,
                       temperature: float = 0.7,
                       max_tokens: int = 4000,
                       response_format: Optional[dict] = None,
                       ) -> LLMResponse:
        ...

    @abstractmethod
    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        ...

class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float

# === LiteLLM 实现 ===
class LiteLLMService(LLMService):
    async def complete(self, messages, model, temperature, max_tokens, response_format):
        resp = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        return LLMResponse(
            content=resp.choices[0].message.content,
            model=resp.model,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            cost_usd=litellm.cost_calculator.completion_cost(resp),
            latency_ms=resp._response_ms,
        )

# BaseAgent 改为依赖注入：
class BaseAgent:
    def __init__(self, llm: LLMService, config: AgentProfile):
        self.llm = llm     # ← 抽象依赖，可替换
        self.config = config

    async def call_llm(self, messages):
        return await self.llm.complete(
            messages=messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens,
        )

# 测试时注入 FakeLLMService：
class FakeLLMService(LLMService):
    def __init__(self, canned_responses: List[str]):
        self.responses = canned_responses
        self.call_count = 0

    async def complete(self, messages, model, temperature, max_tokens, response_format):
        resp = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return LLMResponse(content=resp, model="fake", input_tokens=0,
                           output_tokens=0, cost_usd=0, latency_ms=0)
```

#### 问题 5: SQLite + ChromaDB 双写一致性

```python
# 当前的问题路径：
# src/agents/collector.py

async def process(self, raw: RawInput) -> IdeaNode:
    # Step A: 写入 SQLite
    node = await self.idea_repo.create(idea_node)

    # Step B: 写入 ChromaDB
    embedding = await self.embeddings.generate(node.standardized_content)
    await self.vector_store.add(node.id, embedding, metadata)

    # ⚠️ 危险窗口：Step A 成功 + Step B 失败 = 数据不一致
    #   SQLite 中有记录但没有 embedding → 搜索时找不到
    #   或者 embedding 但没有结构化记录 → 搜索结果无法解析
```

**解耦方案 —— Write-Ahead + 补偿模式：**

```python
# src/storage/unit_of_work.py

class IdeaUnitOfWork:
    """
    保证 SQLite 和 ChromaDB 的最终一致性。

    策略：SQLite 是主存储（source of truth），ChromaDB 是派生。
    写入流程：
      1. 写入 SQLite（同步提交）
      2. embedding 生成放入 pending 队列
      3. 后台 worker 消费队列 → 写入 ChromaDB
      4. 写入成功后标记 SQLite 中 embedding_status = 'ready'
      5. 失败则重试 3 次 → 仍失败标记 'failed'

    恢复：
      启动时扫描 embedding_status != 'ready' 的节点，重新入队。
    """

    async def create_idea(self, idea: IdeaNode) -> IdeaNode:
        # Step 1: 写入主存储（原子）
        idea.embedding_status = "pending"
        node = await self.idea_repo.create(idea)

        # Step 2: 入队（非阻塞）
        await self.embedding_queue.enqueue(node.id, node.standardized_content)

        return node

# idea_nodes 表新增字段：
#   embedding_status TEXT DEFAULT 'pending' CHECK(embedding_status IN
#     ('pending', 'generating', 'ready', 'failed'))
```

#### 问题 6: API 路由直接依赖 Agent 实现

```python
# 当前（紧耦合）:
# src/api/routes/weaving.py
from core.workflow import build_weaving_workflow  # ← 路由 → workflow → 所有 Agent

# 问题：
#   · API 路由间接知道了所有 Agent 的存在
#   · 如果想替换 Workflow 引擎（例如从 LangGraph 换成 Temporal），路由也要改
#   · 路由的单元测试必须 mock 整个 workflow
```

**解耦方案 —— Application Service 层：**

```python
# src/services/weaving_service.py  (新层)

from abc import ABC, abstractmethod

class WeavingService(ABC):
    """编织用例的抽象接口。API 路由只依赖此接口。"""

    @abstractmethod
    async def start_weave(self, session_id: str,
                          divergence_degree: int = 2) -> WeaveResult:
        ...

    @abstractmethod
    async def get_progress(self, session_id: str) -> WeaveProgress:
        ...

# === LangGraph 实现 ===
class LangGraphWeavingService(WeavingService):
    def __init__(self, workflow: StateGraph, session_repo, ws_manager):
        self.workflow = workflow
        ...

    async def start_weave(self, session_id, divergence_degree):
        # 委托给 LangGraph workflow
        ...

# === API 路由（只依赖抽象） ===
# src/api/routes/weaving.py
from src.services.weaving_service import WeavingService  # 抽象，非实现

router = APIRouter()

@router.post("/api/sessions/{session_id}/weave")
async def trigger_weave(
    session_id: str,
    weaving_service: WeavingService = Depends(get_weaving_service),  # DI
):
    result = await weaving_service.start_weave(session_id)
    return result
```

### 17.4 耦合度改善前后对比

```
指标                            改善前          改善后          改善幅度
────────────────────────────────────────────────────────────────────
core/models.py 被依赖数          18 个模块       18 个模块        — (基础层，不可减少)
workflow.py 直接 import 数       5 个 Agent      0 个 Agent       -5（Node Registry）
Weaver 扇入依赖数                5 个模块        2-3 个/子组件    -40%（组件化拆分）
Agent → LLM 耦合                 直接依赖 LiteLLM  依赖 LLMService  从内容耦合降为数据耦合
双写一致性                       无保障           最终一致性      从无到有
API → Agent 耦合                 3 层穿透         4 层（含抽象）  引入 Service 层隔断
WeaverState 字段数               14               6 (+ 嵌套)      -57%
LangGraph 节点与实现耦合         编译时绑定       运行时注册       编译时解耦
```

### 17.5 改进后的分层架构

```
┌──────────────────────────────────────────────┐
│                   UI 层                        │
│  tray_app  hotkey_listener  overlay_window    │
│  static/ (HTML + CSS + JS)                    │
└────────────────────┬─────────────────────────┘
                     │ HTTP (localhost:8765)
┌────────────────────▼─────────────────────────┐
│                  API 层                        │
│  routes/ (ideas, sessions, weaving, designs)  │
│  websocket_manager                            │
│  dependencies.py (DI wiring)                  │
└────────────────────┬─────────────────────────┘
                     │ 依赖注入
┌────────────────────▼─────────────────────────┐
│              Service 层 (★ 新增)              │
│  WeavingService (抽象)                         │
│    └── LangGraphWeavingService (实现)          │
│  IdeaService (抽象)                            │
│    └── IdeaServiceImpl (实现)                  │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│               Domain 层                        │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Collector│  │ Weaver   │  │ Architect  │  │
│  │  组件    │  │  组件包   │  │  组件      │  │
│  │          │  │ ·cluster │  │            │  │
│  │          │  │ ·rel_bld │  │            │  │
│  │          │  │ ·bridge  │  │            │  │
│  │          │  │ ·conflict│  │            │  │
│  └──────────┘  └──────────┘  └────────────┘  │
│  ┌──────────┐  ┌──────────────────────────┐  │
│  │  Critic  │  │    LLMService (抽象)      │  │
│  │  组件    │  │    NodeRegistry           │  │
│  └──────────┘  └──────────────────────────┘  │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│            Infrastructure 层                   │
│  ┌─────────┐ ┌──────────┐ ┌───────────────┐ │
│  │ SQLite  │ │ ChromaDB │ │ File Store    │ │
│  │ + repos │ │          │ │               │ │
│  └─────────┘ └──────────┘ └───────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │ LiteLLMService (LLMService 实现)         │ │
│  │ WhisperTranscriber                      │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### 17.6 解耦实施的优先级

| 优先级 | 措施 | 影响范围 | 风险 | 建议时机 |
|---|---|---|---|---|
| 🔴 P0 | **Node Registry 模式** | workflow.py + 4 个 Agent | 低（纯重构，外部行为不变） | Week 4（workflow 实现时直接采用） |
| 🔴 P0 | **LLMService 抽象** | base.py + 4 个 Agent + 测试 | 低（接口兼容） | Week 3（写第一个 Agent 前） |
| 🟡 P1 | **Weaver 组件化拆分** | weaver/ 包 | 中（涉及文件重组） | Week 3-4（Weaver 实现时采用） |
| 🟡 P1 | **双写最终一致性** | collector + vector_store | 低（补充补偿逻辑） | Week 3（Collector 实现时内置） |
| 🟢 P2 | **Service 层引入** | api/routes/ + 新增 services/ | 中（增加一层抽象） | Week 5（写 API 时采用） |
| 🟢 P2 | **节点级输入/输出契约** | workflow.py + 所有 Agent 节点 | 中（改变状态结构） | Week 7（集成阶段重构） |

---

## 18. 部署方案：Docker 一键部署 & 阿里云 FC Serverless

> FC 的核心约束：**环境是原生的（只有 stdlib）| 配置是声明式的（s.yaml）| 无状态（实例可随时回收）| 冷启动有成本**。
> 这些约束直接决定了哪些模块能上 FC、哪些必须改造、哪些只能留在客户端。

### 18.1 FC 对现有架构的冲击分析

回顾当前架构的三层：

```
┌──────────────────────────────────────────┐
│  Desktop (Windows)                        │
│  ├── 系统托盘 (pystray)     ← 不能上 FC  │
│  ├── 全局热键 (pynput)      ← 不能上 FC  │
│  └── WebView2 浮窗           ← 不能上 FC  │
├──────────────────────────────────────────┤
│  FastAPI Server (localhost:8765)          │
│  ├── API 路由                ← ✅ 可上 FC │
│  ├── Collector Agent         ← ✅ 可上 FC │
│  ├── Weaver Agent            ← ⚠️ 长任务  │
│  ├── Architect Agent         ← ✅ 可上 FC │
│  ├── Critic Agent            ← ✅ 可上 FC │
│  └── LangGraph Workflow      ← ⚠️ 长任务  │
├──────────────────────────────────────────┤
│  Storage                                  │
│  ├── SQLite                  ← ❌ 本地文件│
│  ├── ChromaDB                ← ❌ 本地文件│
│  └── 资产文件                 ← ❌ 本地文件 │
└──────────────────────────────────────────┘
```

**结论：必须拆分为客户端（Desktop Shell）和服务端（FC/Docker 后端）。**

| 模块 | Docker 部署 | FC 部署 | 备注 |
|---|---|---|---|
| 系统托盘 + 热键 + WebView2 | ❌ 不需要 | ❌ 不能上 | 留在用户 Windows 机器 |
| FastAPI Server | ✅ 容器内 | ✅ HTTP 触发器 | — |
| Collector Agent | ✅ 容器内 | ✅ | 轻量级，冷启动友好 |
| Weaver Agent | ✅ 容器内 | ⚠️ 异步 | 长任务，需异步模式 |
| Architect Agent | ✅ 容器内 | ⚠️ 异步 | 同上 |
| Critic Agent | ✅ 容器内 | ⚠️ 异步 | 同上 |
| SQLite | ✅ 容器内 volume | ⚠️ → NAS | FC 不能信赖本地写 |
| ChromaDB | ✅ 容器内 volume | ⚠️ → NAS | 同上 |
| 资产文件 | ✅ 容器内 volume | ⚠️ → NAS 或 OSS | 同上 |
| openai-whisper | ✅ 容器内 | 🔴 → 层 (Layer) | 模型文件大，冷启动慢 |

### 18.2 统一部署架构

无论是 Docker 还是 FC，客户端都是同一个轻量壳：

```
┌────────────────────────────────────────────────────────────┐
│                DESKTOP CLIENT (Windows/macOS)               │
│                                                             │
│  ┌─────────┐ ┌──────────┐ ┌────────────────────┐           │
│  │ System  │ │ Keyboard │ │  WebView2 Overlay  │           │
│  │  Tray   │ │ Listener │ │  · 文字输入          │           │
│  │         │ │          │ │  · 图片粘贴          │           │
│  │         │ │          │ │  · 语音录制          │           │
│  └────┬────┘ └────┬─────┘ └─────────┬──────────┘           │
│       │           │                │                        │
│       └───────────┴────────────────┘                        │
│                   │                                         │
│                   │ HTTPS (api.weaver.example.com)          │
│                   │ 或 http://localhost:8765 (Docker)       │
│                   ▼                                         │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│              SERVER (Docker 容器 / FC 函数)                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               FastAPI (HTTP 入口)                    │   │
│  │  /api/ideas  /api/sessions  /api/weave  /api/designs│   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │                                  │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │          Async Task Dispatcher (FC 关键改造)          │   │
│  │                                                       │   │
│  │  短任务 (<30s)：同步 HTTP 响应                         │   │
│  │    · Collector 标准化                                 │   │
│  │    · 想法 CRUD                                        │   │
│  │                                                       │   │
│  │  长任务 (30-600s)：异步触发 + WebSocket/轮询             │   │
│  │    · Weaver 编织                                      │   │
│  │    · Architect 设计生成                               │   │
│  │    · Critic 评估                                      │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │                                  │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │              Agent Pool                               │   │
│  │  Collector │ Weaver │ Architect │ Critic             │   │
│  │  (sync)    │ (async)│ (async)   │ (async)            │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │                                  │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │           Storage (根据部署模式切换)                    │   │
│  │                                                       │   │
│  │  Docker: SQLite + ChromaDB (本地 volume)              │   │
│  │  FC:     SQLite + ChromaDB (NAS 挂载)                 │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

**客户端改造要点（连接远端时）：**

```javascript
// src/ui/static/app.js  改造
const API_BASE = window.WEAVER_API_URL || 'http://localhost:8765';
// Docker:     http://localhost:8765
// FC:         https://api.weaver.your-domain.com

async function submitIdea(content, files) {
    const resp = await fetch(`${API_BASE}/api/ideas`, {
        method: 'POST',
        body: buildFormData(content, files),
    });
    return resp.json();
}
```

### 18.3 Docker 一键部署

#### 18.3.1 目录结构（新增文件）

```
WEAVE/
├── Dockerfile                    # 单容器构建
├── docker-compose.yml            # 一键启动（含 ChromaDB 独立容器可选）
├── .dockerignore
├── docker/
│   ├── entrypoint.sh             # 容器入口脚本
│   └── healthcheck.py            # 容器健康检查
└── requirements.txt              # Python 依赖清单
```

#### 18.3.2 Dockerfile

```dockerfile
# WEAVE/Dockerfile
# 多阶段构建：build → runtime

# ==================== 构建阶段 ====================
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .

# 安装构建依赖
RUN pip install --no-cache-dir --user \
    -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/  # 国内镜像加速

# ==================== 运行阶段 ====================
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Idea Weaver"
LABEL org.opencontainers.image.description="碎碎念到结构化设计文档的 AI 助手"

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    ffmpeg \                    # Whisper 需要
    curl \                       # 健康检查
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash weaver
USER weaver
WORKDIR /home/weaver/app

# 从构建阶段复制 Python 包
COPY --from=builder /root/.local /home/weaver/.local
ENV PATH="/home/weaver/.local/bin:$PATH"

# 复制应用代码
COPY --chown=weaver:weaver src/ ./src/
COPY --chown=weaver:weaver skills/ ./skills/
COPY --chown=weaver:weaver docker/entrypoint.sh ./entrypoint.sh

# 数据目录（运行时挂载 volume）
RUN mkdir -p /home/weaver/app/data /home/weaver/app/exports

# FastAPI 监听端口
EXPOSE 8765

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8765/api/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
```

#### 18.3.3 入口脚本

```bash
#!/bin/bash
# WEAVE/docker/entrypoint.sh
set -e

echo "=== Idea Weaver ==="
echo "LLM Provider: ${LLM_PROVIDER:-litellm}"
echo "Data dir: /home/weaver/app/data"

# 初始化数据目录
mkdir -p /home/weaver/app/data/{chroma,assets/images,assets/audio,logs}
mkdir -p /home/weaver/app/exports

# 数据库迁移
python -c "
from src.storage.database import run_migrations
run_migrations()
"

echo "Starting FastAPI server on 0.0.0.0:8765..."
exec uvicorn src.api.server:app \
    --host 0.0.0.0 \
    --port 8765 \
    --workers ${WORKERS:-1} \
    --log-level ${LOG_LEVEL:-info}
```

#### 18.3.4 docker-compose.yml

```yaml
# WEAVE/docker-compose.yml
version: "3.9"

services:
  weaver:
    build:
      context: .
      dockerfile: Dockerfile
    image: idea-weaver:latest
    container_name: idea-weaver
    restart: unless-stopped

    ports:
      - "${WEAVER_PORT:-8765}:8765"

    environment:
      # LLM 配置（通过 .env 注入，不硬编码在 yaml 中）
      - LLM_PROVIDER=${LLM_PROVIDER:-litellm}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - VOYAGE_API_KEY=${VOYAGE_API_KEY:-}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-text-embedding-3-small}
      - WEAVER_MODEL=${WEAVER_MODEL:-claude-sonnet-5}
      - LIGHT_MODEL=${LIGHT_MODEL:-claude-haiku-4-5-20251001}
      # 运行时
      - WORKERS=1
      - LOG_LEVEL=${LOG_LEVEL:-info}
      - WEAVER_MAX_ITERATIONS=${WEAVER_MAX_ITERATIONS:-3}

    volumes:
      # 持久化数据
      - weaver_data:/home/weaver/app/data
      - weaver_exports:/home/weaver/app/exports

    # 资源限制
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: "4G"
        reservations:
          cpus: "1"
          memory: "2G"

    networks:
      - weaver-net

  # (可选) 独立的 ChromaDB 服务——单容器部署不需要
  # chromadb:
  #   image: chromadb/chroma:latest
  #   volumes:
  #     - chroma_data:/chroma/chroma
  #   networks:
  #     - weaver-net

volumes:
  weaver_data:
    name: weaver_data
  weaver_exports:
    name: weaver_exports

networks:
  weaver-net:
    name: weaver-net
```

#### 18.3.5 .env.example（Docker 用）

```bash
# WEAVE/.env.example
# 复制为 .env 后 docker-compose up

# === 必填 ===
ANTHROPIC_API_KEY=sk-ant-xxxxx

# === 可选 ===
OPENAI_API_KEY=sk-xxxxx
VOYAGE_API_KEY=pa-xxxxx

# === 模型配置 ===
EMBEDDING_MODEL=text-embedding-3-small
WEAVER_MODEL=claude-sonnet-5
LIGHT_MODEL=claude-haiku-4-5-20251001
LLM_PROVIDER=litellm

# === 运行时 ===
WEAVER_PORT=8765
LOG_LEVEL=info
WEAVER_MAX_ITERATIONS=3
```

#### 18.3.6 一键部署命令

```bash
# 1. 克隆项目
git clone https://github.com/your-org/idea-weaver.git
cd idea-weaver

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env ，填入 ANTHROPIC_API_KEY

# 3. 启动
docker-compose up -d

# 4. 验证
curl http://localhost:8765/api/health
# { "status": "ok", "llm_provider": "connected", "db": "ok", "chromadb": "ok" }

# 5. 查看日志
docker-compose logs -f weaver
```

### 18.4 阿里云 FC 部署

> **牢记 FC 的铁律：环境只有 stdlib → 所有依赖显式声明 | 配置在 s.yaml 中 → 不要手动改控制台 | 实例无状态 → 存储走 NAS**

#### 18.4.1 FC 架构改造要点

```
原架构                     FC 适配后
─────────────────────────────────────────────────────
Python 3.11               ✅ FC 原生支持
uvicorn + FastAPI         ✅ 通过 HTTP 触发器暴露
LangGraph                 ✅ 正常使用
SQLite                    ⚠️ → 文件放到 NAS (/mnt/auto/weaver/data/)
ChromaDB                  ⚠️ → 持久化目录指向 NAS
openai-whisper            🔴 → 放到"自定义层"，避免冷启动加载 1.5GB 模型
                          💡 替代：使用 FC 的异步任务，首次冷启动加载层
LiteLLM                   ✅ API 调用，不占本地资源
资产文件                    ⚠️ → NAS 文件系统
长编织任务 (60-300s)        🔴 → HTTP 触发后同步返回可能超时
                          💡 → 使用 FC 异步调用 + 客户端轮询/WebSocket
.env 密钥                  ⚠️ → s.yaml 中的 environmentVariables
全局热键 + WebView2        ❌ → 留在客户端，改连 FC 公网地址
```

#### 18.4.2 项目结构（FC 新增文件）

```
WEAVE/
├── s.yaml                         # ★ 声明式部署配置（核心文件）
├── fc/
│   ├── entrypoint.sh              # FC 自定义运行时入口
│   └── bootstrap                  # FC 自定义运行时 bootstrap
├── layer/
│   └── requirements-layer.txt     # 层依赖（whisper, torch 等重型库）
├── requirements.txt               # 函数依赖（轻量，不含 whisper）
└── .fcignore                      # FC 部署忽略文件
```

#### 18.4.3 s.yaml —— FC 声明式配置

```yaml
# WEAVE/s.yaml
# 所有 FC 配置的单一事实来源。不要手动改控制台，改这个文件然后 s deploy。
# 文档: https://docs.serverless-devs.com/fc/yaml/readme

edition: 3.0.0
name: idea-weaver
access: "default"           # 通过 s config add 配置的阿里云账号

vars:
  region: cn-hangzhou
  service: idea-weaver-service

resources:
  # ── 函数：核心 API ──
  idea_weaver_api:
    component: fc3
    props:
      region: ${vars.region}
      serviceName: ${vars.service}
      functionName: idea-weaver-api
      description: "Idea Weaver — 想法编织成设计文档"
      runtime: custom.debian10     # 自定义运行时，完全控制环境
      code: ./
      handler: not-used            # custom runtime 忽略此字段
      cpu: 2
      memorySize: 4096             # 4 GB（Weaver 需要大上下文）
      diskSize: 10240              # 10 GB 临时磁盘
      timeout: 600                 # 10 分钟超时（HTTP 触发器最多 600s）
      instanceConcurrency: 1       # 单实例单并发（LangGraph 状态机是串行的）
      instanceType: e1             # 弹性实例

      # 自定义运行时入口
      customRuntimeConfig:
        command:
          - /code/fc/bootstrap    # → 启动 uvicorn
        args: []

      # 环境变量（来自 FC 控制台 → 改为在此声明）
      environmentVariables:
        LLM_PROVIDER: litellm
        EMBEDDING_MODEL: text-embedding-3-small
        WEAVER_MODEL: claude-sonnet-5
        LIGHT_MODEL: claude-haiku-4-5-20251001
        WEAVER_MAX_ITERATIONS: "3"
        LOG_LEVEL: info
        DATA_DIR: /mnt/auto/weaver/data        # NAS 路径
        ANTHROPIC_API_KEY: ${env(ANTHROPIC_API_KEY)}   # 从本地 env 读取，不写死在 yaml
        OPENAI_API_KEY: ${env(OPENAI_API_KEY)}
        VOYAGE_API_KEY: ${env(VOYAGE_API_KEY)}

      # 自定义层（whisper + torch 等重型依赖）
      layers:
        - acs:fc:${vars.region}:${config(accountId)}:layers/weaver-deps/versions/1

      # NAS 挂载（持久化存储 SQLite + ChromaDB + 资产文件）
      nasConfig:
        userId: 1000
        groupId: 1000
        mountPoints:
          - serverAddr: ${nas_server_addr}:/weaver
            mountDir: /mnt/auto/weaver

      # HTTP 触发器
      triggers:
        - triggerName: http-trigger
          triggerType: http
          triggerConfig:
            methods: [GET, POST, PUT, DELETE, OPTIONS]
            authType: anonymous
            disableURLInternet: false   # 公网访问

  # ── 异步任务函数：长编织 (★ FC 关键改造) ──
  idea_weaver_async_worker:
    component: fc3
    props:
      region: ${vars.region}
      serviceName: ${vars.service}
      functionName: idea-weaver-async-worker
      description: "异步编织 Worker——处理耗时超过 60s 的编织任务"
      runtime: custom.debian10
      code: ./
      handler: not-used
      cpu: 2
      memorySize: 4096
      diskSize: 10240
      timeout: 86400                # 异步调用最长 24 小时
      instanceConcurrency: 1
      instanceType: e1

      customRuntimeConfig:
        command:
          - /code/fc/bootstrap-async-worker
        args: []

      environmentVariables:
        DATA_DIR: /mnt/auto/weaver/data
        ANTHROPIC_API_KEY: ${env(ANTHROPIC_API_KEY)}
        OPENAI_API_KEY: ${env(OPENAI_API_KEY)}
        EMBEDDING_MODEL: text-embedding-3-small
        WEAVER_MODEL: claude-sonnet-5

      layers:
        - acs:fc:${vars.region}:${config(accountId)}:layers/weaver-deps/versions/1

      nasConfig:
        userId: 1000
        groupId: 1000
        mountPoints:
          - serverAddr: ${nas_server_addr}:/weaver
            mountDir: /mnt/auto/weaver

      # 异步触发器——由 API 函数触发
      triggers:
        - triggerName: async-weave-trigger
          triggerType: eventbridge
          triggerConfig:
            eventSourceFilter:
              type: acs.fc

  # ── 自定义域名 ──
  custom_domain:
    component: fc3_domain
    props:
      region: ${vars.region}
      domainName: auto           # 自动分配 FC 测试域名
      protocol: HTTP
      routeConfigs:
        - path: /*
          serviceName: ${vars.service}
          functionName: idea-weaver-api
```

#### 18.4.4 FC 自定义运行时 bootstrap

```bash
#!/bin/bash
# WEAVE/fc/bootstrap
# FC custom runtime 入口。FC 会执行此脚本启动应用。
set -e

echo "=== Idea Weaver (FC Runtime) ==="

# 激活自定义层中的 Python 包
export PYTHONPATH=/opt/python/lib/python3.11/site-packages:$PYTHONPATH

# 初始化数据目录（NAS 挂载点）
mkdir -p /mnt/auto/weaver/data/{chroma,assets/images,assets/audio,logs}
mkdir -p /mnt/auto/weaver/exports

# 数据库迁移
python -c "
import sys
sys.path.insert(0, '/code')
from src.storage.database import run_migrations
run_migrations(data_dir='/mnt/auto/weaver/data')
"

# 启动 FastAPI
# FC HTTP 触发器要求监听 0.0.0.0:9000
exec python -m uvicorn src.api.server:app \
    --host 0.0.0.0 \
    --port 9000 \
    --workers 1 \
    --log-level info
```

```bash
#!/bin/bash
# WEAVE/fc/bootstrap-async-worker
# 异步 Worker：接收 EventBridge 事件 → 执行 LangGraph 编织 → 结果写回 NAS
set -e

export PYTHONPATH=/opt/python/lib/python3.11/site-packages:$PYTHONPATH

echo "=== Idea Weaver (FC Async Worker) ==="

# 异步 Worker 从 EventBridge 事件中获取 session_id
exec python /code/src/fc_async_worker.py
```

#### 18.4.5 FC 异步编织处理器

```python
# src/fc_async_worker.py
"""
FC 异步 Worker——处理耗时编织任务。

为什么需要它：
  FC HTTP 触发器有 600s 超时上限，但 LLM 编织（多次 API 调用 + 迭代）可能超出。
  异步调用超时可达 24 小时，适合 LangGraph 工作流。

流程：
  API 函数 (同步)            Async Worker (异步)
  ─────────────────         ──────────────────────
  POST /api/weave
    → 创建 session (状态=weaving)
    → 异步调用本 Worker
    → 返回 202 + session_id     收到 EventBridge 事件
       (总耗时 < 1s)                → 加载 session
                                   → 执行 LangGraph workflow
                                   → 写入 DesignDocument
                                   → 更新 session (状态=complete)
                                   → 写入结果文件到 NAS
                                   (总耗时 30-300s)
"""
import json
import os
import sys
import asyncio

# FC 环境：所有非 stdlib 依赖来自自定义层
sys.path.insert(0, '/code')
sys.path.insert(0, '/opt/python/lib/python3.11/site-packages')

from src.core.workflow import execute_weave_workflow
from src.storage.database import get_async_session
from src.storage.session_repo import SessionRepo
from loguru import logger

async def handle_weave_event(event: dict):
    """处理 EventBridge 异步编织事件"""
    session_id = event.get("session_id")
    if not session_id:
        logger.error("Missing session_id in event")
        return

    logger.info(f"[Async Worker] Starting weave for session {session_id}")

    async with get_async_session() as db:
        repo = SessionRepo(db)

        # 更新状态
        await repo.update_status(session_id, "weaving")

        try:
            # 执行编织
            result = await execute_weave_workflow(session_id)

            # 保存结果
            await repo.mark_complete(
                session_id=session_id,
                design_id=result.design_id,
            )

            logger.info(f"[Async Worker] Session {session_id} complete. "
                        f"Design: {result.design_id}")

        except Exception as e:
            await repo.mark_failed(
                session_id=session_id,
                error=str(e),
            )
            logger.error(f"[Async Worker] Session {session_id} failed: {e}")
            raise


if __name__ == "__main__":
    # FC 异步调用通过 stdin 传入事件
    event_data = json.loads(sys.stdin.read())
    asyncio.run(handle_weave_event(event_data))
```

#### 18.4.6 依赖分层策略

```
┌─────────────────────────────────────────────────┐
│  层 (Layer)    ← 大体积、低频变更                  │
│  requirements-layer.txt                          │
│    torch>=2.1.0              # ~800MB           │
│    openai-whisper>=20231117  # + torch 依赖       │
│    numpy>=1.26.0                                 │
│    pandas>=2.0.0                                 │
│    chromadb>=0.5.0           # ~200MB           │
│    networkx>=3.3                                 │
│                                                  │
│  层只构建一次，后续只改函数代码不重启层。              │
│  冷启动时 FC 并行加载层 + 代码。                     │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  函数代码 (Code) ← 轻量、高频变更                   │
│  requirements.txt                                │
│    fastapi>=0.111.0                              │
│    uvicorn>=0.30.0                               │
│    langgraph>=0.2.0                              │
│    litellm>=1.40.0                               │
│    sqlalchemy>=2.0.0                             │
│    aiosqlite>=0.20.0                             │
│    pydantic>=2.7.0                               │
│    httpx>=0.27.0                                 │
│    loguru>=0.7.0                                 │
│    python-dotenv>=1.0.0                           │
│    pyyaml>=6.0                                   │
│                                                  │
│  每次 s deploy 都会更新函数代码。                    │
│  这些库 ~50MB，冷启动加载 < 3 秒。                   │
└─────────────────────────────────────────────────┘
```

```txt
# WEAVE/layer/requirements-layer.txt
# 自定义层的依赖——重型库，构建一次，很少变

# ASR（语音转写）
openai-whisper>=20231117

# 向量存储（嵌入式）
chromadb>=0.5.0

# 科学计算（whisper 依赖）
torch>=2.1.0
numpy>=1.26.0
pandas>=2.0.0

# 图分析
networkx>=3.3
```

```txt
# WEAVE/requirements.txt
# 函数代码依赖——轻量，高频变更

# Web 框架
fastapi>=0.111.0
uvicorn[standard]>=0.30.0

# Agent 编排
langgraph>=0.2.0
langgraph-checkpoint-sqlite>=0.1.0

# LLM 抽象
litellm>=1.40.0

# 数据
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.20.0
pydantic>=2.7.0
pydantic-settings>=2.3.0

# HTTP 客户端
httpx>=0.27.0

# 工具
loguru>=0.7.0
python-dotenv>=1.0.0
pyyaml>=6.0
```

#### 18.4.7 FC 部署命令

```bash
# 0. 安装 Serverless Devs 工具
npm install -g @serverless-devs/s

# 1. 配置阿里云账号
s config add \
  --AccountID <your-account-id> \
  --AccessKeyID <your-access-key> \
  --AccessKeySecret <your-access-secret>

# 2. 创建 NAS 文件系统（一次性）
#    在阿里云控制台创建 NAS 通用型，记录 serverAddr

# 3. 构建自定义层（一次性）
cd layer/
pip install -r requirements-layer.txt -t python/lib/python3.11/site-packages/
zip -r layer-weaver-deps.zip python/
# 上传到 FC 控制台 → 层 → 新建层
# 在 s.yaml 中填入层 ARN

# 4. 部署
export ANTHROPIC_API_KEY=sk-ant-xxxxx
export NAS_SERVER_ADDR=xxxxx.cn-hangzhou.nas.aliyuncs.com
s deploy

# 5. 测试
curl -X POST https://<fc-auto-domain>/api/ideas \
  -H "Content-Type: application/json" \
  -d '{"content": "需要一个分布式限流系统", "source_type": "text"}'

# 6. 查看日志
s logs --function idea-weaver-api
```

#### 18.4.8 FC 冷启动优化

| 优化点 | 方案 | 效果 |
|---|---|---|
| 重型依赖放入层 | torch + whisper + chromadb 构建自定义层 | 层缓存命中时跳过下载（~1.5GB → 0） |
| 代码包瘦身 | .fcignore 排除 tests/、node_modules/、data/ | 代码包从 ~100MB 降到 ~10MB |
| 预置并发 (Provisioned) | 为 API 函数配置预置实例（1-2 个） | 首个请求无冷启动 |
| 单实例多请求 | 开启 instanceConcurrency，利用 asyncio 并发 | 减少新实例创建 |
| Whisper 懒加载 | 首次语音转写时才 import whisper | API 冷启动不加载 1.5GB 模型 |

```yaml
# s.yaml 补充——预置并发
props:
  instanceConcurrency: 10          # 单实例最多 10 并发（FastAPI async 支持）
  provisionedConcurrency: 1        # 始终保留 1 个热实例
```

### 18.5 存储层的部署模式适配

```python
# src/storage/database.py  —— 部署模式自适应

import os
from pathlib import Path

def get_data_dir() -> Path:
    """根据部署环境返回数据目录"""
    # FC NAS 挂载点
    if os.environ.get("DATA_DIR"):
        return Path(os.environ["DATA_DIR"])
    # Docker volume
    if Path("/home/weaver/app/data").exists():
        return Path("/home/weaver/app/data")
    # 本地开发
    return Path("data")

def get_db_url() -> str:
    data_dir = get_data_dir()
    db_path = data_dir / "weaver.db"
    return f"sqlite+aiosqlite:///{db_path}"

def get_chroma_persist_dir() -> str:
    data_dir = get_data_dir()
    chroma_dir = data_dir / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return str(chroma_dir)
```

### 18.6 Docker vs FC 部署对比

| 维度 | Docker | 阿里云 FC |
|---|---|---|
| **安装难度** | `docker-compose up -d` | `s deploy` + 配置账号/NAS/层 |
| **运维成本** | 自己管服务器/容器 | 零运维（Serverless） |
| **冷启动** | 无（常驻进程） | 有（首次 5-15s，预置实例可消除） |
| **费用模型** | 固定（服务器月费） | 按量（调用次数 × 内存 × 时长） |
| **持久化** | Docker volume → 本地磁盘 | NAS 文件系统挂载 |
| **长任务** | 无限制 | HTTP 600s / 异步 24h |
| **GPU** | 需要 GPU 服务器 | 不提供 GPU（whisper CPU 推理慢） |
| **桌面 UI** | localhost 直连 | HTTPS 公网访问 |
| **适用场景** | 个人自建、离线使用 | 多人共享、零运维需求 |
| **国内加速** | 阿里云镜像 | 天然在阿里云内网 |

### 18.7 部署优先级

| 阶段 | 部署方式 | 适合用户 |
|---|---|---|
| **开发期 (Week 1-7)** | 本地 Python 直接运行 | 开发者 |
| **V1 发布** | Docker 一键部署 | 有服务器的个人用户 |
| **V1.5** | FC 部署（API 模式） | 不想管服务器的用户 |
| **V2** | Docker + FC 双模式 | 全部用户 |

---

## 19. FC 部署对已设计结构的冲击逐文件分析

> 核心结论：**不需要重构文件结构。** 冲击集中在入口层和存储路径，其他层无需改动。
> 新增 6 个文件，修改 7 个文件的部分代码，35+ 文件完全不动。

### 19.1 逐文件影响矩阵

```
图例:
  ⬜ = FC 部署不涉及此文件（无需改动）
  🟢 = 无需任何改动即可同时适配本地/Docker/FC
  🟡 = 需小幅改动（加环境判断 / 路径自适应 / 条件分支）
  🔴 = 需较大改动或拆分为两个版本
  ❌ = 不能上 FC，留在客户端
  ➕ = 需要新增的文件
```

#### src/ 目录逐文件分析：

| 文件 | 影响等级 | FC 冲击点 | 改动量 |
|---|---|---|---|
| `main.py` | 🔴 | 桌面入口（pystray + pynput + pywebview），FC 无桌面环境 | 保留不动，新增 `main_fc.py` |
| **api/server.py** | 🟡 | FC HTTP 触发器要求端口 9000；lifespan 事件中不再启动托盘/热键 | 2 行：端口自适应 + lifespan 跳过桌面初始化 |
| **api/dependencies.py** | 🟢 | 无冲击 | 0 行 |
| **api/routes/ideas.py** | 🟢 | 无冲击 | 0 行 |
| **api/routes/sessions.py** | 🟢 | 无冲击 | 0 行 |
| **api/routes/weaving.py** | 🟡 | FC 需异步编织模式：HTTP 秒返 202 → EventBridge 触发 Worker | ~20 行：加 `_mode` 判断分支 |
| **api/routes/designs.py** | 🟢 | 无冲击 | 0 行 |
| **api/routes/health.py** | 🟢 | 无冲击 | 0 行 |
| **api/websocket_manager.py** | 🔴 | FC HTTP 触发器不支持 WebSocket 长连接 | 保留不动，新增轮询降级逻辑 |
| **agents/base.py** | 🟢 | 无冲击（只做 LLM 调用） | 0 行 |
| **agents/collector.py** | 🟢 | 无冲击 | 0 行 |
| **agents/weaver.py** | 🟢 | 无冲击 | 0 行 |
| **agents/architect.py** | 🟢 | 无冲击 | 0 行 |
| **agents/critic.py** | 🟢 | 无冲击 | 0 行 |
| **agents/prompts/*.yaml** | 🟢 | 无冲击 | 0 行 |
| **core/models.py** | 🟢 | 无冲击 | 0 行 |
| **core/workflow.py** | 🟡 | LangGraph checkpoint 路径需指向 NAS | ~5 行：checkpoint 路径从 `get_data_dir()` 取 |
| **core/graph_ops.py** | 🟢 | 无冲击 | 0 行 |
| **core/embeddings.py** | 🟢 | 无冲击 | 0 行 |
| **core/state_manager.py** | 🟡 | 序列化路径需指向 NAS | ~3 行：路径自适应 |
| **ui/tray_app.py** | ❌ | 不能上 FC | 0 行（不动） |
| **ui/hotkey_listener.py** | ❌ | 不能上 FC | 0 行（不动） |
| **ui/overlay_window.py** | 🔴 | 不能上 FC，但需改造连接地址 | ~5 行：`API_BASE` 从 localhost 变为可配置 |
| **ui/static/index.html** | 🟢 | 无冲击 | 0 行 |
| **ui/static/styles.css** | 🟢 | 无冲击 | 0 行 |
| **ui/static/app.js** | 🟡 | API 地址从硬编码 localhost → 可配置 | ~3 行：读取 `window.WEAVER_API_URL` |
| **ui/static/results.html** | 🟢 | 无冲击 | 0 行 |
| **ui/static/results.js** | 🟡 | 进度监听从 WebSocket → 支持轮询降级 | ~15 行：加 `usePolling` 模式 |
| **ui/templates/design_report.html** | 🟢 | 无冲击 | 0 行 |
| **storage/database.py** | 🟡 | DB 路径需从环境变量取 | ~8 行：已有 `get_data_dir()` 设计 |
| **storage/idea_repo.py** | 🟢 | 无冲击（只依赖 database session） | 0 行 |
| **storage/cluster_repo.py** | 🟢 | 同上 | 0 行 |
| **storage/design_repo.py** | 🟢 | 同上 | 0 行 |
| **storage/session_repo.py** | 🟢 | 同上 | 0 行 |
| **storage/vector_store.py** | 🟡 | ChromaDB 持久化目录需从环境变量取 | ~3 行：路径自适应 |
| **storage/file_store.py** | 🟡 | 资产文件路径需从环境变量取 | ~3 行：路径自适应 |
| **utils/config.py** | 🟡 | 需支持从 FC 环境变量注入 | ~10 行：`Field(env=...)` |
| **utils/logging_config.py** | 🟡 | FC 环境日志输出到 stdout 而非文件 | ~5 行：条件判断 |
| **utils/whisper_transcriber.py** | 🟡 | whisper 来自自定义层而非 pip install | ~3 行：`sys.path` 追加层路径 |
| **utils/metrics.py** | 🟢 | 无冲击 | 0 行 |

### 19.2 冲击分层总结

```
        fc/            ← 6 个新增文件
      ┌──────┐
      │bootstrap      │  ← FC 入口
      │async-worker   │  ← 异步编织
      │...            │
      └──────┘
      
  src/main.py  ← 🔴 保留，运行时判断模式
  api/         ← 🟡 2 个文件需小幅改动，其余不动
  agents/      ← 🟢 0 个文件需要改动 ★
  core/        ← 🟡 2 个文件需小幅改动，其余不动
  storage/     ← 🟡 2 个文件需小幅改动，其余不动
  utils/       ← 🟡 3 个文件需小幅改动，其余不动
  ui/          ← 🟡 2 个文件需小幅改动（API 地址 + 轮询）
  
  ★ 结论：最核心的 agents/ 完全不受 FC 影响。
```

### 19.3 不改结构的理由

**不改结构不是因为 FC 没冲击——FC 冲击很大。不改结构是因为冲击集中在"环境差异"而非"业务逻辑差异"。环境差异应通过配置 + 薄适配层解决，不应拆目录树。**

```
FC 冲击的本质:
┌─────────────────────────────────────────┐
│  环境差异 (通过配置/适配解决)              │
│  ├── 端口号 (8765 → 9000)                │
│  ├── 存储路径 (data/ → /mnt/auto/...)    │
│  ├── 通信协议 (WebSocket → 轮询降级)       │
│  ├── 进程入口 (main.py → bootstrap)       │
│  └── 任务模式 (同步 → 异步触发)            │
├─────────────────────────────────────────┤
│  业务逻辑 (不动)                          │
│  ├── Collector 标准化                     │
│  ├── Weaver 编织                          │
│  ├── Architect 设计生成                   │
│  ├── Critic 评估                          │
│  ├── LangGraph 工作流                     │
│  └── 所有数据模型                         │
└─────────────────────────────────────────┘
```

### 19.4 只需要做 3 件事

#### 第 1 件：入口分流（1 个新文件 + main.py 不改）

```python
# src/main.py  —— 保持不变，仍然是桌面入口

# 新增 src/main_fc.py —— FC 入口，极简
"""
FC 版本的入口。与 main.py 的区别：
  - 不启动 pystray / pynput / pywebview
  - 仅启动 FastAPI server
  - 端口从环境变量 PORT 读取（FC 固定需要 9000）
"""
import os
import uvicorn
from src.api.server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
```

#### 第 2 件：运行时模式标记（1 个环境变量管全部）

```python
# src/utils/config.py —— 追加一个字段
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 现有字段不变 ...
    
    # 新增：部署模式
    DEPLOY_MODE: str = "desktop"  # "desktop" | "docker" | "fc"
    
    # 存储路径（按模式自动切换）
    @property
    def data_dir(self) -> Path:
        if self.DEPLOY_MODE == "fc":
            return Path(os.environ.get("DATA_DIR", "/mnt/auto/weaver/data"))
        if self.DEPLOY_MODE == "docker":
            return Path("/home/weaver/app/data")
        return Path("data")
    
    # FC 异步编织模式
    @property
    def use_async_weave(self) -> bool:
        return self.DEPLOY_MODE == "fc"

settings = Settings()
```

#### 第 3 件：WebSocket → 轮询降级（前端 + 后端各一小段）

```python
# src/api/routes/weaving.py —— 追加一个轮询端点
@router.get("/api/sessions/{session_id}/progress")
async def poll_progress(session_id: str):
    """FC 降级：HTTP 轮询替代 WebSocket"""
    session = await session_repo.get(session_id)
    return {
        "session_id": session_id,
        "status": session.status,
        "progress": estimate_progress(session.status),
    }

# WebSocket 端点保留，Docker/桌面模式正常使用。
```

```javascript
// src/ui/static/results.js —— 追加轮询模式
const USE_POLLING = location.hostname !== 'localhost';  // 远端 = FC

function watchProgress(sessionId, onUpdate) {
    if (USE_POLLING) {
        // FC 模式：每 3 秒轮询
        const timer = setInterval(async () => {
            const resp = await fetch(`${API_BASE}/api/sessions/${sessionId}/progress`);
            const data = await resp.json();
            onUpdate(data);
            if (data.status === 'complete' || data.status === 'failed') {
                clearInterval(timer);
            }
        }, 3000);
    } else {
        // 本地/Docker：WebSocket
        const ws = new WebSocket(`ws://${API_HOST}/ws/progress/${sessionId}`);
        ws.onmessage = (e) => onUpdate(JSON.parse(e.data));
    }
}
```

### 19.5 最终文件结构（加 FC 后）

```
WEAVE/
├── src/
│   ├── main.py                       # 🟢 桌面入口（不动）
│   ├── main_fc.py                    # ➕ FC 入口（新增，15 行）
│   ├── fc_async_worker.py            # ➕ FC 异步编织 Worker（新增，60 行）
│   ├── api/
│   │   ├── server.py                 # 🟡 加 2 行（端口自适应）
│   │   ├── routes/weaving.py         # 🟡 加 10 行（异步触发 + 轮询端点）
│   │   └── ...                       # 🟢 其余不动
│   ├── agents/                       # 🟢 全部不动 ★
│   ├── core/
│   │   ├── workflow.py               # 🟡 加 3 行（checkpoint 路径）
│   │   └── ...                       # 🟢 其余不动
│   ├── storage/
│   │   ├── database.py               # 🟡 加 5 行（路径自适应）
│   │   └── ...                       # 🟢 其余不动
│   ├── ui/                           # 🟡 app.js + results.js 各加 ~10 行
│   └── utils/
│       └── config.py                 # 🟡 加 15 行（DEPLOY_MODE + data_dir）
├── fc/                               # ➕ 新增目录
│   ├── bootstrap                     # ➕ FC API 函数入口
│   └── bootstrap-async-worker        # ➕ FC 异步 Worker 入口
├── layer/
│   └── requirements-layer.txt        # ➕ 重型依赖清单（新增）
├── s.yaml                            # ➕ FC 声明式配置（新增）
├── Dockerfile                        # ➕ Docker 构建（新增）
├── docker-compose.yml                # ➕ Docker 编排（新增）
├── .fcignore                         # ➕ FC 忽略文件（新增）
├── requirements.txt                  # 🟡 新增文件（从 pyproject.toml 拆分）
│
│   ... 其余 30+ 文件完全不变
```

### 19.6 冲击汇总

| 类别 | 计数 | 占比 |
|---|---|---|
| 完全不变的文件 | **35 个** | 85% |
| 小幅改动（< 15 行） | **7 个** | 17% |
| 需分拆/较大改动 | **0 个** | 0% |
| 新增文件 | **6 个** | — |

**结论：FC 部署不会逼你重构。** 已设计的结构经得起两种部署模式的考验。核心业务逻辑（agents/）零改动，存储层通过配置自适应，UI 层只需加一层 API 地址配置和轮询降级。新增的 6 个文件全部是薄适配层，不侵入现有代码。

---

## 附录：关键文件优先级

以下文件承载最大架构权重，应优先实现且投入最多精力：

| 优先级 | 文件 | 原因 |
|---|---|---|
| 🔴 P0 | `src/core/models.py` | 所有 Agent、存储层、API 路由都依赖这些 Pydantic 模型 |
| 🔴 P0 | `src/core/workflow.py` | LangGraph 工作流是中枢神经系统——定义 Agent 连接、状态流、checkpoint、反馈循环 |
| 🔴 P0 | `src/agents/weaver.py` | 最复杂的 Agent——语义聚类、关系发现、跨域桥接、冲突检测，Prompt 设计和输出解析是整个系统最难的工程问题 |
| 🟡 P1 | `src/ui/overlay_window.py` | 用户唯一交互面——慢/丑/不可靠 = 用户弃用，不管后端多好 |
| 🟡 P1 | `src/storage/vector_store.py` | 语义搜索质量决定 Weaver 能否找到相关连接——ChromaDB 配置是单向决策，影响所有后续操作 |
