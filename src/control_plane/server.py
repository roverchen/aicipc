import uvicorn
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator
from contextlib import asynccontextmanager
from src.common.schema import (
    AgentStatus, TelemetryData, TaskRequest, TaskUpdate, TaskStatus,
    DecisionRequest, DecisionType, CommonResponse, RegisterRequest, HeartbeatRequest
)
from src.common.database import init_db, SessionLocal, AgentModel, TaskModel, TelemetryModel
import uuid

# Security Configuration
API_KEY = os.getenv("API_KEY", "aicipc-secret-2026")

# WebSocket connections
active_connections: List[WebSocket] = []

# DB Dependency
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def monitor_agents():
    """Background task to detect offline agents"""
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            agents = db.query(AgentModel).all()
            for agent in agents:
                # Calculate time since last heartbeat
                diff = now - agent.last_seen
                if diff > timedelta(seconds=60):
                    if agent.status != AgentStatus.OFFLINE:
                        agent.status = AgentStatus.OFFLINE
                        print(f"[!] Agent {agent.rack_id} is OFFLINE (timeout)")
                elif diff > timedelta(seconds=30):
                    if agent.status == AgentStatus.ONLINE:
                        agent.status = AgentStatus.DEGRADED
            db.commit()
        except Exception as e:
            print(f"[ERROR] monitor_agents: {e}")
        finally:
            db.close()
        await asyncio.sleep(5)

async def notify_operator(title: str, message: str, level: str = "INFO"):
    """Mock notification system (can be expanded to Email/Slack/SMS)"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[NOTIFICATION] [{level}] {title}: {message} ({timestamp})\n")
    # Broadcast notification to dashboard
    await broadcast_json({
        "type": "notification",
        "data": {"title": title, "message": message, "level": level, "timestamp": timestamp}
    })

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(monitor_agents())
    yield

app = FastAPI(title="AICIPC Control Plane", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/register", response_model=CommonResponse)
async def register_agent(req: RegisterRequest, x_api_key: str = Header(...), db: SessionLocal = Depends(get_db)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    agent = db.query(AgentModel).filter(AgentModel.rack_id == req.rack_id).first()
    if not agent:
        agent = AgentModel(rack_id=req.rack_id)
        db.add(agent)
    
    agent.last_seen = datetime.utcnow()
    agent.ip_address = req.ip_address
    agent.dut_count = req.dut_count
    agent.status = AgentStatus.ONLINE
    agent.metadata_json = req.model_dump()
    db.commit()
    
    print(f"[*] Agent registered: {req.rack_id}")
    return CommonResponse(success=True, message=f"Rack {req.rack_id} registered successfully")

@app.post("/api/v1/verify_mac")
async def verify_mac(mac: str, x_api_key: str = Header(...), db: SessionLocal = Depends(get_db)):
    """Check MAC uniqueness for production requirements"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    # Logic: Fail if MAC exists in DB
    exists = db.query(TelemetryModel).filter(TelemetryModel.dut_id == mac).first()
    if exists:
        return {"status": "FAIL", "message": f"Duplicate MAC detected: {mac}"}
    return {"status": "PASS", "message": "MAC is unique"}

@app.post("/api/v1/heartbeat", response_model=CommonResponse)
async def receive_heartbeat(req: HeartbeatRequest, x_api_key: str = Header(...), db: SessionLocal = Depends(get_db)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
        
    agent = db.query(AgentModel).filter(AgentModel.rack_id == req.rack_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not registered")
    
    agent.last_seen = datetime.utcnow()
    agent.status = AgentStatus.ONLINE
    # Update latest metrics in metadata_json if needed
    current_meta = agent.metadata_json or {}
    current_meta["load"] = req.load_percentage
    current_meta["dut_summary"] = req.dut_summary
    agent.metadata_json = current_meta
    
    # Check for pending tasks
    pending_tasks = db.query(TaskModel).filter(
        TaskModel.rack_id == req.rack_id,
        TaskModel.status == TaskStatus.PENDING
    ).all()
    
    task_list = [
        TaskRequest(
            task_id=t.task_id, 
            rack_id=t.rack_id, 
            dut_id=t.dut_id, 
            action=t.action, 
            params=t.params
        ).model_dump() for t in pending_tasks
    ]
    
    db.commit()
    return CommonResponse(success=True, message="Heartbeat OK", data={"pending_tasks": task_list})

@app.post("/api/v1/tasks", response_model=CommonResponse)
async def create_task(req: TaskRequest, x_api_key: str = Header(...), db: SessionLocal = Depends(get_db)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    existing = db.query(TaskModel).filter(TaskModel.task_id == req.task_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Task ID exists")
    
    new_task = TaskModel(
        task_id=req.task_id,
        rack_id=req.rack_id,
        dut_id=req.dut_id,
        action=req.action,
        params=req.params,
        status=TaskStatus.PENDING,
        message="Task created and pending assignment"
    )
    db.add(new_task)
    db.commit()
    return CommonResponse(success=True, message="Task created", data={"task_id": req.task_id})

@app.post("/api/v1/tasks/update", response_model=CommonResponse)
async def update_task_status(update: TaskUpdate, x_api_key: str = Header(...), db: SessionLocal = Depends(get_db)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    task = db.query(TaskModel).filter(TaskModel.task_id == update.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = update.status
    task.progress = update.progress
    task.message = update.message
    db.commit()
    
    # Broadcast to dashboard
    await broadcast_json({"type": "task_update", "data": update.model_dump()})

    # Send notifications on completion or failure
    if update.status == TaskStatus.SUCCESS:
        if task.action == "FUNCTION_TEST":
            await notify_operator(
                "Function Test Summary",
                f"[Tester Notify] Task {update.task_id} on {task.rack_id}/{task.dut_id}: {update.message}"
            )
        await notify_operator("Task Completed", f"Task {update.task_id} on {task.rack_id}/{task.dut_id} finished successfully.")
    elif update.status == TaskStatus.FAILED:
        await notify_operator("Task Failed", f"Task {update.task_id} failed: {update.message}", level="ERROR")

    return CommonResponse(success=True, message="Status updated")

@app.post("/api/v1/tasks/{task_id}/decision", response_model=CommonResponse)
async def handle_task_decision(task_id: str, req: DecisionRequest, x_api_key: str = Header(...), db: SessionLocal = Depends(get_db)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Store decision in task params or a dedicated field for the agent to pick up
    current_params = task.params or {}
    current_params["operator_decision"] = req.decision
    task.params = current_params
    task.status = TaskStatus.RUNNING # Set back to running so agent sees the decision
    task.message = f"Operator decided to {req.decision}. Resuming..."
    
    db.commit()
    return CommonResponse(success=True, message=f"Decision {req.decision} recorded")

@app.post("/api/v1/tasks/{task_id}/decision/consume", response_model=CommonResponse)
async def consume_task_decision(task_id: str, x_api_key: str = Header(...), db: SessionLocal = Depends(get_db)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    params = task.params or {}
    if "operator_decision" in params:
        params.pop("operator_decision", None)
        task.params = params
        db.commit()
    return CommonResponse(success=True, message="Decision consumed")

@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str, db: SessionLocal = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/v1/agents")
async def list_agents(db: SessionLocal = Depends(get_db)):
    agents = db.query(AgentModel).all()
    return agents

# --- Model Management API ---

CONFIG_DIR = "configs/test_suites"

@app.get("/api/v1/models")
async def list_models():
    if not os.path.exists(CONFIG_DIR):
        return []
    files = [f.replace(".json", "") for f in os.listdir(CONFIG_DIR) if f.endswith(".json")]
    return files

@app.get("/api/v1/models/{name}")
async def get_model(name: str):
    path = os.path.join(CONFIG_DIR, f"{name}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Model not found")
    with open(path, "r") as f:
        import json
        return json.load(f)

@app.post("/api/v1/models/{name}")
async def save_model(name: str, config: Dict, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    os.makedirs(CONFIG_DIR, exist_ok=True)
    path = os.path.join(CONFIG_DIR, f"{name}.json")
    with open(path, "w") as f:
        import json
        json.dump(config, f, indent=2)
    return {"success": True, "message": f"Model {name} saved"}

@app.delete("/api/v1/models/{name}")
async def delete_model(name: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    path = os.path.join(CONFIG_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
        return {"success": True, "message": f"Model {name} deleted"}
    raise HTTPException(status_code=404, detail="Model not found")

@app.websocket("/ws/events")
async def event_websocket(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    db = SessionLocal()
    try:
        agents = db.query(AgentModel).all()
        tasks = db.query(TaskModel).order_by(TaskModel.created_at.desc()).limit(50).all()
        
        agents_dict = {a.rack_id: {
            "rack_id": a.rack_id, 
            "status": a.status, 
            "last_seen": a.last_seen.isoformat(),
            "info": a.metadata_json
        } for a in agents}
        
        tasks_dict = {t.task_id: {
            "task_id": t.task_id,
            "status": t.status,
            "progress": t.progress,
            "message": t.message,
            "rack_id": t.rack_id
        } for t in tasks}

        await websocket.send_json({
            "type": "init", 
            "agents": agents_dict, 
            "tasks": tasks_dict
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    finally:
        db.close()

async def broadcast_json(data: Dict):
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except:
            pass

# Serve Frontend Static Files
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
