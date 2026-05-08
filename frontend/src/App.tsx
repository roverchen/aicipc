import { useState, useEffect, useRef, useCallback } from 'react';
import { Activity, Server, Cpu, Play } from 'lucide-react';
import axios from 'axios';

// Environment detection
const isDev = window.location.port >= '5173' && window.location.port <= '5176';
const API_BASE = isDev ? "http://localhost:8000/api/v1" : window.location.origin + "/api/v1";
const WS_URL = isDev ? "ws://localhost:8000/ws/events" : (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + "/ws/events";
const API_KEY = "aicipc-secret-2026";

interface Agent {
  rack_id: string;
  status: string;
  last_seen: string;
  info: any;
}

interface TaskStatus {
  task_id: string;
  status: string;
  progress: number;
  message: string;
  rack_id: string;
}

// Isolated Model Editor Component
const ModelEditor = ({ selectedModel, onSave, onDelete, onCreate }: { 
  selectedModel: string, 
  onSave: (name: string, configText: string) => Promise<void>,
  onDelete: () => Promise<void>,
  onCreate: (name: string, template: any) => Promise<void>
}) => {
  const [configText, setConfigText] = useState("");
  const [loading, setLoading] = useState(false);
  const [editorMode, setEditorMode] = useState<'visual' | 'source'>('visual');

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/models/${selectedModel}`);
      setConfigText(JSON.stringify(resp.data, null, 2));
    } catch (err) {
      console.error("Failed to fetch config", err);
    } finally {
      setLoading(false);
    }
  }, [selectedModel]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  // Helper to safely parse and update config
  const getParsedConfig = () => {
    try {
      return JSON.parse(configText);
    } catch {
      return { function_test: [], burn_in: {} };
    }
  };

  const updateConfig = (newConfig: any) => {
    setConfigText(JSON.stringify(newConfig, null, 2));
  };

  const handleSaveAs = async () => {
    const name = prompt("Enter new model name:", `${selectedModel}_copy`);
    if (name) {
      try {
        const config = JSON.parse(configText);
        await onCreate(name, config);
      } catch (err) {
        alert("Invalid JSON format. Please fix before cloning.");
      }
    }
  };

  const parsed = getParsedConfig();
  const functionTests = parsed.function_test || [];
  const burnIn = parsed.burn_in || {};

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: '1rem 1.5rem', borderRadius: '1rem', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Model</span>
            <h2 style={{ fontSize: '1.1rem' }}>{selectedModel}.json</h2>
          </div>
          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.3)', padding: '0.25rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
            <button 
              onClick={() => setEditorMode('visual')}
              style={{ padding: '0.4rem 1rem', borderRadius: '0.4rem', border: 'none', background: editorMode === 'visual' ? 'var(--accent)' : 'transparent', color: 'white', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 }}
            >Visual</button>
            <button 
              onClick={() => setEditorMode('source')}
              style={{ padding: '0.4rem 1rem', borderRadius: '0.4rem', border: 'none', background: editorMode === 'source' ? 'var(--accent)' : 'transparent', color: 'white', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 }}
            >Source</button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button onClick={fetchConfig} style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', color: 'white', padding: '0.5rem 1rem', borderRadius: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>Reload</button>
          <button onClick={handleSaveAs} style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', color: 'white', padding: '0.5rem 1rem', borderRadius: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>Clone</button>
          <button onClick={onDelete} style={{ background: 'transparent', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '0.5rem 1.5rem', borderRadius: '0.5rem', cursor: 'pointer', fontWeight: 600 }}>Delete</button>
          <button className="btn btn-primary" onClick={() => onSave(selectedModel, configText)} disabled={loading} style={{ padding: '0.5rem 2.5rem' }}>
            {loading ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.5rem' }}>
        {editorMode === 'source' ? (
          <textarea 
            value={configText}
            onChange={(e) => setConfigText(e.target.value)}
            disabled={loading}
            placeholder={loading ? "Fetching configuration..." : "Enter JSON configuration here..."}
            style={{ 
              width: '100%', height: '100%', minHeight: '600px',
              background: 'rgba(15, 23, 42, 0.8)', color: '#e2e8f0', 
              fontFamily: '"Fira Code", monospace', fontSize: '0.95rem', lineHeight: '1.6',
              padding: '2rem', borderRadius: '1rem', border: '1px solid var(--border)',
              outline: 'none', boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.5)', resize: 'none'
            }}
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Function Test Section */}
            <section style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '1rem', border: '1px solid var(--border)', padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                <h3 style={{ fontSize: '1rem', color: 'var(--accent)' }}>Function Test Steps</h3>
                <button 
                  onClick={() => {
                    const newSteps = [...functionTests, { name: "New Step", progress: 0, command: "echo 'hello'" }];
                    updateConfig({ ...parsed, function_test: newSteps });
                  }}
                  style={{ background: 'var(--success)', border: 'none', color: 'white', padding: '0.3rem 0.8rem', borderRadius: '0.4rem', cursor: 'pointer', fontSize: '0.8rem' }}
                >+ Add Step</button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {functionTests.map((step: any, idx: number) => (
                  <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '0.75rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 800, width: '20px' }}>{idx + 1}</div>
                      <input 
                        value={step.name}
                        onChange={(e) => {
                          const newSteps = [...functionTests];
                          newSteps[idx].name = e.target.value;
                          updateConfig({ ...parsed, function_test: newSteps });
                        }}
                        placeholder="Test Item Name"
                        style={{ flex: 1, background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '0.5rem', padding: '0.5rem 1rem', color: 'white' }}
                      />
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Progress:</span>
                        <input 
                          type="number"
                          value={step.progress}
                          onChange={(e) => {
                            const newSteps = [...functionTests];
                            newSteps[idx].progress = parseInt(e.target.value);
                            updateConfig({ ...parsed, function_test: newSteps });
                          }}
                          style={{ width: '80px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '0.5rem', padding: '0.5rem', color: 'white' }}
                        />
                        <span style={{ fontSize: '0.8rem' }}>%</span>
                      </div>
                      <button 
                        onClick={() => {
                          const newSteps = functionTests.filter((_: any, i: number) => i !== idx);
                          updateConfig({ ...parsed, function_test: newSteps });
                        }}
                        style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: '0.5rem' }}
                      >✕</button>
                    </div>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginLeft: '30px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--accent)', fontWeight: 600 }}>CMD:</span>
                      <input 
                        value={step.command || ""}
                        onChange={(e) => {
                          const newSteps = [...functionTests];
                          newSteps[idx].command = e.target.value;
                          updateConfig({ ...parsed, function_test: newSteps });
                        }}
                        placeholder="Shell command to execute (e.g. stress-ng --cpu 2)"
                        style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '0.4rem', padding: '0.4rem 0.8rem', color: 'var(--success)', fontFamily: 'monospace', fontSize: '0.85rem' }}
                      />
                    </div>
                  </div>
                ))}
                {functionTests.length === 0 && <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>No test steps defined. Add one to begin.</p>}
              </div>
            </section>

            {/* Burn-in Section */}
            <section style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '1rem', border: '1px solid var(--border)', padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1rem', color: 'var(--accent)', marginBottom: '1.5rem' }}>Burn-in Configuration</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', gridColumn: '1 / -1' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Burn-in Load Command (Background Process)</label>
                  <input 
                    value={burnIn.command || ""}
                    onChange={(e) => updateConfig({ ...parsed, burn_in: { ...burnIn, command: e.target.value } })}
                    placeholder="Command to run during burn-in (e.g. stress-ng --cpu 0 --io 4)"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '0.5rem', padding: '0.75rem 1rem', color: 'var(--success)', fontFamily: 'monospace', fontSize: '0.9rem' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Duration (Hours)</label>
                  <input 
                    type="number"
                    value={burnIn.total_hours || 0}
                    onChange={(e) => updateConfig({ ...parsed, burn_in: { ...burnIn, total_hours: parseFloat(e.target.value) } })}
                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '0.5rem', padding: '0.75rem 1rem', color: 'white' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Thermal Threshold (°C)</label>
                  <input 
                    type="number"
                    value={burnIn.thermal_threshold || 0}
                    onChange={(e) => updateConfig({ ...parsed, burn_in: { ...burnIn, thermal_threshold: parseFloat(e.target.value) } })}
                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '0.5rem', padding: '0.75rem 1rem', color: 'white' }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Report Interval (Seconds)</label>
                  <input 
                    type="number"
                    value={burnIn.report_interval_seconds || 0}
                    onChange={(e) => updateConfig({ ...parsed, burn_in: { ...burnIn, report_interval_seconds: parseInt(e.target.value) } })}
                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '0.5rem', padding: '0.75rem 1rem', color: 'white' }}
                  />
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

// i18n Translations
const TRANSLATIONS: Record<string, any> = {
  en: {
    dashboard: "Dashboard",
    testPlans: "Test Plans",
    racks: "Racks",
    health: "System Health",
    activeTasks: "Active Tasks",
    newPlan: "New Plan",
    saveChanges: "Save Changes",
    status: "Status",
    progress: "Progress",
    message: "Message",
    agent: "Agent",
    lastSeen: "Last Seen",
    totalDuts: "Total DUTs",
    capabilities: "Capabilities"
  },
  zh: {
    dashboard: "儀表板",
    testPlans: "測試計畫",
    racks: "機架管理",
    health: "系統健康度",
    activeTasks: "執行中任務",
    newPlan: "新增計畫",
    saveChanges: "儲存變更",
    status: "狀態",
    progress: "進度",
    message: "訊息",
    agent: "代理程序",
    lastSeen: "最後上線",
    totalDuts: "總待測物數",
    capabilities: "功能支援"
  },
  vi: {
    dashboard: "Bảng điều khiển",
    testPlans: "Kế hoạch kiểm tra",
    racks: "Quản lý kệ",
    health: "Sức khỏe hệ thống",
    activeTasks: "Nhiệm vụ đang hoạt động",
    newPlan: "Kế hoạch mới",
    saveChanges: "Lưu thay đổi",
    status: "Trạng thái",
    progress: "Tiến độ",
    message: "Tin nhắn",
    agent: "Đại lý",
    lastSeen: "Thấy lần cuối",
    totalDuts: "Tổng số DUT",
    capabilities: "Khả năng"
  }
};

function App() {
  const [lang, setLang] = useState<'en' | 'zh' | 'vi'>('zh');
  const t = TRANSLATIONS[lang];

  const [agents, setAgents] = useState<Record<string, Agent>>({});
  const [tasks, setTasks] = useState<Record<string, TaskStatus>>({});
  const [notification, setNotification] = useState<string | null>(null);
  const [selectedRack, setSelectedRack] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("default");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [isTaskPanelOpen, setIsTaskPanelOpen] = useState(false);
  const [view, setView] = useState<'dashboard' | 'models'>('dashboard');
  const [searchQuery, setSearchQuery] = useState("");
  const ws = useRef<WebSocket | null>(null);

  // Auto-clear notifications
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  // Initial Data Fetch & WebSocket Setup
  useEffect(() => {
    const fetchData = async () => {
      try {
        const resp = await axios.get(`${API_BASE}/agents`);
        const agentMap: Record<string, Agent> = {};
        resp.data.forEach((a: any) => {
           agentMap[a.rack_id] = {
             rack_id: a.rack_id,
             status: a.status,
             last_seen: a.last_seen,
             info: a.metadata_json
           };
        });
        setAgents(agentMap);
      } catch (err) {
        console.error("Failed to fetch agents", err);
      }
    };

    const fetchModels = async () => {
      try {
        const resp = await axios.get(`${API_BASE}/models`);
        const models = resp.data;
        setAvailableModels(models);
      } catch (err) {
        console.error("Failed to fetch models", err);
      }
    };

    fetchData();
    fetchModels();

    ws.current = new WebSocket(WS_URL);
    ws.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'init') {
          setAgents(msg.agents);
          setTasks(msg.tasks);
        } else if (msg.type === 'task_update') {
          const update = msg.data;
          setTasks(prev => ({ ...prev, [update.task_id]: update }));
          if (update.status === 'SUCCESS') {
            setNotification(`Task ${update.task_id} completed successfully!`);
          } else if (update.status === 'FAILED') {
            setNotification(`Task ${update.task_id} failed!`);
          }
        } else if (msg.type === 'notification') {
          setNotification(`${msg.data.title}: ${msg.data.message}`);
        }
      } catch (e) {
        console.error("WebSocket message parse error", e);
      }
    };

    return () => ws.current?.close();
  }, []);

  const handleSaveModel = async (name: string, configText: string) => {
    try {
      const config = JSON.parse(configText);
      await axios.post(`${API_BASE}/models/${name}`, config, {
        headers: { "X-API-KEY": API_KEY }
      });
      setNotification(`Model ${name} saved successfully`);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message;
      alert(`Save failed: ${msg}`);
    }
  };

  const handleCreateModel = async (name: string, template: any) => {
    try {
      await axios.post(`${API_BASE}/models/${name}`, template, {
        headers: { "X-API-KEY": API_KEY }
      });
      setAvailableModels(prev => [...new Set([...prev, name])]);
      setSelectedModel(name);
      setNotification(`Model ${name} created`);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message;
      alert(`Create failed: ${msg}`);
    }
  };

  const handleScanBarcode = async (rack_id: string, dut_id: string) => {
    const mac = prompt(`[${dut_id}] Please scan or enter MAC Address:`);
    if (!mac) return;

    try {
      // 1. Verify MAC uniqueness (Production Req)
      const resp = await axios.post(`${API_BASE}/verify_mac?mac=${mac}`, {}, {
        headers: { "X-API-KEY": API_KEY }
      });

      if (resp.data.status === "FAIL") {
        alert(`CRITICAL ERROR: ${resp.data.message}`);
        return;
      }

      setNotification(`MAC ${mac} verified. Starting Auto-Test Sequence...`);

      // 2. Trigger Auto Sequence (OS -> FW -> Function -> Burn-in)
      const tasksToRun = [
        { id: `os_${Date.now()}`, action: "OS_INSTALL", msg: "Auto: OS Installation" },
        { id: `fw_${Date.now()}`, action: "FW_UPDATE", msg: "Auto: FW Update" },
        { id: `ft_${Date.now()}`, action: "FUNCTION_TEST", msg: "Auto: Function Test" },
        { id: `bi_${Date.now()}`, action: "BURN_IN", msg: "Auto: Burn-in" }
      ];

      for (const t of tasksToRun) {
        await axios.post(`${API_BASE}/tasks`, {
          task_id: t.id,
          rack_id,
          dut_id,
          action: t.action,
          params: { model: "default" }
        }, { headers: { "X-API-KEY": API_KEY } });
      }

    } catch (err: any) {
      alert(`Scan Flow Failed: ${err.message}`);
    }
  };

  const handleCreateNewBlank = async () => {
    const name = prompt("Enter new model name:");
    if (!name) return;
    const defaultConfig = {
      function_test: [{ name: "New Test", progress: 0 }],
      burn_in: { total_hours: 1, thermal_threshold: 95.0, report_interval_seconds: 60 }
    };
    await handleCreateModel(name, defaultConfig);
  };

  const handleDeleteModel = async () => {
    if (!selectedModel || selectedModel === 'default') {
      alert("Cannot delete default model");
      return;
    }
    if (!confirm(`Are you sure you want to delete ${selectedModel}?`)) return;
    try {
      await axios.delete(`${API_BASE}/models/${selectedModel}`, {
        headers: { "X-API-KEY": API_KEY }
      });
      const newModels = availableModels.filter(m => m !== selectedModel);
      setAvailableModels(newModels);
      setSelectedModel(newModels[0] || "default");
      setNotification(`Model deleted`);
    } catch (err) {
      alert("Delete failed");
    }
  };

  const handleLaunchTask = async (action: string) => {
    if (!selectedRack) return;
    const taskId = `gui-${Math.random().toString(36).substr(2, 9)}`;
    try {
      await axios.post(`${API_BASE}/tasks`, {
        task_id: taskId,
        rack_id: selectedRack,
        dut_id: "DUT-01",
        action: action,
        params: {
          model: selectedModel
        }
      }, {
        headers: { "X-API-KEY": API_KEY }
      });
      setNotification(`Task ${action} launched for ${selectedRack} (${selectedModel})`);
    } catch (err) {
      alert("Failed to launch task");
    }
  };

  return (
    <div className="dashboard-container">
      {notification && <div className="notification">{notification}</div>}
      <header>
        <div className="logo">AICIPC CONTROLLER</div>
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <nav style={{ display: 'flex', gap: '1rem' }}>
            <button 
              onClick={() => setView('dashboard')} 
              style={{ background: 'none', border: 'none', color: view === 'dashboard' ? 'var(--accent)' : 'white', cursor: 'pointer', fontWeight: 600, borderBottom: view === 'dashboard' ? '2px solid var(--accent)' : 'none' }}
            >
              Dashboard
            </button>
            <button 
              onClick={() => setView('models')} 
              style={{ background: 'none', border: 'none', color: view === 'models' ? 'var(--accent)' : 'white', cursor: 'pointer', fontWeight: 600, borderBottom: view === 'models' ? '2px solid var(--accent)' : 'none' }}
            >
              Test Plans
            </button>
          </nav>
          <div className="metric-row" style={{ color: 'var(--success)', marginTop: 0 }}>
            <Activity size={18} />
            <span style={{ marginLeft: '0.5rem', fontWeight: 600 }}>System Ready</span>
          </div>
          <div className="metric-row" style={{ marginTop: 0 }}>
            <Server size={18} />
            <span style={{ marginLeft: '0.5rem' }}>{Object.keys(agents).length} Racks Active</span>
          </div>
        </div>
      </header>

      {view === 'dashboard' ? (
        <>
          <div style={{ padding: '1rem 2rem', background: 'rgba(0,0,0,0.2)', marginBottom: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
             <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700 }}>Filter Racks</span>
             <input 
               type="text" 
               placeholder="Search Rack ID (e.g. RACK-001)" 
               value={searchQuery}
               onChange={(e) => setSearchQuery(e.target.value)}
               style={{ flex: 1, background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '0.5rem', padding: '0.5rem 1rem', color: 'white' }}
             />
          </div>
          <main className="rack-grid">
            {Object.entries(agents)
              .filter(([id]) => id.toLowerCase().includes(searchQuery.toLowerCase()))
              .map(([id, agent]) => (
          <div 
            key={id} 
            className={`rack-card ${selectedRack === id ? 'active' : ''}`}
            onClick={() => {
              setSelectedRack(id);
              setIsTaskPanelOpen(true);
            }}
          >
            <div className="rack-header">
              <div className="rack-id">{id}</div>
              <div className={`status-badge status-${agent.status.toLowerCase()}`}>
                {agent.status}
              </div>
            </div>
            
            <div className="metric-row">
              <span>Power Load</span>
              <span style={{ color: (agent.info?.load || 0) > 80 ? 'var(--danger)' : 'var(--success)', fontWeight: 600 }}>
                {Math.round(agent.info?.load || 0)}%
              </span>
            </div>

            <div className="metric-row">
              <span>DUT Topology</span>
              <span>{agent.info?.dut_count || 10} Nodes</span>
            </div>
            
            <div className="dut-grid">
              {[...Array(agent.info?.dut_count || 10)].map((_, i) => {
                const dutId = `DUT-${(i+1).toString().padStart(2, '0')}`;
                const status = agent.info?.dut_summary?.[dutId] || 'IDLE';
                return (
                  <div key={i} className={`dut-dot ${status.toLowerCase()}`} title={`${dutId}: ${status}`}>
                    <span style={{ fontSize: '0.65rem', marginLeft: '8px', color: 'var(--text-muted)', fontWeight: 600 }}>{dutId}</span>
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right' }}>
              Uptime: {new Date(agent.last_seen).toLocaleTimeString()}
            </div>
          </div>
        ))}

        {Object.keys(agents).length === 0 && (
          <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '6rem', background: 'rgba(0,0,0,0.1)', borderRadius: '1rem' }}>
            <Server size={64} style={{ marginBottom: '1.5rem', opacity: 0.2 }} />
            <p style={{ color: 'var(--text-muted)' }}>Searching for Rack Manager Agents...</p>
          </div>
        )}
      </main>
      </>
      ) : (
        <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
          <div style={{ display: 'flex', gap: '2rem', height: 'calc(100vh - 150px)' }}>
            <div style={{ width: '300px', background: 'rgba(15, 23, 42, 0.4)', padding: '1.5rem', borderRadius: '1rem', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 style={{ fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>Library</h3>
                <button 
                  onClick={handleCreateNewBlank}
                  style={{ background: 'var(--success)', border: 'none', color: 'white', padding: '0.2rem 0.6rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 700 }}
                >
                  + NEW
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflowY: 'auto', flex: 1 }}>
                {availableModels.map(model => (
                  <button 
                    key={model}
                    onClick={() => setSelectedModel(model)}
                    style={{ 
                      textAlign: 'left',
                      padding: '0.8rem 1rem', 
                      borderRadius: '0.75rem', 
                      background: selectedModel === model ? 'var(--accent)' : 'rgba(255,255,255,0.03)',
                      border: '1px solid',
                      borderColor: selectedModel === model ? 'var(--accent)' : 'transparent',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '0.9rem',
                      fontWeight: selectedModel === model ? 700 : 400,
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {model}.json
                  </button>
                ))}
              </div>
            </div>
            
            <ModelEditor 
              key={selectedModel}
              selectedModel={selectedModel} 
              onSave={handleSaveModel}
              onDelete={handleDeleteModel}
              onCreate={handleCreateModel}
            />
          </div>
        </div>
      )}

      <div className={`task-panel ${isTaskPanelOpen ? 'open' : ''}`}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
          <h2 style={{ fontSize: '1.5rem' }}>Rack Control</h2>
          <button onClick={() => setIsTaskPanelOpen(false)} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: 'white', cursor: 'pointer', padding: '0.5rem', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>
        </div>

        <div style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '0.5rem', marginBottom: '2rem', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
          <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 700 }}>Active Target</span>
          <div style={{ fontSize: '1.25rem', fontWeight: 800 }}>{selectedRack}</div>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <label style={{ display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem' }}>Device Model</label>
            <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ 
              width: '100%', 
              background: 'rgba(15, 23, 42, 0.8)', 
              border: '1px solid var(--border)', 
              color: 'white', 
              padding: '0.75rem', 
              borderRadius: '0.5rem',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            {availableModels.map(model => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <button className="btn btn-primary" onClick={() => handleLaunchTask('OS_INSTALL')}>
            <Cpu size={18} /> Deploy OS
          </button>
          <button className="btn btn-primary" onClick={() => handleLaunchTask('FW_UPDATE')}>
            <Play size={18} /> Update Firmware
          </button>
          <button className="btn btn-primary" onClick={() => handleLaunchTask('FUNCTION_TEST')}>
            <Play size={18} /> Run Function Test
          </button>
          <button className="btn btn-primary" onClick={() => handleLaunchTask('BURN_IN')}>
            <Activity size={18} /> Start Burn-in
          </button>
        </div>

        <div style={{ marginTop: '3.5rem' }}>
          <h3 style={{ fontSize: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>Task Monitor</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {Object.values(tasks).filter(t => t.rack_id === selectedRack).slice(-3).reverse().map(task => (
              <div key={task.task_id} style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '1.25rem', borderRadius: '0.75rem', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-muted)' }}>{task.task_id}</span>
                  <span style={{ 
                    fontSize: '0.75rem', 
                    fontWeight: 800,
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                    background: task.status === 'SUCCESS' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                    color: task.status === 'SUCCESS' ? 'var(--success)' : 'var(--accent)' 
                  }}>{task.status}</span>
                </div>
                <div className="task-progress-bar">
                  <div className="task-progress-inner" style={{ width: `${task.progress}%` }} />
                </div>
                <div style={{ marginTop: '0.75rem', color: 'var(--text-main)', fontSize: '0.8rem', opacity: 0.9 }}>
                  {task.message}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
