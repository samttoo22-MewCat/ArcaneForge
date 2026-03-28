import { useEffect, useState } from "react";
import type { Player } from "../types";

interface Props {
  player: Player;
  onAllocateStat?: (stat: string) => void;
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

const STAT_TOOLTIPS: Record<string, string> = {
  STR: "物理攻擊力與蠻力判定。影響近戰傷害、破門、搬重物與壓制敵人的成功率。戰士與狂戰士的核心屬性。",
  DEX: "速度、閃避與精準動作。影響潛行、遠程攻擊精準度、先手順序判定與躲避攻擊的能力。遊俠與盜賊的核心屬性。",
  INT: "奧術學識與邏輯推理。影響法術傷害倍率、製作成功率、鑑定物品與破解機關謎題的判定。法師的核心屬性。",
  WIS: "直覺感知與靈性連結。影響神聖/治癒魔法效果、偵測陷阱埋伏、洞察 NPC 真實意圖，以及抵抗精神操控效果。聖職者的核心屬性。",
  CHA: "社交魅力與領袖氣場。影響說服、欺騙、威脅、賄賂等社交行動的骰子判定，以及 NPC 對你的初始好感度。吟遊詩人的核心屬性。",
  LUK: "命運之力。影響暴擊機率、稀有物品掉落率，以及難以預測的偶發事件結果。在絕境中或許能扭轉一切。",
};

function StatRow({
  label, value, tooltip, onAllocate,
}: {
  label: string; value: number | string; tooltip?: string; onAllocate?: () => void;
}) {
  const [show, setShow] = useState(false);
  return (
    <div
      className="relative flex justify-between items-center py-3 border-b border-stone-800/60 last:border-0 cursor-default select-none"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <span className="font-inter text-sm font-semibold text-stone-500">{label}</span>
      <div className="flex items-center gap-2">
        {onAllocate && (
          <button
            onClick={(e) => { e.stopPropagation(); onAllocate(); }}
            className="w-5 h-5 rounded-full border border-amber-500/70 bg-amber-500/15 text-amber-400 text-xs font-bold flex items-center justify-center hover:bg-amber-500/30 transition-colors"
            title="分配屬性點"
          >+</button>
        )}
        <span className="font-mono text-2xl font-bold text-stone-100">{value}</span>
      </div>
      {tooltip && show && (
        <div className="absolute left-0 bottom-full mb-2 z-50 w-52 rounded-lg border border-forest/40 bg-stone-950/95 px-3 py-2 shadow-xl pointer-events-none">
          <p className="font-inter text-xs leading-relaxed text-stone-300">{tooltip}</p>
          <div className="absolute left-4 top-full w-0 h-0"
            style={{ borderLeft: "6px solid transparent", borderRight: "6px solid transparent", borderTop: "6px solid rgba(46,112,72,0.4)" }}/>
        </div>
      )}
    </div>
  );
}

export function StatsPanel({ player, onAllocateStat }: Props) {
  const hasPoints = (player.stat_points ?? 0) > 0;
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
        {/* 等級與職業 */}
        <p className="font-inter text-sm text-forest-light font-semibold tracking-wide mt-1">
          Lv.{player.level ?? 1}
        </p>
        <p className="font-inter text-xs text-stone-500 mt-0.5">
          {(player.classes ?? []).length > 0
            ? player.classes.join(" · ")
            : "冒險者"}
        </p>
        {/* XP 進度條 */}
        {player.xp_next_level != null ? (
          <div className="w-full mt-2 px-1">
            <div className="flex justify-between text-xs font-mono text-stone-500 mb-1">
              <span>XP</span>
              <span>{player.xp ?? 0} / {player.xp_next_level}</span>
            </div>
            <div className="h-2 bg-stone-800/80 rounded overflow-hidden border border-stone-700/40">
              <div
                className="h-full rounded transition-all duration-700"
                style={{
                  width: `${Math.min(100, ((player.xp ?? 0) / player.xp_next_level) * 100)}%`,
                  background: "linear-gradient(90deg, #92400e88, #d97706)",
                  boxShadow: "0 0 6px rgba(217,119,6,0.5)",
                }}
              />
            </div>
          </div>
        ) : player.xp_next_level === null ? (
          <p className="font-inter text-xs text-amber-600 mt-1">已達頂級</p>
        ) : null}
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

      {/* 六維屬性 — 滑鼠移到屬性上可見說明 */}
      <div className="px-1">
        <StatRow label="力量 STR" value={player.str ?? 8} tooltip={STAT_TOOLTIPS.STR} onAllocate={hasPoints && onAllocateStat ? () => onAllocateStat("str") : undefined}/>
        <StatRow label="敏捷 DEX" value={player.dex ?? 8} tooltip={STAT_TOOLTIPS.DEX} onAllocate={hasPoints && onAllocateStat ? () => onAllocateStat("dex") : undefined}/>
        <StatRow label="智力 INT" value={player.int ?? 8} tooltip={STAT_TOOLTIPS.INT} onAllocate={hasPoints && onAllocateStat ? () => onAllocateStat("int") : undefined}/>
        <StatRow label="感知 WIS" value={player.wis ?? 8} tooltip={STAT_TOOLTIPS.WIS} onAllocate={hasPoints && onAllocateStat ? () => onAllocateStat("wis") : undefined}/>
        <StatRow label="魅力 CHA" value={player.cha ?? 8} tooltip={STAT_TOOLTIPS.CHA} onAllocate={hasPoints && onAllocateStat ? () => onAllocateStat("cha") : undefined}/>
        <StatRow label="幸運 LUK" value={player.luk ?? 8} tooltip={STAT_TOOLTIPS.LUK} onAllocate={hasPoints && onAllocateStat ? () => onAllocateStat("luk") : undefined}/>
      </div>

      {/* 升級點數（有未分配點數時顯示） */}
      {(player.stat_points ?? 0) > 0 && (
        <div className="mx-1 rounded border border-gold/50 bg-gold/10 px-3 py-2 text-center">
          <p className="font-inter text-sm font-semibold text-gold">
            ✦ 未分配點數：{player.stat_points}
          </p>
        </div>
      )}

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
