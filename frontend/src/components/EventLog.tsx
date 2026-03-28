import { useEffect, useRef } from "react";
import type { GameEvent } from "../types";

const EVENT_COLOR: Record<string, string> = {
  player_traveling: "#4A90D8",
  player_arrived: "#40C080",
  player_said: "#E8B840",
  combat_started: "#E84040",
  combat_round: "#E84040",
  combat_ended: "#E84040",
  npc_action: "#C8941E",
  npc_dialogue: "#A0789E",
  npc_moved: "#7A9870",
  status_effect_applied: "#D07840",
  world_state_change: "#9A907E",
  system_announcement: "#9A907E",
  grab_contest_open: "#C040C0",
  grab_contest_resolved: "#C040C0",
  player_leveled_up: "#D4A017",
  npc_alert: "#D97706",
  npc_persuasion: "#C040C0",
};

const EVENT_PREFIX: Record<string, string> = {
  player_traveling: "⟶",
  player_arrived: "✦",
  player_said: "»",
  combat_started: "⚔",
  combat_round: "⚔",
  combat_ended: "⚔",
  npc_action: "◆",
  npc_dialogue: "◉",
  npc_moved: "→",
  status_effect_applied: "☠",
  world_state_change: "~",
  system_announcement: "◉",
  grab_contest_open: "◈",
  grab_contest_resolved: "◈",
  player_leveled_up: "⬆",
  npc_alert: "⚠",
  npc_persuasion: "◈",
};

const DIR_ZH: Record<string, string> = {
  north: "北方", south: "南方", east: "東方", west: "西方",
  up: "上方", down: "下方", in: "裡面", out: "外面",
};

// 移動方向的反方向：往北走 → 從南方進入
const OPPOSITE_DIR: Record<string, string> = {
  north: "南方", south: "北方", east: "西方", west: "東方",
  up: "下方", down: "上方", in: "外面", out: "裡面",
};

function formatEvent(event: GameEvent): string {
  const d = event as Record<string, unknown>;
  const dir = (d.direction as string) ?? "";
  const dirZh = DIR_ZH[dir] ?? dir;
  // 抗達方向：往北走，就是從南方進入
  const arriveFromZh = OPPOSITE_DIR[dir] ?? dirZh;
  switch (event.event_type) {
    case "player_traveling":
      return `${d.player_name} 出發前往${dirZh}…（${d.travel_time_seconds}秒）`;
    case "player_arrived":{
      // 優先用 to_place_name（顯示名稱），沒有則不顯示地點
      const placeName = (d.to_place_name as string) ?? "";
      const placeStr = placeName ? `，來到「${placeName}」` : "";
      return `${d.player_name} 從${arriveFromZh}走來${placeStr}。`;
    }
    case "player_said":
      return `${d.player_name}：「${d.message}」`;
    case "combat_started":
      return `戰鬥爆發！${(d.combatants as {name:string}[])?.map(c => c.name).join(" vs ") ?? ""}`;
    case "combat_round":
      return `${d.actor_id} 攻擊了 ${d.target_id}，造成 ${d.damage} 點傷害。${d.narrative_hint ? " " + d.narrative_hint : ""}`;
    case "combat_ended":
      return d.winner_id ? `${d.winner_id} 獲得了勝利！` : "戰鬥結束。";
    case "npc_action":
      return `${d.npc_name} ${d.action_type}${d.narrative_hint ? "：" + d.narrative_hint : ""}`;
    case "world_state_change": {
      const ct = d.change_type as string;
      const details = (d.details ?? {}) as Record<string, unknown>;
      if (ct === "item_picked_up") {
        const who = (details.player_id as string) ?? "有人";
        return `${who} 撿起了一件物品。`;
      }
      if (ct === "item_dropped") {
        const who = (details.player_id as string) ?? "有人";
        return `${who} 丟下了一件物品。`;
      }
      if (ct === "npc_state_changed") return `${details.npc_id ?? "NPC"} 改變了狀態。`;
      return "世界發生了變化。";
    }
    case "system_announcement":
      return String(d.message ?? "");
    case "grab_contest_open":
      return `出現了 ${d.item_name}！快去撿！`;
    case "grab_contest_resolved":
      return d.winner_id ? `${d.winner_id} 搶先拿到了物品！` : "物品消失了，無人取得。";
    case "npc_dialogue":
      return `${d.npc_name}：「${d.line}」`;
    case "npc_moved":
      return `${d.npc_name} 離開了此地，前往他處。`;
    case "status_effect_applied":
      return `${d.target_name} 受到了【${d.effect_type}】效果！（${d.stacks} 層）`;
    case "player_leveled_up":
      return `${d.player_name} 升至 Lv.${d.new_level}！獲得 ${d.stat_points_gained ?? 3} 屬性點可分配。`;
    case "npc_alert":
      return String(d.message ?? "敵人察覺到入侵者的氣息！");
    case "npc_persuasion": {
      const intentZh: Record<string, string> = { persuade: "說服", threaten: "威脅", bribe: "賄賂" };
      const tierZh: Record<string, string> = {
        large_success: "大成功", medium_success: "成功", small_success: "小成功",
        small_failure: "小失敗", medium_failure: "失敗", large_failure: "大失敗",
      };
      const intentStr = intentZh[d.intent as string] ?? String(d.intent ?? "互動");
      const tierStr = tierZh[d.tier as string] ? `【${tierZh[d.tier as string]}】` : "";
      return `${d.player_name} 嘗試${intentStr} ${d.npc_name}${tierStr}：${d.narrative ?? ""}`;
    }
    default:
      return JSON.stringify(event);
  }
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function EventLog({ events }: { events: GameEvent[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    if (nearBottom) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  return (
    <aside className="flex flex-col w-96 shrink-0 bg-stone-950/60 border-l border-stone-700/30">
      {/* 標題列 — 「戰報」是重要標題，保留 font-cinzel */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-stone-700/30">
        <div className="flex items-center gap-2.5">
          <svg viewBox="0 0 12 12" className="w-3.5 h-3.5" fill="#C8941E" opacity="0.7">
            <circle cx="6" cy="6" r="3" fill="none" stroke="#C8941E" strokeWidth="1.5"/>
            <circle cx="6" cy="6" r="1" fill="#C8941E"/>
          </svg>
          {/* 「戰報」標題 — 保留 font-cinzel */}
          <span className="font-cinzel text-base tracking-widest text-stone-400 uppercase">事件日誌</span>
        </div>
        {/* 事件數量 — 非標題，改 font-inter */}
        <span className="font-inter text-sm text-stone-600">{events.length} 則紀錄</span>
      </div>

      {/* 事件列表 */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-1 scrollbar-thin">
        {events.length === 0 && (
          <p className="font-inter text-base text-stone-600 text-center mt-10 italic">
            世界一片寂靜...
          </p>
        )}
        {events.map((event) => {
          const d = event as Record<string, unknown>;
          const PERSUASION_TIER_COLOR: Record<string, string> = {
            large_success: "#40C080", medium_success: "#60A870", small_success: "#8AAA60",
            small_failure: "#9A9070", medium_failure: "#C86840", large_failure: "#E84040",
          };
          const color = event.event_type === "npc_persuasion"
            ? (PERSUASION_TIER_COLOR[d.tier as string] ?? "#C040C0")
            : (EVENT_COLOR[event.event_type] ?? "#9A907E");
          const prefix = EVENT_PREFIX[event.event_type] ?? "·";
          const text = formatEvent(event);
          return (
            <div key={event.id}
              className="flex gap-3 py-2 border-b border-stone-800/40 last:border-0 animate-glow-in group">
              <span className="font-mono text-base mt-0.5 shrink-0 w-5 text-center" style={{ color }}>
                {prefix}
              </span>
              <div className="flex-1 min-w-0">
                {/* 事件文字 — 改 font-inter */}
                <p className="font-inter text-base leading-snug text-stone-200 break-words">{text}</p>
                <p className="font-inter text-xs text-stone-600 mt-0.5 group-hover:text-stone-500 transition-colors">
                  {formatTime(event.timestamp)}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef}/>
      </div>
    </aside>
  );
}
