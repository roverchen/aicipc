from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class AgentStatus(str, Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    WAITING_DECISION = "WAITING_DECISION"

class TaskAction(str, Enum):
    OS_INSTALL = "OS_INSTALL"
    FW_UPDATE = "FW_UPDATE"
    FUNCTION_TEST = "FUNCTION_TEST"
    BURN_IN = "BURN_IN"

class DUTStatus(str, Enum):
    IDLE = "IDLE"
    TESTING = "TESTING"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"

class DUTInfo(BaseModel):
    dut_id: str
    status: DUTStatus = DUTStatus.IDLE
    current_task_id: Optional[str] = None
    health_metrics: Dict[str, float] = {}

class RegisterRequest(BaseModel):
    rack_id: str
    ip_address: str
    dut_count: int
    capabilities: List[str] = ["OS_INSTALL", "FW_UPDATE", "FUNCTION_TEST", "BURN_IN"]

class HeartbeatRequest(BaseModel):
    rack_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dut_summary: Dict[str, DUTStatus]
    load_percentage: float

class TelemetryData(BaseModel):
    rack_id: str
    dut_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metrics: Dict[str, float] # e.g., {"cpu_temp": 45.5, "fan_speed": 3000}

class TaskRequest(BaseModel):
    task_id: str
    rack_id: str
    dut_id: str
    action: TaskAction
    params: Dict[str, str] = {} # e.g., {"image_url": "...", "checksum": "..."}

class TaskUpdate(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float = 0.0
    message: str = ""
    logs: Optional[str] = None

class CommonResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None

class DecisionType(str, Enum):
    RETRY = "RETRY"
    SKIP = "SKIP"
    ABORT = "ABORT"

class DecisionRequest(BaseModel):
    task_id: str
    decision: DecisionType
