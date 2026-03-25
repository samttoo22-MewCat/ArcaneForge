import type { Player } from "../types";

interface Props {
  player: Player;
}

function StatBar({
  label, value, max, color, glow,
}: {
  label: string; value: number; max: number; color: string; glow: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const danger = pct <= 25;
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-baseline">
        <span className="font-cinzel text-[10px] tracking-widest text-stone-400 uppercase">{label}</span>
        <span className={`font-mono text-xs ${danger ? "text-hp-bright animate-pulse" : "text-stone-200"}`}>
          {value}<span className="text-stone-600">/{max}</span>
        </span>
      </div>
      <div className="h-2 bg-stone-800/80 rounded-full overflow-hidden border border-stone-700/40">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}99, ${color})`,
            boxShadow: pct > 0 ? `0 0 8px ${glow}` : "none",
          }}
        />
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-stone-800/60 last:border-0">
      <span className="font-cinzel text-[10px] tracking-widest text-stone-500 uppercase">{label}</span>
      <span className="font-mono text-sm font-medium text-stone-200">{value}</span>
    </div>
  );
}

export function StatsPanel({ player }: Props) {
  return (
    <aside className="flex flex-col gap-4 p-4 bg-stone-950/60 border-r border-stone-700/30 w-48 shrink-0 overflow-y-auto">
      {/* Avatar */}
      <div className="flex flex-col items-center pt-2 pb-1">
        <div className="relative w-16 h-16 mb-3">
          <div className="w-full h-full rounded-full bg-stone-900 border border-stone-600/50 flex items-center justify-center animate-pulse-gold"
            style={{ boxShadow: "0 0 15px rgba(200,148,30,0.2)" }}>
            <svg viewBox="0 0 48 48" className="w-9 h-9" fill="none">
              <circle cx="24" cy="16" r="7" stroke="#C8941E" strokeWidth="1.2" fill="rgba(200,148,30,0.08)"/>
              <path d="M8 42c0-8.8 7.2-16 16-16s16 7.2 16 16" stroke="#C8941E" strokeWidth="1.2" fill="none"/>
              <line x1="24" y1="4" x2="24" y2="8" stroke="#C8941E" strokeWidth="1" opacity="0.5"/>
              <line x1="24" y1="38" x2="24" y2="42" stroke="#C8941E" strokeWidth="1" opacity="0.5"/>
            </svg>
          </div>
        </div>
        <h2 className="font-cinzel text-sm font-semibold text-gold-light tracking-wide text-center leading-tight">
          {player.name}
        </h2>
        <p className="font-mono text-[10px] text-stone-500 mt-0.5 tracking-widest">ADVENTURER</p>
      </div>

      {/* HP / MP bars */}
      <div className="space-y-3 px-1">
        <StatBar label="HP" value={player.hp} max={player.max_hp} color="#C03030" glow="rgba(192,48,48,0.6)"/>
        <StatBar label="MP" value={player.mp} max={player.max_mp} color="#2860A8" glow="rgba(40,96,168,0.6)"/>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-px bg-stone-700/40"/>
        <svg viewBox="0 0 12 12" className="w-2 h-2 shrink-0" fill="#C8941E" opacity="0.5">
          <polygon points="6,0 12,6 6,12 0,6"/>
        </svg>
        <div className="flex-1 h-px bg-stone-700/40"/>
      </div>

      {/* Combat stats */}
      <div className="px-1">
        <StatRow label="ATK" value={player.atk}/>
        <StatRow label="DEF" value={player.def}/>
        <StatRow label="SPD" value={player.spd}/>
      </div>

      {/* Travel indicator */}
      {player.is_traveling && (
        <div className="mt-auto mx-1 rounded border border-ember/40 bg-ember/10 px-3 py-2 animate-travel-pulse">
          <div className="flex items-center gap-2">
            <svg viewBox="0 0 16 16" className="w-3 h-3 text-ember shrink-0" fill="currentColor">
              <path d="M8 1l1.5 4h4l-3.2 2.3 1.2 3.7L8 9l-3.5 2 1.2-3.7L2.5 5h4z"/>
            </svg>
            <span className="font-mono text-[10px] text-ember tracking-wider">TRAVELING</span>
          </div>
          {player.travel_arrives_at && (
            <TravelCountdown arrivesAt={player.travel_arrives_at}/>
          )}
        </div>
      )}
    </aside>
  );
}

function TravelCountdown({ arrivesAt }: { arrivesAt: number }) {
  const [secs, setSecs] = useState(Math.max(0, Math.ceil(arrivesAt - Date.now() / 1000)));

  useEffect(() => {
    if (secs <= 0) return;
    const t = setInterval(() => {
      const remaining = Math.max(0, Math.ceil(arrivesAt - Date.now() / 1000));
      setSecs(remaining);
      if (remaining <= 0) clearInterval(t);
    }, 500);
    return () => clearInterval(t);
  }, [arrivesAt, secs]);

  return (
    <p className="font-mono text-[10px] text-stone-500 mt-0.5 text-right">
      {secs > 0 ? `${secs}s` : "arriving..."}
    </p>
  );
}

import { useEffect, useState } from "react";
