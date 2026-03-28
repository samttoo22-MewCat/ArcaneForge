const OPENROUTER_AUTH_URL = "https://openrouter.ai/auth";
const EXCHANGE_PROXY_URL = "/api/v1/auth/exchange";

export function buildAuthUrl(callbackUrl?: string): string {
  const callback = callbackUrl ?? (window.location.origin + window.location.pathname);
  const params = new URLSearchParams({ callback_url: callback });
  return `${OPENROUTER_AUTH_URL}?${params.toString()}`;
}

export async function exchangeCodeForKey(code: string): Promise<string> {
  const res = await fetch(EXCHANGE_PROXY_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`授權失敗 (${res.status})${text ? ": " + text : ""}`);
  }
  const json = await res.json();
  if (!json.key) throw new Error("回應中缺少 API 金鑰");
  return json.key as string;
}

export function cleanupOAuthState(): void {
  window.history.replaceState({}, "", window.location.pathname);
}
