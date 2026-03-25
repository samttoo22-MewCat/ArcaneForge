import type { LookResult, Player } from "./types";

const BASE = "/api/v1";

// Global API key (set on login, used for DM ruling requests)
let _llmKey = "";
export function setLlmKey(key: string) { _llmKey = key; }
export function getLlmKey() { return _llmKey; }

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
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  getPlayer: (id: string) =>
    json<Player>(`/player/${id}`),

  createPlayer: (playerId: string, name?: string) =>
    json<{ created: boolean; player_id: string; spawn?: string }>(
      "/player/create",
      { method: "POST", body: JSON.stringify({ player_id: playerId, name: name || playerId }) }
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
    json<{ success: boolean; nonce?: string; signed_packet?: unknown }>(
      "/player/do",
      { method: "POST", body: JSON.stringify({ player_id: playerId, action }) }
    ),

  pickup: (playerId: string, itemInstanceId: string) =>
    json<{ success: boolean }>(
      "/player/pickup",
      { method: "POST", body: JSON.stringify({ player_id: playerId, item_instance_id: itemInstanceId }) }
    ),
};
