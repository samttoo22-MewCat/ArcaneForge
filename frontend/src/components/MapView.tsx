import type { Exit, LookResult } from "../types";

const DIR_OFFSET: Record<string, [number, number]> = {
  north: [0, -110],
  south: [0, 110],
  east: [120, 0],
  west: [-120, 0],
  up: [90, -80],
  down: [90, 80],
  in: [-90, -80],
  out: [-90, 80],
};

const DIR_ICON: Record<string, string> = {
  north: "N", south: "S", east: "E", west: "W",
  up: "↑", down: "↓", in: "⇥", out: "⇤",
};

const CX = 220;
const CY = 160;

interface Props {
  look: LookResult;
  onMove: (direction: string) => void;
  moving: boolean;
}

function RoomNode({
  x, y, name, isCurrent, onClick, direction,
}: {
  x: number; y: number; name?: string; isCurrent: boolean; onClick?: () => void; direction?: string;
}) {
  const w = 74;
  const h = 34;
  const displayName = name ?? "???";
  return (
    <g
      transform={`translate(${x - w / 2}, ${y - h / 2})`}
      onClick={onClick}
      className={onClick ? "cursor-pointer" : ""}
      role={onClick ? "button" : undefined}
    >
      {/* Glow filter for current room */}
      {isCurrent && (
        <rect x={-3} y={-3} width={w + 6} height={h + 6} rx={7} fill="rgba(200,148,30,0.08)"
          className="animate-pulse-gold"/>
      )}
      <rect
        x={0} y={0} width={w} height={h} rx={5}
        fill={isCurrent ? "rgba(200,148,30,0.12)" : "rgba(26,25,23,0.9)"}
        stroke={isCurrent ? "#C8941E" : "#3E3A35"}
        strokeWidth={isCurrent ? 1.5 : 1}
        className={onClick ? "hover:stroke-gold/60 transition-colors" : ""}
      />
      {/* Direction badge */}
      {direction && !isCurrent && (
        <text x={w / 2} y={-6} textAnchor="middle"
          className="fill-stone-500 font-mono" fontSize={9}>
          {DIR_ICON[direction] ?? direction}
        </text>
      )}
      <text
        x={w / 2} y={h / 2 + 4}
        textAnchor="middle"
        className={`font-cinzel select-none ${isCurrent ? "fill-gold-light" : "fill-stone-400"}`}
        fontSize={isCurrent ? 9.5 : 8.5}
        fontWeight={isCurrent ? "600" : "400"}
      >
        {displayName.length > 10 ? displayName.slice(0, 9) + "…" : displayName}
      </text>
    </g>
  );
}

function ConnectionLine({ x1, y1, x2, y2, travelTime }: {
  x1: number; y1: number; x2: number; y2: number; travelTime: number;
}) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  return (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2}
        stroke="#3E3A35" strokeWidth={1} strokeDasharray="4 3"/>
      <text x={mx} y={my - 4} textAnchor="middle"
        className="fill-stone-600 font-mono" fontSize={8}>
        {travelTime}s
      </text>
    </g>
  );
}

export function MapView({ look, onMove, moving }: Props) {
  const { place, exits } = look;

  return (
    <div className="flex flex-col flex-1 min-w-0">
      {/* Room header */}
      <div className="flex items-center justify-between px-5 pt-4 pb-2">
        <div>
          <h2 className="font-cinzel text-base font-semibold text-gold-light tracking-wide"
            style={{ textShadow: "0 0 10px rgba(200,148,30,0.4)" }}>
            {place.name}
          </h2>
          <p className="font-inter text-xs text-stone-400 mt-0.5 leading-relaxed max-w-md">
            {place.description}
          </p>
        </div>
        {moving && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-ember/40 bg-ember/10 animate-travel-pulse shrink-0 ml-4">
            <svg viewBox="0 0 16 16" className="w-3 h-3" fill="#D4700A">
              <path d="M8 1 L10 6 L15 6 L11 9.5 L12.5 14.5 L8 11.5 L3.5 14.5 L5 9.5 L1 6 L6 6 Z"/>
            </svg>
            <span className="font-mono text-[10px] text-ember tracking-wider">TRAVELING</span>
          </div>
        )}
      </div>

      {/* SVG Map */}
      <div className="relative flex-1 mx-4 mb-2 rounded-lg overflow-hidden border border-stone-700/30 bg-stone-950/50"
        style={{ minHeight: 280, maxHeight: 340 }}>
        {/* Stone texture overlay */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
          style={{
            backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(200,148,30,0.3) 39px, rgba(200,148,30,0.3) 40px), repeating-linear-gradient(90deg, transparent, transparent 39px, rgba(200,148,30,0.3) 39px, rgba(200,148,30,0.3) 40px)",
          }}/>

        <svg
          width="100%" height="100%"
          viewBox="0 0 440 320"
          preserveAspectRatio="xMidYMid meet"
          className="w-full h-full"
        >
          {/* Connection lines */}
          {exits.map((exit) => {
            const offset = DIR_OFFSET[exit.direction] ?? [0, 0];
            return (
              <ConnectionLine
                key={exit.direction}
                x1={CX} y1={CY}
                x2={CX + offset[0]} y2={CY + offset[1]}
                travelTime={exit.travel_time_seconds}
              />
            );
          })}

          {/* Exit room nodes */}
          {exits.map((exit) => {
            const offset = DIR_OFFSET[exit.direction] ?? [0, 0];
            return (
              <RoomNode
                key={exit.direction}
                x={CX + offset[0]}
                y={CY + offset[1]}
                name={exit.destination_name || exit.to_place_name || exit.to_place_id}
                isCurrent={false}
                direction={exit.direction}
                onClick={moving ? undefined : () => onMove(exit.direction)}
              />
            );
          })}

          {/* Current room (drawn on top) */}
          <RoomNode
            x={CX} y={CY}
            name={place.name}
            isCurrent={true}
          />

          {/* Center dot */}
          <circle cx={CX} cy={CY} r={3} fill="#C8941E" opacity="0.9">
            <animate attributeName="opacity" values="0.9;0.4;0.9" dur="2s" repeatCount="indefinite"/>
          </circle>
        </svg>

        {/* Legend */}
        <div className="absolute bottom-2 right-3 flex items-center gap-3 opacity-50">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm border border-gold/60 bg-gold/10"/>
            <span className="font-mono text-[9px] text-stone-500">current</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-0 border-t border-dashed border-stone-600"/>
            <span className="font-mono text-[9px] text-stone-500">passage</span>
          </div>
        </div>
      </div>

      {/* Exits quick-info */}
      {exits.length > 0 && (
        <div className="px-4 pb-3 flex flex-wrap gap-1.5">
          {exits.map((exit) => (
            <ExitChip key={exit.direction} exit={exit} onMove={onMove} disabled={moving}/>
          ))}
        </div>
      )}
    </div>
  );
}

function ExitChip({ exit, onMove, disabled }: { exit: Exit; onMove: (d: string) => void; disabled: boolean }) {
  return (
    <button
      onClick={() => onMove(exit.direction)}
      disabled={disabled}
      title={exit.exit_description}
      className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-stone-600/50 bg-stone-900/60 text-stone-400
        hover:border-gold/40 hover:text-gold-light hover:bg-stone-800/60
        disabled:opacity-40 disabled:cursor-not-allowed
        transition-all duration-150 cursor-pointer group"
    >
      <span className="font-mono text-[10px] font-medium text-gold/70 group-hover:text-gold">
        {DIR_ICON[exit.direction] ?? exit.direction.toUpperCase()}
      </span>
      <span className="font-inter text-[11px]">{exit.direction}</span>
      <span className="font-mono text-[9px] text-stone-600 group-hover:text-stone-500">
        {exit.travel_time_seconds}s
      </span>
    </button>
  );
}
