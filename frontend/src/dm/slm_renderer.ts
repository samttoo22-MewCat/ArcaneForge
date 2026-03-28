/**
 * SLM Renderer — client-side narrative renderer.
 * Uses the player's API key to call a lightweight LLM and turn
 * structured game events into immersive flavour text.
 * Falls back to raw narrative_hint if the call fails.
 */
import type { DMRulingAppliedEvent } from "./schema";
import { serverLog } from "../api";

const RENDER_TIMEOUT_MS = 30_000;
const NPC_RESPONSE_TIMEOUT_MS = 30_000;
const COMPRESS_TIMEOUT_MS = 20_000;

const TIER_LABELS: Record<string, string> = {
  large_success:  "大成功",
  medium_success: "中等成功",
  small_success:  "小成功",
  small_failure:  "小失敗",
  medium_failure: "中等失敗",
  large_failure:  "大失敗",
};

export interface MemoryContext {
  summary: string;         // long-term impression from FalkorDB
  recent_rounds: string[]; // last ≤10 compressed rounds from Redis
  attitude: number;        // -100..+100
}

// ── Shared LLM caller ─────────────────────────────────────────────────────────

function detectProvider(key: string): "anthropic" | "openrouter" {
  return key.startsWith("sk-ant-") ? "anthropic" : "openrouter";
}

async function callLlm(
  prompt: string,
  llmKey: string,
  maxTokens: number,
  timeoutMs: number = RENDER_TIMEOUT_MS,
): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    if (detectProvider(llmKey) === "anthropic") {
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
          max_tokens: maxTokens,
        }),
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        serverLog(`[callLlm] anthropic error ${res.status}: ${body}`, "error");
        throw new Error(`${res.status}`);
      }
      const data = await res.json();
      return (data.content?.[0]?.text ?? "").trim();
    } else {
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
          model: "google/gemini-3.1-flash-lite-preview",
          messages: [{ role: "user", content: prompt }],
          max_tokens: maxTokens,
          temperature: 0.7,
        }),
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        serverLog(`[callLlm] openrouter error ${res.status}: ${body}`, "error");
        throw new Error(`${res.status}`);
      }
      const data = await res.json();
      serverLog(`[callLlm] openrouter ok model=${data.model} tokens=${JSON.stringify(data.usage)}`);
      return (data.choices?.[0]?.message?.content ?? "").trim();
    }
  } finally {
    clearTimeout(timer);
  }
}

// ── NPC Response ──────────────────────────────────────────────────────────────

const NPC_TYPE_PERSONALITY: Record<string, string> = {
  merchant: "友善的商人，說話親切、熱情，喜歡做生意",
  guard:    "嚴肅的衛兵，說話簡短有力，重視秩序",
  monster:  "危險的怪物，說話威嚇，語氣粗魯或低吼",
};

function attitudeLabel(attitude: number): string {
  if (attitude >= 60) return "視對方為信任的友人";
  if (attitude >= 20) return "對對方態度友好";
  if (attitude >= -20) return "對對方態度中立";
  if (attitude >= -60) return "對對方有所戒心";
  return "對對方充滿敵意";
}

/**
 * Generate a contextual NPC response to a player's say action.
 * Injects memory context (long-term impression + recent rounds) into prompt.
 * Always resolves — returns null on failure.
 */
export async function generateNpcResponse(
  npcName: string,
  npcType: string,
  npcState: string,
  playerName: string,
  playerMessage: string,
  llmKey: string,
  memory?: MemoryContext,
): Promise<string | null> {
  if (!llmKey) return null;

  const personality = NPC_TYPE_PERSONALITY[npcType] ?? "普通角色，性格一般";

  const parts: string[] = [
    `你是「${npcName}」，一個${personality}。`,
    `目前狀態：${npcState || "idle"}。`,
  ];

  // Inject memory if available
  if (memory) {
    if (memory.summary) {
      parts.push(`【你對這位玩家的長期印象】${memory.summary}`);
    }
    if (memory.recent_rounds.length > 0) {
      parts.push(`【你們最近的對話】\n${memory.recent_rounds.join("\n")}`);
    }
    if (memory.attitude !== undefined) {
      parts.push(`【你目前的態度】${attitudeLabel(memory.attitude)}`);
    }
  }

  parts.push(
    `玩家「${playerName}」說：「${playerMessage}」`,
    "請用繁體中文以你的角色性格回應，1-2 句話，不要加引號或角色名前綴，直接輸出台詞內容。",
  );

  try {
    const result = await callLlm(parts.join("\n"), llmKey, 100, NPC_RESPONSE_TIMEOUT_MS);
    return result || null;
  } catch (e) {
    serverLog(`[generateNpcResponse] threw: ${e}`, "error");
    return null;
  }
}

// ── Round Compression ─────────────────────────────────────────────────────────

/**
 * Compress one dialogue exchange into a single short sentence (~15 chars).
 * Falls back to a simple template if LLM fails.
 */
export async function compressRound(
  npcName: string,
  playerName: string,
  playerMsg: string,
  npcResponse: string,
  llmKey: string,
): Promise<string> {
  const fallback = `${playerName}：${playerMsg.slice(0, 20)} → ${npcName}：${npcResponse.slice(0, 20)}`;
  if (!llmKey) return fallback;

  const prompt = [
    "將以下對話壓縮成一句話（20字以內），只保留最關鍵的信息：",
    `玩家「${playerName}」說：「${playerMsg}」`,
    `「${npcName}」說：「${npcResponse}」`,
    "直接輸出壓縮後的一句話，不加任何說明或前綴。",
  ].join("\n");

  try {
    const result = await callLlm(prompt, llmKey, 40, COMPRESS_TIMEOUT_MS);
    return result || fallback;
  } catch {
    return fallback;
  }
}

// ── Long-term Summary ─────────────────────────────────────────────────────────

/**
 * Generate a new long-term summary by combining old summary + 10 compressed rounds.
 * Falls back to oldSummary if LLM fails.
 */
export async function generateSummary(
  rounds: string[],
  oldSummary: string,
  npcName: string,
  llmKey: string,
): Promise<string> {
  if (!llmKey) return oldSummary;

  const parts: string[] = [];
  if (oldSummary) {
    parts.push(`【舊的長期印象】${oldSummary}`);
  }
  parts.push(
    `【最近十輪對話摘要】\n${rounds.join("\n")}`,
    `請從「${npcName}」的視角，將上述資訊整合成對這位玩家的長期印象（3-5句話）。`,
    "用第三人稱描述玩家的行為傾向、值得注意的事件、以及你對他的整體觀感。只輸出印象文字。",
  );

  try {
    const result = await callLlm(parts.join("\n\n"), llmKey, 200, RENDER_TIMEOUT_MS);
    return result || oldSummary;
  } catch {
    return oldSummary;
  }
}

// ── DM Ruling Narrative ───────────────────────────────────────────────────────

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
    const result = await callLlm(buildRenderPrompt(event), llmKey, 150, RENDER_TIMEOUT_MS);
    return result || fallback;
  } catch {
    return fallback;
  }
}
