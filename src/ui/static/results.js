/**
 * Idea Weaver — Results Viewer
 * 评分动画 + Mermaid 渲染 + D3.js 力导向概念图
 */

const API_BASE = window.location.origin;
const API_HOST = window.location.hostname;
const USE_POLLING = API_HOST !== 'localhost' && API_HOST !== '127.0.0.1';
const DESIGN_ID = new URLSearchParams(window.location.search).get('design_id');
const SESSION_ID = new URLSearchParams(window.location.search).get('session_id');

const CIRCUMFERENCE = 2 * Math.PI * 24; // r=24

async function load() {
  if (!DESIGN_ID) {
    document.getElementById('design-title').textContent = '未指定设计 ID';
    return;
  }

  try {
    const resp = await fetch(`${API_BASE}/api/designs/${DESIGN_ID}`);
    const data = await resp.json();
    render(data);
  } catch (err) {
    console.error('Failed to load design:', err);
    document.getElementById('design-title').textContent = '加载失败';
  }
}

function render(data) {
  // Title
  document.getElementById('design-title').textContent = data.title;
  document.getElementById('design-meta').textContent =
    `Idea Weaver · v${data.version} · ${new Date().toLocaleDateString('zh-CN')}`;

  // Scores with ring animation
  animateRing('ring-innovation', data.innovation_score);
  animateRing('ring-coherence', data.coherence_score);
  animateRing('ring-feasibility', data.feasibility_score);
  document.getElementById('score-innovation').textContent = data.innovation_score?.toFixed(2) || '-';
  document.getElementById('score-coherence').textContent = data.coherence_score?.toFixed(2) || '-';
  document.getElementById('score-feasibility').textContent = data.feasibility_score?.toFixed(2) || '-';

  // Markdown content
  const markdownHtml = simpleMarkdownToHtml(data.content_markdown);
  document.getElementById('markdown-content').innerHTML = markdownHtml;

  // Extract Mermaid diagrams
  const mermaidMatches = data.content_markdown.match(/```mermaid\n([\s\S]*?)```/g);
  if (mermaidMatches) {
    const mermaidCode = mermaidMatches.map(m => m.replace(/```mermaid\n/, '').replace(/```$/, '')).join('\n');
    document.getElementById('mermaid-render').innerHTML = `<div class="mermaid">${mermaidCode}</div>`;
    mermaid.init(undefined, document.querySelectorAll('.mermaid'));
  } else {
    document.getElementById('mermaid-section').style.display = 'none';
  }

  // D3 graph placeholder
  renderD3Graph(data);
}

function animateRing(elementId, score) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const offset = CIRCUMFERENCE * (1 - (score || 0));
  setTimeout(() => {
    el.style.strokeDashoffset = offset;
  }, 200);
}

function simpleMarkdownToHtml(md) {
  if (!md) return '';
  let html = md
    // Headers
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold/Italic
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Tables
    .replace(/^\|(.+)\|$/gm, (line) => {
      const cells = line.split('|').filter(c => c.trim());
      const tag = line.includes('---') ? 'th' : 'td';
      return `<tr>${cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('')}</tr>`;
    })
    // Paragraphs
    .replace(/\n\n/g, '</p><p>')
    // Lists
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // Blockquotes
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

  return `<p>${html}</p>`;
}

function renderD3Graph(data) {
  const container = document.getElementById('d3-graph');
  if (!container) return;

  const width = container.clientWidth;
  const height = 420;

  // Create a basic D3 force graph
  const svg = d3.select('#d3-graph')
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  // Simulated nodes from design clusters
  const nodes = [
    { id: '设计', group: 1, size: 12 },
    { id: '限流', group: 2, size: 10 },
    { id: 'Redis', group: 2, size: 8 },
    { id: 'API网关', group: 1, size: 10 },
    { id: '滑动窗口', group: 2, size: 7 },
    { id: '分布式', group: 3, size: 9 },
    { id: '高可用', group: 3, size: 8 },
  ];

  const links = [
    { source: '设计', target: '限流' },
    { source: '限流', target: 'Redis' },
    { source: '限流', target: '滑动窗口' },
    { source: '设计', target: 'API网关' },
    { source: '分布式', target: 'Redis' },
    { source: '高可用', target: '分布式' },
    { source: 'API网关', target: '高可用' },
  ];

  const color = d3.scaleOrdinal()
    .domain([1, 2, 3])
    .range(['#0891B2', '#06B6D4', '#CFFAFE']);

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(30))
    .alphaDecay(0.02)
    .velocityDecay(0.3);

  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#E5E5E8')
    .attr('stroke-width', 2);

  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', d => d.size)
    .attr('fill', d => color(d.group))
    .attr('stroke', '#0891B2')
    .attr('stroke-width', 1.5)
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }));

  const labels = svg.append('g')
    .selectAll('text')
    .data(nodes)
    .join('text')
    .text(d => d.id)
    .attr('text-anchor', 'middle')
    .attr('dy', d => -d.size - 4)
    .attr('fill', '#6E6E7C')
    .attr('font-size', '11px')
    .style('pointer-events', 'none');

  node.on('mouseenter', function() {
    d3.select(this).attr('stroke-width', 3).attr('r', d => d.size * 1.3);
  }).on('mouseleave', function() {
    d3.select(this).attr('stroke-width', 1.5).attr('r', d => d.size);
  });

  simulation.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('cx', d => d.x).attr('cy', d => d.y);
    labels.attr('x', d => d.x).attr('y', d => d.y);
  });
}

/**
 * 编织进度监视 —— WebSocket + 轮询降级（FC 兼容）
 * 用法: watchProgress(sessionId, (data) => { updateUI(data); });
 */
function watchProgress(sessionId, onUpdate) {
  if (!sessionId) return;

  if (USE_POLLING) {
    // FC / 远端模式：每 3 秒轮询
    console.log('[Weaver] Polling mode (FC/remote)');
    let pollCount = 0;
    const timer = setInterval(async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/sessions/${sessionId}/progress`);
        const data = await resp.json();
        onUpdate(data);
        pollCount++;
        if (data.status === 'complete' || data.status === 'failed') {
          clearInterval(timer);
          if (data.status === 'complete' && data.design_id) {
            window.location.href = `/results?design_id=${data.design_id}`;
          }
        }
        // 超时保护：最多轮询 100 次（5 分钟）
        if (pollCount > 100) { clearInterval(timer); }
      } catch (err) {
        console.error('[Weaver] Poll error:', err);
      }
    }, 3000);
    return timer;
  } else {
    // 本地 / Docker 模式：WebSocket
    console.log('[Weaver] WebSocket mode (local)');
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${API_HOST}:8765/ws/progress/${sessionId}`;
    try {
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        onUpdate(data);
        if (data.phase === 'complete' && data.design_id) {
          ws.close();
          window.location.href = `/results?design_id=${data.design_id}`;
        }
        if (data.phase === 'error') { ws.close(); }
      };
      ws.onerror = () => {
        console.warn('[Weaver] WebSocket failed, falling back to polling');
        // 降级到轮询
        USE_POLLING = true;
        watchProgress(sessionId, onUpdate);
      };
      return ws;
    } catch (err) {
      console.warn('[Weaver] WebSocket unavailable, using polling');
      USE_POLLING = true;
      return watchProgress(sessionId, onUpdate);
    }
  }
}

// 初始加载设计（如有）或监听编织进度
document.addEventListener('DOMContentLoaded', () => {
  if (DESIGN_ID) {
    load();
  } else if (SESSION_ID) {
    watchProgress(SESSION_ID, (data) => {
      document.getElementById('design-title').textContent =
        `编织中: ${data.status} (${Math.round(data.progress * 100)}%)`;
      if (data.status === 'complete' && data.design_id) {
        window.location.href = `?design_id=${data.design_id}`;
      }
    });
  }
});
