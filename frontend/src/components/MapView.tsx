import { useMemo, useState } from "react";
import type { Exit, LookResult, MiddleContext, LargeContext, RoomMini, DistrictMini } from "../types";

// ─── Direction helpers ────────────────────────────────────────────────────────

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

// ─── SVG constants ────────────────────────────────────────────────────────────

const SVG_W = 440;
const SVG_H = 330;
const ACTIVE_CX = 220;
const ACTIVE_CY = 165;

// ─── Spatial helpers ──────────────────────────────────────────────────────────

interface CoordMap { minX: number; minY: number; scale: number; offX: number; offY: number }

function buildCoordMap(
  items: Array<{ x_pos: number; y_pos: number }>,
  svgW: number, svgH: number,
  pad: number,
): CoordMap {
  if (!items.length) return { minX: 0, minY: 0, scale: 1, offX: pad, offY: pad };
  const xs = items.map(i => i.x_pos);
  const ys = items.map(i => i.y_pos);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const dataW = maxX - minX || 1;
  const dataH = maxY - minY || 1;
  const scale = Math.min((svgW - pad * 2) / dataW, (svgH - pad * 2) / dataH);
  const offX = pad + ((svgW - pad * 2) - dataW * scale) / 2;
  const offY = pad + ((svgH - pad * 2) - dataH * scale) / 2;
  return { minX, minY, scale, offX, offY };
}

function project(x: number, y: number, cm: CoordMap) {
  return {
    sx: (x - cm.minX) * cm.scale + cm.offX,
    sy: (y - cm.minY) * cm.scale + cm.offY,
  };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Ghost floor-plan layer: all rooms in the current district */
function MiddleGhostLayer({
  ctx, currentRoomId,
}: { ctx: MiddleContext; currentRoomId: string }) {
  const cm = useMemo(() =>
    buildCoordMap(ctx.rooms, SVG_W, SVG_H, 52),
    [ctx.rooms],
  );

  const roomById = useMemo(() => {
    const m: Record<string, RoomMini> = {};
    for (const r of ctx.rooms) m[r.id] = r;
    return m;
  }, [ctx.rooms]);

  return (
    <g opacity={0.18}>
      {/* Connection lines */}
      {ctx.connections.map((conn, i) => {
        const a = roomById[conn.from_id];
        const b = roomById[conn.to_id];
        if (!a || !b) return null;
        const pa = project(a.x_pos, a.y_pos, cm);
        const pb = project(b.x_pos, b.y_pos, cm);
        // Only draw each undirected pair once
        if (conn.from_id > conn.to_id) return null;
        return (
          <line key={i}
            x1={pa.sx} y1={pa.sy} x2={pb.sx} y2={pb.sy}
            stroke="#4a6070" strokeWidth={1.2} strokeDasharray="4 3"
          />
        );
      })}
      {/* Room nodes */}
      {ctx.rooms.map((r) => {
        const { sx, sy } = project(r.x_pos, r.y_pos, cm);
        const isCurr = r.id === currentRoomId;
        return (
          <g key={r.id}>
            <rect
              x={sx - 28} y={sy - 12} width={56} height={24} rx={4}
              fill={isCurr ? "rgba(200,144,48,0.25)" : r.is_safe_zone ? "rgba(46,112,72,0.18)" : "rgba(20,24,30,0.6)"}
              stroke={isCurr ? "#C89030" : r.is_safe_zone ? "#2e7048" : "#304040"}
              strokeWidth={isCurr ? 1.6 : 0.8}
            />
            <text x={sx} y={sy + 4.5} textAnchor="middle"
              fill={isCurr ? "#e8c46a" : "#6a8090"} fontSize={9.5} fontFamily="serif">
              {r.name.length > 7 ? r.name.slice(0, 6) + "…" : r.name}
            </text>
          </g>
        );
      })}
      {/* District name watermark */}
      <text
        x={SVG_W / 2} y={SVG_H - 8}
        textAnchor="middle"
        fill="#506070" fontSize={11} fontFamily="serif" letterSpacing={2}
      >
        {ctx.middle_name}
      </text>
    </g>
  );
}

const DISTRICT_COLOR: Record<string, string> = {
  "城鎮": "#a07840",
  "荒野": "#3a7040",
  "地下城": "#7040a0",
};

/** Full-size region overlay panel */
function LargeRegionOverlay({ ctx, onClose }: { ctx: LargeContext; onClose: () => void }) {
  const OW = 320; const OH = 260;
  const cm = useMemo(() => buildCoordMap(ctx.districts, OW, OH, 32), [ctx.districts]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(4,6,10,0.72)" }}
      onClick={onClose}
    >
      <div
        className="relative rounded-xl border border-stone-600/60 bg-stone-950/95 shadow-2xl p-4"
        style={{ minWidth: 360 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="font-cinzel text-sm text-gold-light tracking-widest">{ctx.large_name}</span>
          <button
            onClick={onClose}
            className="text-stone-500 hover:text-stone-300 transition-colors text-lg leading-none cursor-pointer"
          >✕</button>
        </div>

        <svg width={OW} height={OH} viewBox={`0 0 ${OW} ${OH}`}>
          {ctx.districts.map((d: DistrictMini) => {
            const { sx, sy } = project(d.x_pos, d.y_pos, cm);
            const isCurr = d.id === ctx.current_middle_id;
            const col = DISTRICT_COLOR[d.type ?? ""] ?? "#506070";
            return (
              <g key={d.id} transform={`translate(${sx}, ${sy})`}>
                {isCurr && (
                  <circle r={18} fill="none" stroke={col} strokeWidth={1.2} opacity={0.35}/>
                )}
                <circle r={isCurr ? 10 : 7}
                  fill={col} opacity={isCurr ? 0.9 : 0.4}/>
                <text y={isCurr ? -14 : -11} textAnchor="middle"
                  fill={isCurr ? col : "#506070"}
                  fontSize={isCurr ? 11 : 9.5} fontFamily="serif"
                  opacity={isCurr ? 1 : 0.65}>
                  {d.name}
                </text>
                {isCurr && (
                  <text y={16} textAnchor="middle" fill={col} fontSize={8} fontFamily="monospace" opacity={0.7}>
                    ◆ 所在地
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="flex gap-4 mt-2 px-1">
          {Object.entries(DISTRICT_COLOR).map(([type, col]) => (
            <div key={type} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: col, opacity: 0.7 }}/>
              <span className="font-inter text-xs text-stone-500">{type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Active layer: current room at center, exits positioned by direction */
function ActiveLayer({
  place, exits, onMove, moving,
}: {
  place: LookResult["place"];
  exits: Exit[];
  onMove: (d: string) => void;
  moving: boolean;
}) {
  return (
    <g>
      {/* Connection lines */}
      {exits.map((exit) => {
        const [dx, dy] = DIR_OFFSET[exit.direction] ?? [0, 0];
        return (
          <g key={exit.direction}>
            <line
              x1={ACTIVE_CX} y1={ACTIVE_CY}
              x2={ACTIVE_CX + dx} y2={ACTIVE_CY + dy}
              stroke="#405060" strokeWidth={1.5} strokeDasharray="5 3"
            />
            <text
              x={(ACTIVE_CX + ACTIVE_CX + dx) / 2}
              y={(ACTIVE_CY + ACTIVE_CY + dy) / 2 - 6}
              textAnchor="middle" fill="#506070" fontSize={11} fontFamily="monospace">
              {exit.travel_time_seconds}s
            </text>
          </g>
        );
      })}

      {/* Exit nodes */}
      {exits.map((exit) => {
        const [dx, dy] = DIR_OFFSET[exit.direction] ?? [0, 0];
        const nx = ACTIVE_CX + dx;
        const ny = ACTIVE_CY + dy;
        const label = exit.destination_name || exit.to_place_name || "???";
        return (
          <g key={exit.direction}
            transform={`translate(${nx - 48}, ${ny - 21})`}
            onClick={moving ? undefined : () => onMove(exit.direction)}
            className={moving ? "" : "cursor-pointer"}
            role={moving ? undefined : "button"}
          >
            {!moving && (
              <rect x={-3} y={-3} width={102} height={48} rx={7}
                fill="transparent" className="hover:fill-forest/5 transition-colors"/>
            )}
            <rect x={0} y={0} width={96} height={42} rx={5}
              fill="rgba(20,26,32,0.92)" stroke={moving ? "#303840" : "#304848"}
              strokeWidth={1.2}
              className={moving ? "" : "hover:stroke-forest/60 transition-colors"}
            />
            {exit.is_locked && (
              <text x={90} y={12} textAnchor="middle" fill="#805020" fontSize={10}>🔒</text>
            )}
            <text x={48} y={-9} textAnchor="middle" fill="#506060" fontSize={12} fontFamily="monospace">
              {DIR_ICON[exit.direction] ?? exit.direction}
            </text>
            <text x={48} y={26} textAnchor="middle"
              fill={moving ? "#4a5860" : "#9ab0b8"} fontSize={12} fontFamily="serif">
              {label.length > 9 ? label.slice(0, 8) + "…" : label}
            </text>
          </g>
        );
      })}

      {/* Current room glow ring */}
      <circle cx={ACTIVE_CX} cy={ACTIVE_CY} r={56}
        fill="rgba(200,144,48,0.04)" stroke="rgba(200,144,48,0.08)" strokeWidth={1}>
        <animate attributeName="r" values="54;58;54" dur="4s" repeatCount="indefinite"/>
      </circle>

      {/* Current room node */}
      <g transform={`translate(${ACTIVE_CX - 56}, ${ACTIVE_CY - 26})`}>
        <rect x={-4} y={-4} width={120} height={60} rx={8}
          fill="rgba(200,144,48,0.06)" className="animate-pulse-gold"/>
        <rect x={0} y={0} width={112} height={52} rx={6}
          fill="rgba(24,30,38,0.96)" stroke="#C89030" strokeWidth={2}/>
        <text x={56} y={31} textAnchor="middle"
          fill="#e8c46a" fontSize={14} fontFamily="serif" fontWeight="700">
          {place.name.length > 11 ? place.name.slice(0, 10) + "…" : place.name}
        </text>
      </g>

      {/* You-are-here dot */}
      <circle cx={ACTIVE_CX} cy={ACTIVE_CY} r={4} fill="#C89030" opacity={0.9}>
        <animate attributeName="opacity" values="0.9;0.4;0.9" dur="2s" repeatCount="indefinite"/>
      </circle>
    </g>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface Props {
  look: LookResult;
  onMove: (direction: string) => void;
  moving: boolean;
}

export function MapView({ look, onMove, moving }: Props) {
  const { place, exits, middle_context, large_context } = look;
  const [showRegion, setShowRegion] = useState(false);

  return (
    <div className="flex flex-col flex-1 min-w-0">
      {/* Room header */}
      <div className="flex items-start justify-between px-5 pt-4 pb-2 gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            {large_context && (
              <span className="font-inter text-xs text-stone-600 tracking-wide">
                {large_context.large_name}
              </span>
            )}
            {large_context && middle_context && (
              <span className="font-inter text-xs text-stone-700">›</span>
            )}
            {middle_context && (
              <span className="font-inter text-xs text-stone-500 tracking-wide">
                {middle_context.middle_name}
              </span>
            )}
            {middle_context && (
              <span className="font-inter text-xs text-stone-700">›</span>
            )}
          </div>
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

      {/* SVG Map — two layers stacked */}
      <div
        className="relative flex-1 mx-4 mb-2 rounded-lg overflow-hidden border border-stone-700/40 bg-stone-950/60"
        style={{ minHeight: 300, maxHeight: 360 }}
      >
        <svg
          width="100%" height="100%"
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          preserveAspectRatio="xMidYMid meet"
          className="w-full h-full"
        >
          {/* ── Layer 1: Middle ghost floor-plan (background) ── */}
          {middle_context && middle_context.rooms.length > 0 && (
            <MiddleGhostLayer
              ctx={middle_context}
              currentRoomId={place.id}
            />
          )}

          {/* ── Layer 2: Active exits + current room (foreground) ── */}
          <ActiveLayer
            place={place}
            exits={exits}
            onMove={onMove}
            moving={moving}
          />
        </svg>

        {/* Region map button — top-right corner */}
        {large_context && large_context.districts.length > 0 && (
          <button
            onClick={() => setShowRegion(true)}
            className="absolute top-2 right-2 flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-stone-600/50 bg-stone-900/80 text-stone-400 hover:border-stone-500 hover:text-stone-200 transition-all cursor-pointer text-xs font-inter"
            title="查看地區地圖"
          >
            <svg viewBox="0 0 14 14" className="w-3 h-3" fill="currentColor">
              <circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.2"/>
              <circle cx="7" cy="7" r="1.5"/>
              <line x1="7" y1="1.5" x2="7" y2="4" stroke="currentColor" strokeWidth="1"/>
              <line x1="7" y1="10" x2="7" y2="12.5" stroke="currentColor" strokeWidth="1"/>
              <line x1="1.5" y1="7" x2="4" y2="7" stroke="currentColor" strokeWidth="1"/>
              <line x1="10" y1="7" x2="12.5" y2="7" stroke="currentColor" strokeWidth="1"/>
            </svg>
            {large_context.large_name}
          </button>
        )}

        {/* Legend */}
        <div className="absolute bottom-2 right-3 flex items-center gap-3 opacity-40">
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

      {/* Region overlay modal */}
      {showRegion && large_context && (
        <LargeRegionOverlay ctx={large_context} onClose={() => setShowRegion(false)} />
      )}
    </div>
  );
}

// ─── Exit chips (used externally if needed) ───────────────────────────────────

export function ExitChip({ exit, onMove, disabled }: {
  exit: Exit; onMove: (d: string) => void; disabled: boolean
}) {
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
      onMouseEnter={(e) => { if (!disabled) (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 0 10px rgba(46,112,72,0.28)"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "none"; }}
    >
      <span className="font-mono text-base font-bold text-forest/80 group-hover:text-forest-light transition-colors">
        {dirIcon}
      </span>
      <span className="font-inter text-lg text-stone-200 group-hover:text-stone-100">{dirZh}</span>
      <span className="font-inter text-sm text-stone-600 group-hover:text-stone-400 transition-colors">
        {exit.travel_time_seconds}秒
      </span>
    </button>
  );
}
