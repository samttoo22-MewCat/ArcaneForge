import { getLlmKey } from "../api";
import type { Player } from "../types";

interface Props {
  player: Player;
  connected: boolean;
  onLogout: () => void;
}

function MiniBar({ value, max, color, glow }: { value: number; max: number; color: string; glow: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="w-22 h-2.5 bg-stone-800 rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, background: color, boxShadow: pct > 0 ? `0 0 6px ${glow}` : "none" }}
      />
    </div>
  );
}

export function Header({ player, connected, onLogout }: Props) {
  const hasKey = Boolean(getLlmKey());
  return (
    <header className="flex items-center justify-between px-5 py-3.5 bg-stone-950/95 border-b border-stone-700/50 backdrop-blur-sm"
      style={{ boxShadow: "0 1px 24px rgba(0,0,0,0.8)" }}>
      {/* Title — 金色是特殊元素，保留 */}
      <div className="flex items-center gap-3">
        <svg viewBox="0 0 24 24" className="w-6 h-6 shrink-0" fill="none">
          <polygon points="12,2 22,18 2,18" fill="none" stroke="#C89030" strokeWidth="1.4"/>
          <circle cx="12" cy="12" r="2" fill="#C89030"/>
        </svg>
        <span className="font-cinzel font-bold text-xl tracking-[0.2em] text-gold"
          style={{ textShadow: "0 0 14px rgba(200,144,48,0.55)" }}>
          ARCANEFORGE
        </span>
      </div>

      {/* Player info */}
      <div className="flex items-center gap-5">
        {/* HP */}
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-1.5">
            <svg viewBox="0 0 12 12" className="w-3.5 h-3.5" fill="#C03030">
              <path d="M6 10.5C6 10.5 1 7 1 4a2.5 2.5 0 015 0 2.5 2.5 0 015 0c0 3-5 6.5-5 6.5z"/>
            </svg>
            <span className="font-mono text-base text-hp-bright">{player.hp}/{player.max_hp}</span>
          </div>
          <MiniBar value={player.hp} max={player.max_hp} color="#C03030" glow="rgba(192,48,48,0.8)"/>
        </div>

        {/* MP */}
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-1.5">
            <svg viewBox="0 0 12 12" className="w-3.5 h-3.5" fill="#2860A8">
              <polygon points="6,1 11,5 9,11 3,11 1,5"/>
            </svg>
            <span className="font-mono text-base text-mp-bright">{player.mp}/{player.max_mp}</span>
          </div>
          <MiniBar value={player.mp} max={player.max_mp} color="#2860A8" glow="rgba(40,96,168,0.8)"/>
        </div>

        <div className="w-px h-8 bg-stone-700/60"/>

        {/* Player name — 森林綠頭像 */}
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full bg-stone-800 border-2 border-forest/50 flex items-center justify-center"
            style={{ boxShadow: "0 0 8px rgba(46,112,72,0.3)" }}>
            <span className="font-cinzel text-sm font-bold text-forest-light">
              {player.name.charAt(0).toUpperCase()}
            </span>
          </div>
          <span className="font-inter text-base font-medium text-stone-100">{player.name}</span>
        </div>

        {/* OpenRouter key indicator — 有 key 時用綠色 */}
        <div className="flex items-center gap-1.5" title={hasKey ? "OpenRouter API key set" : "No API key — DM rulings disabled"}>
          <svg viewBox="0 0 14 14" className="w-4 h-4" fill="none">
            <rect x="1" y="5" width="12" height="8" rx="1.5" stroke={hasKey ? "#4A9E60" : "#374455"} strokeWidth="1.3"/>
            <path d="M4.5 5V3.5a2.5 2.5 0 015 0V5" stroke={hasKey ? "#4A9E60" : "#374455"} strokeWidth="1.3"/>
            <circle cx="7" cy="9" r="1" fill={hasKey ? "#4A9E60" : "#374455"}/>
          </svg>
          <span className={`font-inter text-sm font-semibold ${hasKey ? "text-forest-light" : "text-stone-600"}`}>
            {hasKey ? "DM開啟" : "無金鑰"}
          </span>
        </div>

        {/* Connection indicator */}
        <div className="flex items-center gap-1.5">
          <div className={`w-2.5 h-2.5 rounded-full ${connected ? "bg-xp-bright" : "bg-hp-bright"}`}
            style={{ boxShadow: connected ? "0 0 8px #50D460" : "0 0 8px #F05050" }}/>
          <span className="font-inter text-base font-semibold text-stone-400">
            {connected ? "線上" : "離線"}
          </span>
        </div>

        <button onClick={onLogout}
          className="font-inter text-base font-semibold text-stone-500 hover:text-forest-light cursor-pointer transition-colors px-3 py-1.5 rounded hover:bg-forest/10 hover:border hover:border-forest/30 border border-transparent">
          登出
        </button>
      </div>
    </header>
  );
}
