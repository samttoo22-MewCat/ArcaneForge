import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { api, getLlmKey, setLlmKey } from "./api";
import { callDM, DmTimeoutError } from "./dm/caller";
import { renderNarrative, generateNpcResponse } from "./dm/slm_renderer";
import type { DMRulingAppliedEvent } from "./dm/schema";
import { ActionBar } from "./components/ActionBar";
import { EventLog } from "./components/EventLog";
import { Header } from "./components/Header";
import { InventoryPanel } from "./components/InventoryPanel";
import { LoginScreen } from "./components/LoginScreen";
import { MapView } from "./components/MapView";
import { StatsPanel } from "./components/StatsPanel";
import { useSSE } from "./hooks/useSSE";
import { BackpackPanel } from "./components/BackpackPanel";
import { DialogueModal } from "./components/DialogueModal";
import { ShopPanel } from "./components/ShopPanel";
import type { GameEvent, GameState, LookResult, Player } from "./types";

// ─── State / Reducer ──────────────────────────────────────────────────────────

type Action =
  | { type: "SET_PLAYER"; player: Player }
  | { type: "SET_LOOK"; look: LookResult }
  | { type: "APPEND_EVENT"; event: GameEvent }
  | { type: "UPDATE_EVENT"; id: string; updates: Partial<GameEvent> }
  | { type: "SET_CONNECTED"; connected: boolean }
  | { type: "UPDATE_TRAVEL"; is_traveling: boolean; travel_arrives_at?: number; travel_destination_id?: string };

const MAX_EVENTS = 200;

function reducer(state: GameState, action: Action): GameState {
  switch (action.type) {
    case "SET_PLAYER":
      return { ...state, player: action.player };
    case "SET_LOOK":
      return { ...state, look: action.look };
    case "APPEND_EVENT":
      return {
        ...state,
        events: [...state.events.slice(-MAX_EVENTS + 1), action.event],
      };
    case "UPDATE_EVENT":
      return {
        ...state,
        events: state.events.map(e => e.id === action.id ? { ...e, ...action.updates } : e),
      };
    case "SET_CONNECTED":
      return { ...state, connected: action.connected };
    case "UPDATE_TRAVEL":
      if (!state.player) return state;
      return {
        ...state,
        player: {
          ...state.player,
          is_traveling: action.is_traveling,
          travel_arrives_at: action.travel_arrives_at,
          travel_destination_id: action.travel_destination_id,
        },
      };
    default:
      return state;
  }
}

const INITIAL: GameState = { player: null, look: null, events: [], connected: false };

// ─── Game HUD ─────────────────────────────────────────────────────────────────

function GameHUD({ playerId, onLogout }: { playerId: string; onLogout: () => void }) {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [backpackOpen, setBackpackOpen] = useState(false);
  const [dialogueState, setDialogueState] = useState<{
    npcId: string; npcName: string; npcType: string;
    dialogue: string; opensShop: boolean;
  } | null>(null);
  const [shopState, setShopState] = useState<{ npcId: string; npcName: string } | null>(null);
  const lookPending = useRef(false);

  // ── Data fetching ──
  async function refreshPlayer() {
    try {
      let player = await api.getPlayer(playerId).catch(async (err: Error) => {
        if (err.message.includes("404") || err.message.includes("Not Found")) {
          // Auto-create player with default stats
          await api.createPlayer(playerId);
          return api.getPlayer(playerId);
        }
        throw err;
      });
      const raw = player as unknown as Record<string, unknown>;
      const p = {
        ...player,
        max_hp: (raw.max_hp as number | undefined) ?? player.hp,
        max_mp: (raw.max_mp as number | undefined) ?? (player.mp ?? 0),
        mp: player.mp ?? 0,
      };
      dispatch({ type: "SET_PLAYER", player: p as Player });
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "無法連線到伺服器");
    }
  }

  async function refreshLook(force = false) {
    if (!force && lookPending.current) return;
    lookPending.current = true;
    try {
      const look = await api.look(playerId);
      dispatch({ type: "SET_LOOK", look });
      setLoadError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "無法連線到伺服器";
      const isPlaceNotFound = msg.includes("404") || msg.includes("Not Found");
      setLoadError(
        isPlaceNotFound
          ? "世界資料不存在。請在後端執行：\npython data/seed/world_seed.py"
          : msg
      );
    } finally {
      lookPending.current = false;
    }
  }

  // Initial load
  useEffect(() => {
    refreshPlayer();
    refreshLook();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerId]);

  // ── SSE ──
  const handleEvent = useCallback((event: GameEvent) => {
    dispatch({ type: "APPEND_EVENT", event });

    const d = event as Record<string, unknown>;

    if (event.event_type === "player_traveling" && d.player_id === playerId) {
      dispatch({
        type: "UPDATE_TRAVEL",
        is_traveling: true,
        travel_arrives_at: d.arrives_at as number,
        travel_destination_id: d.to_place_id as string,
      });
    }

    if (event.event_type === "player_arrived" && d.player_id === playerId) {
      dispatch({ type: "UPDATE_TRAVEL", is_traveling: false });
      refreshPlayer();
      refreshLook(true); // force=true: 抵達時一定要更新，不受 lookPending 阻擋
    }

    // Refresh look when someone else moves into/out of our room
    if (
      (event.event_type === "player_arrived" || event.event_type === "player_traveling") &&
      d.player_id !== playerId
    ) {
      refreshLook();
    }

    if (event.event_type === "world_state_change") {
      refreshLook();
    }

    // Refresh look when an NPC moves into/out of our room
    if (event.event_type === "npc_moved") {
      refreshLook();
    }

    // ── DM ruling applied ───────────────────────────────────────────────────
    if (event.event_type === "dm_ruling_applied") {
      const e = event as Record<string, unknown>;
      const TIER_LABELS: Record<string, string> = {
        large_success: "大成功", medium_success: "中等成功", small_success: "小成功",
        small_failure: "小失敗", medium_failure: "中等失敗", large_failure: "大失敗",
      };
      const tier = (e.tier as string) ?? "";
      const tierLabel = TIER_LABELS[tier] ?? tier;
      const isMine = e.player_id === playerId;
      const hint = (e.narrative_hint as string) ?? "";

      if (!e.feasible) {
        dispatch({ type: "APPEND_EVENT", event: {
          ...event,
          id: event.id ?? `dm-infeasible-${Date.now()}`,
          message: `⚔ 行動不可行：${hint}`,
        }});
        return;
      }

      const rawRoll = (e.raw_roll as number) ?? 0;
      const finalRoll = (e.final_roll as number) ?? 0;
      const threshold = (e.threshold as number) ?? 0;
      const whoPrefix = isMine ? "你的行動" : `${e.player_id} 的行動`;
      const rollLine = `[${tierLabel}] 擲骰 ${rawRoll} + 屬性 = ${finalRoll}，門檻 ${threshold}`;
      const rulingEventId = `dm-result-${Date.now()}`;

      dispatch({ type: "APPEND_EVENT", event: {
        id: rulingEventId,
        event_type: "dm_ruling_applied",
        timestamp: event.timestamp,
        message: `${whoPrefix} — ${rollLine}\n${hint}`,
      }});

      // Refresh player HP/status after ruling
      if (isMine) refreshPlayer();

      // Async SLM render — upgrades narrative_hint to a full rendered narration
      const key = getLlmKey();
      if (key && hint) {
        renderNarrative(event as unknown as DMRulingAppliedEvent, key).then(rendered => {
          if (rendered && rendered !== hint) {
            dispatch({ type: "UPDATE_EVENT", id: rulingEventId, updates: {
              message: `${whoPrefix} — ${rollLine}\n\n${rendered}`,
            }});
          }
        });
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerId]);

  const handleConnected = useCallback((connected: boolean) => {
    dispatch({ type: "SET_CONNECTED", connected });
  }, []);

  useSSE({ playerId, onEvent: handleEvent, onConnected: handleConnected });

  // ── Actions ──
  async function handleMove(direction: string) {
    if (!state.player || state.player.is_traveling) return;
    try {
      await api.move(playerId, direction);
      refreshLook(); // immediately show destination room during travel
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      dispatch({
        type: "APPEND_EVENT",
        event: {
          id: `err-${Date.now()}`,
          event_type: "system_announcement",
          timestamp: Date.now() / 1000,
          message: `Cannot move: ${msg}`,
        },
      });
    }
  }

  async function handleSay(message: string) {
    dispatch({ type: "APPEND_EVENT", event: {
      id: `said-local-${Date.now()}`,
      event_type: "player_said",
      timestamp: Date.now() / 1000,
      player_name: state.player?.name ?? playerId,
      message,
    }});
    try {
      await api.say(playerId, message);
    } catch { /* silent */ }

    // NPC responses — each NPC in the room reacts asynchronously
    const key = getLlmKey();
    if (!key) return;
    const aliveNpcs = (state.look?.npcs ?? [])
      .filter(n => n.behavior_state !== "dead")
      .slice(0, 3); // cap at 3 concurrent calls
    const playerName = state.player?.name ?? playerId;
    for (const npc of aliveNpcs) {
      generateNpcResponse(npc.name, npc.npc_type ?? "monster", npc.behavior_state ?? "idle", playerName, message, key)
        .then(line => {
          if (!line) return;
          api.npcSayResponse(npc.id, playerId, line).catch(() => {/* silent */});
        });
    }
  }

  async function handleDo(action: string) {
    const key = getLlmKey();
    if (!key) {
      dispatch({ type: "APPEND_EVENT", event: {
        id: `dm-nokey-${Date.now()}`,
        event_type: "system_announcement",
        timestamp: Date.now() / 1000,
        message: "請先在登入頁設定 API Key 才能使用自由行動（/do）。",
      }});
      return;
    }

    const thinkingId = `dm-thinking-${Date.now()}`;
    dispatch({ type: "APPEND_EVENT", event: {
      id: thinkingId,
      event_type: "system_announcement",
      timestamp: Date.now() / 1000,
      message: "⟳ DM 裁決中...",
    }});

    try {
      const result = await api.doAction(playerId, action);
      if (!result.requires_ruling) {
        // Chat / zero-cost path — server already broadcast the speech event
        dispatch({ type: "UPDATE_EVENT", id: thinkingId, updates: { message: "" } });
        // Remove the thinking placeholder entirely by zeroing the message (SSE player_said will show it)
        return;
      }
      const { dm_packet } = result;
      const ruling = await callDM(dm_packet, key);
      await api.submitRuling({
        nonce: dm_packet.nonce,
        timestamp: dm_packet.timestamp,
        session_id: dm_packet.session_id,
        signature: dm_packet.signature,
        ruling,
      });
      // Result arrives via SSE dm_ruling_applied; remove the thinking placeholder
      dispatch({ type: "UPDATE_EVENT", id: thinkingId, updates: { message: "✓ 裁決送出，等待結果..." } });
    } catch (err) {
      const msg = err instanceof DmTimeoutError
        ? err.message
        : err instanceof Error ? err.message : String(err);
      dispatch({ type: "UPDATE_EVENT", id: thinkingId, updates: { message: `✗ ${msg}` } });
    }
  }

  async function handlePickup(instanceId: string) {
    try {
      await api.pickup(playerId, instanceId);
      refreshLook();
      refreshPlayer();
    } catch { /* silent */ }
  }

  async function handleTalkToNpc(npcId: string, npcName: string, npcType: string) {
    try {
      const result = await api.talkToNpc(playerId, npcId);
      setDialogueState({
        npcId,
        npcName: result.npc_name || npcName,
        npcType: result.npc_type || npcType,
        dialogue: result.dialogue,
        opensShop: result.opens_shop,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      dispatch({
        type: "APPEND_EVENT",
        event: {
          id: `err-${Date.now()}`,
          event_type: "system_announcement",
          timestamp: Date.now() / 1000,
          message: `無法對話：${msg}`,
        },
      });
    }
  }

  // ── Render ──
  const { player, look, events, connected } = state;

  if (!player || !look) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center">
        <div className="text-center space-y-4 max-w-sm px-4">
          {loadError ? (
            <>
              <svg viewBox="0 0 48 48" className="w-10 h-10 mx-auto" fill="none">
                <circle cx="24" cy="24" r="20" stroke="#C83838" strokeWidth="1.5"/>
                <line x1="24" y1="14" x2="24" y2="27" stroke="#C83838" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="24" cy="33" r="1.5" fill="#C83838"/>
              </svg>
              <p className="font-cinzel text-sm text-stone-100">連線失敗</p>
              <p className="font-mono text-xs text-stone-400 break-all">{loadError}</p>
              <p className="font-mono text-xs text-stone-500 leading-relaxed">
                請確認後端伺服器已啟動：<br/>
                <span className="text-gold">python scripts/run_dev.py</span>
              </p>
              <button
                onClick={() => { setLoadError(null); refreshPlayer(); refreshLook(); }}
                className="mt-2 px-5 py-2 font-cinzel text-xs tracking-widest uppercase rounded border border-gold/40 bg-gold/10 text-gold-light hover:bg-gold/20 cursor-pointer transition-colors"
              >
                重試
              </button>
              <button onClick={onLogout} className="block mx-auto font-mono text-xs text-stone-600 hover:text-stone-400 cursor-pointer transition-colors mt-1">
                返回登入
              </button>
            </>
          ) : (
            <>
              <div className="inline-block animate-spin w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full"/>
              <p className="font-cinzel text-xs tracking-widest text-stone-400 uppercase">Loading realm...</p>
            </>
          )}
        </div>
      </div>
    );
  }

  const isTraveling = player.is_traveling;

  return (
    <>
      <div className="flex flex-col h-screen bg-void overflow-hidden">
        <Header player={player} connected={connected} onLogout={onLogout}/>

        <div className="flex flex-1 min-h-0">
          <StatsPanel player={player}/>

          <div className="flex flex-col flex-1 min-w-0">
            {/* 上方：地圖 + 房間物品/在場者 + 事件日誌 並排 */}
            <div className="flex flex-1 min-h-0">
              <MapView look={look} onMove={handleMove} moving={isTraveling}/>
              <InventoryPanel
                items={look.items}
                npcs={look.npcs}
                onPickup={handlePickup}
                onTalkToNpc={handleTalkToNpc}
                disabled={isTraveling}
              />
              <EventLog events={events}/>
            </div>

            <ActionBar
              exits={look.exits}
              onMove={handleMove}
              onSay={handleSay}
              onDo={handleDo}
              onLook={refreshLook}
              onBackpack={() => setBackpackOpen(true)}
              disabled={isTraveling}
            />
          </div>
        </div>
      </div>

      <BackpackPanel
        playerId={player.id}
        open={backpackOpen}
        onClose={() => setBackpackOpen(false)}
      />

      {dialogueState && (
        <DialogueModal
          npcId={dialogueState.npcId}
          npcName={dialogueState.npcName}
          npcType={dialogueState.npcType}
          dialogue={dialogueState.dialogue}
          opensShop={dialogueState.opensShop}
          onOpenShop={() => {
            setShopState({ npcId: dialogueState.npcId, npcName: dialogueState.npcName });
            setDialogueState(null);
          }}
          onClose={() => setDialogueState(null)}
          onSay={handleSay}
        />
      )}

      {shopState && (
        <ShopPanel
          playerId={player.id}
          npcId={shopState.npcId}
          npcName={shopState.npcName}
          open={!!shopState}
          onClose={() => setShopState(null)}
        />
      )}
    </>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────

export default function App() {
  // Player ID: check localStorage first, then sessionStorage.
  // JSON.parse handles old entries that were stored with JSON.stringify (e.g. `"mewcat"` → `mewcat`).
  const [playerId, setPlayerId] = useState<string | null>(() => {
    const raw = localStorage.getItem("arcaneforge_player") ?? sessionStorage.getItem("arcaneforge_player_session");
    if (!raw) return null;
    try { const p = JSON.parse(raw); return typeof p === "string" ? p : raw; } catch { return raw; }
  });

  // API key always lives in localStorage (not sensitive enough to clear on tab close)
  const [apiKey, setApiKey] = useLocalStorage<string>("arcaneforge_llm_key", "");

  useEffect(() => {
    if (apiKey) setLlmKey(apiKey);
  }, [apiKey]);

  function handleLogin(id: string, key: string, remember: boolean) {
    if (remember) {
      localStorage.setItem("arcaneforge_player", id);
      sessionStorage.removeItem("arcaneforge_player_session");
    } else {
      sessionStorage.setItem("arcaneforge_player_session", id);
      localStorage.removeItem("arcaneforge_player");
    }
    setPlayerId(id);
    setApiKey(key);
    setLlmKey(key);
  }

  function handleLogout() {
    localStorage.removeItem("arcaneforge_player");
    sessionStorage.removeItem("arcaneforge_player_session");
    setPlayerId(null);
  }

  if (!playerId) {
    return <LoginScreen onLogin={handleLogin}/>;
  }

  return <GameHUD playerId={playerId} onLogout={handleLogout}/>;
}



function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [val, setVal] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored ? (JSON.parse(stored) as T) : initial;
    } catch {
      return initial;
    }
  });

  function set(v: T) {
    setVal(v);
    try {
      if (v === null || v === undefined) {
        localStorage.removeItem(key);
      } else {
        localStorage.setItem(key, JSON.stringify(v));
      }
    } catch { /* storage full */ }
  }

  return [val, set];
}
