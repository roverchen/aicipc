import httpx
import asyncio
import uuid
import sys
import os
from src.common.schema import TaskRequest, TaskAction

CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "aicipc-secret-2026")

async def submit_and_monitor(rack_id: str, dut_id: str, action: TaskAction):
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    
    # Parse additional params from sys.argv
    params = {
        "image_url": "http://images.local/ubuntu-22.04.iso",
        "simulate_overheat": "true" if "--overheat" in sys.argv else "false"
    }
    
    for arg in sys.argv:
        if arg.startswith("--params"):
            # Handle --params model=name
            try:
                param_str = sys.argv[sys.argv.index(arg) + 1]
                if "=" in param_str:
                    key, val = param_str.split("=")
                    params[key] = val
            except:
                pass
        elif arg.startswith("model="):
            # Handle model=name directly
            key, val = arg.split("=")
            params[key] = val

    async with httpx.AsyncClient() as client:
        # Submit Task
        print(f"[*] Submitting {action} for {rack_id}/{dut_id}...")
        resp = await client.post(
            f"{CONTROL_PLANE_URL}/api/v1/tasks", 
            content=TaskRequest(
                task_id=task_id,
                rack_id=rack_id,
                dut_id=dut_id,
                action=action,
                params=params
            ).model_dump_json(), 
            headers={"Content-Type": "application/json", "X-API-KEY": API_KEY}
        )
        resp.raise_for_status()
        print(f"[*] Task submitted: {task_id}")
        
        # Monitor Progress
        while True:
            resp = await client.get(f"{CONTROL_PLANE_URL}/api/v1/tasks/{task_id}")
            status_data = resp.json()
            status = status_data["status"]
            progress = status_data["progress"]
            message = status_data["message"]
            
            print(f"[{task_id}] Status: {status} | Progress: {progress}% | Message: {message}")
            
            if status in ["SUCCESS", "FAILED", "CANCELLED"]:
                break
            
            await asyncio.sleep(2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 -m src.rack_manager.test_task <RACK_ID> <DUT_ID> <ACTION> [--params model=name] [--overheat]")
        sys.exit(1)
        
    rack = sys.argv[1]
    dut = sys.argv[2]
    act = TaskAction.OS_INSTALL
    if len(sys.argv) > 3:
        try:
            act = TaskAction(sys.argv[3])
        except ValueError:
            print(f"Invalid action: {sys.argv[3]}")
            sys.exit(1)
        
    asyncio.run(submit_and_monitor(rack, dut, act))
