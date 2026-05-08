# 工業電腦自動化測試系統 (Automated Industrial Computer Platform Integration Control)

[![Project Status: Active](https://img.shields.io/badge/Project%20Status-Active-brightgreen.svg)](https://github.com/roverchen/aicipc)
[![Target Go-Live](https://img.shields.io/badge/Target%20Go--Live-2026--07-blue.svg)](#)

## 專案概述 | Project Overview

本專案旨在建置一套高效能的工業電腦自動化測試平台，實現「一人多機」的自動化作業模式。系統支援單一操作員同時管理多達 **300 台待測物 (DUT)**，涵蓋從 OS 部署、韌體更新到功能與壓力測試的全流程自動化。

### 核心目標 | Core Goals
*   **高擴展性**：支援 30 組 Rack，每組 Rack 10 台 DUT，總計 300 個節點。
*   **全自動化**：透過 PXE、rshim 與 BMC 實現遠端操控，減少人工插拔。
*   **即時監控**：Dashboard 延遲低於 2 秒，具備動態過熱保護機制。

---

## 核心功能與部署路徑 | Core Functions & Deployment Paths

系統支援三種主要的部署與啟動方式，根據硬體機種自動切換路徑。

### 1. OS 自動安裝 (OS Auto-installation)
*   **PXE 網路開機 (標準)**：適用於一般 Server/工控主機。透過 BMC 修改 BIOS 順序，由 Rack Manager 提供 DHCP/TFTP 引導及映像檔傳輸。
*   **rshim 介面 (特定機種)**：專為 Bluefield DPU 設計。不佔用外部網路頻寬，直接透過主機 `/dev/rshim0` 推送引導映像檔至 ARM 核心。

### 2. 韌體自動更新 (FW Auto-update)
*   透過 **BMC/IPMI/Redfish** 介面傳輸二進位檔。
*   支援 **SHA-256 Checksum** 驗證與分階段的版本刷新，避免檔案毀損導致裝置變磚。

### 📁 資產管理與置放路徑 (Asset Management)

為了確保系統能正確讀取相關資源，請依照以下路徑置放檔案：

| 資源類型 | 建議路徑 | 說明 |
| :--- | :--- | :--- |
| **測試計畫 (Test Plans)** | `configs/test_suites/*.json` | 定義測試步驟的 JSON，可透過 Dashboard 直接維護。 |
| **韌體檔案 (Firmware)** | `assets/firmware/` | 放置 `.bin` 或 `.rom` 檔，供 FW_UPDATE 任務使用。 |
| **系統鏡像 (OS Images)** | `assets/images/` | 放置 `.iso` 或 `.img` 檔，供 OS_INSTALL 任務使用。 |

> [!TIP]
> 在執行 `FW_UPDATE` 任務時，請在參數中帶入 `firmware_path: "assets/firmware/your_file.bin"`。

---

## 大規模序列埠監控解決方案 | High-Scale Serial Monitoring Solution

針對需求中提到的每台 DUT 需監控 8 個 COM Port（2 Canisters × 4 Ports），在管理 300 台 DUT 的規模下，系統總計需處理高達 **2,400 個 Serial 連線**。以下是針對 I/O 處理與硬體連接的專業解決方案：

### 1. 硬體連接層：Serial-over-LAN (SoL) 與 Serial Server
單台 Rack Manager 主機無法直接擴充數百個實體 COM Port，必須採用網路化方案：
*   **使用 Serial Server (Console Server)**：部署支援高密度埠數（如 32 或 48 埠）的 Serial Server，將實體 COM Port 轉為 IP 網路訊號。
*   **IPMI SoL (Serial-over-LAN)**：針對 COM4 (BMC)，優先使用 BMC 內建的 SoL 功能，透過管理網路直接擷取日誌，無需額外接線。
*   **實體接線規劃**：
    *   **COM1/COM2 (BF)**、**COM3 (Switch)**：需透過實體 Serial 線路連接至 Rack 內的 Serial Server。

### 2. 軟體架構層：非同步 I/O 與多進程處理
處理 2,400 個連線時，傳統的「一連線一執行緒」會耗盡系統資源。
*   **Asyncio 非同步框架**：在 Rack Manager Agent 使用 `Python asyncio`。利用單一 Event Loop 同時監控數百個 Socket 連線，僅在有資料傳入時才觸發處理。
*   **多層級緩衝 (Buffer Management)**：
    *   **Ring Buffer**：為每個 Serial Port 建立循環緩衝區，防止大量 Log 湧入時導致記憶體溢位。
    *   **關鍵字過濾器 (Pre-filter)**：在寫入資料庫前，先在 Agent 端進行關鍵字比對（如開機完成字串），減少傳輸至 Control Plane 的流量。

### 3. 資料儲存層：永久 Log 與開機 Log 處理
*   **串流寫入 (Streaming to Disk)**：將 Serial Log 直接以文字檔 (.log) 形式儲存於本地或 NAS，資料庫僅儲存檔案路徑與索引，避免資料庫肥大。
*   **日誌切割機制**：設定按任務編號 (taskId) 或日期自動切割檔案，方便後續 R&D 依任務查詢。

### 4. 系統開發注意事項
*   **埠號對映表 (Mapping Table)**：必須在配置檔中嚴格定義每個 COM Port 對應的元件（如 Port 8001 = DUT01_BF_COM1），避免擷取錯誤。
*   **中斷自動重連**：Serial Server 可能因網路波動斷線，Agent 必須具備自動偵測並重新掛載 Socket 的能力。

### 5. 實作範例邏輯 (Python)
```python
import asyncio

async def handle_serial_log(port_ip, component_name):
    reader, writer = await asyncio.open_connection(port_ip, 8000)
    while True:
        data = await reader.read(1024)
        if not data: break
        message = data.decode(errors='ignore')
        # 關鍵字監控邏輯 (如 Login: 字串偵測)
        if "Login:" in message:
            await notify_status_update(component_name, "READY")
        # 寫入本地 Log 檔實現永久保存
        save_to_permanent_storage(component_name, message)

# 同時啟動多個監控任務
tasks = [handle_serial_log(ip, name) for ip, name in serial_mapping.items()]
await asyncio.gather(*tasks)
```

透過此組合方案，可確保 2,400 個 Port 的 Log 不遺失，且 Dashboard 更新延遲低於 2 秒。

---

### 🚀 2026 生產環境進階需求 (Production Requirements / Roadmap)

以下項目為生產目標與規範，部分尚在開發中：

#### 1. 硬體介面與序列通訊 (Serial Mapping)
單台待測物 (DUT) 包含兩個 Canister，共計 **8 個 COM Port**：
*   **COM1, COM2**: 用於 **BF (Bluefield DPU)** 監控。
*   **COM3**: 用於 **Switch** 管理。
*   **COM4**: 用於 **BMC** 存取。
*   **方案實作**: 詳見 [大規模序列埠監控解決方案](#大規模序列埠監控解決方案--high-scale-serial-monitoring-solution)。系統需具備處理高達 **2,400 個同步序列連線** 的能力。

#### 2. 自動化流程優化 (Flow Logic)
*   **刷碼啟動**: 已實現。操作員在 Dashboard 點選 DUT 並輸入 MAC 後，自動觸發「全自動連續測試」(OS -> FW -> Function -> Burn-in)。
*   **關鍵字偵測開機**: 已導入 `task_handler.py`；系統能偵測 Serial 輸出字串以判斷開機進度。

#### 3. 資料處理與安全性 (Data & Security)
*   **永久保存與備份**: 實作 `TelemetryModel` 實現測試紀錄持久化，Log 檔採串流寫入。
*   **MAC Address 唯一性校驗**: 已提供 `/api/v1/verify_mac` 檢查生產線 MAC 重複。
*   **越南語系支援**: Dashboard 已全面支援中、英、越三語系。

---

### ⚙️ 環境變數 (Environment Variables)
*   `API_KEY`: Control Plane / Agent API 驗證金鑰（預設 `aicipc-secret-2026`）。
*   `CONTROL_PLANE_URL`: Agent 連線的 Control Plane URL（預設 `http://localhost:8000`）。
*   `HEARTBEAT_INTERVAL_SECONDS`: Agent 心跳間隔秒數（預設 `2`）。
*   `DUT_COUNT`: 每個 Agent 管理的 DUT 數量（預設 `10`）。
*   `VITE_API_KEY`: 前端呼叫受保護 API 時使用的金鑰。

### 技術比較表

| 項目 | **PXE 網路開機** | **rshim 介面 (DPU)** | **BMC Bootup 驗證** |
| :--- | :--- | :--- | :--- |
| **主要對象** | 標準 Server/工業電腦 | Bluefield DPU 及其 ARM 核心 | 已安裝 OS 的 DUT 狀態檢查 |
| **通訊媒介** | 乙太網路 (Data Network) | 虛擬 USB/PCIe (`/dev/rshim0`) | IPMI / Redfish 管理網路 |
| **關鍵優點** | 產業標準，支援大規模並行 | 無需網路設定，直接存取內部 | 僅驗證狀態，無需安裝程序 |

> [!IMPORTANT]
> **網路頻寬建議**：當 30 組 Rack 同時執行 PXE 部署時，建議控制平面到 Rack Manager 具備 **10G 以上頻寬**，且管理網路 (IPMI) 應與資料網路實體隔離。

---

## 測試定製化 | Test Customization

系統支援「配置驅動 (Configuration-driven)」模式，可根據不同機種 (Model) 彈性調整測試內容。

### 1. 配置結構
在 `configs/test_suites/` 目錄下存放特定機種的 JSON 配置檔（如 `default.json`, `model_name.json`）。

### 2. 配置範例 (JSON)
```json
{
  "function_test": [
    {"name": "CPU_Check", "progress": 20},
    {"name": "Memory_ECC_Test", "progress": 50},
    {"name": "100G_NIC_Link", "progress": 85}
  ],
  "burn_in": {
    "total_hours": 24,
    "thermal_threshold": 85.0
  }
}
```

### 3. 使用方式
下發任務時指定 `model` 即可載入配置：
```bash
python3 -m src.rack_manager.test_task RACK-001 DUT-01 FUNCTION_TEST --params model=model_name
```

---

## 任務參數與實機串接範例 | Runtime Parameters & Integration Examples

以下參數可透過 `TaskRequest.params` 下發，讓系統在同一套流程中切換模擬/實機模式。

### A. OS 安裝參數（PXE / rshim / BMC）
* `model`: 機種名稱（對應 `configs/test_suites/*.json`）
* `rshim`: `true/false`，強制走 rshim 路徑
* `bmc_set_boot_cmd`: 設定開機順序指令（例如 `ipmitool` / `redfishtool`）
* `pxe_boot_cmd`: PXE 啟動指令
* `rshim_push_cmd`: rshim 映像推送指令

範例（PXE）：
```json
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
