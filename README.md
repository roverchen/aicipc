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

### 3. 測試引擎 (Test Engine)
*   **功能測試 (Function Test)**：自動執行自定義測試套件。具備 **Auto-Skip** 容錯機制，子項目失敗時自動記錄並跳過，最後匯總 **完測摘要報告**。
*   **燒機測試 (Burn-in Test)**：高負載壓力測試。支援 **每一小時定時回報**，並監控 CPU 溫度。當超過閾值（如 95°C）時，由 BMC 執行 **強制斷電**。

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

## 快速開始與開發階段 | Getting Started & Development Phases

### Phase 1: 基礎環境與服務啟動
1. **安裝依賴**: `pip install fastapi uvicorn httpx pydantic sqlalchemy typer rich`
2. **啟動控制平面 (Server)**: `python3 -m src.control_plane.server`
3. **啟動 Rack Manager Agent (模擬終端)**: `python3 -m src.rack_manager.agent`

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
