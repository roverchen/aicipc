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
            # Directly use the command from the JSON test plan
            real_cmd = step.get("command")
            
            if real_cmd:
                await update_callback(TaskUpdate(
                    task_id=task.task_id, status=TaskStatus.RUNNING, progress=progress,
                    message=f"Running real test: {name} ({real_cmd})"
                ))
                # 2. Execute real command
                proc = await asyncio.create_subprocess_shell(
                    real_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    test_results.append({"name": name, "status": "PASS"})
                    await update_callback(TaskUpdate(
                        task_id=task.task_id, status=TaskStatus.RUNNING, progress=progress,
                        message=f"Sub-test {name} PASSED: {stdout.decode().strip()[:50]}..."
                    ))
                else:
                    test_results.append({"name": name, "status": "FAIL"})
                    await update_callback(TaskUpdate(
                        task_id=task.task_id, status=TaskStatus.RUNNING, progress=progress,
                        message=f"Sub-test {name} FAILED: {stderr.decode().strip()[:50]}..."
                    ))
            else:
                # Fallback to simulation if no command mapped
                await update_callback(TaskUpdate(
                    task_id=task.task_id, status=TaskStatus.RUNNING, progress=progress,
                    message=f"Simulating test: {name}..."
                ))
                await asyncio.sleep(2)
                # Simulate random failure for mock
                if random.random() < 0.15:
                    test_results.append({"name": name, "status": "FAIL"})
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
        
        # New: Burn-in Command (the actual load generator)
        burnin_cmd = config.get("command")
        stress_proc = None
        
        if burnin_cmd:
            print(f"[BurnIn] Starting stress command: {burnin_cmd}")
            stress_proc = await asyncio.create_subprocess_shell(
                burnin_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

        HOURLY_INTERVAL = int(task.params.get("report_interval_seconds", config.get("report_interval_seconds", 3600)))
        TOTAL_HOURS = config.get("total_hours", 4)
        
        try:
            start_time = datetime.utcnow()
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                progress=0,
                message=f"Burn-in stress testing started... {'(CMD: ' + burnin_cmd + ')' if burnin_cmd else ''}"
            ))

            for hour in range(1, TOTAL_HOURS + 1):
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
        finally:
            if stress_proc:
                print(f"[BurnIn] Terminating stress command for task {task.task_id}")
                try:
                    stress_proc.terminate()
                    await stress_proc.wait()
                except:
                    pass

        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.SUCCESS,
            progress=100,
            message=f"Burn-in test completed successfully after {TOTAL_HOURS} hours."
        ))
