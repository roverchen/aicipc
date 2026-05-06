import asyncio
import random
from src.common.schema import TaskRequest, TaskUpdate, TaskStatus, TaskAction
from src.rack_manager.test_engine import ThermalMonitor, FunctionTestRunner, BurnInRunner

class TaskHandler:
    def __init__(self, agent_id: str, control_plane_url: str):
        self.agent_id = agent_id
        self.control_plane_url = control_plane_url
        self.function_runner = FunctionTestRunner()
        self.burnin_runner = BurnInRunner()
        self.active_aborts = {} # task_id: bool

    async def execute(self, task: TaskRequest, update_callback):
        """Execute a task and call the update_callback with progress"""
        print(f"[*] Task received: {task.task_id} {task.action} for {task.dut_id}")
        print(f"[*] Task params: {task.params}")
        self.active_aborts[task.task_id] = False
        
        try:
            if task.action == TaskAction.OS_INSTALL:
                await self._handle_os_install(task, update_callback)
            elif task.action == TaskAction.FW_UPDATE:
                await self._handle_fw_update(task, update_callback)
            elif task.action == TaskAction.FUNCTION_TEST:
                await self.function_runner.run(task, update_callback)
            elif task.action == TaskAction.BURN_IN:
                await self._handle_burn_in(task, update_callback)
            else:
                await update_callback(TaskUpdate(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    message=f"Unsupported action: {task.action}"
                ))
        finally:
            self.active_aborts.pop(task.task_id, None)

    async def _handle_burn_in(self, task: TaskRequest, update_callback):
        thermal_monitor = ThermalMonitor(threshold=95.0, poll_interval=1.0) # Faster poll for prototype
        
        async def emergency_stop(temp: float):
            self.active_aborts[task.task_id] = True
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                progress=0, 
                message=f"CRITICAL: Burn-in aborted! CPU Temperature reached {temp:.1f}°C (Threshold: 95°C)"
            ))

        def check_abort():
            return self.active_aborts.get(task.task_id, False)

        # Start thermal monitor
        await thermal_monitor.start(emergency_stop)
        
        try:
            # If user wants to force high temp for testing
            if task.params.get("simulate_overheat") == "true":
                thermal_monitor.current_temp = 90.0 # Force starting temp high
            
            await self.burnin_runner.run(task, update_callback, check_abort)
        finally:
            await thermal_monitor.stop()

    async def _handle_os_install(self, task: TaskRequest, update_callback):
        print(f"[Task] Starting OS Install for {task.dut_id}")
        steps = [
            (10, "Setting PXE boot flags..."),
            (30, "Requesting IP from DHCP..."),
            (50, "Downloading OS image (Ubuntu 22.04)..."),
            (70, "Formatting disk and installing..."),
            (90, "Configuring post-install scripts...")
        ]
        for progress, message in steps:
            await update_callback(TaskUpdate(task_id=task.task_id, status=TaskStatus.RUNNING, progress=progress, message=message))
            await asyncio.sleep(1.5)
        
        await update_callback(TaskUpdate(task_id=task.task_id, status=TaskStatus.SUCCESS, progress=100, message="OS Installation Complete"))

    async def _handle_fw_update(self, task: TaskRequest, update_callback):
        print(f"[Task] Starting FW Update for {task.dut_id}")
        steps = [
            (10, "Validating binary signature..."),
            (40, "Uploading firmware to BMC cache..."),
            (60, "Writing to SPI flash..."),
            (85, "Verifying checksum..."),
        ]
        for progress, message in steps:
            await update_callback(TaskUpdate(task_id=task.task_id, status=TaskStatus.RUNNING, progress=progress, message=message))
            await asyncio.sleep(2.0)
            
        await update_callback(TaskUpdate(task_id=task.task_id, status=TaskStatus.SUCCESS, progress=100, message="Firmware Update Success"))
