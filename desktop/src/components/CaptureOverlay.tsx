import { useState, useRef, useEffect } from "react";
import { api, InquisitorQuestion } from "../lib/api";

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
  } catch {
    /* 浏览器环境忽略 */
  }
}

export default function CaptureOverlay({ sessionId, setSessionId, onOpenDashboard, onClose }: Props) {
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [questions, setQuestions] = useState<InquisitorQuestion[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = async () => {
    const text = content.trim();
    if (!text || submitting) return;
    setSubmitting(true);

    try {
      // Ensure session
      let sid = sessionId;
      if (!sid) {
        const s = await api.createSession(text.slice(0, 80));
        sid = s.session_id;
        setSessionId(sid);
      }

      await api.submitIdea(text, sid);
      setContent("");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 600);

      // Check for V2 inquisitor questions
      try {
        const q = await api.checkInquisitor(sid);
        if (q.questions?.length) setQuestions(q.questions.slice(0, 1));
      } catch {}

      inputRef.current?.focus();
    } catch (e) {
      console.error("Submit failed:", e);
    } finally {
      setSubmitting(false);
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

  return (
    <>
      {/* Title bar */}
      <div className="titlebar" onMouseDown={startDrag} style={{ cursor: "move" }}>
        <div className="titlebar-left">
          <span className="titlebar-title">✦ 捕捉想法</span>
        </div>
        <div className="titlebar-actions" onMouseDown={(e) => e.stopPropagation()}>
          <button className="titlebar-btn" onClick={onOpenDashboard} title="用户后台">
            ☰
          </button>
          <button
            className="titlebar-btn danger"
            onClick={onClose}
            title="关闭 (Esc)"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Input */}
      <textarea
        ref={inputRef}
        className="input-area"
        placeholder="写下你的想法……"
        value={content}
        onChange={(e) => setContent(e.target.value)}
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

      {/* Hint */}
      <p className="hint">
        Ctrl+↵ 提交 · {content.length} 字符
      </p>

      {/* Submit button */}
      <button
        className={`submit-btn ${success ? "success" : ""}`}
        onClick={submit}
        disabled={!content.trim() || submitting}
      >
        <span>{success ? "✓ 已捕捉" : submitting ? "捕捉中..." : "捕捉想法"}</span>
        {!success && !submitting && <span className="arrow">→</span>}
      </button>
    </>
  );
}
