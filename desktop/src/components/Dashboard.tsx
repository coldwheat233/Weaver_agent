import { useEffect, useState, useRef } from "react";
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
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [tab, setTab] = useState<"ideas" | "graph" | "designs" | "v3" | "news">("ideas");
  const [ideaPage, setIdeaPage] = useState(1);
  const [designPage, setDesignPage] = useState(1);
  const [dailyPrompt, setDailyPrompt] = useState<{ question: string; context: string } | null>(null);
  const [newsItems, setNewsItems] = useState<any[]>([]);
  const PAGE_SIZE = 10;

  useEffect(() => {
    loadAll();
    // 监听"想法提交"事件自动刷新
    let unlisten: (() => void) | undefined;
    import("@tauri-apps/api/event").then(({ listen }) => {
      listen("idea-submitted", () => loadAll()).then((fn) => { unlisten = fn; });
    }).catch(() => {});
    return () => { unlisten?.(); };
  }, []);

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
    try {
      const r = await fetch("http://localhost:8765/api/daily-prompt");
      if (r.ok) setDailyPrompt(await r.json());
    } catch {}
    try {
      const r = await fetch("http://localhost:8765/api/tech-news");
      if (r.ok) { const d = await r.json(); setNewsItems(d.items || []); }
    } catch {}

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
          <button className="titlebar-btn" onClick={onOpenCapture} title="输入想法 (Ctrl+Alt+[)">
            ✏️
          </button>
          <button className="titlebar-btn" onClick={onOpenSettings} title="模型配置">
            ⚙
          </button>
          <button className="titlebar-btn" onClick={async () => {
            try { const { getCurrentWindow } = await import("@tauri-apps/api/window");
                  await getCurrentWindow().minimize(); } catch {}
          }} title="最小化">
            ─
          </button>
          <button className="titlebar-btn" onClick={() => openUrl("http://localhost:8765/dashboard")} title="在浏览器查看">
            🔗
          </button>
          <button className="titlebar-btn danger" onClick={onClose} title="隐藏 (Esc)">
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

        {/* 每日思考题 */}
        {dailyPrompt && dailyPrompt.question && (
          <div style={{
            margin: "0 0 12px", padding: "12px 16px", borderRadius: 12,
            background: "linear-gradient(135deg, #ECFEFF, #F0F9FF)",
            border: "1px solid #CFFAFE", cursor: "pointer",
          }} onClick={async () => {
            try {
              const s = await api.createSession(dailyPrompt.question.slice(0, 80));
              await api.submitIdea(dailyPrompt.question, s.session_id);
              setToastMsg("✓ 已作为想法捕捉");
              setTimeout(() => setToastMsg(null), 2000);
            } catch {}
          }}>
            <div style={{ fontSize: 11, color: "#0891B2", fontWeight: 600, marginBottom: 4 }}>
              💡 每日思考
            </div>
            <div style={{ fontSize: 13, color: "#1A1A2E", fontWeight: 500, lineHeight: 1.5 }}>
              {dailyPrompt.question}
            </div>
            {dailyPrompt.context && (
              <div style={{ fontSize: 11, color: "#6E6E7C", marginTop: 4 }}>
                {dailyPrompt.context}
              </div>
            )}
            <div style={{ fontSize: 10, color: "#A0A0AC", marginTop: 6 }}>点击捕捉为想法 →</div>
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
        <div style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
          <button className="action-btn primary" onClick={triggerWeave} disabled={weaving}>
            {weaving ? "编织中..." : ideas.length > 0 ? `编织 ${ideas.length} 条想法 →` : "编织所有想法 →"}
          </button>
          {designs.length > 0 && (
            <span style={{ fontSize: 12, color: "#10B981", fontWeight: 500 }}>
              ✓ {designs.length} 份设计成果
            </span>
          )}
          {ideas.length > 0 && designs.length === 0 && !weaving && (
            <span style={{ fontSize: 12, color: "#F59E0B", fontWeight: 500 }}>
              {ideas.length} 条想法待编织
            </span>
          )}
        </div>

        {/* Tab 导航 (文字按钮) */}
        <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #E5E5E8", marginBottom: 12 }}>
          {[
            { key: "ideas", label: `想法 · ${ideas.length}` },
            { key: "graph", label: "图谱" },
            { key: "designs", label: `设计 · ${designs.length}` },
            { key: "v3", label: `V3 · ${proposals.length}` },
            { key: "news", label: `资讯 · ${newsItems.length}` },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key as any)}
              style={{
                padding: "8px 20px", border: "none", borderBottom: tab === t.key ? "2px solid #0891B2" : "2px solid transparent",
                background: "transparent", color: tab === t.key ? "#0891B2" : "#6E6E7C",
                fontSize: 13, fontWeight: 600,
                cursor: "pointer", fontFamily: "inherit",
                transition: "all 120ms ease",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content (固定最小高度防抖动) */}
        <div style={{ minHeight: 280 }}>
        {tab === "ideas" && (
          <>
            {ideas.slice(-(ideaPage * PAGE_SIZE)).reverse().slice(0, PAGE_SIZE).map((i) => (
              <div key={i.id} className="card">
                <div className="card-title">
                  {(i.standardized_content || i.raw_content || "").slice(0, 100)}
                </div>
                <div className="card-subtitle">
                  {(i.intent_tags || []).slice(0, 3).join(" · ")} · {(i.context_tags || []).slice(0, 3).join(", ")}
                </div>
              </div>
            ))}
            {ideas.length > ideaPage * PAGE_SIZE && (
              <button onClick={() => setIdeaPage((p) => p + 1)}
                style={{ width:"100%", padding:8, border:"none", borderRadius:10, background:"#F3F3F5", color:"#6E6E7C", fontSize:12, cursor:"pointer", fontFamily:"inherit" }}>
                加载更多 ({ideas.length - ideaPage * PAGE_SIZE} 条剩余)
              </button>
            )}
            {ideas.length === 0 && (
              <div className="empty-state">还没有想法。按 Ctrl+Alt+[ 开始捕捉</div>
            )}
          </>
        )}

        {/* Tab: 设计 */}
        {tab === "designs" && (
          <>
            {designs.slice(-(designPage * PAGE_SIZE)).reverse().slice(0, PAGE_SIZE).map((d) => (
              <div key={d.design_id} className="card" onClick={() => openDesign(d.design_id)}>
                <div className="card-title">{(d.title || "未命名").slice(0, 60)}</div>
                <div className="card-scores">
                  <div className="card-score">创新 <span>{d.innovation_score?.toFixed(2)}</span></div>
                  <div className="card-score">自洽 <span>{d.coherence_score?.toFixed(2)}</span></div>
                  <div className="card-score">可行 <span>{d.feasibility_score?.toFixed(2)}</span></div>
                </div>
              </div>
            ))}
            {designs.length > designPage * PAGE_SIZE && (
              <button onClick={() => setDesignPage((p) => p + 1)}
                style={{ width:"100%", padding:8, border:"none", borderRadius:10, background:"#F3F3F5", color:"#6E6E7C", fontSize:12, cursor:"pointer", fontFamily:"inherit" }}>
                加载更多 ({designs.length - designPage * PAGE_SIZE} 条剩余)
              </button>
            )}
            {designs.length === 0 && (
              <div className="empty-state">提交想法后点击「编织所有想法」生成设计</div>
            )}
          </>
        )}

        {/* Tab: 图谱 */}
        {tab === "graph" && (
          <div style={{ width: "100%", height: 320, background: "#FFF", borderRadius: 14, overflow: "hidden", position: "relative" }}>
            <GraphView ideas={ideas} />
            {ideas.length === 0 && (
              <div className="empty-state" style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                还没有想法，提交后这里会呈现关联图谱
              </div>
            )}
          </div>
        )}

        {/* Tab: V3 */}
        {tab === "v3" && (
          <>
            {proposals.slice(0, 5).map((p, i) => (
              <div key={i} className="card">
                <div className="card-title">{p.cluster_name}</div>
                <div className="card-subtitle">
                  {p.node_count} 想法 · {p.cross_domains} 领域 · {p.status}
                </div>
              </div>
            ))}
            {proposals.length === 0 && (
              <div className="empty-state">概念簇达到临界质量时将自动推送设计提案</div>
            )}
          </>
        )}

        {/* Tab: 资讯 */}
        {tab === "news" && (
          <>
            {newsItems.filter((item: any) => !item.title?.startsWith("抓取失败")).map((item: any, i: number) => (
              <div key={i} className="card"
                style={{ transition: "opacity 0.2s", cursor: "pointer" }}
                onClick={() => item.link && openUrl(item.link)}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div className="card-title" style={{ flex: 1 }}>{item.title?.slice(0, 100)}</div>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      try {
                        const r = await fetch("http://localhost:8765/api/tech-news/ingest", {
                          method: "POST", headers: { "Content-Type": "application/json" },
                          body: JSON.stringify(item),
                        });
                        if (r.ok) { setToastMsg("✓ 已捕捉"); setTimeout(() => setToastMsg(null), 2000); loadAll(); }
                      } catch { setToastMsg("✗ 失败"); setTimeout(() => setToastMsg(null), 2000); }
                    }}
                    style={{
                      padding: "2px 10px", border: "1px solid #CFFAFE", borderRadius: 999,
                      background: "#ECFEFF", color: "#0891B2", fontSize: 11, cursor: "pointer",
                      fontFamily: "inherit", flexShrink: 0, marginLeft: 8,
                    }}
                  >捕捉</button>
                </div>
                <div className="card-subtitle">
                  {item.source} · {item.description?.slice(0, 80)}
                </div>
              </div>
            ))}
            {newsItems.length === 0 && (
              <div className="empty-state">正在抓取技术资讯...</div>
            )}
          </>
        )}
        </div>

        {/* Toast */}
        {toastMsg && (
          <div style={{
            position: "absolute", bottom: 48, left: "50%", transform: "translateX(-50%)",
            padding: "6px 16px", borderRadius: 999, background: "#1A1A2E", color: "#FFF",
            fontSize: 12, zIndex: 10, whiteSpace: "nowrap",
          }}>
            {toastMsg}
          </div>
        )}

        {/* 快捷键提示 */}
        <div style={{ textAlign: "center", padding: "24px 0 8px", fontSize: 11, color: "#A0A0AC" }}>
          Ctrl+Alt+[ 输入想法 · Ctrl+Alt+] 用户后台 · Esc 隐藏 · 左键托盘切换
        </div>
      </div>
    </>
  );
}

// ═══ 力导向图谱组件 (拖动 + 缩放 + 簇细节) ═══
const COLORS = ["#0891B2", "#06B6D4", "#0D9488", "#6366F1", "#8B5CF6", "#EC4899", "#F59E0B"];
const NODE_R = 10;

function GraphView({ ideas }: { ideas: IdeaNode[] }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ideas.length === 0 || !svgRef.current) return;
    const svg = svgRef.current;
    const el = containerRef.current!;
    const W = el.clientWidth || 560;
    const H = 320;

    // 状态
    interface GNode { id: string; x: number; y: number; vx: number; vy: number; label: string; full: string; tags: string; r: number; color: string; fx?: number; fy?: number; }
    const nodes: GNode[] = ideas.slice(0, 20).map((i) => ({
      id: i.id,
      x: W / 2 + (Math.random() - 0.5) * W * 0.4,
      y: H / 2 + (Math.random() - 0.5) * H * 0.4,
      vx: 0, vy: 0,
      label: (i.standardized_content || i.raw_content || "").slice(0, 18),
      full: i.standardized_content || i.raw_content || "",
      tags: [...(i.intent_tags || []), ...(i.context_tags || [])].slice(0, 4).join(" · "),
      r: NODE_R + (i.context_tags?.length || 0) * 1.5,
      color: COLORS[(i.context_tags || []).length % COLORS.length],
    }));

    const edges: [number, number, number][] = [];
    for (let i = 0; i < nodes.length; i++) {
      const iTags = new Set(ideas[i]?.context_tags || []);
      for (let j = i + 1; j < nodes.length; j++) {
        const shared = (ideas[j]?.context_tags || []).filter((t) => iTags.has(t)).length;
        if (shared > 0) edges.push([i, j, 0.5 + shared * 0.15]);
        else if (Math.random() < 0.06) edges.push([i, j, 0.15]);
      }
    }

    // 缩放 + 平移
    let scale = 1, tx = 0, ty = 0;
    let dragging: number | null = null;
    let dragOX = 0, dragOY = 0;
    let tooltipNode: GNode | null = null;

    // 渲染 (Canvas-like approach: direct DOM manipulation)
    const render = () => {
      let html = `<g transform="translate(${tx},${ty}) scale(${scale})">`;
      // 边
      for (const [a, b, s] of edges) {
        html += `<line x1="${nodes[a].x}" y1="${nodes[a].y}" x2="${nodes[b].x}" y2="${nodes[b].y}" stroke="#E5E5E8" stroke-width="${1 + s * 2}" opacity="0.5" style="pointer-events:none"/>`;
      }
      // 节点
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        html += `<g class="graph-node" data-idx="${i}" style="cursor:grab">
          <circle cx="${n.x}" cy="${n.y}" r="${n.r}" fill="${n.color}" opacity="0.9" stroke="#FFF" stroke-width="1.5"/>
          <text x="${n.x}" y="${n.y - n.r - 5}" text-anchor="middle" font-size="10" fill="#6E6E7C" style="pointer-events:none">${n.label}</text>
        </g>`;
      }
      html += `</g>`;
      svg.innerHTML = html;

      // 绑定事件
      svg.querySelectorAll(".graph-node").forEach((g) => {
        const idx = parseInt(g.getAttribute("data-idx") || "-1");
        const n = nodes[idx];
        if (!n) return;
        g.addEventListener("mousedown", (e) => {
          e.stopPropagation();
          dragging = idx;
          const me = e as MouseEvent;
          dragOX = me.clientX - (n.fx ?? n.x);
          dragOY = me.clientY - (n.fy ?? n.y);
          n.fx = n.x; n.fy = n.y;
          (e.target as HTMLElement).style.cursor = "grabbing";
        });
        g.addEventListener("click", () => {
          if (dragging === null) {
            tooltipNode = tooltipNode?.id === n.id ? null : n;
          }
        });
      });

      // Tooltip
      let tipHtml = "";
      if (tooltipNode) {
        tipHtml = `<foreignObject x="${tx + tooltipNode.x * scale + 16}" y="${ty + tooltipNode.y * scale - 30}" width="200" height="80">
          <div style="background:#FFF;border-radius:10px;padding:8px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.1);font-size:11px;line-height:1.5;color:#1A1A2E;">
            <div style="font-weight:600;margin-bottom:4px;color:#0891B2">${tooltipNode.full.slice(0, 80)}</div>
            <div style="color:#6E6E7C;font-size:10px">${tooltipNode.tags}</div>
          </div>
        </foreignObject>`;
      }
      svg.innerHTML += tipHtml;
    };

    // 拖动/缩放事件
    el.onmousedown = (e) => {
      if (dragging === null) {
        dragOX = e.clientX - tx; dragOY = e.clientY - ty;
        el.style.cursor = "grabbing";
      }
    };
    window.addEventListener("mousemove", (e) => {
      if (dragging !== null) {
        const n = nodes[dragging];
        n.fx = e.clientX - dragOX;
        n.fy = e.clientY - dragOY;
        n.x = n.fx; n.y = n.fy; n.vx = 0; n.vy = 0;
      } else if (el.style.cursor === "grabbing") {
        tx = e.clientX - dragOX; ty = e.clientY - dragOY;
      }
    });
    window.addEventListener("mouseup", () => {
      dragging = null;
      el.style.cursor = "default";
    });
    el.onwheel = (e) => {
      e.preventDefault();
      const ds = e.deltaY > 0 ? 0.9 : 1.1;
      scale = Math.max(0.3, Math.min(3, scale * ds));
    };

    // 物理 tick
    let settled = 0;
    function tick() {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].fx !== undefined) continue;
        for (let j = i + 1; j < nodes.length; j++) {
          if (nodes[j].fx !== undefined) continue;
          const dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y;
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          const f = 800 / (d * d);
          nodes[i].vx -= (dx / d) * f; nodes[i].vy -= (dy / d) * f;
          nodes[j].vx += (dx / d) * f; nodes[j].vy += (dy / d) * f;
        }
      }
      for (const [a, b, s] of edges) {
        const dx = nodes[b].x - nodes[a].x, dy = nodes[b].y - nodes[a].y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const f = (d - 60) * 0.005 * s;
        if (nodes[a].fx === undefined) { nodes[a].vx += (dx / d) * f; nodes[a].vy += (dy / d) * f; }
        if (nodes[b].fx === undefined) { nodes[b].vx -= (dx / d) * f; nodes[b].vy -= (dy / d) * f; }
      }
      let maxMove = 0;
      for (const n of nodes) {
        if (n.fx !== undefined) { n.vx = 0; n.vy = 0; continue; }
        n.vx += (W / 2 - n.x) * 0.001; n.vy += (H / 2 - n.y) * 0.001;
        n.vx *= 0.85; n.vy *= 0.85;
        n.x = Math.max(NODE_R, Math.min(W - NODE_R, n.x + n.vx));
        n.y = Math.max(NODE_R, Math.min(H - NODE_R, n.y + n.vy));
        maxMove = Math.max(maxMove, Math.abs(n.vx), Math.abs(n.vy));
      }
      if (maxMove < 0.05) settled++; else settled = 0;
      render();
      if (settled < 30) requestAnimationFrame(tick);
    }
    tick();
    return () => { settled = 99; };
  }, [ideas]);

  return <div ref={containerRef} style={{ width: "100%", height: 320 }}>
    <svg ref={svgRef} width="100%" height="320" style={{ background: "#FCFCFD", borderRadius: 14 }} />
  </div>;
}
