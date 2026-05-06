import asyncio
import random
from datetime import datetime, timedelta
from typing import Callable, Optional
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

class FunctionTestRunner:
    async def run(self, task: TaskRequest, update_callback):
        sub_tests = [
            ("CPU_Check", 20),
            ("Memory_Check", 40),
            ("Network_Check", 60),
            ("Disk_IO_Check", 80),
            ("BMC_Communication", 95)
        ]
        
        for name, progress in sub_tests:
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                progress=progress,
                message=f"Executing sub-test: {name}..."
            ))
            await asyncio.sleep(2)
            
            # Simulate random failure
            if random.random() < 0.05:
                await update_callback(TaskUpdate(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    progress=progress,
                    message=f"Sub-test {name} FAILED!"
                ))
                return

        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.SUCCESS,
            progress=100,
            message="All functional tests PASSED"
        ))

class BurnInRunner:
    async def run(self, task: TaskRequest, update_callback, check_abort: Callable[[], bool]):
        # Requirement: Report result every 1 hour.
        # For prototype, we'll speed this up to 30 seconds for "1 hour"
        HOURLY_INTERVAL = 30 # seconds (for prototype)
        TOTAL_HOURS = 4
        
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
