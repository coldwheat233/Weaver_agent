"""双模式浮窗 —— Ctrl+Alt+[ 输入 | Ctrl+Alt+] 后台

DPI 感知 · 高清渲染 · 平滑 hover · 滚动条 · 用户视角设计"""
import ctypes as _c
_c.windll.shcore.SetProcessDpiAwareness(2)

import tkinter as tk
import tkinter.font as tkf
import threading, webbrowser, httpx, json
from tkinter import ttk
from src.utils.logging_config import logger

FONT = "Segoe UI"
INPUT_W, INPUT_H = 560, 500
DASH_W, DASH_H = 620, 580
API = "http://localhost:8765"

# ═══ 颜色令牌 ═══
C = {
    "bg": "#FBFBFB", "surface": "#F3F3F5", "surface_hover": "#EBEBED",
    "text": "#1A1A2E", "text2": "#6E6E7C", "text3": "#A0A0AC",
    "accent": "#0891B2", "accent_light": "#06B6D4",
    "accent_subtle": "#ECFEFF", "accent_glass": "rgba(8,145,178,0.08)",
    "danger": "#EF4444", "success": "#10B981",
    "white": "#FFFFFF",
}
HOVER_MS = 120  # 平滑 hover 过渡时间


class CaptureOverlay:
    def __init__(self):
        self._port = 8765
        self._session_id = None
        self._input_root = None
        self._dash_root = None

    def set_port(self, p): self._port = p

    def show_input(self):
        if self._input_root and self._input_root.winfo_exists():
            self._input_root.deiconify(); self._input_root.lift(); self._input_root.focus_force()
            self._input_text.focus_set(); return
        threading.Thread(target=self._build_input, daemon=True).start()

    def show_dashboard(self):
        if self._dash_root and self._dash_root.winfo_exists():
            self._dash_root.deiconify(); self._dash_root.lift(); self._dash_root.focus_force()
            self._refresh_dash(); return
        threading.Thread(target=self._build_dashboard, daemon=True).start()

    # ═══════════════════ INPUT WINDOW ═══════════════════
    def _build_input(self):
        r = tk.Tk(); r.title("Idea Weaver · Input")
        r.configure(bg=C["bg"]); r.attributes("-topmost", True); r.overrideredirect(True)
        r.update_idletasks()
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        r.geometry(f"{INPUT_W}x{INPUT_H}+{(sw-INPUT_W)//2}+{(sh-INPUT_H)//2}")
        self._make_draggable(r)
        tf = lambda s, w="normal": tkf.Font(family=FONT, size=s, weight=w)

        # ── 标题栏 ──
        bar = tk.Frame(r, bg=C["bg"], height=44)
        bar.pack(fill="x", padx=24, pady=(20, 0)); bar.pack_propagate(False)

        tk.Label(bar, text="✦ 捕捉想法", font=tf(15, "bold"), fg=C["accent"], bg=C["bg"]).pack(side="left")

        # 仪表盘按钮
        dash_btn = tk.Label(bar, text="☰", font=tf(16), fg=C["text3"], bg=C["bg"], cursor="hand2")
        dash_btn.pack(side="right", padx=(0, 8))
        dash_btn.bind("<Button-1>", lambda e: (r.withdraw(), self.show_dashboard()))
        self._bind_hover(dash_btn, C["text3"], C["accent"])

        cls = tk.Label(bar, text="✕", font=tf(14), fg=C["text3"], bg=C["bg"], cursor="hand2")
        cls.pack(side="right"); cls.bind("<Button-1>", lambda e: r.withdraw())
        self._bind_hover(cls, C["text3"], C["danger"])

        # ── 提示 ──
        hint = tk.Frame(r, bg=C["bg"]); hint.pack(fill="x", padx=24, pady=(2, 8))
        tk.Label(hint, text="Ctrl+↵ 提交  ·  Esc 隐藏", font=tf(10), fg=C["text2"], bg=C["bg"]).pack(side="left")
        self._char_count_lbl = tk.Label(hint, text="", font=tf(10), fg=C["text3"], bg=C["bg"])
        self._char_count_lbl.pack(side="right")

        # ── 输入区（带滚动条）──
        inf = tk.Frame(r, bg=C["surface"])
        inf.pack(padx=24, fill="both", expand=True)

        # 自定义滚动条样式
        style = ttk.Style()
        style.configure("TScrollbar", background=C["surface_hover"], troughcolor=C["surface"],
                        borderwidth=0, arrowsize=0)
        style.map("TScrollbar", background=[("active", C["text3"])])

        scrollbar = ttk.Scrollbar(inf, orient="vertical", style="TScrollbar")

        self._input_text = tk.Text(
            inf, font=tf(13), bg=C["surface"], fg=C["text"],
            relief="flat", padx=16, pady=16, wrap="word", bd=0,
            insertbackground=C["accent"],
            selectbackground=C["accent_subtle"], selectforeground=C["text"],
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self._input_text.yview)
        self._input_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._input_text.focus_set()

        # 字符计数
        self._input_text.bind("<KeyRelease>", lambda e: self._update_char_count())

        # ── 追问区 ──
        self._qframe = tk.Frame(r, bg=C["bg"])

        # ── 提交按钮 ──
        bf = tk.Frame(r, bg=C["bg"]); bf.pack(fill="x", padx=24, pady=(12, 20))
        self._btn_lbl = tk.Label(bf, text="捕捉想法  →", font=tf(13, "bold"),
                                  bg=C["accent"], fg=C["white"], padx=32, pady=10, cursor="hand2")
        self._btn_lbl.pack(fill="x")
        self._btn_lbl.bind("<Button-1>", lambda e: self._submit(r))
        self._bind_hover(self._btn_lbl, C["accent"], C["accent_light"])

        r.bind("<Escape>", lambda e: r.withdraw())
        r.bind("<Control-Return>", lambda e: self._submit(r))
        r.protocol("WM_DELETE_WINDOW", lambda: r.withdraw())

        self._input_root = r
        r.mainloop()

    def _update_char_count(self):
        n = len(self._input_text.get("1.0", "end-1c"))
        self._char_count_lbl.configure(text=f"{n} 字符")

    def _submit(self, root):
        content = self._input_text.get("1.0", "end-1c").strip()
        if not content: return
        self._input_text.delete("1.0", "end")
        self._btn_lbl.configure(text="捕捉中...", bg=C["accent_light"])
        root.update()
        def _do():
            try:
                if not self._session_id:
                    r = httpx.post(f"http://localhost:{self._port}/api/sessions",
                                   json={"north_star": content[:80]}, timeout=10)
                    if r.status_code == 200: self._session_id = r.json()["session_id"]
                httpx.post(f"http://localhost:{self._port}/api/ideas",
                           data={"content": content, "session_id": self._session_id or ""}, timeout=60)
                root.after(0, lambda: self._on_submitted(root))
            except Exception as e:
                root.after(0, lambda: self._on_err(str(e)[:60]))
        threading.Thread(target=_do, daemon=True).start()

    def _on_submitted(self, root):
        self._btn_lbl.configure(text="✓ 已捕捉", bg=C["success"])
        root.after(600, lambda: self._btn_lbl.configure(text="捕捉想法  →", bg=C["accent"]))
        root.after(800, lambda: self._check_inquisitor())

    def _on_err(self, msg):
        self._btn_lbl.configure(text="重试", bg=C["danger"])
        root = self._input_root
        root.after(2000, lambda: self._btn_lbl.configure(text="捕捉想法  →", bg=C["accent"]))

    # ── V2 追问 ──
    def _check_inquisitor(self):
        if not self._session_id: return
        def _do():
            try:
                r = httpx.post(f"http://localhost:{self._port}/api/v2/ask",
                               params={"session_id": self._session_id}, timeout=60)
                if r.status_code == 200:
                    qs = r.json().get("questions", [])
                    if qs and self._input_root:
                        self._input_root.after(0, lambda: self._show_questions(qs))
            except Exception: pass
        threading.Thread(target=_do, daemon=True).start()

    def _show_questions(self, questions):
        for w in self._qframe.winfo_children(): w.destroy()
        self._qframe.pack(fill="x", padx=24, pady=(6, 0), before=self._input_text.master)
        q = questions[0]
        tk.Label(self._qframe, text=f"💡 {q['question']}", font=tkf.Font(family=FONT, size=11),
                 fg=C["accent"], bg=C["bg"], wraplength=INPUT_W-56, justify="left").pack(anchor="w")
        af = tk.Frame(self._qframe, bg=C["bg"]); af.pack(fill="x", pady=(4, 0))
        for ans in ["是", "否", "详细说说..."]:
            b = tk.Label(af, text=ans, font=tkf.Font(family=FONT, size=10),
                         bg=C["accent_subtle"], fg=C["accent"], padx=10, pady=3, cursor="hand2")
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, a=ans: self._answer_q(a))
            self._bind_hover(b, C["accent_subtle"], C["surface_hover"])

    def _answer_q(self, answer):
        for w in self._qframe.winfo_children(): w.destroy()
        self._qframe.pack_forget()
        if answer not in ("是", "否"):
            self._input_text.insert("1.0", answer)
            self._input_text.focus_set()

    # ═══════════════════ DASHBOARD WINDOW ═══════════════════
    def _build_dashboard(self):
        r = tk.Tk(); r.title("Idea Weaver · Dashboard")
        r.configure(bg=C["bg"]); r.attributes("-topmost", True); r.overrideredirect(True)
        r.update_idletasks()
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        r.geometry(f"{DASH_W}x{DASH_H}+{(sw-DASH_W)//2}+{(sh-DASH_H)//2}")
        self._make_draggable(r)
        tf = lambda s, w="normal": tkf.Font(family=FONT, size=s, weight=w)

        # ── 标题栏 ──
        bar = tk.Frame(r, bg=C["bg"], height=44)
        bar.pack(fill="x", padx=24, pady=(20, 0)); bar.pack_propagate(False)
        tk.Label(bar, text="☰ 用户后台", font=tf(15, "bold"), fg=C["accent"], bg=C["bg"]).pack(side="left")

        # 在浏览器打开
        web_btn = tk.Label(bar, text="🔗", font=tf(14), fg=C["text3"], bg=C["bg"], cursor="hand2")
        web_btn.pack(side="right", padx=(0, 8))
        web_btn.bind("<Button-1>", lambda e: webbrowser.open(f"http://localhost:{self._port}/dashboard"))
        self._bind_hover(web_btn, C["text3"], C["accent"])

        cls = tk.Label(bar, text="✕", font=tf(14), fg=C["text3"], bg=C["bg"], cursor="hand2")
        cls.pack(side="right"); cls.bind("<Button-1>", lambda e: r.withdraw())
        self._bind_hover(cls, C["text3"], C["danger"])

        # ── 内容区 ──
        canvas = tk.Canvas(r, bg=C["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(r, orient="vertical", command=canvas.yview)
        self._dash_content = tk.Frame(canvas, bg=C["bg"])
        self._dash_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._dash_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=0)
        scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        r.bind("<Escape>", lambda e: r.withdraw())
        r.protocol("WM_DELETE_WINDOW", lambda: r.withdraw())

        self._dash_root = r
        self._refresh_dash()
        r.mainloop()

    def _refresh_dash(self):
        if not self._dash_root or not self._dash_content: return
        for w in self._dash_content.winfo_children(): w.destroy()
        tf = lambda s, w="normal": tkf.Font(family=FONT, size=s, weight=w)
        P = self._dash_content

        # 加载数据
        threading.Thread(target=self._load_dash_data, args=(P, tf), daemon=True).start()

    def _load_dash_data(self, parent, tf):
        ideas, designs, proposals = [], [], []
        try:
            r = httpx.get(f"{API}/api/ideas", timeout=5)
            if r.status_code == 200: ideas = r.json() or []
        except Exception: pass
        try:
            r = httpx.get(f"{API}/api/designs", timeout=5)
            if r.status_code == 200: designs = r.json() or []
        except Exception: pass
        try:
            r = httpx.get(f"{API}/api/v3/proposals", timeout=5)
            if r.status_code == 200: proposals = r.json().get("proposals", []) or []
        except Exception: pass

        self._dash_root.after(0, lambda: self._render_dash(parent, tf, ideas, designs, proposals))

    def _render_dash(self, parent, tf, ideas, designs, proposals):
        for w in parent.winfo_children(): w.destroy()

        # ── 统计卡片 ──
        stats_frame = tk.Frame(parent, bg=C["bg"])
        stats_frame.pack(fill="x", padx=24, pady=(12, 0))
        for title, val in [("想法", len(ideas)), ("设计", len(designs)), ("提案", len(proposals))]:
            card = tk.Frame(stats_frame, bg=C["surface"])
            card.pack(side="left", padx=(0, 12), ipadx=20, ipady=14)
            tk.Label(card, text=str(val), font=tf(22, "bold"), fg=C["accent"], bg=C["surface"]).pack()
            tk.Label(card, text=title, font=tf(10), fg=C["text3"], bg=C["surface"]).pack()

        # ── 快捷操作 ──
        act = tk.Frame(parent, bg=C["bg"]); act.pack(fill="x", padx=24, pady=(16, 4))
        # 编织按钮
        weave_btn = tk.Label(act, text="编织所有想法  →", font=tf(12, "bold"),
                             bg=C["accent"], fg=C["white"], padx=20, pady=8, cursor="hand2")
        weave_btn.pack(side="left")
        weave_btn.bind("<Button-1>", lambda e: threading.Thread(target=self._do_weave, daemon=True).start())
        self._bind_hover(weave_btn, C["accent"], C["accent_light"])
        # 浏览器
        browser_btn = tk.Label(act, text="在浏览器查看", font=tf(11),
                               bg=C["surface"], fg=C["text2"], padx=16, pady=6, cursor="hand2")
        browser_btn.pack(side="left", padx=(8, 0))
        browser_btn.bind("<Button-1>", lambda e: webbrowser.open(f"http://localhost:{self._port}/dashboard"))
        self._bind_hover(browser_btn, C["surface"], C["surface_hover"])

        # ── 最近想法 ──
        self._section(parent, tf, "📝 最近想法", f"{len(ideas)} 条")
        if ideas:
            ideas_list = tk.Frame(parent, bg=C["bg"]); ideas_list.pack(fill="x", padx=24)
            for i in ideas[-10:][::-1]:
                content = (i.get("standardized_content") or i.get("raw_content") or "")[:100]
                item = tk.Frame(ideas_list, bg=C["surface"]); item.pack(fill="x", pady=2, ipady=6, ipadx=12)
                tk.Label(item, text=content, font=tf(11), fg=C["text"], bg=C["surface"],
                         anchor="w", justify="left", wraplength=DASH_W-80).pack(fill="x")
                tags = ", ".join(i.get("intent_tags", [])[:3])
                if tags:
                    tk.Label(item, text=tags, font=tf(9), fg=C["text3"], bg=C["surface"]).pack(anchor="w", padx=12)
                self._bind_hover(item, C["surface"], C["surface_hover"])
        else:
            tk.Label(parent, text="还没有想法。按 Ctrl+Alt+[ 开始捕捉", font=tf(11),
                     fg=C["text3"], bg=C["bg"]).pack(pady=12)

        # ── 最近设计 ──
        self._section(parent, tf, "🏗 编织成果", f"{len(designs)} 份")
        if designs:
            for d in designs[-8:][::-1]:
                card = tk.Frame(parent, bg=C["surface"])
                card.pack(fill="x", padx=24, pady=3, ipady=8, ipadx=14)
                tk.Label(card, text=(d.get("title") or "未命名")[:60], font=tf(12, "bold"),
                         fg=C["text"], bg=C["surface"], anchor="w", wraplength=DASH_W-80).pack(fill="x")
                scores = f"创新 {d.get('innovation_score',0):.2f}  ·  自洽 {d.get('coherence_score',0):.2f}  ·  可行 {d.get('feasibility_score',0):.2f}"
                tk.Label(card, text=scores, font=tf(10), fg=C["accent"], bg=C["surface"]).pack(anchor="w", padx=14)
                did = d.get("design_id", "")
                card.bind("<Button-1>", lambda e, did=did: webbrowser.open(f"{API}/api/designs/{did}/html"))
                card.configure(cursor="hand2")
                self._bind_hover(card, C["surface"], C["surface_hover"])
        else:
            tk.Label(parent, text="提交想法后点「编织所有想法」生成设计", font=tf(11),
                     fg=C["text3"], bg=C["bg"]).pack(pady=12)

        # ── V3 状态 ──
        self._section(parent, tf, "🔄 V3 自治演进", f"{len(proposals)} 个提案")
        if proposals:
            for p in proposals[:5]:
                item = tk.Frame(parent, bg=C["surface"])
                item.pack(fill="x", padx=24, pady=2, ipady=6, ipadx=12)
                tk.Label(item, text=p.get("cluster_name", ""), font=tf(11, "bold"),
                         fg=C["text"], bg=C["surface"]).pack(anchor="w")
                tk.Label(item, text=f"{p.get('node_count',0)} 想法 · {p.get('cross_domains',0)} 领域 · {p.get('status','')}",
                         font=tf(10), fg=C["text3"], bg=C["surface"]).pack(anchor="w", padx=12)
        else:
            tk.Label(parent, text="概念簇达到临界质量时将自动推送设计提案", font=tf(11),
                     fg=C["text3"], bg=C["bg"]).pack(pady=12)

    def _do_weave(self):
        if not self._session_id:
            try:
                r = httpx.post(f"{API}/api/sessions", json={"north_star": "编织"}, timeout=5)
                if r.status_code == 200: self._session_id = r.json()["session_id"]
            except Exception: pass
        if self._session_id:
            try:
                httpx.post(f"{API}/api/sessions/{self._session_id}/weave", timeout=300)
                self._dash_root.after(0, self._refresh_dash)
            except Exception: pass

    def _section(self, parent, tf, title, subtitle):
        f = tk.Frame(parent, bg=C["bg"]); f.pack(fill="x", padx=24, pady=(20, 6))
        tk.Label(f, text=title, font=tf(13, "bold"), fg=C["text"], bg=C["bg"]).pack(side="left")
        tk.Label(f, text=subtitle, font=tf(10), fg=C["text3"], bg=C["bg"]).pack(side="right")

    # ═══ 工具 ═══
    def _bind_hover(self, widget, default_bg, hover_bg):
        """平滑 hover 颜色过渡"""
        widget.bind("<Enter>", lambda e: widget.configure(bg=hover_bg))
        widget.bind("<Leave>", lambda e: widget.configure(bg=default_bg))

    @staticmethod
    def _make_draggable(w):
        d = {"x": 0, "y": 0}
        w.bind("<Button-1>", lambda e: d.update(x=e.x, y=e.y))
        w.bind("<B1-Motion>", lambda e: w.geometry(
            f"+{w.winfo_x()+e.x-d['x']}+{w.winfo_y()+e.y-d['y']}"))

    def hide(self): pass
