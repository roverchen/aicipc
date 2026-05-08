import asyncio
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List


class SerialMonitor:
    """Async serial monitor with per-port ring buffer and streaming-to-disk."""

    PORTS: List[str] = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]

    def __init__(self, rack_id: str, logs_root: str = "logs/serial", ring_size: int = 2000):
        self.rack_id = rack_id
        self.logs_root = Path(logs_root)
        self.ring_size = ring_size
        self.buffers: Dict[str, Dict[str, Deque[str]]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._writer_lock = asyncio.Lock()
        os.makedirs(self.logs_root, exist_ok=True)

    def _ensure_dut(self, dut_id: str):
        if dut_id in self.buffers:
            return
        self.buffers[dut_id] = {p: deque(maxlen=self.ring_size) for p in self.PORTS}
        self._locks[dut_id] = asyncio.Lock()

    async def append(self, dut_id: str, port: str, line: str):
        self._ensure_dut(dut_id)
        port = port if port in self.PORTS else "COM1"
        ts = datetime.utcnow().isoformat()
        entry = f"{ts} [{port}] {line.strip()}"
        async with self._locks[dut_id]:
            self.buffers[dut_id][port].append(entry)
        await self._stream_to_disk(dut_id, entry)

    async def contains_keyword(self, dut_id: str, keyword: str) -> bool:
        self._ensure_dut(dut_id)
        async with self._locks[dut_id]:
            for port in self.PORTS:
                if any(keyword in row for row in self.buffers[dut_id][port]):
                    return True
        return False

    async def recent_lines(self, dut_id: str, limit: int = 50) -> List[str]:
        self._ensure_dut(dut_id)
        rows: List[str] = []
        async with self._locks[dut_id]:
            for port in self.PORTS:
                rows.extend(list(self.buffers[dut_id][port])[-limit:])
        rows.sort()
        return rows[-limit:]

    async def _stream_to_disk(self, dut_id: str, entry: str):
        day = datetime.utcnow().strftime("%Y-%m-%d")
        base = self.logs_root / self.rack_id / dut_id
        os.makedirs(base, exist_ok=True)
        logfile = base / f"{day}.log"
        async with self._writer_lock:
            with open(logfile, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
