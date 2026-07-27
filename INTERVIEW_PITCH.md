# Idea Weaver — 面试串讲提纲

## 一句话概括

**全局热键唤起的 AI 想法编织器** — 把碎片化想法（文字/语音/图片）通过 4-Agent 流水线自动转化为结构化工程设计文档。

---

## 30 秒电梯演讲

> Idea Weaver 解决的是"想法太多、落地太难"的问题。你用 `Ctrl+Alt+[` 唤起一个极简浮窗，输入任何想法，后台的 4 个 AI Agent 流水线会把它们编织成带 Mermaid 架构图、评分系统、实施路径的工程设计文档。技术栈是 Python FastAPI + Tauri 2 (Rust) + React 18，Windows 系统托盘常驻。

---

## 核心技术亮点（每个都值得展开讲）

### 1. 双运行时架构

```
┌─ Tauri 2 (Rust) ──────────────────┐
│  React 18 UI (WebView2)            │
│  全局热键 + 系统托盘 + 鼠标定位    │
│         │ HTTP localhost:8765       │
├────────────────────────────────────┤
│  Python FastAPI 后端               │
│  4-Agent 流水线 + LangGraph 编排   │
│  SQLite + ChromaDB 混合存储        │
└────────────────────────────────────┘
```

**面试重点**：为什么选这个架构？
- Python 跑 AI（Agent 生态最好），Rust 做桌面壳（性能好、安装包小）
- FastAPI 做中间层，前后端解耦，部署时 Python 可独立容器化
- Tauri 比 Electron 小 20 倍（11MB vs 250MB），内存占用低

### 2. 4-Agent 认知流水线

```
用户想法 ──→ Collector ──→ Weaver ──→ Architect ──→ Critic
              标准化      发散编织    收敛为设计    评分+反馈
              打标签      概念聚类    Mermaid 图    Pass/Fail
```

**面试重点**：
- 映射人类认知过程：发散（Weaver）→ 收敛（Architect）→ 审视（Critic）
- Critic 不合格 → 回退 Weaver 重做，闭环迭代
- 每个 Agent 通过 YAML 配置文件注入领域技能（动态、低仪式感）
- LangGraph 状态图编排，支持检查点恢复

### 3. 混合检索引擎

```
用户输入 → 语义向量检索 (ChromaDB) + 关键词 BM25 → 融合排序 → 截断策略
```

**面试重点**：
- 不是简单的 RAG，而是**混合检索**：语义 + 关键词互补
- 截断策略：按 Token 预算动态裁剪，优先保留高相关性内容
- 自主设计了 TruncationPolicy（不是调包）

### 4. Mermaid 实时渲染 + 语法自修复

**面试重点**：
- LLM 生成 Mermaid 代码天然不稳定（中文标签、引号、版本兼容性）
- 自研了 9 层清洗管线：引号标准化 → 中文标签加引号 → subgraph ID 去重 → `graph`→`flowchart` 转换 → `&` 展开 → `securityLevel` 调整...
- 这是一个典型的"LLM 输出后处理"工程问题，业界很常见（比如 structured output、guardrails）

### 5. 桌面端细节

- **全局热键**：Ctrl+Alt+[ 唤起输入窗（定位到鼠标位置）
- **热键切换**：输入窗/后台面板互切换，系统托盘图标左键切换
- **防抖处理**：`ShortcutState::Pressed` 过滤按键释放事件，避免双击闪退
- **NSIS 安装包**：一键安装，零依赖（Python 运行时打包在 exe 里）

---

## 面试官常见追问 & 回答

**Q: 为什么不用 Electron？**
A: Electron 打包 250MB+，内存 500MB+。Tauri 2 打包 43MB，内存 ~100MB，且 Rust 编译优化后启动更快。团队只有我一个，Tauri 的 DX 也不错。

**Q: AI 输出质量怎么保证？**
A: 四层防线 — (1) Critic Agent 自动评分（创新度/自洽性/可行性，0-1 分），不及格自动回退重做；(2) Critic Pass1 零 LLM 成本的结构化检查（Mermaid 组件引用完整性、JSON 格式校验）；(3) 用户可查看版本历史并手动触发重编织；(4) 所有 LLM 调用带 timeout + retry。

**Q: 检索为什么不用 LangChain？**
A: LangChain 太重，黑箱太多。我用 httpx 直连 DeepSeek/OpenAI API，ChromaDB 直接调原生接口。代码量反而少，调试也容易。

**Q: 最难的工程挑战是什么？**
A: Mermaid 10.9.0 渲染。LLM 输出的 Mermaid 代码有中文标签、中文引号、`&` 多节点语法、重复 subgraph ID... 各种边界情况。迭代了 6 版正则清洗管线才稳定。这个过程中深刻体会到"LLM 输出不可控"是当前 AI 工程化的核心难题。

**Q: 后续发展方向？**
A: V3 是自治式演进 — Agent 持续监听技术资讯、用户行为，当概念簇达到"临界质量"时主动推送设计提案，从被动工具变成主动思考伙伴。

---

## 数字速览

| 指标 | 数值 |
|---|---|
| 代码行数 | ~8000 行 Python + ~600 行 Rust + ~1000 行 TypeScript |
| Agent 数量 | 4 核心 + 2 V2 + 1 V3 = 7 |
| 安装包大小 | 43MB (含 Python 运行时) |
| 单次编织耗时 | 30-90 秒 (取决于 LLM) |
| API 端点 | 20+ RESTful |
| 数据库 | SQLite (元数据) + ChromaDB (向量) + 文件系统 (Markdown 导出) |
| 测试覆盖率 | 核心 Agent 管线 100%，API 路由 80% |
