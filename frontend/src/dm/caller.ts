/**
 * DM LLM Caller — client-side, uses player's own API key.
 * Detects provider from key prefix and calls the appropriate API.
 */
import type { DMPromptPacket, DMRuling } from "./schema";
import { ALL_TIERS } from "./schema";

const DM_TIMEOUT_MS = 15_000;

export class DmTimeoutError extends Error {
  constructor() { super("DM 裁決逾時（15 秒），行動取消。"); }
}

export class DmParseError extends Error {
  constructor(raw: string) { super(`DM 回傳格式無效：${raw.slice(0, 120)}`); }
}

type Provider = "anthropic" | "openrouter" | "openai";

function detectProvider(key: string): Provider {
  if (key.startsWith("sk-ant-")) return "anthropic";
  if (key.startsWith("sk-or-"))  return "openrouter";
  return "openrouter"; // default — OpenRouter supports most models
}

function buildMessages(packet: DMPromptPacket): { role: string; content: string }[] {
  const worldRules: string = (packet.payload.world_rules as string) ?? "";
  const systemPrompt = [
    "你是一位公平、嚴謹的桌遊地城主（DM）。",
    "請根據提供的世界規則、場景資訊與玩家行動，做出 TRPG 裁決。",
    "你必須以 JSON 格式回應，不得加入任何額外說明文字。",
    "不得在任何欄位填入數值傷害或 HP 數字——伺服器負責所有數值計算。",
    worldRules ? `\n世界規則摘要：\n${worldRules.slice(0, 600)}` : "",
  ].filter(Boolean).join("\n");

  // Build user message: omit world_rules from payload (already in system)
  const userPayload = { ...packet.payload };
  delete userPayload.world_rules;

  return [
    { role: "system", content: systemPrompt },
    { role: "user",   content: JSON.stringify(userPayload) },
  ];
}

async function callOpenAICompatible(
  endpoint: string,
  apiKey: string,
  messages: { role: string; content: string }[],
  extraHeaders: Record<string, string> = {},
): Promise<string> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DM_TIMEOUT_MS);

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`,
        ...extraHeaders,
      },
      body: JSON.stringify({
        model: "google/gemini-3.1-flash-lite-preview",
        messages,
        response_format: { type: "json_object" },
        temperature: 0.3,
        max_tokens: 800,
      }),
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => res.statusText);
      throw new Error(`LLM API ${res.status}: ${txt}`);
    }
    const data = await res.json();
    return data.choices?.[0]?.message?.content ?? "";
  } finally {
    clearTimeout(timeout);
  }
}

async function callAnthropic(
  apiKey: string,
  messages: { role: string; content: string }[],
): Promise<string> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DM_TIMEOUT_MS);
  const system = messages.find(m => m.role === "system")?.content ?? "";
  const userMsgs = messages.filter(m => m.role !== "system");

  try {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        system,
        messages: userMsgs,
        max_tokens: 800,
      }),
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => res.statusText);
      throw new Error(`Anthropic API ${res.status}: ${txt}`);
    }
    const data = await res.json();
    return data.content?.[0]?.text ?? "";
  } finally {
    clearTimeout(timeout);
  }
}

function parseRuling(raw: string): DMRuling {
  // Strip markdown code fences if present
  const cleaned = raw.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();
  let obj: unknown;
  try {
    obj = JSON.parse(cleaned);
  } catch {
    throw new DmParseError(raw);
  }
  if (typeof obj !== "object" || obj === null || !("feasible" in obj)) {
    throw new DmParseError(raw);
  }
  const ruling = obj as DMRuling;

  // If feasible, ensure all 6 tier keys exist
  if (ruling.feasible && ruling.outcomes) {
    for (const tier of ALL_TIERS) {
      if (!ruling.outcomes[tier]) {
        ruling.outcomes[tier] = { narrative: "", effect_type: "no_effect" };
      }
    }
  }
  return ruling;
}

export async function callDM(packet: DMPromptPacket, llmKey: string): Promise<DMRuling> {
  if (!llmKey) throw new Error("未設定 API Key，無法呼叫 DM。");

  const provider = detectProvider(llmKey);
  const messages = buildMessages(packet);
  let raw: string;

  try {
    if (provider === "anthropic") {
      raw = await callAnthropic(llmKey, messages);
    } else {
      // OpenRouter (default)
      raw = await callOpenAICompatible(
        "https://openrouter.ai/api/v1/chat/completions",
        llmKey,
        messages,
        { "HTTP-Referer": window.location.origin, "X-Title": "ArcaneForge" },
      );
    }
  } catch (err) {
    if ((err as Error).name === "AbortError") throw new DmTimeoutError();
    throw err;
  }

  return parseRuling(raw);
}
