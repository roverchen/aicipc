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
| `RACK_ID` | `RACK-XXX` | 機架唯一代號 (Docker 模式下必填) |
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

## 📋 任務參數與串接範例 | Runtime Parameters

### A. OS 安裝 (PXE / rshim / BMC)
範例（rshim/Bluefield）：
```json
{
  "task_id": "task-os-002",
  "action": "OS_INSTALL",
  "params": {
    "model": "bluefield_dpu",
    "rshim": "true",
    "rshim_push_cmd": "cat assets/images/bf-boot.img > /dev/rshim0/boot"
  }
}
```

### B. 韌體更新 (SHA-256 驗證)
範例：
```json
{
  "task_id": "task-fw-001",
  "action": "FW_UPDATE",
  "params": {
    "firmware_path": "assets/firmware/bios_v2.8.1.bin",
    "sha256": "3e7a8b3d1d7ec5b4d8cf2f95e5f8feecf0d7dc0f3a0dca193a9f77b0d4a4d8ee"
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
├── assets/               # 韌體檔與系統鏡像存儲 (firmware/, images/)
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
