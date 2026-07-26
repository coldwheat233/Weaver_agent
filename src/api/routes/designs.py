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

    # 后端渲染 Markdown → HTML (零 CDN 依赖)
    import re as _re
    md = doc.content_markdown
    # Mermaid 块 → 清洗语法 → <div class="mermaid">code</div>
    def _save_mermaid(m):
        code = m.group(1)
        # 1. 字面量 \n → 真换行
        code = code.replace('\\n', '\n')
        # 2. 中文引号 → 英文
        code = code.replace('“', '"').replace('”', '"')
        # 3. graph → flowchart（向下兼容，支持 & 多节点语法）
        code = _re.sub(r'\bgraph\s+(TD|LR|BT|RL)\b', r'flowchart \1', code)
        # 5. subgraph 行清洗：去掉中文，保留 ASCII 标签；纯中文用唯一 ID
        _sg_counter = [0]
        def _clean_subgraph(sm):
            label = sm.group(1).strip()
            ascii_part = _re.sub(r'[^\x00-\x7F]+', '', label).strip()
            ascii_part = ascii_part.strip('"\'').strip()
            if not ascii_part:
                _sg_counter[0] += 1
                ascii_part = f'SG{_sg_counter[0]}'
            return f'subgraph "{ascii_part}"'
        code = _re.sub(r'subgraph\s+(.+)', _clean_subgraph, code)
        # 6. 含中文/特殊字符的节点标签加双引号（覆盖全部 4 种 Mermaid 节点形状）
        def _quote_node(nm):
            nid = nm.group(1)
            br = nm.group(2)   # [ { ( >
            label = nm.group(3)
            cl = nm.group(4)   # ] } ) ]
            # 已是 "..." 包裹则跳过
            if label.startswith('"') and label.endswith('"'):
                return nm.group(0)
            if _re.search(r'[一-鿿＀-￯/:()（）]', label):
                clean = label.replace('"', "'")
                return f'{nid}{br}"{clean}"{cl}'
            return nm.group(0)
        code = _re.sub(r'(\w+)(\[)([^\]]+)(\])', _quote_node, code)   # 方括号
        code = _re.sub(r'(\w+)(\{)([^}]+)(\})', _quote_node, code)    # 花括号
        code = _re.sub(r'(\w+)(\()([^)]+)(\))', _quote_node, code)    # 圆括号
        code = _re.sub(r'(\w+)(>)([^\]]+)(\])', _quote_node, code)    # 不对称（稀有，但保留）
        # 7. 边标签：含中文的 -->|标签| → 加引号保护
        def _quote_edge(em):
            lbl = em.group(2)
            if lbl.startswith('"') and lbl.endswith('"'):
                return em.group(0)
            if _re.search(r'[一-鿿]', lbl):
                return f'{em.group(1)}"{lbl}"{em.group(3)}'
            return em.group(0)
        code = _re.sub(r'(-[.\-]?>?\s*\|)([^|]+)(\|)', _quote_edge, code)
        # 8. 展开 & 多节点语法 → 独立边（消除版本兼容风险）
        def _expand_ampersand(line):
            if '&' not in line:
                return line
            # 匹配: NODES & NODES  ARROW  NODES & NODES（edge label 版 & 无 label 版）
            m = _re.match(r'^(\s*)([\w\s&]+?)(\s*(?:-[.\-]?>|==>)\s*\|[^|]+\|)(\s*)([\w\s&]+)(.*)', line)
            if not m:
                m = _re.match(r'^(\s*)([\w\s&]+?)(\s*(?:-[.\-]?>|==>))(\s*)([\w\s&]+)(.*)', line)
            if m:
                indent = m.group(1)
                left_nodes  = [n.strip() for n in m.group(2).split('&')]
                arrow = m.group(3).strip()
                # m.group(4) is whitespace between arrow and right side — discard, use single space
                right_nodes = [n.strip() for n in m.group(5).split('&')]
                rest = m.group(6)
                if len(left_nodes) > 1:
                    return '\n'.join(f'{indent}{n} {arrow} {right_nodes[0]}{rest}' for n in left_nodes)
                elif len(right_nodes) > 1:
                    return '\n'.join(f'{indent}{left_nodes[0]} {arrow} {n}{rest}' for n in right_nodes)
            return line
        code = '\n'.join(_expand_ampersand(l) for l in code.split('\n'))
        # 9. 插入 div（Mermaid 代码作为 textContent）
        return f'<div class="mermaid">{code}</div>'
    md = _re.sub(r'```mermaid\n(.*?)```', _save_mermaid, md, flags=_re.DOTALL)
    # 基本 Markdown → HTML
    html_body = _simple_md_to_html(md)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{doc.title} — Idea Weaver</title>
<script src="/static/mermaid.min.js"></script>
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

<div class="content" id="markdown-content">{html_body}</div>

<script>
// Mermaid 渲染
mermaid.initialize({{
  startOnLoad: false,
  securityLevel: 'loose',
  theme: 'base',
  themeVariables: {{
    primaryColor: '#ECFEFF', primaryBorderColor: '#0891B2',
    primaryTextColor: '#1A1A2E', lineColor: '#A0A0AC',
    fontFamily: '"PingFang SC","Microsoft YaHei",sans-serif'
  }}
}});
mermaid.run({{ querySelector: '.mermaid' }});
</script>
</body>
</html>"""

    return HTMLResponse(html)


def _simple_md_to_html(md: str) -> str:
    """简易 Markdown → HTML（无需 CDN）"""
    import re
    # 代码块 (非 mermaid)
    md = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', md, flags=re.DOTALL)
    # 行内代码
    md = re.sub(r'`([^`]+)`', r'<code>\1</code>', md)
    # 标题
    md = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', md, flags=re.MULTILINE)
    md = re.sub(r'^### (.+)$', r'<h3>\1</h3>', md, flags=re.MULTILINE)
    md = re.sub(r'^## (.+)$', r'<h2>\1</h2>', md, flags=re.MULTILINE)
    md = re.sub(r'^# (.+)$', r'<h1>\1</h1>', md, flags=re.MULTILINE)
    # 粗体/斜体
    md = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', md)
    md = re.sub(r'\*(.+?)\*', r'<em>\1</em>', md)
    # 引用
    md = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', md, flags=re.MULTILINE)
    # 分隔线
    md = re.sub(r'^---$', '<hr>', md, flags=re.MULTILINE)
    # 无序列表
    md = re.sub(r'^- (.+)$', r'<li>\1</li>', md, flags=re.MULTILINE)
    md = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', md, flags=re.DOTALL)
    # 表格
    md = re.sub(r'^\|(.+)\|$', lambda m: '<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in m.group(1).split('|') if c.strip()) + '</tr>', md, flags=re.MULTILINE)
    md = re.sub(r'<tr>(<td>-+</td>)+</tr>', '', md)
    md = re.sub(r'(<tr>.*</tr>)', r'<table>\1</table>', md, flags=re.DOTALL)
    # 段落
    paragraphs = md.split('\n\n')
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p or p.startswith('<h') or p.startswith('<pre') or p.startswith('<table') or p.startswith('<ul') or p.startswith('<blockquote') or p.startswith('<hr') or p.startswith('<div'):
            result.append(p)
        else:
            result.append(f'<p>{p}</p>')
    return '\n'.join(result)
