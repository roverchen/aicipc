# AICIPC: Automated Industrial Computer Platform Integration Control

[![Project Status: Active](https://img.shields.io/badge/Project%20Status-Active-brightgreen.svg)](https://github.com/roverchen/aicipc)
[![Target Go-Live](https://img.shields.io/badge/Target%20Go--Live-2026--07-blue.svg)](#)
[![Stack: Python/React/FastAPI](https://img.shields.io/badge/Stack-Python%20%7C%20React%20%7C%20FastAPI-blue.svg)](#)

## 📖 專案概述 | Project Overview

本專案旨在建置一套高效能的工業電腦自動化測試平台，實現「一人多機」的自動化作業模式。系統支援單一操作員同時管理多達 **300 台待測物 (DUT)**，涵蓋從 OS 部署、韌體更新到功能與壓力測試的全流程自動化。

### 🎯 核心目標 | Core Goals
*   **大規模並行處理**：支援 30 組 Rack，總計 300 個節點，2,400 個序列埠監控。
*   **全流程自動化**：整合 PXE、rshim 與 BMC 實現遠端操控，支援刷碼啟動。
*   **即時監控中心**：Dashboard 延遲 < 2s，具備動態過熱保護與多語系支援 (CN/EN/VN)。

---

## 🏗️ 系統架構 | System Architecture

系統採用分散式邊緣架構，確保在大規模測試下的穩定性與即時性。

*   **Control Plane (中央控制平面)**：負責任務調度、歷史數據持久化 (SQLite/Telemetry) 與多語系 Dashboard。
*   **Rack Manager Agent (邊緣代理)**：部署於每個機架旁，負責執行實體測試、監控 Serial 日誌與環境參數。
*   **Communication Layer**：基於 REST API 與 WebSocket 實現任務下發與狀態實時回報。

---

## 🚀 核心功能與部署路徑 | Core Capabilities

### 1. OS 自動安裝 (OS Auto-installation)
*   **PXE 網路開機**：標準機種透過 BMC 修改 Boot Order，由 Agent 提供引導。
*   **rshim 介面**：專為 Bluefield DPU 設計，透過 `/dev/rshim0` 直接推送映像檔。

### 2. 韌體自動更新 (FW Auto-update)
*   支援 **SHA-256 Checksum** 驗證，確保傳輸完整性。
*   透過 BMC/Redfish 介面自動執行分階段版本刷新。

### 3. 高密度序列埠監控 (High-Scale Serial Monitoring)
針對每台 DUT 需監控 8 個 COM Port (BF, Switch, BMC) 的生產需求：
*   **硬體連接**：採用 **Serial Server (Console Server)** 網路化方案與 **IPMI SoL**。
*   **軟體處理**：使用 `Python asyncio` 非同步框架處理 **2,400 個連線**。
*   **日誌策略**：實作 **Ring Buffer** 緩衝與 **Streaming to Disk** 永久保存機制。

---

## ⚙️ 快速開始 | Getting Started

### 1. 環境變數配置 (Environment)
| 變數名稱 | 預設值 | 說明 |
| :--- | :--- | :--- |
| `API_KEY` | `aicipc-secret-2026` | 全域通訊驗證金鑰 |
| `CONTROL_PLANE_URL` | `http://localhost:8000` | Agent 回報位址 |
| `DUT_COUNT` | `10` | 每個機架管理之單位數 |

### 2. 開發模式啟動 (Development)
```bash
# 啟動後端與控制中心
python3 -m src.control_plane.server

# 啟動邊緣代理程序
python3 -m src.rack_manager.agent

# 啟動前端介面
cd frontend && npm install && npm run dev
```

### 3. 生產環境部署 (Docker)
```bash
docker-compose up --build --scale rack-manager-1=30
```

---

## 🛠️ 測試定製化 | Test Customization

系統支援「配置驅動 (Configuration-driven)」模式，可根據 `configs/test_suites/*.json` 彈性調整。

### 配置範例
```json
{
  "function_test": [
    {"name": "CPU_Check", "progress": 20, "command": "stress-ng --cpu 2"},
    {"name": "100G_NIC_Link", "progress": 85, "command": "ethtool eth0"}
  ],
  "burn_in": {
    "total_hours": 24,
    "thermal_threshold": 85.0,
    "command": "stress-ng --cpu 0 --io 4"
  }
}
```

---

## 📁 專案結構 | Project Structure

```text
aicipc/
├── src/
│   ├── common/           # 共用模型、資料庫 (SQLite) 與 Telemetry
│   ├── control_plane/    # 中央伺服器 (FastAPI) & 任務調度
│   └── rack_manager/     # 邊緣代理、非同步日誌處理與測試引擎
├── frontend/             # Dashboard 前端 (React + Vite + i18n)
├── configs/test_suites/  # 測試計畫 JSON 配置檔
├── assets/               # 韌體檔與系統鏡像存儲
├── Dockerfile            # 容器化定義
└── docker-compose.yml    # 多節點大規模部署
```

---

## 🗺️ 開發進度 | Roadmap

- [x] **核心架構**：FastAPI/React 框架建立、WebSocket 實時通訊。
- [x] **測試引擎**：非同步任務處理、關鍵字偵測、燒機過熱保護。
- [x] **生產需求**：MAC 唯一性校驗、中英越三語系、2,400 Port 監控方案。
- [x] **資料持久化**：Telemetry 歷史紀錄儲存、Log 永久保存機制。
- [ ] **權限管理**：RBAC 角色權限控制 (規劃中)。

---

## 📞 維護與支援 | Support
*   **目標上線**: 2026 年 7 月
*   **技術諮詢**: 工作日提供緊急技術支援。
on
{
  "task_id": "task-os-001",
  "rack_id": "RACK-001",
  "dut_id": "DUT-01",
  "action": "OS_INSTALL",
  "params": {
    "model": "model_pro_server",
    "bmc_set_boot_cmd": "ipmitool -I lanplus -H 10.10.1.21 -U admin -P '***' chassis bootdev pxe",
    "pxe_boot_cmd": "echo 'PXE boot request sent for DUT-01'"
  }
}
```

範例（rshim/Bluefield）：
```json
{
  "task_id": "task-os-002",
  "rack_id": "RACK-002",
  "dut_id": "DUT-01",
  "action": "OS_INSTALL",
  "params": {
    "model": "bluefield_dpu",
    "rshim": "true",
    "rshim_push_cmd": "cat /opt/images/bf-boot.img > /dev/rshim0/boot"
  }
}
```

### B. 韌體更新參數（含 SHA-256 驗證）
* `firmware_path`: 韌體檔絕對路徑
* `sha256`: 期望 SHA-256（必須與檔案實際值一致）
* `model`: 機種名稱

範例：
```json
{
  "task_id": "task-fw-001",
  "rack_id": "RACK-001",
  "dut_id": "DUT-01",
  "action": "FW_UPDATE",
  "params": {
    "model": "model_pro_server",
    "firmware_path": "/opt/fw/bios_v2.8.1.bin",
    "sha256": "3e7a8b3d1d7ec5b4d8cf2f95e5f8feecf0d7dc0f3a0dca193a9f77b0d4a4d8ee"
  }
}
```

### C. 燒機測試參數（過熱保護與回報週期）
* `model`: 機種名稱
* `simulate_overheat`: `true/false`（測試用）
* `bmc_poweroff_cmd`: 超溫時執行的 BMC 強制斷電命令
* `report_interval_seconds`: 開發/驗證用回報秒數；生產建議保持 3600（每小時）

範例：
```json
{
  "task_id": "task-burn-001",
  "rack_id": "RACK-001",
  "dut_id": "DUT-01",
  "action": "BURN_IN",
  "params": {
    "model": "model_pro_server",
    "simulate_overheat": "false",
    "bmc_poweroff_cmd": "ipmitool -I lanplus -H 10.10.1.21 -U admin -P '***' chassis power off",
    "report_interval_seconds": "3600"
  }
}
```

### D. 功能測試行為（Auto-Skip + Dashboard 查核 + 完測通知）
* 子測項失敗時會自動略過並持續執行。
* 每一步都會透過 `/api/v1/tasks/update` 寫入最新狀態，Dashboard 可即時查核。
* 完測時會產生摘要（成功數/總數/失敗項目）並由控制平面發送通知訊息給測試者（`Function Test Summary`）。

---

## 快速開始與開發階段 | Getting Started & Development Phases

### Phase 1: 基礎環境與服務啟動
1. **安裝依賴**: `pip install fastapi uvicorn httpx pydantic sqlalchemy typer rich`
2. **啟動控制平面 (Server)**: `API_KEY=<your-key> python3 -m src.control_plane.server`
3. **啟動 Rack Manager Agent (模擬終端)**: `API_KEY=<your-key> HEARTBEAT_INTERVAL_SECONDS=2 python3 -m src.rack_manager.agent`

### Phase 2: 視覺化介面與 CLI 工具
1. **Web Dashboard**:
   ```bash
   cd frontend
   npm install && npm run dev # 訪問 http://localhost:5173
   ```
2. **Python CLI**: 提供大規模批次操作與過熱模擬。
   ```bash
   python3 -m src.control_plane.cli deploy RACK-XXX --action BURN_IN --model model_pro_server
   ```

### Phase 3: 生產環境 Docker 部署
系統支援完整容器化，適合正式上線環境。
```bash
docker-compose up --build
```
*   **持久化**: 資料庫檔案 `aicipc.db` 自動掛載。
*   **安全性**: 系統通訊受 `X-API-KEY` 保護。
*   **水平擴展**: 可用 `docker compose up --build --scale rack-manager-1=30` 進行多 Agent 壓測（建議改為模板化 service 命名後再正式使用）。

---

## 專案結構 | Project Structure

```text
aicipc/
├── src/
│   ├── common/           # 共用模型與資料庫 (SQLite)
│   ├── control_plane/    # 中央伺服器 (FastAPI) & CLI
│   └── rack_manager/     # 邊緣代理 (Agent) & 測試引擎
├── frontend/             # Dashboard 前端 (React + Vite)
├── configs/test_suites/  # 測試計畫 JSON 配置
├── Dockerfile            # 生產環境鏡像
└── docker-compose.yml    # 多代理大規模模擬
```

---

## 開發進度 | Development Status

- [x] **Phase 1-4**: 核心架構、PXE/rshim 流程、測試引擎與 Dashboard 開發。
- [x] **Phase 5-6**: 邊緣端日誌系統、資料庫持久化與 Docker 容器化。
- [x] **Phase 7-8**: 雲端部署支援、自動化摘要報告與過熱警報中心。

---

## 維護與支援 | Support
*   **目標上線**: 2026 年 7 月
*   **技術諮詢**: 支援工作日緊急技術諮詢與操作手冊提供。
