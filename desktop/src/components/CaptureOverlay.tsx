import { useState, useRef, useEffect } from "react";
import { api, InquisitorQuestion } from "../lib/api";

const API = "http://localhost:8765";

interface Props {
  sessionId: string;
  setSessionId: (id: string) => void;
  onOpenDashboard: () => void;
  onClose: () => void;
}

interface Attachment {
  name: string;
  blob: Blob;
  dataUrl?: string;
  type: "image" | "audio";
}

async function startDrag() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().startDragging();
  } catch {}
}

export default function CaptureOverlay({ sessionId, setSessionId, onOpenDashboard, onClose }: Props) {
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [questions, setQuestions] = useState<InquisitorQuestion[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [recording, setRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [toast, setToast] = useState<{ type: "ok" | "err"; msg: string } | null>(null);
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const [aiQuestion, setAiQuestion] = useState<{ question: string; context: string; completeness: number } | null>(null);
  const [conversationHistory, setConversationHistory] = useState<string[]>([]);
  const [conversing, setConversing] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const converseTimerRef = useRef<number | null>(null);

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
  const recognitionRef = useRef<any>(null);
  const recordingTimerRef = useRef<number | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // ── 剪贴板图片粘贴 ──
  useEffect(() => {
    const handler = async (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          e.preventDefault();
          const blob = item.getAsFile();
          if (blob) {
            const dataUrl = await blobToDataUrl(blob);
            setAttachments((prev) => [
              ...prev,
              { name: `clipboard-${Date.now()}.png`, blob, dataUrl, type: "image" },
            ]);
          }
        }
      }
    };
    document.addEventListener("paste", handler);
    return () => document.removeEventListener("paste", handler);
  }, []);

  // ── 拖拽上传 ──
  const onDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    for (const file of e.dataTransfer.files) {
      if (file.type.startsWith("image/")) {
        const dataUrl = await blobToDataUrl(file);
        setAttachments((prev) => [
          ...prev,
          { name: file.name, blob: file, dataUrl, type: "image" },
        ]);
      } else if (file.type.startsWith("audio/")) {
        setAttachments((prev) => [
          ...prev,
          { name: file.name, blob: file, type: "audio" },
        ]);
      }
    }
  };

  // ── 录音（Web Speech API 实时转写）──
  const toggleRecording = async () => {
    if (recording) {
      if (recognitionRef.current) {
        if (typeof recognitionRef.current.stop === "function") {
          recognitionRef.current.stop();
        }
        recognitionRef.current = null;
      }
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      setRecording(false);
    } else {
      try {
        const SpeechRecognition =
          (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
          // 优先: Web Speech API 实时转写
          const recognition = new SpeechRecognition();
          recognition.lang = "zh-CN";
          recognition.continuous = true;
          recognition.interimResults = true;

          let lastFinalIdx = -1;
          recognition.onresult = (event: any) => {
            let interim = "";
            let finalPart = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
              const r = event.results[i];
              if (r.isFinal && i > lastFinalIdx) {
                finalPart += (finalPart ? " " : "") + r[0].transcript;
                lastFinalIdx = i;
              } else if (!r.isFinal) {
                interim += r[0].transcript;
              }
            }
            setContent((prev) => {
              const base = prev.replace(/\s*\(…\)\s*$/g, "").trim();
              const newText = base ? base + " " + finalPart : finalPart;
              return interim ? newText + (newText ? " " : "") + "(…)" : newText;
            });
          };

          recognition.onerror = (event: any) => {
            if (event.error === "no-speech" || event.error === "aborted") return;
            setRecording(false);
            if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
          };

          recognition.onend = () => {
            setContent((prev) => prev.replace(/\s*\(…\)\s*/g, "").trim());
            setRecording(false);
            if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
          };

          recognition.start();
          recognitionRef.current = recognition;
        } else {
          // 降级: MediaRecorder 录制成文件
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
          const chunks: BlobPart[] = [];
          mr.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
          mr.onstop = () => {
            const blob = new Blob(chunks, { type: "audio/webm" });
            setAttachments((prev) => [...prev, { name: `recording-${Date.now()}.webm`, blob, type: "audio" }]);
            stream.getTracks().forEach((t) => t.stop());
          };
          mr.start();
          recognitionRef.current = mr;
        }
        setRecording(true);
        setRecordingTime(0);
        recordingTimerRef.current = window.setInterval(() => {
          setRecordingTime((t) => t + 1);
        }, 1000);
      } catch (err) {
        console.error("Mic access denied:", err);
      }
    }
  };

  const removeAttachment = (idx: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== idx));
  };

  // ── 提交 ──
  const submit = async () => {
    const text = content.trim();
    if (!text && attachments.length === 0) return;
    if (submitting) return;
    setSubmitting(true);

    try {
      let sid = sessionId;
      if (!sid && text) {
        const s = await api.createSession(text.slice(0, 80));
        sid = s.session_id;
        setSessionId(sid);
      }

      // 提交文字
      if (text) {
        await api.submitIdea(text, sid);
      }

      // 上传图片附件
      for (const att of attachments) {
        if (att.type !== "image") continue;
        const fd = new FormData();
        fd.append("file", att.blob, att.name);
        fd.append("source_type", "image");
        if (sid) fd.append("session_id", sid);
        fd.append("content", "(图片输入)");
        try {
          await fetch(`${API}/api/ideas`, { method: "POST", body: fd });
        } catch (e) {
          console.error("Upload failed:", e);
        }
      }

      // 记录对话历史
      if (aiQuestion?.question) {
        setConversationHistory((prev) => [
          ...prev,
          `Q: ${aiQuestion.question}`,
          `A: ${text}`,
        ].slice(-12));
        setAiQuestion(null);
      }
      setContent("");
      setAttachments([]);
      setSuccess(true);
      setToast({ type: "ok", msg: "✓ 想法已捕捉" });
      setTimeout(() => { setSuccess(false); setToast(null); }, 2000);

      // 通知 Dashboard 刷新
      try {
        const { emit } = await import("@tauri-apps/api/event");
        await emit("idea-submitted", { sessionId: sid });
      } catch {}

      if (sid) {
        try {
          const q = await api.checkInquisitor(sid);
          if (q.questions?.length) setQuestions(q.questions.slice(0, 1));
        } catch {}
      }

      inputRef.current?.focus();
    } catch (e: any) {
      setToast({ type: "err", msg: `✗ ${e?.message || "提交失败"}` });
      setTimeout(() => setToast(null), 3000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleInputChange = (val: string) => {
    setContent(val);
    // 输入停顿 1.5s 后自动触发 AI 追问
    if (converseTimerRef.current) clearTimeout(converseTimerRef.current);
    if (val.trim().length > 15) {
      converseTimerRef.current = window.setTimeout(() => {
        fetch("http://localhost:8765/api/v2/converse", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idea: val, history: conversationHistory }),
        })
          .then((r) => r.json())
          .then((d) => {
            if (d.question) setAiQuestion(d);
          })
          .catch(() => {});
      }, 1500);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  };

  const answerQuestion = (answer: string) => {
    setQuestions([]);
    if (answer !== "是" && answer !== "否") {
      setContent(answer);
      inputRef.current?.focus();
    }
  };

  const formatTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  return (
    <>
      {/* Title bar */}
      <div className="titlebar" onMouseDown={startDrag} style={{ cursor: "move" }}>
        <div className="titlebar-left">
          <span className="titlebar-title">✦ 捕捉想法</span>
        </div>
        <div className="titlebar-actions" onMouseDown={(e) => e.stopPropagation()}>
          <button className="titlebar-btn" onClick={toggleRecording} title={recording ? "停止录音" : "录音"}>
            {recording ? "⏹" : "🎤"}
          </button>
          <button className="titlebar-btn" onClick={onOpenDashboard} title="用户后台">
            ☰
          </button>
          <button className="titlebar-btn danger" onClick={onClose} title="关闭 (Esc)">
            ✕
          </button>
        </div>
      </div>

      {/* Toast notification */}
      {toast && (
        <div style={{
          margin: "0 24px 0", padding: "8px 14px", borderRadius: 10, fontSize: 12,
          background: toast.type === "ok" ? "#ECFDF5" : "#FEF2F2",
          border: `1px solid ${toast.type === "ok" ? "#A7F3D0" : "#FECACA"}`,
          color: toast.type === "ok" ? "#059669" : "#EF4444",
          transition: "opacity 0.3s ease",
        }}>
          {toast.msg}
        </div>
      )}

      {/* Drop zone */}
      <div
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        style={{ flex: 1, display: "flex", flexDirection: "column" }}
      >
        {/* Recording indicator */}
        {recording && (
          <div style={{
            margin: "0 24px 8px", padding: "6px 14px",
            background: "#FEF2F2", borderRadius: 999, fontSize: 12, color: "#EF4444",
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: 999, background: "#EF4444",
              animation: "pulse 1.2s infinite",
            }} />
            ● REC {formatTime(recordingTime)}
          </div>
        )}

        {/* Attachment thumbnails */}
        {attachments.length > 0 && (
          <div style={{ display: "flex", gap: 8, padding: "0 24px 8px", flexWrap: "wrap" }}>
            {attachments.map((att, i) => (
              <div key={i} style={{
                position: "relative", width: 64, height: 64,
                borderRadius: 12, overflow: "hidden", background: "#F3F3F5",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                {att.dataUrl ? (
                  <img src={att.dataUrl} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  <span style={{ fontSize: 24 }}>🎵</span>
                )}
                <button
                  onClick={() => removeAttachment(i)}
                  style={{
                    position: "absolute", top: 2, right: 2, width: 18, height: 18,
                    border: "none", borderRadius: 999, background: "rgba(0,0,0,0.4)",
                    color: "#FFF", fontSize: 11, cursor: "pointer", lineHeight: 1,
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Input */}
        <textarea
          ref={inputRef}
          className="input-area"
          placeholder={prompts[placeholderIdx]}
          value={content}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
        />

        {/* Inquiry panel (V2) */}
        {questions.length > 0 && (
          <div className="inquiry-panel">
            <div className="inquiry-text">💡 {questions[0].question}</div>
            <div className="inquiry-actions">
              {["是", "否", "详细说说..."].map((a) => (
                <button key={a} className="inquiry-btn" onClick={() => answerQuestion(a)}>
                  {a}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* AI 追问气泡 */}
      {aiQuestion && aiQuestion.question && (
        <div style={{
          margin: "0 24px 4px", padding: "8px 14px", borderRadius: 12,
          background: "#F0F9FF", border: "1px solid #BAE6FD",
          fontSize: 12, color: "#0369A1", lineHeight: 1.5,
        }}>
          <div style={{ fontWeight: 600, marginBottom: 2 }}>💬 {aiQuestion.question}</div>
          {aiQuestion.context && (
            <div style={{ fontSize: 11, color: "#6E6E7C" }}>{aiQuestion.context}</div>
          )}
          {aiQuestion.completeness > 0.7 && (
            <div style={{ fontSize: 11, color: "#10B981", marginTop: 4 }}>✓ 想法已足够具体，可以提交了</div>
          )}
        </div>
      )}

      {/* Hint */}
      <p className="hint">
        Ctrl+↵ 提交 · {content.length} 字符 · 🎤 录音 · Ctrl+V 粘贴图片
      </p>

      {/* Submit button */}
      <button
        className={`submit-btn ${success ? "success" : ""}`}
        onClick={submit}
        disabled={(!content.trim() && attachments.length === 0) || submitting}
      >
        <span>{success ? "✓ 已捕捉" : submitting ? "捕捉中..." : "捕捉想法"}</span>
        {!success && !submitting && <span className="arrow">→</span>}
      </button>
    </>
  );
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.readAsDataURL(blob);
  });
}
