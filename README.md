# 工業電腦自動化測試系統 (AICPIC - Automated Industrial Computer Platform Integration Control)

[![Project Status: Active](https://img.shields.io/badge/Project%20Status-Active-brightgreen.svg)](https://github.com/roverchen/aicpic)
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

## 快速開始 | Quick Start (Prototype Phase 1)

### 依賴安裝
```bash
pip install fastapi uvicorn httpx pydantic
```

### 啟動服務
1. **啟動控制平面 (Server)**:
   ```bash
   python3 -m src.control_plane.server
   ```
2. **啟動 Rack Manager Agent (模擬終端)**:
   ```bash
   python3 -m src.rack_manager.agent
   ```

### 任務測試 (Phase 2)
在啟動 Server 與 Agent 後，可使用測試腳本下發任務：
```bash
# 下發 OS 安裝任務 (請根據 Agent 日誌更換 RACK_ID)
python3 -m src.rack_manager.test_task RACK-XXX DUT-01 OS_INSTALL

# 下發韌體更新任務
python3 -m src.rack_manager.test_task RACK-XXX DUT-02 FW_UPDATE

### 測試引擎驗證 (Phase 3)
可以模擬功能測試與帶有熱保護機制的燒機測試：
```bash
# 執行功能測試套件 (CPU, Memory, Network, BMC)
python3 -m src.rack_manager.test_task RACK-XXX DUT-01 FUNCTION_TEST

# 執行標準燒機測試 (包含每小時進度回報)
python3 -m src.rack_manager.test_task RACK-XXX DUT-02 BURN_IN

# 模擬高溫自動中止 (熱保護機制驗證)
python3 -m src.rack_manager.test_task RACK-XXX DUT-03 BURN_IN --overheat
```
```

### 介面與批次操作 (Phase 4)
#### 網頁 Dashboard
1. 進入 `frontend` 目錄並啟動開發伺服器：
   ```bash
   cd frontend
   npm run dev
   ```
2. 開啟瀏覽器訪問預設位址 (通常為 `http://localhost:5173`)。

#### Python CLI 工具
提供強大的命令列批次操作功能：
```bash
# 列出所有在線的 Rack 狀態
python3 -m src.control_plane.cli list-agents

# 下發並監控任務進度
python3 -m src.control_plane.cli deploy RACK-XXX --action OS_INSTALL
```

### 生產環境部署 (Phase 5)
系統已支援資料庫持久化與 Docker 容器化部署。
#### 使用 Docker Compose 啟動全系統
```bash
# 構建並啟動控制平面與 3 組模擬 Agent
docker-compose up --build
```
*   **控制平面**: 存取 `http://localhost:8000` 即可看到整合後的儀表板。
*   **持久化**: 資料庫檔案 `aicpic.db` 會掛載於主機，確保數據在容器重啟後保留。
*   **安全性**: 系統通訊受 `X-API-KEY` 保護。

---

## 專案結構 | Project Structure

```text
aicpic/
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

## 開發技術棧 | Tech Stack (Planned)

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
- [x] **Phase 5 (分階段部署)**: 實作資料庫持久化、安全驗證與 Docker 部署。

---

## 維護與支援 | Support

*   **上線時間**: 2026 年 7 月
*   **支援方式**: 提供操作手冊與現場教學，支援工作日及緊急技術諮詢。
