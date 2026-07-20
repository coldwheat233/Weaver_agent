"""设计文档路由"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from uuid import UUID
from src.storage.database import get_async_session
from src.storage.design_repo import DesignRepo
from src.storage.file_store import FileStore

router = APIRouter(prefix="/api/designs", tags=["designs"])
file_store = FileStore()


@router.get("")
async def list_designs(limit: int = 20):
    """列出所有设计文档"""
    async with await get_async_session() as db:
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT * FROM design_documents ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit},
        )
        docs = result.fetchall()
    return [
        {
            "design_id": d[0],
            "title": d[1],
            "type": d[2],
            "innovation_score": d[5],
            "coherence_score": d[6],
            "feasibility_score": d[7],
            "critic_approval": bool(d[8]),
            "version": d[10],
        }
        for d in docs
    ]


@router.get("/{design_id}")
async def get_design(design_id: str):
    """获取设计文档 JSON"""
    async with await get_async_session() as db:
        repo = DesignRepo(db)
        doc = await repo.get(UUID(design_id))

    if not doc:
        return {"error": "not found"}, 404

    return {
        "design_id": str(doc.id),
        "title": doc.title,
        "type": doc.type.value,
        "content_markdown": doc.content_markdown,
        "innovation_score": doc.innovation_score,
        "coherence_score": doc.coherence_score,
        "feasibility_score": doc.feasibility_score,
        "critic_approval": doc.critic_approval,
        "critic_feedback": doc.critic_feedback,
        "version": doc.version,
    }


@router.get("/{design_id}/html", response_class=HTMLResponse)
async def get_design_html(design_id: str):
    """获取设计文档为自包含 HTML"""
    async with await get_async_session() as db:
        repo = DesignRepo(db)
        doc = await repo.get(UUID(design_id))

    if not doc:
        return HTMLResponse("<h1>Not Found</h1>", status_code=404)

    # 构建自包含 HTML — marked.js 解析 Markdown, mermaid 渲染图表
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{doc.title} — Idea Weaver</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  :root {{
    --bg: #FCFCFD; --text: #1A1A2E; --text-secondary: #6E6E7C;
    --accent: #0891B2; --surface: #F3F3F5; --radius: 14px;
  }}
  * {{ box-sizing:border-box;margin:0;padding:0; }}
  body {{
    background: var(--bg); color: var(--text);
    font-family: "PingFang SC","Microsoft YaHei",sans-serif;
    line-height:1.7; max-width:780px; margin:0 auto; padding:48px 24px;
    -webkit-font-smoothing:antialiased;
  }}
  h1 {{ font-size:28px;font-weight:600;margin-bottom:8px; }}
  h2 {{ font-size:20px;font-weight:600;margin:40px 0 16px;color:var(--accent); }}
  h3 {{ font-size:16px;font-weight:600;margin:24px 0 12px; }}
  .meta {{ color:var(--text-secondary);font-size:14px;margin-bottom:32px; }}
  .scores {{ display:flex;gap:24px;justify-content:center;margin:32px 0; }}
  .score-card {{
    display:flex;flex-direction:column;align-items:center;gap:8px;
    padding:20px 32px;background:#FFF;border-radius:var(--radius);
    box-shadow:0 1px 3px rgba(0,0,0,0.04),0 1px 2px rgba(0,0,0,0.06);
  }}
  .score-value {{ font-size:22px;font-weight:600;color:var(--accent); }}
  .score-label {{ font-size:12px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px; }}
  .mermaid {{ background:var(--surface);border-radius:var(--radius);padding:24px;margin:16px 0; }}
  table {{ width:100%;border-collapse:collapse;margin:16px 0;font-size:14px; }}
  th, td {{ padding:10px 14px;text-align:left;border-bottom:1px solid #E5E5E8; }}
  th {{ font-weight:600;color:var(--text-secondary);font-size:12px;text-transform:uppercase; }}
  /* Markdown 渲染 */
  #markdown-content h1 {{ font-size:24px;font-weight:600;margin:32px 0 12px;color:var(--text); }}
  #markdown-content h2 {{ font-size:20px;font-weight:600;margin:28px 0 10px;color:var(--accent); }}
  #markdown-content h3 {{ font-size:16px;font-weight:600;margin:20px 0 8px; }}
  #markdown-content h4 {{ font-size:14px;font-weight:600;margin:16px 0 6px; }}
  #markdown-content p {{ margin:8px 0;line-height:1.8; }}
  #markdown-content ul, #markdown-content ol {{ padding-left:24px;margin:8px 0; }}
  #markdown-content li {{ margin:4px 0;line-height:1.7; }}
  #markdown-content a {{ color:var(--accent);text-decoration:none; }}
  #markdown-content a:hover {{ text-decoration:underline; }}
  #markdown-content strong {{ font-weight:600; }}
  #markdown-content em {{ font-style:italic; }}
  #markdown-content pre {{ background:var(--surface);border-radius:var(--radius);padding:20px;overflow-x:auto;font-size:13px;margin:12px 0;border:1px solid #E5E5E8; }}
  #markdown-content pre code {{ background:none;padding:0;font-size:13px;display:block;line-height:1.6; }}
  #markdown-content code {{ font-family:"Cascadia Code","Fira Code","SF Mono",monospace;font-size:0.9em;background:var(--surface);padding:2px 6px;border-radius:4px;color:#E11D48; }}
  #markdown-content pre code {{ color:var(--text); }}
  #markdown-content blockquote {{ border-left:3px solid var(--accent);padding:8px 16px;margin:16px 0;color:var(--text-secondary);background:var(--accent-subtle);border-radius:0 8px 8px 0; }}
  #markdown-content table {{ width:100%;border-collapse:collapse;margin:16px 0;font-size:14px; }}
  #markdown-content th, #markdown-content td {{ padding:10px 14px;text-align:left;border-bottom:1px solid #E5E5E8; }}
  #markdown-content th {{ font-weight:600;color:var(--text-secondary);font-size:12px;text-transform:uppercase;background:var(--surface); }}
  #markdown-content tr:hover {{ background:#FAFAFA; }}
  #markdown-content hr {{ border:none;border-top:1px solid #E5E5E8;margin:24px 0; }}
  #markdown-content img {{ max-width:100%;border-radius:var(--radius);margin:12px 0; }}
  .mermaid {{ background:var(--surface);border-radius:var(--radius);padding:24px;margin:16px 0;overflow-x:auto; }}
</style>
</head>
<body>
<h1>{doc.title}</h1>
<p class="meta">Idea Weaver · v{doc.version}</p>

<div class="scores">
  <div class="score-card"><span class="score-value">{doc.innovation_score:.2f}</span><span class="score-label">创新度</span></div>
  <div class="score-card"><span class="score-value">{doc.coherence_score:.2f}</span><span class="score-label">自洽性</span></div>
  <div class="score-card"><span class="score-value">{doc.feasibility_score:.2f}</span><span class="score-label">可行性</span></div>
</div>

<div class="content" id="markdown-content"></div>

<script>
// 1. 提取 Mermaid 块并替换为占位符
const raw = `{doc.content_markdown.replace('`', '\\`').replace('$', '\\$')}`;
const mermaidBlocks = [];
let processed = raw.replace(/```mermaid\\n([\\s\\S]*?)```/g, (_, code) => {{
  mermaidBlocks.push(code);
  return '<div class="mermaid"></div>';
}});

// 2. Markdown → HTML
marked.setOptions({{ breaks: true, gfm: true }});
document.getElementById('markdown-content').innerHTML = marked.parse(processed);

// 3. 渲染 Mermaid
mermaid.initialize({{
  startOnLoad: false,
  theme: 'base',
  themeVariables: {{
    primaryColor: '#ECFEFF',
    primaryBorderColor: '#0891B2',
    primaryTextColor: '#1A1A2E',
    lineColor: '#A0A0AC',
    fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif'
  }}
}});
mermaidBlocks.forEach((code, i) => {{
  const el = document.querySelectorAll('.mermaid')[i];
  if (el) el.textContent = code;
}});
mermaid.run({{ querySelector: '.mermaid' }});
</script>
</body>
</html>"""

    return HTMLResponse(html)
