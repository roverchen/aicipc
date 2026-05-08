import { useState, useEffect, useRef } from 'react';
import { Activity, Server, Cpu, Play } from 'lucide-react';
import axios from 'axios';

const API_BASE = window.location.origin + "/api/v1";
const WS_URL = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + "/ws/events";
const API_KEY = import.meta.env.VITE_API_KEY || "aicipc-secret-2026";

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

function App() {
  const [agents, setAgents] = useState<Record<string, Agent>>({});
  const [tasks, setTasks] = useState<Record<string, TaskStatus>>({});
  const [notification, setNotification] = useState<string | null>(null);
  const [selectedRack, setSelectedRack] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("default");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [editingModelConfig, setEditingModelConfig] = useState<string>("");
  const [isTaskPanelOpen, setIsTaskPanelOpen] = useState(false);
  const [view, setView] = useState<'dashboard' | 'models'>('dashboard');
  const [searchQuery, setSearchQuery] = useState("");
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

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
        if (models.length > 0 && !models.includes("default")) {
          setSelectedModel(models[0]);
        }
      } catch (err) {
        console.error("Failed to fetch models", err);
      }
    };

    fetchData();
    fetchModels();

    ws.current = new WebSocket(WS_URL);
    ws.current.onmessage = (event) => {
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
      } else {
        fetchData();
      }
    };

    return () => ws.current?.close();
  }, []);

  useEffect(() => {
    if (view === 'models' && selectedModel) {
      const fetchModelConfig = async () => {
        try {
          const resp = await axios.get(`${API_BASE}/models/${selectedModel}`);
          setEditingModelConfig(JSON.stringify(resp.data, null, 2));
        } catch (err) {
          console.error("Failed to fetch model config", err);
        }
      };
      fetchModelConfig();
    }
  }, [view, selectedModel]);

  const handleSaveModel = async () => {
    if (!selectedModel) return;
    try {
      const config = JSON.parse(editingModelConfig);
      await axios.post(`${API_BASE}/models/${selectedModel}`, config, {
        headers: { "X-API-KEY": API_KEY }
      });
      setNotification(`Model ${selectedModel} saved successfully`);
    } catch (err) {
      alert("Invalid JSON or save failed");
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
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ display: 'flex', gap: '2rem' }}>
            <div style={{ width: '300px', background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '1rem' }}>
              <h3 style={{ marginBottom: '1.5rem' }}>Model Library</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {availableModels.map(model => (
                  <button 
                    key={model}
                    onClick={() => setSelectedModel(model)}
                    style={{ 
                      textAlign: 'left',
                      padding: '0.75rem', 
                      borderRadius: '0.5rem', 
                      background: selectedModel === model ? 'var(--accent)' : 'rgba(255,255,255,0.05)',
                      border: 'none',
                      color: 'white',
                      cursor: 'pointer'
                    }}
                  >
                    {model}
                  </button>
                ))}
              </div>
            </div>
            
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h2 style={{ fontSize: '1.5rem' }}>Test Plan: {selectedModel}</h2>
                <button className="btn btn-primary" onClick={handleSaveModel} style={{ padding: '0.5rem 2rem' }}>Save Changes</button>
              </div>
              <textarea 
                value={editingModelConfig}
                onChange={(e) => setEditingModelConfig(e.target.value)}
                style={{ 
                  width: '100%', 
                  height: '600px', 
                  background: '#0f172a', 
                  color: '#e2e8f0', 
                  fontFamily: 'monospace', 
                  fontSize: '0.9rem', 
                  padding: '1.5rem', 
                  borderRadius: '1rem', 
                  border: '1px solid var(--border)',
                  outline: 'none'
                }}
              />
            </div>
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
