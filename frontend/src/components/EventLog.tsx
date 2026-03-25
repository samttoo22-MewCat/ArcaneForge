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
  world_state_change: "#9A907E",
  system_announcement: "#9A907E",
  grab_contest_open: "#C040C0",
  grab_contest_resolved: "#C040C0",
};

const EVENT_PREFIX: Record<string, string> = {
  player_traveling: "⟶",
  player_arrived: "✦",
  player_said: "»",
  combat_started: "⚔",
  combat_round: "⚔",
  combat_ended: "⚔",
  npc_action: "◆",
  world_state_change: "~",
  system_announcement: "◉",
  grab_contest_open: "◈",
  grab_contest_resolved: "◈",
};

function formatEvent(event: GameEvent): string {
  const d = event as Record<string, unknown>;
  switch (event.event_type) {
    case "player_traveling":
      return `${d.player_name} sets off towards the ${d.direction}... (${d.travel_time_seconds}s)`;
    case "player_arrived":
      return `${d.player_name} arrives from the ${d.direction}.`;
    case "player_said":
      return `${d.player_name}: "${d.message}"`;
    case "combat_started":
      return `Combat erupts! ${(d.combatants as {name:string}[])?.map(c => c.name).join(" vs ") ?? ""}`;
    case "combat_round":
      return `${d.actor_id} strikes ${d.target_id} for ${d.damage} damage. ${d.narrative_hint ?? ""}`;
    case "combat_ended":
      return d.winner_id ? `${d.winner_id} is victorious!` : "The battle concludes.";
    case "npc_action":
      return `${d.npc_name} ${d.action_type}${d.narrative_hint ? ": " + d.narrative_hint : ""}`;
    case "world_state_change":
      return `The world stirs... ${d.change_type}`;
    case "system_announcement":
      return String(d.message ?? "");
    case "grab_contest_open":
      return `A ${d.item_name} appears! Grab it quickly!`;
    case "grab_contest_resolved":
      return d.winner_id ? `${d.winner_id} snatches the item!` : "The item vanishes unclaimed.";
    default:
      return JSON.stringify(event);
  }
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function EventLog({ events }: { events: GameEvent[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll: only if user is near the bottom
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    if (nearBottom) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  return (
    <aside className="flex flex-col w-72 shrink-0 bg-stone-950/60 border-l border-stone-700/30">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-stone-700/30">
        <div className="flex items-center gap-2">
          <svg viewBox="0 0 12 12" className="w-3 h-3" fill="#C8941E" opacity="0.7">
            <circle cx="6" cy="6" r="3" fill="none" stroke="#C8941E" strokeWidth="1.5"/>
            <circle cx="6" cy="6" r="1" fill="#C8941E"/>
          </svg>
          <span className="font-cinzel text-[10px] tracking-widest text-stone-400 uppercase">Chronicle</span>
        </div>
        <span className="font-mono text-[10px] text-stone-600">{events.length} events</span>
      </div>

      {/* Events */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5 scrollbar-thin">
        {events.length === 0 && (
          <p className="font-mono text-[11px] text-stone-700 text-center mt-8 italic">
            The world is silent...
          </p>
        )}
        {events.map((event) => {
          const color = EVENT_COLOR[event.event_type] ?? "#9A907E";
          const prefix = EVENT_PREFIX[event.event_type] ?? "·";
          const text = formatEvent(event);
          return (
            <div key={event.id}
              className="flex gap-2 py-1 border-b border-stone-800/40 last:border-0 animate-glow-in group">
              <span className="font-mono text-[11px] mt-0.5 shrink-0 w-4 text-center" style={{ color }}>
                {prefix}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-mono text-[11px] leading-relaxed text-stone-300 break-words">{text}</p>
                <p className="font-mono text-[9px] text-stone-700 mt-0.5 group-hover:text-stone-600 transition-colors">
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
