# 工業電腦自動化測試系統 (Automated Industrial Computer Platform Integration Control)

[![Project Status: Active](https://img.shields.io/badge/Project%20Status-Active-brightgreen.svg)](https://github.com/roverchen/aicipc)
[![Target Go-Live](https://img.shields.io/badge/Target%20Go--Live-2026--07-blue.svg)](#)

## 專案概述 | Project Overview

本專案旨在建置一套高效能的工業電腦自動化測試平台，實現「一人多機」的自動化作業模式。系統設計支援單一操作員同時管理多達 **300 台待測物 (DUT)**，涵蓋從 OS 安裝、韌體更新到功能與壓力測試的全流程自動化。

### 核心目標
*   **高擴展性**：支援 30 組 Rack，每組 Rack 容納 5–10 台 DUT。
*   **全自動化**：減少人工插拔與監看，透過 PXE 與 BMC 實現遠端操控。
*   **即時監控**：Dashboard 延遲低於 2 秒，即時掌握 300 台機器的健康狀態。

---

## 四大核心功能 | Core Functions

1.  **OS 自動安裝 (OS Auto-installation)**
    *   透過 PXE 網路開機或特定機種的 `rshim` 介面自動部署作業系統。
    *   支援安裝後的版本自動驗證與開機順序還原。

2.  **韌體自動更新 (FW Auto-update)**
    *   透過 BMC/IPMI 介面傳輸二進位檔。
    *   支援 Checksum 驗證與分階段的版本刷新。

3.  **功能測試 (Function Test)**
    *   自動部署並執行測試套件 (Test Suite)。
    *   即時進度回報與完整日誌報告產出。

4.  **燒機測試 (Burn-in Test)**
    *   高負載壓力測試（CPU / Memory / Disk / Network）。
    *   **安全機制**：當 CPU 溫度超過安全閾值（預設 95°C）或偵測到硬體異常時自動中止。

---

## 測試定製化 | Test Customization

系統支援「配置驅動 (Configuration-driven)」的測試定製化，允許測試者根據不同機種 (Model) 彈性調整測試內容。

### 1. 配置結構
在 `configs/test_suites/` 目錄下存放特定機種的 JSON 配置檔：
*   `default.json`: 通用基準測試。
*   `model_name.json`: 特定機種定製化測試。

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
下發任務時，在參數中指定 `model` 即可自動載入對應配置：
```bash
python3 -m src.rack_manager.test_task RACK-001 DUT-01 FUNCTION_TEST --params model=model_name
```

---

## 快速開始與開發階段 | Getting Started & Development Phases

### Phase 1: 基礎環境與服務啟動
本階段涵蓋基礎依賴安裝與核心服務的模擬運行。
#### 1. 依賴安裝
```bash
pip install fastapi uvicorn httpx pydantic sqlalchemy typer rich
```

#### 2. 啟動服務
1. **啟動控制平面 (Server)**:
   ```bash
   python3 -m src.control_plane.server
   ```
2. **啟動 Rack Manager Agent (模擬終端)**:
   ```bash
   python3 -m src.rack_manager.agent
   ```

### Phase 2: 基礎任務下發測試
在啟動 Server 與 Agent 後，可使用測試腳本模擬下發單一任務（OS 安裝或韌體更新）：
```bash
# 下發 OS 安裝任務 (請根據 Agent 日誌更換 RACK_ID)
python3 -m src.rack_manager.test_task RACK-XXX DUT-01 OS_INSTALL

# 下發韌體更新任務
python3 -m src.rack_manager.test_task RACK-XXX DUT-02 FW_UPDATE
```

### Phase 3: 測試引擎與熱保護驗證
測試引擎負責執行更複雜的邏輯，包含多步驟的功能測試與具備「自動溫控中斷」機制的燒機測試：
```bash
# 執行功能測試套件 (使用預設配置)
python3 -m src.rack_manager.test_task RACK-XXX DUT-01 FUNCTION_TEST

# 執行特定機種的燒機測試 (自動載入 model_pro_server.json)
python3 -m src.rack_manager.test_task RACK-XXX DUT-02 BURN_IN --params model=model_pro_server

# 模擬高溫自動中止 (驗證動態熱保護機制)
python3 -m src.rack_manager.test_task RACK-XXX DUT-03 BURN_IN --overheat
```

### Phase 4: 視覺化介面與批次操作工具
本階段提供 Web Dashboard 進行即時監控，以及 CLI 工具進行大規模批次操作。

#### 網頁 Dashboard
1. 進入 `frontend` 目錄並啟動開發伺服器：
   ```bash
   cd frontend
   npm install && npm run dev
   ```
2. 開啟瀏覽器訪問 `http://localhost:5173`。
3. **機種選擇**：在控制面板中可透過「Device Model」下拉選單切換測試配置。

#### Python CLI 工具
提供強大的命令列批次操作功能，支援機種指定與過熱模擬：
```bash
# 下發特定機種任務
python3 -m src.control_plane.cli deploy RACK-XXX --action BURN_IN --model model_pro_server

# 下發並模擬過熱保護
python3 -m src.control_plane.cli deploy RACK-XXX --action BURN_IN --overheat
```

### Phase 5: 日誌追蹤與生產部署
#### 日誌追蹤
Agent 會在本地儲存詳細執行日誌，可隨時查看：
```bash
cat logs/<TASK_ID>.log
```

### Phase 6: 生產環境 Docker 部署
系統已完整支援資料庫持久化與 Docker 容器化部署，適合正式上線環境。
#### 使用 Docker Compose 啟動全系統
```bash
# 構建並啟動控制平面與 3 組模擬 Agent
docker-compose up --build
```
*   **控制平面**: 存取 `http://localhost:8000` 即可看到整合後的儀表板。
*   **持久化**: 資料庫檔案 `aicipc.db` 會掛載於主機，確保數據在容器重啟後保留。
*   **安全性**: 系統通訊受 `X-API-KEY` 保護。

---

## 專案結構 | Project Structure

```text
aicipc/
├── src/
│   ├── common/           # 共用模型、Schema 與資料庫 (SQLite)
│   ├── control_plane/    # 中央控制伺服器 (FastAPI)
│   └── rack_manager/     # 邊緣代理程式 (Agent)
├── frontend/             # Dashboard 前端專案 (React + Vite)
├── Dockerfile            # 控制平面生產環境鏡像描述
├── docker-compose.yml    # 多代理大規模模擬配置
└── README.md
```

---

## 系統架構 | Architecture

系統採用分散式代理架構以支援大規模並行測試：

*   **控制平面 (Control Plane)**: 負責任務排程、資料匯總與 Web Dashboard。
*   **Rack Manager Agent**: 部署於每個 Rack 的代理程序，負責與該 Rack 內 DUT 的 BMC (BMC, Bluefield DPU, Switch, MCU) 進行低延遲通訊。
*   **待測物 (DUT)**: 執行測試任務的主體。

---

## 高密度序列通訊管理 | High-Density Serial Management

針對單一 Rack 內多達 10 台 DUT (每台 8 個 COM ports，總計 80 個連接) 的複雜情境，系統採用以下架構進行管理：

1.  **物理層 (Hardware Layer)**:
    *   使用 **工業級序列伺服器 (Serial-to-Ethernet Server)**，如 Moxa NPort 或 Digi PortServer。
    *   透過高密度電纜 (RJ45 to DB9/Flat Cable) 將 80 個實體埠匯聚至序列伺服器。
2.  **傳輸層 (Transport Layer)**:
    *   將實體序列通訊轉換為 **TCP/IP 串流 (COM-over-IP)**。
    *   Rack Manager Agent 與序列伺服器透過區域網路連接，免除實體序列卡限制。
3.  **軟體層 (Software Layer)**:
    *   **異步並發 (Asynchronous I/O)**: Agent 利用 `asyncio` 維護 80 個並行 Socket 連接，實現低延遲的日誌擷取與指令下發。
    *   **虛擬埠映射**: 系統自動將 `Device ID + Port Index` 映射至對應的 `IP:Port` 端點。

---

## 系統技術棧 | Tech Stack

*   **後端服務**: Python / Go (適合處理大量並發 I/O 與 BMC 通訊)
*   **通訊協定**: IPMI 2.0, Redfish, PXE, WebSocket (即時狀態推送)
*   **前端介面**: Modern Web Framework (React/Vue) + Tailwind CSS
*   **命令列工具**: CLI 工具支援批次任務提交

---

## 需求細節 | Requirement Highlights

根據《工業電腦自動化測試系統_需求確認文件》，以下為開發重點：
*   **任務管理**：支援 300 台任務同時執行，不設優先權，採依序測試。
*   **健康監控**：持續讀取硬體 Sensor (溫度、風扇、功耗)，每一小時回報燒機結果。
*   **異常處理**：若燒機異常立即停止並顯示 Fail，需記錄完整 Log 供 R&D 分析。
*   **驗收標準**：需完成 1 個 Rack 的完整流程驗證。

---

## 開發進度 | Development Status

- [x] **Phase 1 (基礎架構)**: 建立控制平面與 Rack Manager 通訊原型。
- [x] **Phase 2 (核心功能)**: 實作 PXE OS 安裝與 BMC FW 更新流程。
- [x] **Phase 3 (測試引擎)**: 整合 Function Test 套件與 Burn-in 壓力設定檔。
- [x] **Phase 4 (介面開發)**: 完成 Web Dashboard 與 Python CLI 工具。
- [x] **Phase 5 (日誌系統)**: 實作邊緣端本地日誌儲存與追蹤。
- [x] **Phase 6 (分階段部署)**: 實作資料庫持久化、安全驗證與 Docker 部署。

---

## 維護與支援 | Support

*   **上線時間**: 2026 年 7 月
*   **支援方式**: 提供操作手冊與現場教學，支援工作日及緊急技術諮詢。
