import { useState, useEffect, useRef } from 'react';
import { Activity, Server, Cpu, Play } from 'lucide-react';
import axios from 'axios';

const API_BASE = "http://localhost:8000/api/v1";
const WS_URL = "ws://localhost:8000/ws/events";
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

function App() {
  const [agents, setAgents] = useState<Record<string, Agent>>({});
  const [tasks, setTasks] = useState<Record<string, TaskStatus>>({});
  const [selectedRack, setSelectedRack] = useState<string | null>(null);
  const [isTaskPanelOpen, setIsTaskPanelOpen] = useState(false);
  const ws = useRef<WebSocket | null>(null);

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
    fetchData();

    ws.current = new WebSocket(WS_URL);
    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'init') {
        setAgents(msg.agents);
        setTasks(msg.tasks);
      } else if (msg.type === 'task_update') {
        const update = msg.data;
        setTasks(prev => ({ ...prev, [update.task_id]: update }));
      } else {
        fetchData();
      }
    };

    return () => ws.current?.close();
  }, []);

  const handleLaunchTask = async (action: string) => {
    if (!selectedRack) return;
    const taskId = `gui-${Math.random().toString(36).substr(2, 9)}`;
    try {
      await axios.post(`${API_BASE}/tasks`, {
        task_id: taskId,
        rack_id: selectedRack,
        dut_id: "DUT-01",
        action: action,
        params: {}
      }, {
        headers: { "X-API-KEY": API_KEY }
      });
      setIsTaskPanelOpen(false);
    } catch (err) {
      alert("Failed to launch task");
    }
  };

  return (
    <div className="dashboard-container">
      <header>
        <div className="logo">AICIPC CONTROLLER</div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div className="metric-row" style={{ color: 'var(--success)' }}>
            <Activity size={16} />
            <span style={{ marginLeft: '0.5rem' }}>System Healthy</span>
          </div>
          <div className="metric-row">
            <Server size={16} />
            <span style={{ marginLeft: '0.5rem' }}>{Object.keys(agents).length} Racks Active</span>
          </div>
        </div>
      </header>

      <main className="rack-grid">
        {Object.entries(agents).map(([id, agent]) => (
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
              <span>System Load</span>
              <span style={{ color: (agent.info?.load || 0) > 80 ? 'var(--accent)' : 'var(--success)' }}>
                {Math.round(agent.info?.load || 0)}%
              </span>
            </div>

            <div className="metric-row">
              <span>DUT Capacity</span>
              <span>{agent.info?.dut_count || 10} Units</span>
            </div>
            
            <div className="dut-grid">
              {[...Array(agent.info?.dut_count || 10)].map((_, i) => {
                const dutId = `DUT-${(i+1).toString().padStart(2, '0')}`;
                const status = agent.info?.dut_summary?.[dutId] || 'IDLE';
                return (
                  <div key={i} className={`dut-dot ${status.toLowerCase()}`} title={`${dutId}: ${status}`} />
                );
              })}
            </div>

            <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Last Seen: {new Date(agent.last_seen).toLocaleTimeString()}
            </div>
          </div>
        ))}

        {Object.keys(agents).length === 0 && (
          <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
            <Server size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No active Rack Managers detected.</p>
          </div>
        )}
      </main>

      <div className={`task-panel ${isTaskPanelOpen ? 'open' : ''}`}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
          <h2>Rack Control</h2>
          <button onClick={() => setIsTaskPanelOpen(false)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>✕</button>
        </div>

        <h3 style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>Target: {selectedRack}</h3>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <button className="btn btn-primary" onClick={() => handleLaunchTask('OS_INSTALL')}>
            <Cpu size={18} style={{ marginRight: '0.5rem' }} /> Deploy OS
          </button>
          <button className="btn btn-primary" onClick={() => handleLaunchTask('FW_UPDATE')}>
            <Play size={18} style={{ marginRight: '0.5rem' }} /> Update Firmware
          </button>
          <button className="btn btn-primary" onClick={() => handleLaunchTask('BURN_IN')}>
            <Activity size={18} style={{ marginRight: '0.5rem' }} /> Start Burn-in
          </button>
        </div>

        <div style={{ marginTop: '3rem' }}>
          <h3>Recent Tasks</h3>
          <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {Object.values(tasks).filter(t => t.rack_id === selectedRack).slice(-5).reverse().map(task => (
              <div key={task.task_id} style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '0.5rem', fontSize: '0.875rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 600 }}>{task.task_id}</span>
                  <span style={{ color: task.status === 'SUCCESS' ? 'var(--success)' : 'var(--accent)' }}>{task.status}</span>
                </div>
                <div style={{ height: '4px', background: '#334155', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: `${task.progress}%`, height: '100%', background: 'var(--accent)', transition: 'width 0.3s' }} />
                </div>
                <div style={{ marginTop: '0.5rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
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
