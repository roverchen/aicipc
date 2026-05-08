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
        del wait_for_decision
        model = task.params.get("model")
        config = load_test_config(model)
        sub_tests = config.get("function_test", [])
        
        test_results = []
        for step in sub_tests:
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
                test_results.append({"name": name, "status": "FAIL"})
                passed_count = sum(1 for r in test_results if r["status"] == "PASS")
                fail_count = sum(1 for r in test_results if r["status"] == "FAIL")
                await update_callback(TaskUpdate(
                    task_id=task.task_id,
                    status=TaskStatus.RUNNING,
                    progress=progress,
                    message=f"Sub-test {name} FAILED. Auto-skip enabled. Live result PASS={passed_count}, FAIL={fail_count}."
                ))
            else:
                test_results.append({"name": name, "status": "PASS"})
            
            await asyncio.sleep(0.5)

        # Generate summary report
        passed_count = sum(1 for r in test_results if r["status"] == "PASS")
        total_count = len(sub_tests)
        failed_items = [r["name"] for r in test_results if r["status"] == "FAIL"]
        
        summary = f"Test Complete. Success: {passed_count}/{total_count}. "
        if failed_items:
            summary += f"Failures detected in: {', '.join(failed_items)}."
        else:
            summary += "All items PASSED perfectly."

        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.SUCCESS,
            progress=100,
            message=summary
        ))

class BurnInRunner:
    async def run(self, task: TaskRequest, update_callback, check_abort: Callable[[], bool]):
        model = task.params.get("model")
        config = load_test_config(model).get("burn_in", {})
        
        # Requirement: Report result every 1 hour in production.
        # For development/demo, users may override with report_interval_seconds in params/config.
        HOURLY_INTERVAL = int(task.params.get("report_interval_seconds", config.get("report_interval_seconds", 3600)))
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
            message=f"Burn-in test completed successfully after {TOTAL_HOURS} hours."
        ))
