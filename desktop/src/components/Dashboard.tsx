import { useEffect, useState } from "react";
import { api, IdeaNode, DesignDoc, V3Proposal } from "../lib/api";

interface Props {
  onOpenCapture: () => void;
  onClose: () => void;
  onOpenSettings: () => void;
}

async function startDrag() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().startDragging();
  } catch {
    /* 浏览器环境忽略 */
  }
}

export default function Dashboard({ onOpenCapture, onClose, onOpenSettings }: Props) {
  const [ideas, setIdeas] = useState<IdeaNode[]>([]);
  const [designs, setDesigns] = useState<DesignDoc[]>([]);
  const [proposals, setProposals] = useState<V3Proposal[]>([]);
  const [weaving, setWeaving] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [backendError, setBackendError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [needsConfig, setNeedsConfig] = useState(false);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    setLoading(true);
    setBackendError(null);

    // 先检查后端连通性
    try {
      const r = await fetch("http://localhost:8765/api/health");
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    } catch (e) {
      setBackendError("后端未启动或无法连接 (localhost:8765)");
      setLoading(false);
      return;
    }

    // 检查模型是否已配置
    try {
      const r = await fetch("http://localhost:8765/api/config");
      const d = await r.json();
      setNeedsConfig(!d.has_api_key && d.provider !== "ollama");
    } catch {}

    const errs: string[] = [];
    try { setIdeas(await api.listIdeas()); } catch (e) { errs.push("想法加载失败"); }
    try { setDesigns(await api.listDesigns()); } catch (e) { errs.push("设计加载失败"); }
    try {
      const p = await api.listProposals();
      setProposals(p.proposals || []);
    } catch (e) { errs.push("V3 提案加载失败"); }

    if (errs.length) setBackendError(errs.join(" · "));
    setLoading(false);
  };

  const triggerWeave = async () => {
    setWeaving(true);
    setBackendError(null);
    try {
      let sid = sessionId;
      if (!sid) {
        const s = await api.createSession("编织所有想法");
        sid = s.session_id;
        setSessionId(sid);
      }
      await api.triggerWeave(sid);
      setTimeout(async () => {
        try { setDesigns(await api.listDesigns()); } catch {}
        setWeaving(false);
      }, 3000);
    } catch (e) {
      setBackendError(`编织失败: ${e}`);
      setWeaving(false);
    }
  };

  const openUrl = async (url: string) => {
    try {
      const { open } = await import("@tauri-apps/plugin-shell");
      await open(url);
    } catch {
      window.open(url, "_blank");
    }
  };

  const openDesign = (did: string) => {
    openUrl(`http://localhost:8765/api/designs/${did}/html`);
  };

  return (
    <>
      {/* Title bar */}
      <div className="titlebar" onMouseDown={startDrag} style={{ cursor: "move" }}>
        <div className="titlebar-left">
          <span className="titlebar-title">☰ 用户后台</span>
        </div>
        <div className="titlebar-actions" onMouseDown={(e) => e.stopPropagation()}>
          <button className="titlebar-btn" onClick={onOpenCapture} title="输入想法">
            ✏️
          </button>
          <button className="titlebar-btn" onClick={onOpenSettings} title="模型配置">
            ⚙
          </button>
          <button
            className="titlebar-btn"
            onClick={() => openUrl("http://localhost:8765/dashboard")}
            title="在浏览器中查看"
          >
            🔗
          </button>
          <button className="titlebar-btn danger" onClick={onClose} title="关闭 (Esc)">
            ✕
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="dash-scroll">
        {/* 未配置模型横幅 */}
        {needsConfig && (
          <div
            style={{
              margin: "8px 0", padding: "12px 16px", borderRadius: 12,
              background: "#FFFBEB", border: "1px solid #FDE68A",
              fontSize: 12, color: "#D97706", cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}
            onClick={onOpenSettings}
          >
            <span>⚠ 尚未配置模型 API Key，点击前往设置</span>
            <span style={{ fontWeight: 600 }}>配置 →</span>
          </div>
        )}

        {/* Backend error banner */}
        {backendError && (
          <div style={{
            margin: "8px 0", padding: "10px 14px",
            background: "#FEF2F2", border: "1px solid #FECACA",
            borderRadius: 12, fontSize: 12, color: "#EF4444",
          }}>
            ⚠ {backendError}
            <button
              style={{ marginLeft: 8, padding: "2px 10px", border: "none", borderRadius: 999,
                       background: "#FFF", color: "#EF4444", fontSize: 11, cursor: "pointer" }}
              onClick={loadAll}
            >
              重试
            </button>
          </div>
        )}
        {loading && !backendError && (
          <div style={{ textAlign: "center", padding: "20px 0", fontSize: 12, color: "#A0A0AC" }}>
            加载中...
          </div>
        )}

        {/* Stats */}
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-value">{ideas.length}</div>
            <div className="stat-label">想法</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{designs.length}</div>
            <div className="stat-label">设计</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{proposals.length}</div>
            <div className="stat-label">提案</div>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button className="action-btn primary" onClick={triggerWeave} disabled={weaving}>
            {weaving ? "编织中..." : "编织所有想法 →"}
          </button>
          <button
            className="action-btn secondary"
            onClick={() => openUrl("http://localhost:8765/dashboard")}
          >
            在浏览器查看
          </button>
        </div>

        {/* Recent Ideas */}
        <div className="section-header">
          <span className="section-title">📝 最近想法</span>
          <span className="section-count">{ideas.length} 条</span>
        </div>
        {ideas.slice(-10).reverse().map((i) => (
          <div key={i.id} className="card">
            <div className="card-title">
              {(i.standardized_content || i.raw_content || "").slice(0, 100)}
            </div>
            <div className="card-subtitle">
              {(i.intent_tags || []).slice(0, 3).join(" · ")} · {(i.context_tags || []).slice(0, 3).join(", ")}
            </div>
          </div>
        ))}
        {ideas.length === 0 && (
          <div className="empty-state">
            还没有想法。按 Ctrl+Alt+[ 开始捕捉
          </div>
        )}

        {/* Recent Designs */}
        <div className="section-header">
          <span className="section-title">🏗 编织成果</span>
          <span className="section-count">{designs.length} 份</span>
        </div>
        {designs.slice(-8).reverse().map((d) => (
          <div key={d.design_id} className="card" onClick={() => openDesign(d.design_id)}>
            <div className="card-title">{(d.title || "未命名").slice(0, 60)}</div>
            <div className="card-scores">
              <div className="card-score">
                创新 <span>{d.innovation_score?.toFixed(2)}</span>
              </div>
              <div className="card-score">
                自洽 <span>{d.coherence_score?.toFixed(2)}</span>
              </div>
              <div className="card-score">
                可行 <span>{d.feasibility_score?.toFixed(2)}</span>
              </div>
            </div>
          </div>
        ))}
        {designs.length === 0 && (
          <div className="empty-state">
            提交想法后点击「编织所有想法」生成设计
          </div>
        )}

        {/* V3 Proposals */}
        <div className="section-header">
          <span className="section-title">🔄 V3 自治演进</span>
          <span className="section-count">{proposals.length} 个提案</span>
        </div>
        {proposals.slice(0, 5).map((p, i) => (
          <div key={i} className="card">
            <div className="card-title">{p.cluster_name}</div>
            <div className="card-subtitle">
              {p.node_count} 想法 · {p.cross_domains} 领域 · {p.status}
            </div>
          </div>
        ))}
        {proposals.length === 0 && (
          <div className="empty-state">
            概念簇达到临界质量时将自动推送设计提案
          </div>
        )}
      </div>
    </>
  );
}
