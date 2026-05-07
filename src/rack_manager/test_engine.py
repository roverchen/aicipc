import asyncio
import random
import json
import os
from datetime import datetime, timedelta
from typing import Callable, Optional, List, Dict
from src.common.schema import TaskRequest, TaskUpdate, TaskStatus

class ThermalMonitor:
    def __init__(self, threshold: float = 95.0, poll_interval: float = 5.0):
        self.threshold = threshold
        self.poll_interval = poll_interval
        self.is_running = False
        self.current_temp = 45.0 # Starting temp
        self._task = None

    async def start(self, on_emergency_stop: Callable[[float], asyncio.Future]):
        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop(on_emergency_stop))

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self, on_emergency_stop):
        while self.is_running:
            # Simulate sensor reading
            # In a real system, this would be an IPMI/Redfish call
            self.current_temp += random.uniform(-1.0, 3.0) 
            # print(f"[Thermal] Current Temp: {self.current_temp:.1f}°C")
            
            if self.current_temp >= self.threshold:
                print(f"[CRITICAL] Thermal threshold reached: {self.current_temp:.1f}°C!")
                await on_emergency_stop(self.current_temp)
                break
            
            await asyncio.sleep(self.poll_interval)

def load_test_config(model: Optional[str] = None) -> Dict:
    """Load test suite configuration based on model name."""
    config_dir = "configs/test_suites"
    config_file = f"{model}.json" if model else "default.json"
    config_path = os.path.join(config_dir, config_file)
    
    if not os.path.exists(config_path):
        # Fallback to default if model config doesn't exist
        config_path = os.path.join(config_dir, "default.json")
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[Error] Failed to load config {config_path}: {e}")
        # Return a bare minimum default if file loading fails
        return {
            "function_test": [{"name": "Basic_Check", "progress": 50}],
            "burn_in": {"total_hours": 1, "thermal_threshold": 95.0, "report_interval_seconds": 10}
        }

class FunctionTestRunner:
    async def run(self, task: TaskRequest, update_callback, wait_for_decision):
        model = task.params.get("model")
        config = load_test_config(model)
        sub_tests = config.get("function_test", [])
        
        i = 0
        while i < len(sub_tests):
            step = sub_tests[i]
            name = step.get("name", "Unknown")
            progress = step.get("progress", 0)
            
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                progress=progress,
                message=f"Executing sub-test: {name}..."
            ))
            await asyncio.sleep(2)
            
            # Simulate random failure
            if random.random() < 0.15: # Demo failure rate
                await update_callback(TaskUpdate(
                    task_id=task.task_id,
                    status=TaskStatus.WAITING_DECISION,
                    progress=progress,
                    message=f"Sub-test {name} FAILED! Waiting for operator decision..."
                ))
                
                decision = await wait_for_decision(task.task_id)
                
                if decision == "RETRY":
                    await update_callback(TaskUpdate(
                        task_id=task.task_id,
                        status=TaskStatus.RUNNING,
                        progress=progress,
                        message=f"Retrying sub-test: {name}..."
                    ))
                    continue # Repeat the same step
                elif decision == "SKIP":
                    await update_callback(TaskUpdate(
                        task_id=task.task_id,
                        status=TaskStatus.RUNNING,
                        progress=progress,
                        message=f"Skipping failed sub-test: {name}..."
                    ))
                    # Fall through to next step
                elif decision == "ABORT":
                    await update_callback(TaskUpdate(
                        task_id=task.task_id,
                        status=TaskStatus.FAILED,
                        progress=progress,
                        message=f"Task ABORTED by operator at {name}"
                    ))
                    return
            
            i += 1 # Next step

        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.SUCCESS,
            progress=100,
            message="All functional tests completed (some steps might have been skipped)"
        ))

class BurnInRunner:
    async def run(self, task: TaskRequest, update_callback, check_abort: Callable[[], bool]):
        model = task.params.get("model")
        config = load_test_config(model).get("burn_in", {})
        
        # Requirement: Report result every 1 hour.
        # Use config values, with defaults as fallback
        HOURLY_INTERVAL = config.get("report_interval_seconds", 30)
        TOTAL_HOURS = config.get("total_hours", 4)
        
        start_time = datetime.utcnow()
        last_report_time = start_time
        
        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            progress=0,
            message="Burn-in stress testing started..."
        ))

        for hour in range(1, TOTAL_HOURS + 1):
            # Simulate testing for "1 hour"
            elapsed = 0
            while elapsed < HOURLY_INTERVAL:
                if check_abort():
                    print(f"[BurnIn] Aborting task {task.task_id} due to external trigger")
                    return
                
                await asyncio.sleep(2)
                elapsed += 2
            
            progress = (hour / TOTAL_HOURS) * 100
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                progress=progress,
                message=f"Burn-in progress: {hour} hour(s) completed. Health: OK."
            ))
            last_report_time = datetime.utcnow()

        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.SUCCESS,
            progress=100,
            message="Burn-in test completed successfully after 4 hours."
        ))
