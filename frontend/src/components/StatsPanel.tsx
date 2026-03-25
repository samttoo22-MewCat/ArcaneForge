import { useEffect, useState } from "react";
import type { Player } from "../types";

interface Props {
  player: Player;
}

// 方向中文對照
const DIR_ZH: Record<string, string> = {
  north: "北", south: "南", east: "東", west: "西",
  up: "上", down: "下", in: "入", out: "出",
};

function StatBar({
  label, value, max, color, glow,
}: {
  label: string; value: number; max: number; color: string; glow: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const danger = pct <= 25;
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-baseline">
        {/* 標籤：改 font-inter，非標題 */}
        <span className="font-inter text-sm font-semibold tracking-wide text-stone-400">{label}</span>
        <span className={`font-mono text-xl font-bold ${danger ? "text-hp-bright animate-pulse" : "text-stone-100"}`}>
          {value}<span className="text-stone-500 text-base">/{max}</span>
        </span>
      </div>
      <div className="h-4 bg-stone-800/80 rounded overflow-hidden border border-stone-700/40">
        <div
          className="h-full rounded transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}88, ${color})`,
            boxShadow: pct > 0 ? `0 0 10px ${glow}` : "none",
          }}
        />
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex justify-between items-center py-3 border-b border-stone-800/60 last:border-0">
      {/* 標籤：改 font-inter */}
      <span className="font-inter text-sm font-semibold text-stone-500">{label}</span>
      <span className="font-mono text-2xl font-bold text-stone-100">{value}</span>
    </div>
  );
}

export function StatsPanel({ player }: Props) {
  return (
    <aside className="flex flex-col gap-5 p-5 bg-stone-950/70 border-r border-stone-700/40 w-64 shrink-0 overflow-y-auto"
      style={{ borderColor: "rgba(37,46,62,0.7)" }}>
      {/* 頭像 */}
      <div className="flex flex-col items-center pt-2 pb-1">
        <div className="relative w-24 h-24 mb-3">
          <div className="w-24 h-24 rounded-full bg-stone-900 border-2 border-forest/50 flex items-center justify-center animate-pulse-forest mx-auto"
            style={{ boxShadow: "0 0 24px rgba(46,112,72,0.32)" }}>
            <svg viewBox="0 0 48 48" className="w-13 h-13" fill="none">
              <circle cx="24" cy="16" r="7" stroke="#2E7048" strokeWidth="1.5" fill="rgba(46,112,72,0.14)"/>
              <path d="M8 42c0-8.8 7.2-16 16-16s16 7.2 16 16" stroke="#2E7048" strokeWidth="1.5" fill="none"/>
              <line x1="24" y1="4" x2="24" y2="8" stroke="#2E7048" strokeWidth="1.2" opacity="0.5"/>
              <line x1="24" y1="38" x2="24" y2="42" stroke="#2E7048" strokeWidth="1.2" opacity="0.5"/>
            </svg>
          </div>
        </div>
        {/* 玩家名稱 — 這是標題，保留 font-cinzel */}
        <h2 className="font-cinzel text-lg font-bold text-stone-100 tracking-wide text-center leading-tight">
          {player.name}
        </h2>
        {/* 職業標籤 — 非標題，改 font-inter */}
        <p className="font-inter text-sm text-forest-light font-semibold tracking-wide mt-2">冒險者</p>
      </div>

      {/* HP / MP 條 */}
      <div className="space-y-4 px-1">
        <StatBar label="生命" value={player.hp} max={player.max_hp} color="#C03030" glow="rgba(192,48,48,0.6)"/>
        <StatBar label="魔力" value={player.mp} max={player.max_mp} color="#2860A8" glow="rgba(40,96,168,0.6)"/>
      </div>

      {/* 分隔線 */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-px bg-stone-700/40"/>
        <svg viewBox="0 0 12 12" className="w-3 h-3 shrink-0" fill="#2E7048" opacity="0.6">
          <polygon points="6,0 12,6 6,12 0,6"/>
        </svg>
        <div className="flex-1 h-px bg-stone-700/40"/>
      </div>

      {/* 戰鬥數值 */}
      <div className="px-1">
        <StatRow label="攻擊" value={player.atk}/>
        <StatRow label="防禦" value={player.def}/>
        <StatRow label="速度" value={player.spd}/>
      </div>

      {/* 旅行中指示 */}
      {player.is_traveling && (
        <div className="mt-auto mx-1 rounded border border-ember/50 bg-ember/10 px-3 py-3 animate-travel-pulse">
          <div className="flex items-center gap-2">
            <svg viewBox="0 0 16 16" className="w-5 h-5 text-ember shrink-0" fill="currentColor">
              <path d="M8 1l1.5 4h4l-3.2 2.3 1.2 3.7L8 9l-3.5 2 1.2-3.7L2.5 5h4z"/>
            </svg>
            <span className="font-inter text-base font-semibold text-ember">旅途中</span>
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
    <p className="font-mono text-base text-stone-500 mt-1 text-right">
      {secs > 0 ? `${secs}秒` : "即將抵達..."}
    </p>
  );
}
