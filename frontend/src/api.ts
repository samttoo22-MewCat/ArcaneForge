import type { DMPromptPacket, DMRulingSubmission } from "./dm/schema";
import type { AbilitiesData, CraftableData, LookResult, Player, ShopData, UseSkillResult } from "./types";
import type { MemoryContext } from "./dm/slm_renderer";

const BASE = "/api/v1";

// Global API key (set on login, used for DM ruling requests)
let _llmKey = "";
export function setLlmKey(key: string) { _llmKey = key; }
export function getLlmKey() { return _llmKey; }

// Server-side debug logger — prints to the Python terminal instead of DevTools
export function serverLog(message: string, level: "debug" | "warn" | "error" = "debug") {
  fetch(`${BASE}/debug/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ level, message }),
  }).catch(() => {/* fire-and-forget */});
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (_llmKey) headers["X-LLM-Key"] = _llmKey;

  const res = await fetch(BASE + path, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    console.error(`[api] ${init?.method ?? "GET"} ${BASE + path} → ${res.status}`, text);
    if (res.status === 429) {
      const retryAfter = res.headers.get("Retry-After");
      const hint = retryAfter ? `（${retryAfter} 秒後重試）` : "";
      throw new Error(`429: 請求過於頻繁，請稍後再試。${hint}`);
    }
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  getPlayer: (id: string) =>
    json<Player>(`/player/${id}`),

  createPlayer: (playerId: string, classId: string, name?: string) =>
    json<{ created: boolean; player_id: string; spawn?: string }>(
      "/player/create",
      { method: "POST", body: JSON.stringify({ player_id: playerId, class_id: classId, name: name || playerId }) }
    ),

  look: (playerId: string) =>
    json<LookResult>(`/player/look?player_id=${playerId}`),

  move: (playerId: string, direction: string) =>
    json<{ success: boolean; travel_time?: number; transition_description?: string }>(
      "/player/move",
      { method: "POST", body: JSON.stringify({ player_id: playerId, direction }) }
    ),

  say: (playerId: string, message: string) =>
    json<{ success: boolean }>(
      "/player/say",
      { method: "POST", body: JSON.stringify({ player_id: playerId, message }) }
    ),

  doAction: (playerId: string, action: string) =>
    json<{ dm_packet: DMPromptPacket; requires_ruling: true } | { requires_ruling: false; message?: string }>(
      "/player/do",
      { method: "POST", body: JSON.stringify({ player_id: playerId, action }) }
    ),

  submitRuling: (sub: DMRulingSubmission) =>
    json<{
      success: boolean;
      feasible: boolean;
      tier?: string;
      raw_roll?: number;
      final_roll?: number;
      threshold?: number;
      effect_type?: string;
      modifier?: number;
      narrative_hint?: string;
      status_applied?: string | null;
    }>("/dm/ruling", { method: "POST", body: JSON.stringify(sub) }),

  pickup: (playerId: string, itemInstanceId: string) =>
    json<{ success: boolean }>(
      "/player/pickup",
      { method: "POST", body: JSON.stringify({ player_id: playerId, item_instance_id: itemInstanceId }) }
    ),

  talkToNpc: (playerId: string, npcId: string) =>
    json<{ dialogue: string; opens_shop: boolean; npc_id: string; npc_name: string; npc_type: string }>(
      `/npc/${npcId}/talk`,
      { method: "POST", body: JSON.stringify({ player_id: playerId }) }
    ),

  getNpcShop: (npcId: string) =>
    json<ShopData>(`/npc/${npcId}/shop`),

  getInventory: (playerId: string) =>
    json<{ items: Array<{ instance_id: string; item_id: string; name: string; description: string; category: string; quantity: number; durability: number; weight: number }> }>(
      `/player/${playerId}/inventory`
    ),

  buyItem: (playerId: string, npcId: string, itemId: string, quantity: number) =>
    json<{ success: boolean; cost?: number }>(
      "/player/buy",
      { method: "POST", body: JSON.stringify({ player_id: playerId, npc_id: npcId, item_id: itemId, quantity }) }
    ),

  npcSayResponse: (npcId: string, playerId: string, line: string) =>
    json<{ success: boolean }>(
      `/npc/${npcId}/say_response`,
      { method: "POST", body: JSON.stringify({ player_id: playerId, line }) }
    ),

  sellItem: (playerId: string, npcId: string, itemInstanceId: string) =>
    json<{ success: boolean; received_coins?: number }>(
      "/player/sell",
      { method: "POST", body: JSON.stringify({ player_id: playerId, npc_id: npcId, item_instance_id: itemInstanceId }) }
    ),

  getCraftable: (playerId: string) =>
    json<CraftableData>(`/player/${playerId}/craftable`),

  craftItem: (playerId: string, itemId: string) =>
    json<{ success: boolean; crafted: string; instance_id: string }>(
      "/player/craft",
      { method: "POST", body: JSON.stringify({ player_id: playerId, item_id: itemId }) }
    ),

  getAbilities: (playerId: string) =>
    json<AbilitiesData>(`/player/${playerId}/abilities`),

  useSkill: (
    playerId: string,
    abilityId: string,
    abilityType: "skill" | "spell",
    targetId?: string,
  ) =>
    json<UseSkillResult>("/player/use_skill", {
      method: "POST",
      body: JSON.stringify({
        player_id: playerId,
        ability_id: abilityId,
        ability_type: abilityType,
        target_id: targetId ?? null,
      }),
    }),

  allocateStat: (playerId: string, stat: string) =>
    json<{ success: boolean; stat: string; new_value: number; stat_points: number }>(
      "/player/allocate_stat",
      { method: "POST", body: JSON.stringify({ player_id: playerId, stat }) }
    ),

  // ── NPC Persuasion ──────────────────────────────────────────────────────────

  getNpcPersuasionPacket: (npcId: string, playerId: string, playerMessage: string, intent: string) =>
    json<{ dm_packet: import("./dm/schema").DMPromptPacket; npc_name: string; intent: string }>(
      `/npc/${npcId}/persuade`,
      { method: "POST", body: JSON.stringify({ player_id: playerId, player_message: playerMessage, intent }) }
    ),

  submitNpcPersuasionResult: (npcId: string, req: {
    player_id: string;
    nonce: string;
    timestamp: number;
    session_id: string;
    signature: string;
    ruling: unknown;
  }) =>
    json<{ success: boolean; feasible: boolean; tier?: string; disposition?: number; narrative?: string }>(
      `/npc/${npcId}/persuasion_result`,
      { method: "POST", body: JSON.stringify(req) }
    ),

  // ── NPC Memory ──────────────────────────────────────────────────────────────

  getNpcMemory: (npcId: string, playerId: string) =>
    json<MemoryContext & { interaction_count: number; tags: string[] }>(
      `/npc/${npcId}/memory?player_id=${encodeURIComponent(playerId)}`
    ),

  addNpcRound: (npcId: string, playerId: string, compressedRound: string) =>
    json<{ overflow: boolean; rounds_for_summary: string[] }>(
      `/npc/${npcId}/memory/add_round`,
      { method: "POST", body: JSON.stringify({ player_id: playerId, compressed_round: compressedRound }) }
    ),

  updateNpcSummary: (npcId: string, playerId: string, newSummary: string) =>
    json<{ success: boolean }>(
      `/npc/${npcId}/memory/update_summary`,
      { method: "POST", body: JSON.stringify({ player_id: playerId, new_summary: newSummary }) }
    ),
};
