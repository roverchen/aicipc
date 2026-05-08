import asyncio
import hashlib
import random
from pathlib import Path
from src.common.schema import TaskRequest, TaskUpdate, TaskStatus, TaskAction
from src.rack_manager.test_engine import ThermalMonitor, FunctionTestRunner, BurnInRunner, load_test_config
from src.rack_manager.serial_monitor import SerialMonitor

class TaskHandler:
    def __init__(self, agent_id: str, control_plane_url: str):
        self.agent_id = agent_id
        self.control_plane_url = control_plane_url
        self.function_runner = FunctionTestRunner()
        self.burnin_runner = BurnInRunner()
        self.active_aborts = {} # task_id: bool
        self.serial_monitor = SerialMonitor(agent_id)

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
        model = task.params.get("model")
        config = load_test_config(model).get("burn_in", {})
        threshold = config.get("thermal_threshold", 95.0)
        
        thermal_monitor = ThermalMonitor(threshold=threshold, poll_interval=1.0) # Faster poll for prototype
        
        async def emergency_stop(temp: float):
            self.active_aborts[task.task_id] = True
            await self._bmc_force_power_off(task, update_callback, temp, threshold)
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                progress=0, 
                message=f"CRITICAL: Burn-in aborted! CPU Temperature reached {temp:.1f}°C (Threshold: {threshold:.1f}°C)"
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
        is_rshim = task.params.get("rshim") == "true" or "bluefield" in task.params.get("model", "").lower()
        boot_cmd = task.params.get("rshim_push_cmd") if is_rshim else task.params.get("pxe_boot_cmd")
        prep_cmd = task.params.get("bmc_set_boot_cmd")

        if prep_cmd:
            ok = await self._run_shell_step(task, update_callback, 8, f"Applying BMC boot order: {prep_cmd}", prep_cmd)
            if not ok:
                return

        if boot_cmd:
            ok = await self._run_shell_step(task, update_callback, 20, f"Executing boot command: {boot_cmd}", boot_cmd)
            if not ok:
                return
        
        if is_rshim:
            print(f"[Task] Starting rshim OS Deployment for {task.dut_id} (Bluefield DPU)")
            steps = [
                (10, "Detecting /dev/rshim0 interface..."),
                (30, "Mapping virtual USB/PCIe channel..."),
                (60, "Pushing boot image to DPU ARM core..."),
                (85, "Waiting for DPU internal install..."),
            ]
        else:
            print(f"[Task] Starting PXE OS Install for {task.dut_id}")
            steps = [
                (10, "Setting PXE boot flags via BMC..."),
                (30, "Requesting IP from DHCP..."),
                (50, "Downloading OS image via TFTP/HTTP..."),
                (70, "Formatting disk and installing..."),
                (90, "Configuring post-install scripts...")
            ]
            
        for progress, message in steps:
            await update_callback(TaskUpdate(task_id=task.task_id, status=TaskStatus.RUNNING, progress=progress, message=message))
            
            # New: Keyword-based monitoring instead of fixed sleep
            if "Waiting" in message or "Downloading" in message:
                keyword = "READY" if not is_rshim else "ARM_BOOT_OK"
                await self._wait_for_keyword(task, update_callback, keyword)
            else:
                await asyncio.sleep(1.0)
        
        await update_callback(TaskUpdate(task_id=task.task_id, status=TaskStatus.SUCCESS, progress=100, message=f"{'rshim' if is_rshim else 'PXE'} Installation Complete"))

    async def _wait_for_keyword(self, task: TaskRequest, update_callback, keyword: str, timeout: int = 60):
        """Monitor serial ring buffer for a specific keyword with timeout."""
        await update_callback(TaskUpdate(
            task_id=task.task_id, status=TaskStatus.RUNNING, 
            message=f"Monitoring Serial for keyword: [{keyword}]..."
        ))

        elapsed = 0
        # For prototype mode without real serial feed, inject synthetic lines into COM1.
        inject_after = random.randint(2, 5)
        while elapsed < timeout:
            if elapsed == inject_after:
                await self.serial_monitor.append(task.dut_id, "COM1", f"BOOT MSG ... {keyword} ...")

            found = await self.serial_monitor.contains_keyword(task.dut_id, keyword)
            if found:
                await update_callback(TaskUpdate(
                    task_id=task.task_id, status=TaskStatus.RUNNING,
                    message=f"Keyword [{keyword}] DETECTED at T+{elapsed}s. Proceeding."
                ))
                return

            await asyncio.sleep(1)
            elapsed += 1

        await update_callback(TaskUpdate(
            task_id=task.task_id, status=TaskStatus.FAILED,
            message=f"Keyword [{keyword}] not detected within {timeout}s."
        ))
        self.active_aborts[task.task_id] = True

    async def _handle_fw_update(self, task: TaskRequest, update_callback):
        print(f"[Task] Starting FW Update for {task.dut_id}")

        fw_path = task.params.get("firmware_path")
        expected_sha = task.params.get("sha256")
        if fw_path and expected_sha:
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                progress=5,
                message=f"Computing SHA-256 for {fw_path}..."
            ))
            if not Path(fw_path).exists():
                await update_callback(TaskUpdate(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    progress=5,
                    message=f"Firmware file not found: {fw_path}"
                ))
                return

            actual_sha = self._sha256_file(fw_path)
            if actual_sha.lower() != expected_sha.lower():
                await update_callback(TaskUpdate(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    progress=8,
                    message=f"SHA-256 mismatch. expected={expected_sha.lower()} actual={actual_sha.lower()}"
                ))
                return
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                progress=10,
                message="SHA-256 validation passed."
            ))

        steps = [
            (40, "Uploading firmware to BMC cache..."),
            (60, "Writing to SPI flash..."),
            (85, "Verifying checksum..."),
        ]
        for progress, message in steps:
            await update_callback(TaskUpdate(task_id=task.task_id, status=TaskStatus.RUNNING, progress=progress, message=message))
            await asyncio.sleep(2.0)
            
        await update_callback(TaskUpdate(task_id=task.task_id, status=TaskStatus.SUCCESS, progress=100, message="Firmware Update Success"))

    async def _bmc_force_power_off(self, task: TaskRequest, update_callback, current_temp: float, threshold: float):
        command = task.params.get("bmc_poweroff_cmd")
        if not command:
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                progress=0,
                message=f"Overheat {current_temp:.1f}°C >= {threshold:.1f}°C. No bmc_poweroff_cmd provided; marked as emergency stop."
            ))
            return

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            msg = stdout.decode().strip() or "BMC power-off command executed."
            await update_callback(TaskUpdate(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                progress=0,
                message=f"BMC emergency power-off executed: {msg}"
            ))
            return

        err = stderr.decode().strip() or "Unknown BMC command error"
        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            progress=0,
            message=f"BMC emergency power-off failed: {err}"
        ))

    def _sha256_file(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    async def _run_shell_step(self, task: TaskRequest, update_callback, progress: float, announce: str, command: str) -> bool:
        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            progress=progress,
            message=announce
        ))
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            text = stdout.decode().strip()
            if text:
                await update_callback(TaskUpdate(
                    task_id=task.task_id,
                    status=TaskStatus.RUNNING,
                    progress=progress + 5,
                    message=text
                ))
            return True

        err = stderr.decode().strip() or "Unknown command error"
        await update_callback(TaskUpdate(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            progress=progress,
            message=f"Command failed: {err}"
        ))
        return False
