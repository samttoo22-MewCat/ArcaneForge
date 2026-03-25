import { useState } from "react";

interface Props {
  onLogin: (playerId: string, apiKey: string, remember: boolean) => void;
}

export function LoginScreen({ onLogin }: Props) {
  const [playerId, setPlayerId] = useState("");
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("arcaneforge_llm_key_raw") ?? "");
  const [showKey, setShowKey] = useState(false);
  const [remember, setRemember] = useState(() => localStorage.getItem("arcaneforge_remember") === "1");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const id = playerId.trim();
    if (!id) return;
    localStorage.setItem("arcaneforge_remember", remember ? "1" : "0");
    onLogin(id, apiKey.trim(), remember);
  }

  return (
    <div className="min-h-screen bg-void flex items-center justify-center overflow-hidden">
      {/* Radial ambient glow */}
      <div className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse 60% 50% at 50% 55%, rgba(46,112,72,0.06) 0%, transparent 70%)",
        }}/>

      {/* Rune grid */}
      <div className="absolute inset-0 opacity-[0.035] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%232E7048' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      <div className="relative w-full max-w-sm px-4">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-20 h-20 mb-5 rounded-full border border-gold/40 bg-stone-900"
            style={{ boxShadow: "0 0 40px rgba(46,112,72,0.2), inset 0 0 20px rgba(0,0,0,0.7)" }}>
            <svg viewBox="0 0 48 48" className="w-10 h-10 animate-pulse-gold" fill="none">
              <polygon points="24,4 44,36 4,36" fill="none" stroke="#2E7048" strokeWidth="1.8"/>
              <polygon points="24,12 38,34 10,34" fill="rgba(46,112,72,0.12)" stroke="#2E7048" strokeWidth="0.8" strokeDasharray="3 2"/>
              <circle cx="24" cy="23" r="4" fill="#2E7048" opacity="0.9"/>
              <line x1="24" y1="4" x2="24" y2="44" stroke="#2E7048" strokeWidth="0.6" opacity="0.4"/>
              <line x1="4" y1="24" x2="44" y2="24" stroke="#2E7048" strokeWidth="0.6" opacity="0.4"/>
            </svg>
          </div>
          <h1 className="font-cinzel text-4xl font-black tracking-widest text-gold-light"
            style={{ textShadow: "0 0 24px rgba(212,160,48,0.7), 0 2px 6px rgba(0,0,0,0.9)" }}>
            ARCANEFORGE
          </h1>
          {/* 副標 — 非主標題，改 font-inter */}
          <p className="mt-2 font-inter text-sm tracking-widest text-stone-500">
            世界正在等待你的到來
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}
          className="bg-stone-900 border border-stone-700/70 rounded-lg p-7"
          style={{ boxShadow: "0 8px 48px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.05)" }}>

          {/* 玩家 ID */}
          <div className="mb-5">
            {/* label 非標題，改 font-inter */}
            <label className="block font-inter text-sm font-semibold text-stone-400 mb-2">
              玩家 ID
            </label>
            <input
              type="text"
              value={playerId}
              onChange={(e) => setPlayerId(e.target.value)}
              placeholder="例如：hero_001"
              className="w-full bg-stone-900 border border-stone-700 rounded px-4 py-3
                text-stone-100 font-inter text-base placeholder-stone-600
                focus:outline-none focus:border-forest/60 focus:ring-1 focus:ring-forest/30
                transition-colors"
              autoFocus
            />
          </div>

          {/* OpenRouter API 金鑰 */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              {/* label 非標題，改 font-inter */}
              <label className="font-inter text-sm font-semibold text-stone-400">
                OpenRouter API 金鑰
              </label>
              <span className="font-inter text-xs text-stone-600">選項 · 用於 DM 袃裁</span>
            </div>
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-or-v1-..."
                className="w-full bg-stone-900 border border-stone-700 rounded px-4 py-3 pr-10
                  text-stone-100 font-mono text-sm placeholder-stone-600
                  focus:outline-none focus:border-forest/60 focus:ring-1 focus:ring-forest/30
                  transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowKey((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 hover:text-stone-300 cursor-pointer transition-colors"
                aria-label={showKey ? "隱藏金鑰" : "顯示金鑰"}
              >
                {showKey ? (
                  <svg viewBox="0 0 16 16" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2 8s2.5-4 6-4 6 4 6 4-2.5 4-6 4-6-4-6-4z"/>
                    <path d="M3 3l10 10" strokeLinecap="round"/>
                  </svg>
                ) : (
                  <svg viewBox="0 0 16 16" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2 8s2.5-4 6-4 6 4 6 4-2.5 4-6 4-6-4-6-4z"/>
                    <circle cx="8" cy="8" r="1.5"/>
                  </svg>
                )}
              </button>
            </div>
            <p className="mt-1.5 font-inter text-xs text-stone-600 leading-relaxed">
              在本機使用，用於驅動 AI GM 裁判。不會將金鑰傳輸到任何伺服器。
            </p>
          </div>

          {/* Remember me */}
          <label className="flex items-center gap-3 mb-5 cursor-pointer group select-none">
            <div className="relative w-4 h-4 shrink-0">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="peer sr-only"
              />
              <div className="w-4 h-4 rounded border border-stone-600 bg-stone-800
                peer-checked:bg-gold/20 peer-checked:border-gold/70
                group-hover:border-stone-500 transition-colors"/>
              {remember && (
                <svg viewBox="0 0 10 10" className="absolute inset-0 w-4 h-4 p-0.5 pointer-events-none" fill="none">
                  <polyline points="1.5,5 4,7.5 8.5,2" stroke="#F0C060" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </div>
            <span className="font-inter text-sm text-stone-300 group-hover:text-stone-100 transition-colors">
              記住我
            </span>
            <span className="font-mono text-[10px] text-stone-600 ml-auto">
              {remember ? "關分頁後保留登入" : "關分頁後自動登出"}
            </span>
          </label>

          {/* 進入按鈕 — 主要行動按鈕，保留大字體但改 font-inter（非展示標題）*/}
          <button
            type="submit"
            disabled={!playerId.trim()}
            className="w-full py-3 font-inter text-base font-bold tracking-widest uppercase rounded cursor-pointer
              bg-forest/20 border border-forest/60 text-forest-light
              hover:bg-forest/35 hover:border-forest/90
              disabled:opacity-35 disabled:cursor-not-allowed
              transition-all duration-200"
            style={{ boxShadow: playerId.trim() ? "0 0 14px rgba(46,112,72,0.3)" : "none" }}
          >
            進入世界
          </button>
        </form>

        <p className="mt-4 text-center font-inter text-xs text-stone-600">
          v0.1.0 · ArcaneForge MUD
        </p>
      </div>
    </div>
  );
}
