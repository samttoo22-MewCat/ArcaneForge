import type { Exit, LookResult } from "../types";

const DIR_OFFSET: Record<string, [number, number]> = {
  north: [0, -115],
  south: [0, 115],
  east: [128, 0],
  west: [-128, 0],
  up: [96, -86],
  down: [96, 86],
  in: [-96, -86],
  out: [-96, 86],
};

const DIR_ICON: Record<string, string> = {
  north: "北", south: "南", east: "東", west: "西",
  up: "上", down: "下", in: "入", out: "出",
};

const DIR_ZH: Record<string, string> = {
  north: "北方", south: "南方", east: "東方", west: "西方",
  up: "上方", down: "下方", in: "裡面", out: "外面",
};

const CX = 220;
const CY = 165;

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
  const w = isCurrent ? 104 : 96;
  const h = isCurrent ? 48 : 42;
  const displayName = name ?? "???";
  return (
    <g
      transform={`translate(${x - w / 2}, ${y - h / 2})`}
      onClick={onClick}
      className={onClick ? "cursor-pointer" : ""}
      role={onClick ? "button" : undefined}
    >
      {isCurrent && (
        <rect x={-4} y={-4} width={w + 8} height={h + 8} rx={8} fill="rgba(200,144,48,0.07)"
          className="animate-pulse-gold"/>
      )}
      <rect
        x={0} y={0} width={w} height={h} rx={5}
        fill={isCurrent ? "rgba(200,144,48,0.14)" : "rgba(24,28,36,0.92)"}
        stroke={isCurrent ? "#C89030" : "#303840"}
        strokeWidth={isCurrent ? 2 : 1.2}
        className={onClick ? "hover:stroke-forest/70 transition-colors" : ""}
      />
      {direction && !isCurrent && (
        <text x={w / 2} y={-8} textAnchor="middle"
          className="fill-stone-500 font-mono" fontSize={13}>
          {DIR_ICON[direction] ?? direction}
        </text>
      )}
      <text
        x={w / 2} y={h / 2 + 5.5}
        textAnchor="middle"
        className={`font-cinzel select-none ${isCurrent ? "fill-gold-light" : "fill-stone-400"}`}
        fontSize={isCurrent ? 14 : 13}
        fontWeight={isCurrent ? "700" : "400"}
      >
        {displayName.length > 11 ? displayName.slice(0, 10) + "…" : displayName}
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
        stroke="#303840" strokeWidth={1.4} strokeDasharray="5 3"/>
      <text x={mx} y={my - 6} textAnchor="middle"
        className="fill-stone-500 font-mono" fontSize={13}>
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
      <div className="flex items-start justify-between px-5 pt-4 pb-2 gap-4">
        <div className="min-w-0">
          <h2 className="font-cinzel text-xl font-bold text-gold-light tracking-wide leading-tight"
            style={{ textShadow: "0 0 14px rgba(200,144,48,0.5)" }}>
            {place.name}
          </h2>
          <p className="font-inter text-base text-stone-400 mt-1 leading-relaxed max-w-md">
            {place.description}
          </p>
        </div>
        {moving && (
          <div className="flex items-center gap-2 px-3 py-2 rounded border border-ember/50 bg-ember/10 animate-travel-pulse shrink-0">
            <svg viewBox="0 0 16 16" className="w-4 h-4" fill="#D06820">
              <path d="M8 1 L10 6 L15 6 L11 9.5 L12.5 14.5 L8 11.5 L3.5 14.5 L5 9.5 L1 6 L6 6 Z"/>
            </svg>
            <span className="font-inter text-sm font-semibold text-ember tracking-wider">旅途中</span>
          </div>
        )}
      </div>

      {/* SVG Map */}
      <div className="relative flex-1 mx-4 mb-2 rounded-lg overflow-hidden border border-stone-700/40 bg-stone-950/60"
        style={{ minHeight: 300, maxHeight: 360 }}>
        <svg
          width="100%" height="100%"
          viewBox="0 0 440 330"
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

          {/* Current room */}
          <RoomNode
            x={CX} y={CY}
            name={place.name}
            isCurrent={true}
          />

          {/* You-are-here dot */}
          <circle cx={CX} cy={CY} r={3.5} fill="#C89030" opacity="0.9">
            <animate attributeName="opacity" values="0.9;0.4;0.9" dur="2s" repeatCount="indefinite"/>
          </circle>
        </svg>

        {/* 圖例 */}
        <div className="absolute bottom-2 right-3 flex items-center gap-3 opacity-50">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm border border-gold/60 bg-gold/10"/>
            <span className="font-inter text-xs text-stone-500">所在地</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0 border-t border-dashed border-stone-600"/>
            <span className="font-inter text-xs text-stone-500">通道</span>
          </div>
        </div>
      </div>

    
    </div>
  );
}

function ExitChip({ exit, onMove, disabled }: { exit: Exit; onMove: (d: string) => void; disabled: boolean }) {
  const dirZh = DIR_ZH[exit.direction] ?? exit.direction;
  const dirIcon = DIR_ICON[exit.direction] ?? exit.direction;
  return (
    <button
      onClick={() => onMove(exit.direction)}
      disabled={disabled}
      title={exit.exit_description}
      className="flex items-center gap-2.5 px-4 py-2.5 rounded border border-stone-700/50 bg-stone-900/70 text-stone-400
        hover:border-forest/60 hover:text-forest-light hover:bg-forest/10
        disabled:opacity-40 disabled:cursor-not-allowed
        transition-all duration-150 cursor-pointer group"
      style={{ boxShadow: undefined }}
      onMouseEnter={(e) => { if (!disabled) (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 0 10px rgba(46,112,72,0.28)"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "none"; }}
    >
      {/* 方向字母圖示 — font-mono 保留等寬特性 */}
      <span className="font-mono text-base font-bold text-forest/80 group-hover:text-forest-light transition-colors">
        {dirIcon}
      </span>
      {/* 方向中文名稱 — font-inter */}
      <span className="font-inter text-lg text-stone-200 group-hover:text-stone-100">{dirZh}</span>
      <span className="font-inter text-sm text-stone-600 group-hover:text-stone-400 transition-colors">
        {exit.travel_time_seconds}秒
      </span>
    </button>
  );
}
