import { useState, useRef, useEffect } from "react";

const API = "http://localhost:8765";

interface Props {
  sessionId: string;
  setSessionId: (id: string) => void;
  onOpenDashboard: () => void;
  onClose: () => void;
}

async function startDrag() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().startDragging();
  } catch {}
}

import { api, InquisitorQuestion } from "../lib/api";

export default function CaptureOverlay({ sessionId, setSessionId, onOpenDashboard, onClose }: Props) {
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [questions, setQuestions] = useState<InquisitorQuestion[]>([]);
  const [recording, setRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [toast, setToast] = useState<{ type: "ok" | "err"; msg: string } | null>(null);
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const [aiQuestion, setAiQuestion] = useState<{ question: string; context: string; completeness: number } | null>(null);
  const [conversationHistory, setConversationHistory] = useState<string[]>([]);
  const [converseRound, setConverseRound] = useState(1);
  const MAX_ROUNDS = 3;
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const converseTimerRef = useRef<number | null>(null);
  const recordingTimerRef = useRef<number | null>(null);

  const prompts = [
    "你的微服务最大的性能瓶颈在哪里？",
    "最近让你头疼的技术问题是什么？",
    "如果要重构一个模块，你会从哪里开始？",
    "有没有一个灵感突然闪过，还没来得及写下来？",
    "你见过的最优雅的架构设计是什么样的？",
    "现在做的项目里，哪个决策让你最纠结？",
    "说说你最近学到的一个新概念…",
    "如果资源不限，你的系统会怎么设计？",
  ];

  useEffect(() => {
    const timer = setInterval(() => setPlaceholderIdx((i) => (i + 1) % prompts.length), 4000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleInputChange = (val: string) => {
    setContent(val);
    if (converseTimerRef.current) clearTimeout(converseTimerRef.current);
    if (val.trim().length > 15 && converseRound <= MAX_ROUNDS) {
      converseTimerRef.current = window.setTimeout(() => {
        fetch("http://localhost:8765/api/v2/converse", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idea: val, history: conversationHistory, round_num: converseRound }),
        }).then((r) => r.json()).then((d) => { if (d.question) setAiQuestion(d); }).catch(() => {});
      }, 1500);
    }
  };

  const toggleRecording = async () => {
    if (recording) {
      if (recognitionRef.current?.stop) recognitionRef.current.stop();
      recognitionRef.current = null;
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      setRecording(false);
    } else {
      try {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognition) { setToast({ type: "err", msg: "语音识别不可用" }); setTimeout(() => setToast(null), 2000); return; }
        const recognition = new SpeechRecognition();
        recognition.lang = "zh-CN"; recognition.continuous = true; recognition.interimResults = true;
        let lastFinalIdx = -1;
        recognition.onresult = (event: any) => {
          let interim = "", finalPart = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const r = event.results[i];
            if (r.isFinal && i > lastFinalIdx) { finalPart += (finalPart ? " " : "") + r[0].transcript; lastFinalIdx = i; }
            else if (!r.isFinal) { interim += r[0].transcript; }
          }
          setContent((prev) => {
            const base = prev.replace(/\s*\(…\)\s*$/g, "").trim();
            const newText = base ? base + " " + finalPart : finalPart;
            return interim ? newText + (newText ? " " : "") + "(…)" : newText;
          });
        };
        recognition.onerror = () => { setRecording(false); };
        recognition.onend = () => { setContent((p) => p.replace(/\s*\(…\)\s*/g, "").trim()); setRecording(false); };
        recognition.start(); recognitionRef.current = recognition;
        setRecording(true); setRecordingTime(0);
        recordingTimerRef.current = window.setInterval(() => setRecordingTime((t) => t + 1), 1000);
      } catch { setToast({ type: "err", msg: "麦克风权限未授权" }); setTimeout(() => setToast(null), 2000); }
    }
  };

  const submit = async () => {
    const text = content.trim(); if (!text || submitting) return;
    setSubmitting(true);
    try {
      let sid = sessionId;
      if (!sid) { const s = await api.createSession(text.slice(0, 80)); sid = s.session_id; setSessionId(sid); }
      await api.submitIdea(text, sid);
      if (aiQuestion?.question) {
        setConversationHistory((prev) => [...prev, `Q: ${aiQuestion.question}`, `A: ${text}`].slice(-12));
        setConverseRound((r) => r + 1); setAiQuestion(null);
      }
      setContent(""); setSuccess(true);
      setToast({ type: "ok", msg: "✓ 想法已捕捉" });
      setTimeout(() => { setSuccess(false); setToast(null); }, 2000);
      try { const { emit } = await import("@tauri-apps/api/event"); await emit("idea-submitted", { sessionId: sid }); } catch {}
      if (sid) { try { const q = await api.checkInquisitor(sid); if (q.questions?.length) setQuestions(q.questions.slice(0, 1)); } catch {} }
      inputRef.current?.focus();
    } catch (e: any) { setToast({ type: "err", msg: `✗ ${e?.message || "提交失败"}` }); setTimeout(() => setToast(null), 3000); }
    finally { setSubmitting(false); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.ctrlKey && e.key === "Enter") { e.preventDefault(); submit(); } };
  const answerQuestion = (answer: string) => { setQuestions([]); if (answer !== "是" && answer !== "否") { setContent(answer); inputRef.current?.focus(); } };
  const formatTime = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  return (
    <>
      <div className="titlebar" onMouseDown={startDrag} style={{ cursor: "move" }}>
        <div className="titlebar-left"><span className="titlebar-title">✦ 捕捉想法</span></div>
        <div className="titlebar-actions" onMouseDown={(e) => e.stopPropagation()}>
          <button className="titlebar-btn" onClick={toggleRecording} title={recording ? "停止录音" : "录音"}>{recording ? "⏹" : "🎤"}</button>
          <button className="titlebar-btn" onClick={onOpenDashboard} title="用户后台">☰</button>
          <button className="titlebar-btn danger" onClick={onClose} title="关闭 (Esc)">✕</button>
        </div>
      </div>

      {toast && (
        <div style={{ margin: "0 24px 0", padding: "8px 14px", borderRadius: 10, fontSize: 12,
          background: toast.type === "ok" ? "#ECFDF5" : "#FEF2F2",
          border: `1px solid ${toast.type === "ok" ? "#A7F3D0" : "#FECACA"}`,
          color: toast.type === "ok" ? "#059669" : "#EF4444" }}>{toast.msg}</div>
      )}

      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {recording && (
          <div style={{ margin: "0 24px 8px", padding: "6px 14px", background: "#FEF2F2", borderRadius: 999, fontSize: 12, color: "#EF4444", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: 999, background: "#EF4444", animation: "pulse 1.2s infinite" }} />● REC {formatTime(recordingTime)}
          </div>
        )}
        <textarea ref={inputRef} className="input-area" placeholder={prompts[placeholderIdx]} value={content}
          onChange={(e) => handleInputChange(e.target.value)} onKeyDown={handleKeyDown} autoFocus />
        {questions.length > 0 && (
          <div className="inquiry-panel">
            <div className="inquiry-text">💡 {questions[0].question}</div>
            <div className="inquiry-actions">{[ "是", "否", "详细说说..."].map((a) => (<button key={a} className="inquiry-btn" onClick={() => answerQuestion(a)}>{a}</button>))}</div>
          </div>
        )}
      </div>

      {converseRound > MAX_ROUNDS && (
        <div style={{ margin: "0 24px 4px", padding: "8px 14px", borderRadius: 12, background: "#FFFBEB", border: "1px solid #FDE68A", fontSize: 12, color: "#D97706" }}>💡 已追问 {converseRound-1} 轮，可直接编织</div>
      )}
      {aiQuestion?.question && converseRound <= MAX_ROUNDS && (
        <div style={{ margin: "0 24px 4px", padding: "8px 14px", borderRadius: 12, background: "#F0F9FF", border: "1px solid #BAE6FD", fontSize: 12, color: "#0369A1" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontWeight: 600 }}>💬 {aiQuestion.question}</span>
            <span style={{ fontSize: 10, color: "#A0A0AC" }}>第{converseRound}轮 · {Math.round(aiQuestion.completeness * 100)}%</span>
          </div>
          {aiQuestion.context && <div style={{ fontSize: 11, color: "#6E6E7C" }}>{aiQuestion.context}</div>}
          {aiQuestion.completeness > 0.6 && <div style={{ fontSize: 11, color: "#10B981", marginTop: 4 }}>✓ 已足够具体，可提交后直接编织</div>}
        </div>
      )}

      <p className="hint">Ctrl+↵ 提交 · {content.length} 字符 · 🎤 录音</p>
      <button className={`submit-btn ${success ? "success" : ""}`} onClick={submit} disabled={!content.trim() || submitting}>
        <span>{success ? "✓ 已捕捉" : submitting ? "捕捉中..." : "捕捉想法"}</span>
        {!success && !submitting && <span className="arrow">→</span>}
      </button>
    </>
  );
}
