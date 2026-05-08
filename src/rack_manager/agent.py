import httpx
import asyncio
import socket
import uuid
import random
import os
from typing import Optional
from src.common.schema import (
    RegisterRequest, HeartbeatRequest, TaskRequest, TaskUpdate, 
    TaskStatus, DUTStatus, DecisionType
)
from src.rack_manager.task_handler import TaskHandler
from src.rack_manager.logger import logger

# Configuration via environment variables
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "aicipc-secret-2026")

class RackManagerAgent:
    def __init__(self, rack_id: str):
        self.rack_id = rack_id
        self.ip_address = self._get_ip()
        self.task_handler = TaskHandler(rack_id, CONTROL_PLANE_URL)
        self.headers = {"X-API-KEY": API_KEY}
        self.dut_count = int(os.getenv("DUT_COUNT", "10"))
        self.heartbeat_interval_seconds = float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "2"))
        self.dut_status = {f"DUT-{i+1:02d}": DUTStatus.IDLE for i in range(self.dut_count)}

    def _get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    async def register(self):
        req = RegisterRequest(
            rack_id=self.rack_id,
            ip_address=self.ip_address,
            dut_count=self.dut_count
        )
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{CONTROL_PLANE_URL}/api/v1/register", content=req.model_dump_json(), headers=self.headers)
                print(f"[*] Registered successfully: {resp.json()}")
            except Exception as e:
                print(f"[!] Registration failed: {e}")

    async def send_heartbeat(self):
        # Calculate load (count of non-IDLE DUTs)
        busy_duts = sum(1 for s in self.dut_status.values() if s != DUTStatus.IDLE)
        load = (busy_duts / self.dut_count) * 100

        req = HeartbeatRequest(
            rack_id=self.rack_id,
            dut_summary=self.dut_status,
            load_percentage=load
        )
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{CONTROL_PLANE_URL}/api/v1/heartbeat", content=req.model_dump_json(), headers=self.headers)
                data = resp.json()
                if data["success"] and "pending_tasks" in data["data"]:
                    for task_data in data["data"]["pending_tasks"]:
                        task = TaskRequest(**task_data)
                        asyncio.create_task(self.execute_task(task))
            except Exception as e:
                print(f"[!] Heartbeat failed: {e}")

    async def check_decision(self, task_id: str) -> Optional[DecisionType]:
        """Poll the server for an operator decision on a paused task"""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{CONTROL_PLANE_URL}/api/v1/tasks/{task_id}")
                data = resp.json()
                params = data.get("params", {})
                decision = params.get("operator_decision")
                if decision:
                    await client.post(
                        f"{CONTROL_PLANE_URL}/api/v1/tasks/{task_id}/decision/consume",
                        headers=self.headers
                    )
                    return DecisionType(decision)
            except Exception as e:
                print(f"[!] Check decision failed for {task_id}: {e}")
        return None

    async def execute_task(self, task: TaskRequest):
        # Update DUT status to TESTING
        self.dut_status[task.dut_id] = DUTStatus.TESTING
        
        async def update_status(update: TaskUpdate):
            logger.log(update.task_id, update.message)
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(f"{CONTROL_PLANE_URL}/api/v1/tasks/update", content=update.model_dump_json(), headers=self.headers)
                except Exception as e:
                    print(f"[!] Task update failed: {e}")

        async def wait_for_decision(task_id: str) -> DecisionType:
            print(f"[*] Task {task_id} paused. Waiting for operator decision...")
            while True:
                decision = await self.check_decision(task_id)
                if decision:
                    return decision
                await asyncio.sleep(3)

        print(f"[+] Executing task: {task.task_id} ({task.action})")
        try:
            await self.task_handler.execute(task, update_status, wait_for_decision)
        finally:
            # Revert DUT status to IDLE (or ERROR if failed, but for prototype IDLE is fine)
            self.dut_status[task.dut_id] = DUTStatus.IDLE

    async def run(self):
        await self.register()
        while True:
            await self.send_heartbeat()
            await asyncio.sleep(self.heartbeat_interval_seconds)

if __name__ == "__main__":
    import random
    import sys
    
    # Priority: Env Var > Command Line Arg > Random Fallback
    rack_id = os.getenv("RACK_ID")
    if not rack_id and len(sys.argv) > 1:
        rack_id = sys.argv[1]
    if not rack_id:
        rack_id = f"RACK-{random.randint(1, 99):03d}"
        
    print(f"[*] Starting Rack Manager Agent for {rack_id}")
    agent = RackManagerAgent(rack_id)
    asyncio.run(agent.run())
