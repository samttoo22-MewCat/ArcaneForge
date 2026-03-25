# ArcaneForge AI MUD

> 以 TRPG 精神為核心的多人文字冒險遊戲  
> 玩家帶自己的 LLM Key，AI 擔任地城主（DM），伺服器掌控一切遊戲邏輯。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal.svg)]()
[![FalkorDB](https://img.shields.io/badge/FalkorDB-1.6-red.svg)]()
[![Version](https://img.shields.io/badge/Version-0.1.0--alpha-orange.svg)]()

---

## 三個不妥協的原則

| 原則 | 說明 |
|------|------|
| 🔒 **遊戲邏輯由伺服器掌控** | 誰死、誰贏、誰拿到東西，永遠在伺服器計算，不可被客戶端竄改 |
| 📦 **物品系統固定** | AI DM 無法憑空創造主表以外的物品，所有物品引用都對照白名單驗證 |
| 💳 **玩家自帶 Token** | 伺服器不承擔 LLM 推論費用，玩家自備 API Key 呼叫 DM 模型 |

---

## 現有進度（v0.1.0-alpha）

### ✅ 已完成的模組

#### 後端伺服器（`/server`）

| 模組 | 狀態 | 說明 |
|------|------|------|
| `server/main.py` | ✅ 完成 | FastAPI 應用工廠，lifespan 管理，啟動時自動初始化 Schema、BatchWriter、EventBus |
| `server/config.py` | ✅ 完成 | 集中式設定，含 DM modifier 上限、批次寫入間隔等參數 |
| `server/api/player.py` | ✅ 完成 | **玩家核心 API**：`/create` `/move` `/look` `/say` `/do` `/pickup` `/inventory` |
| `server/api/combat.py` | ✅ 完成 | 戰鬥發起/結算端點 |
| `server/api/grab.py` | ✅ 完成 | 搶奪判定端點，含競爭窗口管理 |
| `server/api/dm.py` | ✅ 完成 | DM 裁決提交端點（Step 6 回傳裁決結果） |
| `server/api/sse.py` | ✅ 完成 | SSE 連線端點 |
| `server/api/health.py` | ✅ 完成 | 健康檢查端點 |
| `server/engine/combat.py` | ✅ 完成 | 充能條系統、回合順序、傷害公式（含 DM modifier 套用） |
| `server/engine/dice.py` | ✅ 完成 | 骰子系統：1d20、傷害隨機係數、速度擾動 |
| `server/engine/grab_contest.py` | ✅ 完成 | 搶奪骰子公式（先手加值 + DM dice_bonus） |
| `server/engine/rules.py` | ✅ 完成 | 規則守門員：移動限制、安全區、行動前置條件驗證 |
| `server/engine/state_machine.py` | ✅ 完成 | 玩家狀態機（一般 / 移動中 / 戰鬥中） |
| `server/engine/status_effects.py` | ✅ 完成 | 5 種狀態異常（燃燒、中毒、暈眩、緩速、流血）的計算邏輯 |
| `server/dm/prompt_builder.py` | ✅ 完成 | 組裝 DM Prompt 封包（上下文嚴格裁切至 ~1500 tokens） |
| `server/dm/signer.py` | ✅ 完成 | HMAC-SHA256 簽署，含 nonce + timestamp 有效期（30 秒） |
| `server/dm/validator.py` | ✅ 完成 | **核心防作弊層**：格式、合法性、邏輯、時效四層驗證；可疑行為旗標追蹤 |
| `server/dm/nonce_store.py` | ✅ 完成 | Redis nonce 儲存（防重放攻擊） |
| `server/dm/schemas.py` | ✅ 完成 | `DMRuling` Pydantic schema |
| `server/db/connection.py` | ✅ 完成 | FalkorDB + Redis 連線管理，含 Docker 自動確認 |
| `server/db/schema.py` | ✅ 完成 | 圖資料庫 Schema 初始化（冪等） |
| `server/db/batch_writer.py` | ✅ 完成 | 非同步批次寫入（每 2 秒 UNWIND 批次，重要事件即時寫入） |
| `server/db/optimistic_lock.py` | ✅ 完成 | 樂觀鎖，解決 `player_ids[]` 高並發競態條件 |
| `server/db/repositories/` | ✅ 完成 | 資料存取層：`player_repo` `place_repo` `item_repo` `npc_repo` |
| `server/broadcast/event_bus.py` | ✅ 完成 | SSE 事件匯流排（房間廣播 / 建築廣播 / 全服廣播） |
| `server/broadcast/event_types.py` | ✅ 完成 | 型別化事件定義（移動、戰鬥、說話、物品、世界變化） |

#### 前端（`/frontend` — React + TypeScript + Vite）

| 元件 | 狀態 | 說明 |
|------|------|------|
| `LoginScreen.tsx` | ✅ 完成 | 玩家登入 / 創建角色 |
| `Header.tsx` | ✅ 完成 | 頂部欄（玩家資訊、伺服器狀態） |
| `MapView.tsx` | ✅ 完成 | 場景描述、出口列表、NPC 清單 |
| `ActionBar.tsx` | ✅ 完成 | 指令輸入列（`/move` `/say` `/do` `/pickup` 等） |
| `EventLog.tsx` | ✅ 完成 | SSE 事件串流顯示（即時接收伺服器廣播） |
| `StatsPanel.tsx` | ✅ 完成 | 戰鬥屬性面板（HP/MP/ATK/DEF/SPD） |
| `BackpackPanel.tsx` | ✅ 完成 | 背包介面 |
| `InventoryPanel.tsx` | ✅ 完成 | 物品詳情 |
| 主題 | ✅ 完成 | 深色生存冒險風格，護林員綠 + 黑暗系調色盤 |

#### 客戶端 SDK（`/client-sdk`）

| 模組 | 狀態 | 說明 |
|------|------|------|
| `dm_caller.py` | ✅ 完成 | 接收伺服器簽署封包 → 呼叫玩家 LLM API → 回傳裁決 |
| `renderer.py` | ✅ 完成 | 接收 SSE 事件 JSON → 呼叫玩家 SLM 轉換為文字描述 |
| `sse_client.py` | ✅ 完成 | SSE 連線管理與事件路由 |
| `schemas.py` | ✅ 完成 | 共用 Pydantic 型別 |

#### 靜態遊戲資料（`/data`）

| 資料 | 狀態 | 說明 |
|------|------|------|
| `items.json` | ✅ 完成 | 10 種物品（武器、防具、消耗品、材料、貨幣） |
| `status_effects.json` | ✅ 完成 | 5 種狀態異常定義 |
| `npc_templates.json` | ✅ 完成 | NPC 模板（怪物、商人、任務 NPC） |
| `world_rules.md` | ✅ 完成 | DM 裁決參考文件（世界觀、裁決準則、屬性克制） |
| `data/seed/` | ✅ 完成 | 種子資料（初始地圖、房間連接） |

#### 驗證測試（`/tests`）

| 驗證程式 | 狀態 | 說明 |
|---------|------|------|
| `V-01` 節點建立與移動 | ✅ 完成 | 圖 Schema 建立、玩家移動查詢延遲、批次寫入吞吐量 |
| `V-02` DM 裁決 Schema | ✅ 完成 | Schema 合法率、邊緣情況拒絕率、HMAC 驗證正確性 |
| `V-03` 搶奪判定 | ✅ 完成 | 2/3 人搶奪公平性統計、競態條件處理 |
| `V-04` 戰鬥回合順序 | ✅ 完成 | 不同速度組合的行動順序分布合理性 |
| `V-05` SSE 廣播 | 🚧 進行中 | 20 連線壓力測試，目標廣播延遲 < 100ms |

---

## 系統架構

```
玩家輸入
  ├─ 標準動作（/move /attack /pickup）
  │     └─→ 規則引擎（無 AI，毫秒級）
  │               └─→ 數據計算層 → 事件廣播（SSE）
  │
  └─ 自由文本動作（/do /say）
        └─→ 伺服器簽署 Prompt 封包
              ├─ 客戶端用玩家 Key 呼叫 DM LLM
              ├─ 回傳裁決結果
              └─→ 伺服器四層驗證
                      ├─ 合法 → 數據計算層 → 事件廣播
                      └─ 非法 → 拒絕並記錄

每個客戶端用自己的 SLM 將數據事件渲染成文字
伺服器只負責廣播結構化 JSON，不生成文字
```

### 技術棧

| 層 | 技術 |
|----|------|
| **後端** | Python 3.11 · FastAPI 0.115 · Uvicorn |
| **圖資料庫** | FalkorDB 1.6（Property Graph） |
| **快取 / Nonce** | Redis 7 |
| **前端** | React 18 · TypeScript · Vite · Tailwind CSS |
| **即時通訊** | SSE（伺服器推播）· HTTP REST（客戶端請求） |
| **安全** | HMAC-SHA256 封包簽署 · Nonce 防重放 · 四層 DM 裁決驗證 |

---

## 快速開始

### 先決條件

- Python 3.11+
- Node.js 18+
- Docker（用於 FalkorDB + Redis）

### 1. 環境設定

```bash
git clone https://github.com/your-org/ArcaneForge.git
cd ArcaneForge

cp .env.example .env
# 編輯 .env，設定 HMAC 私鑰等必要參數
```

### 2. 啟動後端

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 啟動開發伺服器（自動啟動 FalkorDB Docker）
python scripts/run_dev.py
```

伺服器預設在 `http://localhost:8000`，API 文件見 `/docs`。

### 3. 啟動前端

```bash
cd frontend
npm install
npm run dev
```

前端預設在 `http://localhost:5173`。

### 4. 設定 API Key（玩家端）

在前端登入介面設定你的 LLM API Key（OpenAI / Gemini / 其他相容 API）。  
Key 只存在本地客戶端，不會傳送至遊戲伺服器。

---

## 目錄結構

```
ArcaneForge/
├── server/              # 伺服器端（開源）
│   ├── api/             # REST API 端點
│   ├── engine/          # 規則引擎、戰鬥、骰子、狀態機
│   ├── dm/              # Prompt 簽署與裁決驗證
│   ├── broadcast/       # SSE 事件匯流排
│   └── db/              # FalkorDB ORM 層
│       └── repositories/
├── client-sdk/          # 客戶端 SDK（開源）
│   ├── dm_caller.py     # DM LLM 呼叫邏輯
│   ├── renderer.py      # SLM 文字渲染
│   └── sse_client.py    # SSE 事件接收
├── frontend/            # 前端 UI（React + TypeScript）
│   └── src/
│       └── components/  # UI 元件
├── data/                # 靜態遊戲資料（開源）
│   ├── items.json       # 物品主表
│   ├── status_effects.json
│   ├── npc_templates.json
│   ├── world_rules.md   # DM 裁決參考文件
│   └── seed/            # 初始地圖種子資料
└── tests/               # 驗證測試（V-01 ~ V-05）
```

---

## 即將開發的功能

### 🔜 短期（v0.2）

| 功能 | 說明 |
|------|------|
| **NPC 行為樹** | 層級 0：巡邏、攻擊、逃跑的無 AI 行為樹實作 |
| **NPC 休眠機制** | 無玩家區域的 NPC 凍結與延遲演算（重新喚醒時補算經過時間） |
| **DM 介入 NPC** | 層級 1：玩家說服對話觸發 AI 裁決，更新 NPC `memory_summary` |
| **物品製作系統** | 依 `craft_recipe` 合成物品，由規則引擎執行，無需 DM |
| **完整 V-05 壓力測試** | SSE 廣播 20 連線延遲驗證 |
| **更多地圖房間** | 擴充初始種子地圖（目前只有城鎮廣場作為起始點） |

### 📅 中期（v0.3）

| 功能 | 說明 |
|------|------|
| **全局事件系統** | 跨區域的重大世界事件廣播（不依賴 NPC 自主行為） |
| **副本系統** | `is_instanced: true` 的中區域獨立分配給玩家小隊 |
| **抽查機制** | 對旗標玩家用伺服器備用 Key 比對 DM 裁決結果分布 |
| **更多狀態異常** | 魅惑、石化、隱身等進階狀態效果 |
| **屬性克制矩陣** | 完整的元素克制關係資料表與計算整合 |
| **商店 NPC** | 可交易的商人 NPC，固定價格清單 |

### 🚀 長期（v1.0）

| 功能 | 說明 |
|------|------|
| **公會系統** | 玩家組織、共享倉庫 |
| **任務系統** | `quest_giver` NPC 觸發、任務追蹤、獎勵分配 |
| **世界時間軸** | 日夜循環影響 NPC 行為和場景描述 |
| **自架伺服器支援** | 完整私服部署文件 + Docker Compose 一鍵啟動 |
| **非技術玩家友善 UI** | API Key 設定精靈，降低技術門檻 |

---

## 已知限制

| 問題 | 嚴重程度 | 目前處理方式 |
|------|---------|------------|
| 方案 C 無法完全防作弊 | 中 | 四層邏輯驗證 + 可疑行為旗標追蹤 |
| 延遲演算無法處理跨區域 NPC 互動 | 中 | 全局事件系統補充（規劃中） |
| SLM 渲染品質因玩家模型差異而不一致 | 低 | 屬於客戶端自理範疇 |
| 非技術玩家的 API Key 設定門檻 | 中 | 需要完善的文件與 UI 引導 |

---

## 開放原始碼策略

| 項目 | 費用歸屬 |
|------|---------|
| FalkorDB + 遊戲伺服器 | 專案維護者負擔 |
| DM LLM 呼叫 | 玩家自備 API Key |
| SLM 文字渲染 | 玩家自備（API 或本地模型） |
| 客戶端 SDK | 免費開源 |

伺服器端完整開源，社群可自行架設私服。

---

## Contributing

歡迎 PR！開始前請先閱讀 [CONTRIBUTING.md](CONTRIBUTING.md)（待撰寫）。

---

## License

MIT License — 詳見 [LICENSE](LICENSE)。
