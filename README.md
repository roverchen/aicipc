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

## 部署模式與技術細節 | Deployment Modes & Technical Details

這三種部署與啟動方式在技術層級、依賴路徑以及適用情境上有顯著差異。根據您的《需求確認文件》，本系統支援以下模式來應對不同的硬體機種。

### 一、 程序差異比較

| 項目 | **PXE 網路開機部署** | **rshim 介面部署 (DPU)** | **BMC Bootup 測試** |
| :--- | :--- | :--- | :--- |
| **主要對象** | 標準 Server/工業電腦主機 [cite: 46] | Bluefield DPU 及其 ARM 核心 [cite: 46, 50] | 已安裝 OS 的 DUT 狀態檢查 [cite: 10, 58] |
| **通訊媒介** | 乙太網路 (Data Network) [cite: 40, 48] | 虛擬 USB/PCIe 通道 (`/dev/rshim0`) [cite: 20] | IPMI / Redfish API 管理網路 [cite: 10, 46] |
| **核心流程** | DHCP -> TFTP 下載引導 -> NFS/HTTP 傳輸 OS 映像檔。 | 直接將引導映像檔寫入 `/dev/rshim0/boot` 進行推送 [cite: 20]。 | 下達 Chassis Power On 指令，監控開機 Log [cite: 58]。 |
| **優點** | 產業標準，支援大規模並行部署 [cite: 9]。 | 無需複雜網路設定，可直接存取 DPU 內部。 | 無需安裝程序，僅驗證硬體啟動狀態。 |

---

### 二、 程序細節與技術路徑

#### 1. PXE 網路開機 (標準流程)
這是針對一般機種的自動化核心。
* **流程**：系統透過 BMC 修改 BIOS 開機順序為 PXE [cite: 20] -> 重啟 DUT -> DUT 向 Rack Manager 請求 IP 與引導檔案 [cite: 30] -> 自動安裝腳本執行 [cite: 54]。
* **關鍵點**：依賴 Rack Manager 提供穩定的 DHCP/TFTP 服務 [cite: 30]。

#### 2. rshim 介面 (特定機種)
專為具有 Bluefield DPU 的機種設計 [cite: 20]。
* **流程**：主機 OS 啟動後，識別出 `rshim` 驅動 [cite: 20] -> 測試系統將約 2GB 的映像檔寫入 `/dev/rshim0/boot` -> DPU 內部的 ARM 核心偵測到映像檔並開始安裝。
* **關鍵點**：這是「後門」式安裝，不佔用外部網路頻寬，但需要 Host 端有對應的驅動。

#### 3. BMC Bootup (管理啟動)
這主要用於測試全自動流程中的「開機階段」驗證 [cite: 58]。
* **流程**：不涉及 OS 安裝，而是驗證 BIOS/BMC 刷新後是否能正確進入 OS [cite: 22]。
* **關鍵點**：利用 BMC 讀取 Sensor 數據（溫度、風扇）來判斷開機是否正常 [cite: 28, 56]。

---

### 三、 需要特別注意的事項

#### 1. 網路頻寬與隔離
* **10G 需求**：當 30 組 Rack 同時執行 PXE 安裝時，若 OS 映像檔達 10GB，會造成網路壅塞 [cite: 48, 50]。需確保控制平面到 Rack Manager 具備 10G 以上頻寬 [cite: 48]。
* **實體隔離**：管理網路 (IPMI) 應與資料網路 (PXE/OS 傳輸) 實體隔離，避免大量部署時影響到 BMC 的控制連線 [cite: 40]。

#### 2. 狀態判斷機制 (關鍵字監測)
* **不建議使用時間判定**：每台機器安裝 OS 或開機的速度不同，強行設定「逾時時間」會導致誤判 [cite: 24, 50]。
* **關鍵字偵測**：應透過 Serial Console 監控特定的關鍵字串（如 `Login:` 或 `Installation Complete`）來觸發下一個測試階段 [cite: 58]。

#### 3. 韌體與驅動相容性
* **Checksum 驗證**：傳輸 FW 或 OS 映像檔前，必須比對 SHA-256 Checksum，避免因檔案毀損導致 DUT 變磚 [cite: 22]。
* **rshim 依賴**：執行 `rshim` 部署前，需確認 Host 端的驅動程式版本與 DPU 韌體相容，否則 `/dev/rshim0` 裝置可能無法出現 [cite: 20]。

#### 4. 安全保護機制
* **過熱保護**：無論哪種啟動模式，系統必須在偵測到 CPU 溫度超過閾值（如 95°C）時，由 BMC 直接執行強制斷電，而非等待軟體指令 [cite: 26, 56]。

> [!TIP]
> 針對本專案，建議將 **PXE 與 rshim 邏輯模組化**。在下發測試計畫時，由系統自動根據「機種參數」判斷應走哪一條路徑，並統一將 Log 匯總至 Dashboard 顯示 [cite: 16, 58]。

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

### Phase 3: 測試引擎與自動化邏輯
測試引擎負責執行複雜的邏輯，具備以下工業級特性：
- **自動容錯跳過 (Auto-Skip)**: 子項目測試失敗時自動記錄錯誤並跳過，確保批次測試流程不因單點故障而中斷。
- **完測摘要報告 (Summary Report)**: 測試結束後自動彙整成功率，並條列所有失敗項目名稱。
- **動態熱保護 (Thermal Protection)**: 燒機期間即時監控溫度，達到機種閾值時自動強制中斷。

```bash
# 執行功能測試套件 (使用預設配置，具備自動跳過與報告彙整功能)
python3 -m src.rack_manager.test_task RACK-XXX DUT-01 FUNCTION_TEST

# 執行特定機種的燒機測試 (自動載入 model_pro_server.json)
python3 -m src.rack_manager.test_task RACK-XXX DUT-02 BURN_IN --params model=model_pro_server
```

### Phase 4: 視覺化介面與批次操作工具
本階段提供 Web Dashboard 進行即時監控，以及 CLI 工具進行大規模批次操作。

#### 網頁 Dashboard
![Dashboard Preview](docs/images/dashboard_preview.png)
*圖：AICIPC 視覺化儀表板 - 支援多機架狀態監控與機種自定義測試下發*

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

### Phase 7: 雲端部署指南 | Cloud Deployment Guide
本系統支援 Docker 化部署，可輕易發布至雲端環境（如 Google Cloud Run, AWS, VPS）。

#### 1. 部署控制中心 (Control Plane + Dashboard)
由於 `Dockerfile` 包含前端編譯，您只需部署一個容器即可：
- **Google Cloud Run (推薦)**：
  1. 在 GCP Console 建立 Cloud Run 服務，連結 GitHub 倉庫。
  2. 設定環境變數 `API_KEY` (選填)。
  3. 部署後獲得 HTTPS 網址。
- **自建 VPS (Docker Compose)**：
  ```bash
  docker-compose up -d --build
  ```

#### 2. 設定邊緣代理 (Edge Agent) 連向雲端
當控制中心在雲端運行時，本地或邊緣端的 Agent 需指定連線網址：
```bash
# 設定環境變數並啟動
export CONTROL_PLANE_URL="https://your-cloud-app-url"
python3 -m src.rack_manager.agent
```

#### 3. CLI 工具連接遠端
```bash
export CONTROL_PLANE_URL="https://your-cloud-app-url"
python3 -m src.control_plane.cli list-agents
```

---

## 開發進度 | Development Status

- [x] **Phase 1 (基礎架構)**: 建立控制平面與 Rack Manager 通訊原型。
- [x] **Phase 2 (核心功能)**: 實作 PXE OS 安裝與 BMC FW 更新流程。
- [x] **Phase 3 (測試引擎)**: 整合 Function Test 套件與 Burn-in 壓力設定檔。
- [x] **Phase 4 (介面開發)**: 完成 Web Dashboard 與 Python CLI 工具。
- [x] **Phase 5 (日誌系統)**: 實作邊緣端本地日誌儲存與追蹤。
- [x] **Phase 6 (生產部署)**: 實作資料庫持久化、安全驗證與 Docker 部署。
- [x] **Phase 7 (雲端優化)**: 支援環境變數配置與遠端 URL 自動適應。
- [x] **Phase 8 (自動化回報)**: 實作失敗自動跳過、完測摘要報告與警報通知中心。

---

## 維護與支援 | Support

*   **上線時間**: 2026 年 7 月
*   **支援方式**: 提供操作手冊與現場教學，支援工作日及緊急技術諮詢。
