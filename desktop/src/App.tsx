import { useState, useEffect } from "react";
import CaptureOverlay from "./components/CaptureOverlay";
import Dashboard from "./components/Dashboard";
import Settings from "./components/Settings";

type View = "input" | "dashboard" | "settings";

const hideWindow = async () => {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().hide();
  } catch {
    // 非 Tauri 环境（浏览器调试）静默忽略
  }
};

export default function App() {
  const [view, setView] = useState<View>("dashboard");
  const [windowLabel, setWindowLabel] = useState<string>("");
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    import("@tauri-apps/api/window")
      .then(({ getCurrentWindow }) => {
        const w = getCurrentWindow();
        setWindowLabel(w.label);
        if (w.label === "input") setView("input");
        else setView("dashboard");
      })
      .catch(() => {
        const v = new URLSearchParams(window.location.search).get("view");
        if (v === "input") setView("input");
      });
  }, []);

  // Esc 隐藏当前窗口
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        hideWindow();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const onClose = () => {
    hideWindow();
  };

  const onSwitchToDashboard = () => setView("dashboard");
  const onSwitchToCapture = () => setView("input");

  return (
    <div className="app-window">
      {view === "settings" ? (
        <Settings onBack={onSwitchToDashboard} onClose={onClose} />
      ) : view === "input" || windowLabel === "input" ? (
        <CaptureOverlay
          sessionId={sessionId}
          setSessionId={setSessionId}
          onOpenDashboard={onSwitchToDashboard}
          onClose={onClose}
        />
      ) : (
        <Dashboard
          onOpenCapture={onSwitchToCapture}
          onClose={onClose}
          onOpenSettings={() => setView("settings")}
        />
      )}
    </div>
  );
}
