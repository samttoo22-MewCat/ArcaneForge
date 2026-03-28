<p align="center">
  <img src="logo.png" alt="ArcaneForge Logo" width="600"/>
</p>

# ArcaneForge AI MUD

> 以 TRPG 精神為核心的多人文字冒險遊戲  
> 玩家帶自己的 LLM Key，AI 擔任地城主（DM），伺服器掌控一切遊戲邏輯。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal.svg)]()
[![FalkorDB](https://img.shields.io/badge/FalkorDB-1.6-red.svg)]()
[![Version](https://img.shields.io/badge/Version-0.2.0--alpha-orange.svg)]()

---

## 三個不妥協的原則

| 原則 | 說明 |
|------|------|
| 🔒 **遊戲邏輯由伺服器掌控** | 誰死、誰贏、誰拿到東西，永遠在伺服器計算，不可被客戶端竄改 |
| 📦 **物品系統固定** | AI DM 無法憑空創造主表以外的物品，所有物品引用都對照白名單驗證 |
| 💳 **玩家自帶 Token** | 伺服器不承擔 LLM 推論費用，玩家自備 API Key 呼叫 DM 模型 |

---

## 現有進度（v0.2.0-alpha）

### ✅ 已完成的模組

#### 後端伺服器（`/server`）

| 模組 | 狀態 | 說明 |
|------|------|------|
| `server/main.py` | ✅ | FastAPI 應用工廠，lifespan 管理，啟動時自動初始化 Schema、BatchWriter、EventBus |
| `server/config.py` | ✅ | 集中式設定，含 DM modifier 上限、批次寫入間隔等參數 |
| `server/api/player.py` | ✅ | **玩家核心 API**：`/create` `/move` `/look` `/say` `/do` `/pickup` `/inventory`；DEFAULT_STATS 已擴充為六維屬性 + level/xp/classes |
| `server/api/npc.py` | ✅ | NPC 互動 API：`/talk`（觸發 DM）、`/say_response`（接收客戶端 LLM 生成的 NPC 回應並廣播） |
| `server/api/combat.py` | ✅ | 戰鬥發起/結算端點 |
| `server/api/grab.py` | ✅ | 搶奪判定端點，含競爭窗口管理 |
| `server/api/dm.py` | ✅ | DM 裁決提交端點（Step 6 回傳裁決結果） |
| `server/api/sse.py` | ✅ | SSE 連線端點 |
| `server/api/health.py` | ✅ | 健康檢查端點 |
| `server/api/auth.py` | ✅ | **OpenRouter OAuth proxy**：`/auth/exchange` 代理 code 換取 API Key，`/auth/revoke` 撤銷授權 |
| `server/api/debug.py` | ✅ | 前端 debug log 轉印至伺服器終端（`/debug/log`） |
| `server/engine/combat.py` | ✅ | 充能條系統、回合順序、傷害公式（含 DM modifier 套用） |
| `server/engine/dice.py` | ✅ | 骰子系統：1d20、傷害隨機係數、速度擾動 |
| `server/engine/grab_contest.py` | ✅ | 搶奪骰子公式（先手加值 + DM dice_bonus） |
| `server/engine/rules.py` | ✅ | 規則守門員：移動限制、安全區、行動前置條件驗證 |
| `server/engine/state_machine.py` | ✅ | 玩家狀態機（一般 / 移動中 / 戰鬥中） |
| `server/engine/status_effects.py` | ✅ | 5 種狀態異常（燃燒、中毒、暈眩、緩速、流血）的計算邏輯 |
| `server/dm/prompt_builder.py` | ✅ | 組裝 DM Prompt 封包（含六維屬性、等級、職業）；上下文嚴格裁切至 ~1500 tokens |
| `server/dm/signer.py` | ✅ | HMAC-SHA256 簽署，含 nonce + timestamp 有效期（30 秒） |
| `server/dm/validator.py` | ✅ | **核心防作弊層**：格式、合法性、邏輯、時效四層驗證；可疑行為旗標追蹤 |
| `server/dm/nonce_store.py` | ✅ | Redis nonce 儲存（防重放攻擊） |
| `server/dm/schemas.py` | ✅ | `DMRuling` Pydantic schema；`relevant_stat` 已擴充為六維屬性 |
| `server/db/connection.py` | ✅ | FalkorDB + Redis 連線管理，含 Docker 自動確認 |
| `server/db/schema.py` | ✅ | 圖資料庫 Schema 初始化（冪等） |
| `server/db/batch_writer.py` | ✅ | 非同步批次寫入（每 2 秒 UNWIND 批次，重要事件即時寫入） |
| `server/db/optimistic_lock.py` | ✅ | 樂觀鎖，解決 `player_ids[]` 高並發競態條件 |
| `server/db/repositories/` | ✅ | 資料存取層：`player_repo` `place_repo` `item_repo` `npc_repo` |
| `server/broadcast/event_bus.py` | ✅ | SSE 事件匯流排（房間廣播 / 建築廣播 / 全服廣播） |
| `server/broadcast/event_types.py` | ✅ | 型別化事件定義（移動、戰鬥、說話、NPC 對話、物品、世界變化） |

#### 前端（`/frontend` — React + TypeScript + Vite）

| 元件 | 狀態 | 說明 |
|------|------|------|
| `LoginScreen.tsx` | ✅ | 玩家登入 / 創建角色；**必須完成 OpenRouter OAuth 授權才能進入世界** |
| `Header.tsx` | ✅ | 頂部欄（玩家名稱、DM Key 指示燈、連線狀態）；已移除 HP/MP 迷你欄 |
| `MapView.tsx` | ✅ | 場景描述、出口列表、NPC 清單 |
| `ActionBar.tsx` | ✅ | 指令輸入列（說話 / 行動 Tab）；已修復「行動」Tab 無法送出的 Bug |
| `EventLog.tsx` | ✅ | SSE 事件串流顯示（即時接收伺服器廣播）；說話事件使用樂觀更新立即顯示 |
| `StatsPanel.tsx` | ✅ | 屬性面板：HP/MP 條、等級/職業、**六維屬性（STR/DEX/INT/感知/CHA/LUK）**；hover 顯示屬性說明 tooltip |
| `DialogueModal.tsx` | ✅ | NPC 對話模態：可自由輸入文字向 NPC 說話，所有在場 NPC 透過客戶端 SLM 生成回應 |
| `BackpackPanel.tsx` | ✅ | 背包介面 |
| `InventoryPanel.tsx` | ✅ | 物品詳情 |
| 主題 | ✅ | 深色生存冒險風格，護林員綠 + 黑暗系調色盤 |

#### 客戶端 DM / SLM 層（`/frontend/src/dm`）

| 模組 | 狀態 | 說明 |
|------|------|------|
| `caller.ts` | ✅ | 接收伺服器簽署封包 → 呼叫玩家 DM LLM（`google/gemini-3.1-flash-lite-preview`） → 回傳裁決 |
| `slm_renderer.ts` | ✅ | SSE 事件 → 玩家 SLM（`google/gemini-3.1-flash-lite-preview`）渲染文字描述；`generateNpcResponse()` 生成 NPC 現場回應 |
| `validator.ts` | ✅ | 客戶端裁決格式驗證 |

#### 靜態遊戲資料（`/data`）

| 資料 | 狀態 | 說明 |
|------|------|------|
| `items.json` | ✅ | 10 種物品（武器、防具、消耗品、材料、貨幣） |
| `status_effects.json` | ✅ | 5 種狀態異常定義 |
| `npc_templates.json` | ✅ | NPC 模板（怪物、商人、任務 NPC） |
| `action_rules.json` | ✅ | 行動類型 → 骰子判定屬性映射（更新為六維屬性） |
| `classes.json` | ✅ | **7 種職業**（戰士/遊俠/法師/聖職者/盜賊/狂戰士/吟遊詩人），支援多職業 |
| `levels.json` | ✅ | **50 級 XP 表**，每升一級 3 屬性點 |
| `skills.json` | ✅ | **16 種技能**（4 通用 + 12 職業專屬），含等級/屬性前置需求 |
| `magic.json` | ✅ | **15 種魔法**（跨法師/聖職者/遊俠/吟遊詩人/狂戰士），含元素 + 狀態效果 |
| `element_matrix.json` | ✅ | 元素克制矩陣 |
| `world_rules.md` | ✅ | DM 裁決參考文件（世界觀、裁決準則、屬性說明） |
| `data/seed/` | ✅ | 種子資料（初始地圖、房間連接） |

#### 驗證測試（`/tests`）

| 驗證程式 | 狀態 | 說明 |
|---------|------|------|
| `V-01` 節點建立與移動 | ✅ | 圖 Schema 建立、玩家移動查詢延遲、批次寫入吞吐量 |
| `V-02` DM 裁決 Schema | ✅ | Schema 合法率、邊緣情況拒絕率、HMAC 驗證正確性 |
| `V-03` 搶奪判定 | ✅ | 2/3 人搶奪公平性統計、競態條件處理 |
| `V-04` 戰鬥回合順序 | ✅ | 不同速度組合的行動順序分布合理性 |
| `V-05` SSE 廣播 | 🚧 進行中 | 20 連線壓力測試，目標廣播延遲 < 100ms |

---

## 系統架構

```
玩家輸入
  ├─ 標準動作（/move /attack /pickup）
  │     └─→ 規則引擎（無 AI，毫秒級）
  │               └─→ 數據計算層 → 事件廣播（SSE）
  │
  ├─ 自由行動（/do）
  │     └─→ 伺服器簽署 Prompt 封包
  │               ├─ 客戶端用玩家 Key 呼叫 DM LLM（Gemini Flash Lite）
  │               ├─ 回傳裁決結果
  │               └─→ 伺服器四層驗證
  │                       ├─ 合法 → 數據計算層 → 事件廣播
  │                       └─ 非法 → 拒絕並記錄
  │
  └─ 說話（/say）
        ├─ 樂觀更新立即顯示文字
        ├─ POST → 伺服器 → 廣播給同房間玩家
        └─ 在場 NPC（最多 3 個）
              └─ 客戶端 SLM（Qwen Flash）生成 NPC 回應
                    └─→ POST /npc/{id}/say_response → 伺服器驗證 → 廣播

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
| **DM 模型** | `google/gemini-3.1-flash-lite-preview`（via OpenRouter，玩家自備 Key） |
| **SLM 模型** | `google/gemini-3.1-flash-lite-preview`（via OpenRouter，玩家自備 Key） |
| **安全** | HMAC-SHA256 封包簽署 · Nonce 防重放 · 四層 DM 裁決驗證 |

---

## 角色成長系統

### 六維屬性

| 屬性 | 定位 | 影響 |
|------|------|------|
| **STR 力量** | 物理攻擊與蠻力 | 近戰傷害、破門、壓制判定 |
| **DEX 敏捷** | 速度與精準 | 潛行、遠程精準、先手順序、閃躲 |
| **INT 智力** | 奧術學識與邏輯 | 法術傷害、鑑識物品、破解機關謎題 |
| **WIS 感知** | 直覺感知與靈性 | 神聖/治癒魔法、偵測陷阱、洞察 NPC 意圖、抗精神操控 |
| **CHA 魅力** | 社交與領袖氣場 | 說服/威脅/賄賂判定、NPC 初始好感度 |
| **LUK 幸運** | 命運之力 | 暴擊率、稀有掉落、偶發事件結果 |

### 職業（7 種，支援多職業）

戰士 · 遊俠 · 法師 · 聖職者 · 盜賊 · 狂戰士 · 吟遊詩人

### 技能（16 種）

4 種通用技能（無職業限制）+ 12 種職業專屬技能，含等級/屬性前置需求。

### 魔法（15 種）

跨五個職業的魔法，含元素（火/冰/雷/神聖/黑暗）分類及狀態效果觸發。

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

伺服器預設在 `http://localhost:3031`，API 文件見 `/docs`。

### 3. 啟動前端

```bash
cd frontend
npm install
npm run dev
```

前端預設在 `http://localhost:5173`。

### 4. 登入並授權（玩家端）

在前端登入介面輸入玩家 ID，點擊「**使用 OpenRouter 帳號授權**」完成 OAuth 登入。
API Key 透過 OAuth 取得後只存在本地客戶端，不會傳送至遊戲伺服器。

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
├── frontend/            # 前端 UI（React + TypeScript）
│   └── src/
│       ├── components/  # UI 元件
│       └── dm/          # 客戶端 DM/SLM 呼叫層
├── data/                # 靜態遊戲資料（開源）
│   ├── items.json
│   ├── classes.json     # 7 種職業
│   ├── levels.json      # 50 級 XP 表
│   ├── skills.json      # 16 種技能
│   ├── magic.json       # 15 種魔法
│   ├── action_rules.json
│   ├── status_effects.json
│   ├── npc_templates.json
│   ├── element_matrix.json
│   ├── world_rules.md
│   └── seed/            # 初始地圖種子資料
└── tests/               # 驗證測試（V-01 ~ V-05）
```

---

## 即將開發的功能

### 🔜 短期（v0.3）

| 功能 | 說明 |
|------|------|
| **技能/魔法使用系統** | 玩家施放技能/魔法的 API + 前端 UI（施放面板、前置條件驗證） |
| **升級與屬性分配** | 升級後分配 stat_points 的前端介面 |
| **NPC 行為樹** | 層級 0：巡邏、攻擊、逃跑的無 AI 行為樹實作 |
| **NPC 休眠機制** | 無玩家區域的 NPC 凍結與延遲演算 |
| **物品製作系統** | 依 `craft_recipe` 合成物品，由規則引擎執行 |
| **完整 V-05 壓力測試** | SSE 廣播 20 連線延遲驗證 |
| **更多地圖房間** | 擴充初始種子地圖 |

### 📅 中期（v0.4）

| 功能 | 說明 |
|------|------|
| **DM 介入 NPC** | 玩家說服對話觸發 AI 裁決，更新 NPC `memory_summary` |
| **副本系統** | `is_instanced: true` 的區域獨立分配給玩家小隊 |
| **抽查機制** | 對旗標玩家用伺服器備用 Key 比對 DM 裁決結果分布 |
| **更多狀態異常** | 魅惑、石化、隱身等進階狀態效果 |
| **商店 NPC** | 可交易的商人 NPC，固定價格清單 |

### 🚀 長期（v1.0）

| 功能 | 說明 |
|------|------|
| **公會系統** | 玩家組織、共享倉庫 |
| **任務系統** | `quest_giver` NPC 觸發、任務追蹤、獎勵分配 |
| **世界時間軸** | 日夜循環影響 NPC 行為和場景描述 |
| **自架伺服器支援** | 完整私服部署文件 + Docker Compose 一鍵啟動 |
| **非技術玩家友善 UI** | ~~API Key 設定精靈~~ 已完成 OpenRouter OAuth 授權流程 ✅ |

---

## 已知限制

| 問題 | 嚴重程度 | 目前處理方式 |
|------|---------|------------|
| 方案 C 無法完全防作弊 | 中 | 四層邏輯驗證 + 可疑行為旗標追蹤 |
| 延遲演算無法處理跨區域 NPC 互動 | 中 | 全局事件系統補充（規劃中） |
| SLM 渲染品質因玩家模型差異而不一致 | 低 | 屬於客戶端自理範疇 |
| 非技術玩家的 API Key 設定門檻 | 低 | 已改為 OpenRouter OAuth 一鍵授權，無需手動貼 Key |

---

## 開放原始碼策略

| 項目 | 費用歸屬 |
|------|---------|
| FalkorDB + 遊戲伺服器 | 專案維護者負擔 |
| DM LLM 呼叫 | 玩家自備 API Key |
| SLM 文字渲染 | 玩家自備（API 或本地模型） |
| 客戶端前端 | 免費開源 |

伺服器端完整開源，社群可自行架設私服。

---

## Contributing

歡迎 PR！開始前請先閱讀 [CONTRIBUTING.md](CONTRIBUTING.md)（待撰寫）。

---

## License

MIT License — 詳見 [LICENSE](LICENSE)。
