import { useEffect, useState } from "react";

const API = "http://localhost:8765";

interface ProviderInfo {
  id: string;
  base_url: string;
  default_model: string;
}

interface Config {
  provider: string;
  base_url: string;
  model: string;
  light_model: string;
  temperature: number;
  api_key_masked: string;
  has_api_key: boolean;
  providers: ProviderInfo[];
}

interface Props {
  onBack: () => void;
  onClose: () => void;
}

export default function Settings({ onBack, onClose }: Props) {
  const [cfg, setCfg] = useState<Config | null>(null);
  const [provider, setProvider] = useState("deepseek");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [lightModel, setLightModel] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const r = await fetch(`${API}/api/config`);
      const d: Config = await r.json();
      setCfg(d);
      setProvider(d.provider);
      setBaseUrl(d.base_url);
      setModel(d.model);
      setLightModel(d.light_model);
      setTemperature(d.temperature);
    } catch (e) {
      setTestResult({ ok: false, msg: "无法连接后端" });
    }
  };

  const onProviderChange = (pid: string) => {
    setProvider(pid);
    const p = cfg?.providers.find((x) => x.id === pid);
    if (p) {
      setBaseUrl(p.base_url);
      if (!model || model === cfg?.model) setModel(p.default_model);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const body: any = { provider, base_url: baseUrl, model };
      if (apiKey) body.api_key = apiKey;
      const r = await fetch(`${API}/api/config/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (d.ok) {
        setTestResult({ ok: true, msg: `✓ 连接成功 · ${d.latency_ms}ms · ${d.model}` });
      } else {
        setTestResult({ ok: false, msg: `✗ ${d.error}` });
      }
    } catch (e) {
      setTestResult({ ok: false, msg: `✗ 请求失败: ${e}` });
    }
    setTesting(false);
  };

  const save = async () => {
    const body: any = {
      provider,
      base_url: baseUrl,
      model,
      light_model: lightModel,
      temperature,
    };
    if (apiKey) body.api_key = apiKey;
    try {
      const r = await fetch(`${API}/api/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (d.ok) {
        setSaved(true);
        setApiKey(""); // 清空输入框, 不再显示明文
        setTimeout(() => setSaved(false), 2000);
        load();
      }
    } catch (e) {
      setTestResult({ ok: false, msg: `保存失败: ${e}` });
    }
  };

  return (
    <>
      <div className="titlebar" onMouseDown={async () => {
        try {
          const { getCurrentWindow } = await import("@tauri-apps/api/window");
          await getCurrentWindow().startDragging();
        } catch {}
      }} style={{ cursor: "move" }}>
        <div className="titlebar-left">
          <span className="titlebar-title">⚙ 模型配置</span>
        </div>
        <div className="titlebar-actions" onMouseDown={(e) => e.stopPropagation()}>
          <button className="titlebar-btn" onClick={onBack} title="返回后台">←</button>
          <button className="titlebar-btn danger" onClick={onClose} title="关闭">✕</button>
        </div>
      </div>

      <div className="dash-scroll" style={{ padding: "12px 24px 24px" }}>
        {/* Provider */}
        <label style={labelStyle}>供应商</label>
        <select value={provider} onChange={(e) => onProviderChange(e.target.value)} style={inputStyle}>
          <option value="deepseek">DeepSeek</option>
          <option value="openai">OpenAI</option>
          <option value="ollama">Ollama (本地)</option>
          <option value="custom">自定义 (OpenAI 兼容)</option>
        </select>

        {/* API Key */}
        <label style={labelStyle}>
          API Key {cfg?.has_api_key && <span style={{ color: "#A0A0AC" }}>(当前: {cfg.api_key_masked})</span>}
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={cfg?.has_api_key ? "留空则保持不变" : "sk-..."}
          style={inputStyle}
        />

        {/* Base URL */}
        <label style={labelStyle}>Base URL</label>
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://api.deepseek.com"
          style={inputStyle}
        />

        {/* Model */}
        <label style={labelStyle}>主模型 (编织/设计)</label>
        <input
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="deepseek-chat"
          style={inputStyle}
        />

        {/* Light Model */}
        <label style={labelStyle}>轻量模型 (标准化/追问)</label>
        <input
          value={lightModel}
          onChange={(e) => setLightModel(e.target.value)}
          placeholder="deepseek-chat"
          style={inputStyle}
        />

        {/* Temperature */}
        <label style={labelStyle}>温度: {temperature.toFixed(2)}</label>
        <input
          type="range"
          min={0} max={1} step={0.05}
          value={temperature}
          onChange={(e) => setTemperature(parseFloat(e.target.value))}
          style={{ width: "100%", accentColor: "#0891B2" }}
        />

        {/* Test result */}
        {testResult && (
          <div style={{
            margin: "12px 0", padding: "10px 14px", borderRadius: 12, fontSize: 12,
            background: testResult.ok ? "#ECFDF5" : "#FEF2F2",
            border: `1px solid ${testResult.ok ? "#A7F3D0" : "#FECACA"}`,
            color: testResult.ok ? "#059669" : "#EF4444",
          }}>
            {testResult.msg}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
          <button className="action-btn secondary" onClick={testConnection} disabled={testing}>
            {testing ? "测试中..." : "测试连接"}
          </button>
          <button className="action-btn primary" onClick={save} style={{ flex: 1 }}>
            {saved ? "✓ 已保存并生效" : "保存配置"}
          </button>
        </div>

        <p style={{ marginTop: 16, fontSize: 11, color: "#A0A0AC", lineHeight: 1.6 }}>
          配置保存在 ~/.weaver/config.json，保存后立即生效，无需重启。
          API Key 仅存储在本地，不会上传到任何第三方。
        </p>
      </div>
    </>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block", fontSize: 12, fontWeight: 500,
  color: "#6E6E7C", marginTop: 14, marginBottom: 4,
};

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 14px",
  border: "1px solid #E5E5E8", borderRadius: 10,
  background: "#FFF", color: "#1A1A2E", fontSize: 13,
  fontFamily: "inherit", outline: "none",
};
