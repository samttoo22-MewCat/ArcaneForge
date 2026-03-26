/**
 * SLM Renderer — client-side narrative renderer.
 * Uses the player's API key to call a lightweight LLM and turn
 * structured game events into immersive flavour text.
 * Falls back to raw narrative_hint if the call fails.
 */
import type { DMRulingAppliedEvent } from "./schema";

const RENDER_TIMEOUT_MS = 10_000;

const TIER_LABELS: Record<string, string> = {
  large_success:  "大成功",
  medium_success: "中等成功",
  small_success:  "小成功",
  small_failure:  "小失敗",
  medium_failure: "中等失敗",
  large_failure:  "大失敗",
};

function buildRenderPrompt(event: DMRulingAppliedEvent): string {
  const tier = TIER_LABELS[event.tier ?? ""] ?? event.tier ?? "";
  const parts: string[] = [
    `判定結果：${tier}（擲骰 ${event.raw_roll ?? 0}，最終 ${event.final_roll ?? 0}，門檻 ${event.threshold ?? 0}）`,
    `DM 提示：${event.narrative_hint ?? ""}`,
  ];
  if (event.effect_type && event.effect_type !== "no_effect") {
    parts.push(`效果類型：${event.effect_type}${event.modifier && event.modifier !== 1 ? `（倍率 ${event.modifier}x）` : ""}`);
  }
  if (event.status_applied) {
    parts.push(`施加狀態：${event.status_applied}`);
  }

  return [
    "你是一位奇幻文字遊戲的敘事渲染器。",
    "請根據以下遊戲事件，用繁體中文寫出 1-2 句生動的場景描述。",
    "只輸出敘述文字，不要任何說明或前綴。",
    "",
    ...parts,
  ].join("\n");
}

function detectProvider(key: string): "anthropic" | "openrouter" {
  return key.startsWith("sk-ant-") ? "anthropic" : "openrouter";
}

async function fetchNarrative(prompt: string, llmKey: string): Promise<string> {
  const provider = detectProvider(llmKey);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), RENDER_TIMEOUT_MS);

  try {
    if (provider === "anthropic") {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "x-api-key": llmKey,
          "anthropic-version": "2023-06-01",
          "anthropic-dangerous-direct-browser-access": "true",
        },
        body: JSON.stringify({
          model: "claude-haiku-4-5-20251001",
          messages: [{ role: "user", content: prompt }],
          max_tokens: 150,
        }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      return (data.content?.[0]?.text ?? "").trim();
    } else {
      // OpenRouter
      const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${llmKey}`,
          "HTTP-Referer": window.location.origin,
          "X-Title": "ArcaneForge",
        },
        body: JSON.stringify({
          model: "qwen/qwen3.5-flash-02-23",
          messages: [{ role: "user", content: prompt }],
          max_tokens: 150,
          temperature: 0.7,
        }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      return (data.choices?.[0]?.message?.content ?? "").trim();
    }
  } finally {
    clearTimeout(timeout);
  }
}

const NPC_TYPE_PERSONALITY: Record<string, string> = {
  merchant: "友善的商人，說話親切、熱情，喜歡做生意",
  guard: "嚴肅的衛兵，說話簡短有力，重視秩序",
  monster: "危險的怪物，說話威嚇，語氣粗魯或低吼",
};

/**
 * Generate a contextual NPC response to a player's say action.
 * Always resolves — returns null on failure (no response shown).
 */
export async function generateNpcResponse(
  npcName: string,
  npcType: string,
  npcState: string,
  playerName: string,
  playerMessage: string,
  llmKey: string,
): Promise<string | null> {
  if (!llmKey) return null;
  const personality = NPC_TYPE_PERSONALITY[npcType] ?? "普通角色，性格一般";
  const prompt = [
    `你是「${npcName}」，一個${personality}。`,
    `目前狀態：${npcState || "idle"}。`,
    `玩家「${playerName}」說：「${playerMessage}」`,
    "請用繁體中文以你的角色性格回應，1-2 句話，不要加引號或角色名前綴，直接輸出台詞內容。",
  ].join("\n");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8_000);
  try {
    const provider = llmKey.startsWith("sk-ant-") ? "anthropic" : "openrouter";
    if (provider === "anthropic") {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST", signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "x-api-key": llmKey,
          "anthropic-version": "2023-06-01",
          "anthropic-dangerous-direct-browser-access": "true",
        },
        body: JSON.stringify({ model: "claude-haiku-4-5-20251001", messages: [{ role: "user", content: prompt }], max_tokens: 100 }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return (data.content?.[0]?.text ?? "").trim() || null;
    } else {
      const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST", signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${llmKey}`,
          "HTTP-Referer": window.location.origin,
          "X-Title": "ArcaneForge",
        },
        body: JSON.stringify({
          model: "qwen/qwen3.5-flash-02-23",
          messages: [{ role: "user", content: prompt }],
          max_tokens: 100, temperature: 0.8,
        }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return (data.choices?.[0]?.message?.content ?? "").trim() || null;
    }
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Render a dm_ruling_applied event into immersive narrative text.
 * Always resolves — falls back to narrative_hint on error.
 */
export async function renderNarrative(
  event: DMRulingAppliedEvent,
  llmKey: string,
): Promise<string> {
  const fallback = event.narrative_hint || TIER_LABELS[event.tier ?? ""] || "行動完成。";

  if (!llmKey || !event.feasible) return fallback;

  try {
    const prompt = buildRenderPrompt(event);
    const result = await fetchNarrative(prompt, llmKey);
    return result || fallback;
  } catch {
    return fallback;
  }
}
