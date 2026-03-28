import { useEffect, useState } from "react";
import { api } from "../api";
import type { Ability, NPC } from "../types";

// ── Element icons ─────────────────────────────────────────────────────────────
const ELEMENT_ICON: Record<string, string> = {
  fire: "🔥", frost: "❄", ice: "❄", lightning: "⚡", arcane: "✧",
  holy: "✦", nature: "🌿", shadow: "🌑", physical: "⚔",
};
const ELEMENT_COLOR: Record<string, string> = {
  fire: "text-orange-400", frost: "text-sky-300", ice: "text-sky-300",
  lightning: "text-yellow-300", arcane: "text-violet-400",
  holy: "text-amber-300", nature: "text-green-400",
  shadow: "text-purple-400", physical: "text-stone-400",
};

// ── Effect type labels ────────────────────────────────────────────────────────
const EFFECT_LABEL: Record<string, string> = {
  damage_modifier: "傷害", heal: "治療", status_apply: "狀態",
  passive: "被動", utility: "工具", social_outcome: "社交",
  environment_change: "環境",
};
const EFFECT_COLOR: Record<string, string> = {
  damage_modifier: "text-red-400 border-red-900/60",
  heal: "text-green-400 border-green-900/60",
  status_apply: "text-purple-400 border-purple-900/60",
  passive: "text-stone-500 border-stone-700/60",
  utility: "text-sky-400 border-sky-900/60",
  social_outcome: "text-pink-400 border-pink-900/60",
  environment_change: "text-teal-400 border-teal-900/60",
};

// ── Target label ──────────────────────────────────────────────────────────────
const TARGET_LABEL: Record<string, string> = {
  self: "自身", single: "單體", aoe: "範圍", single_friendly: "友方",
};

function needsTarget(ability: Ability): boolean {
  if (ability.is_passive) return false;
  const target = ability.target ?? "self";
  const effect = ability.effect_type;
  if (target === "self" || target === "single_friendly") return false;
  if (effect === "heal") return false;
  if (effect === "utility" || effect === "social_outcome" || effect === "environment_change") return false;
  return target === "single" || target === "aoe";
}

// ── AbilityCard ───────────────────────────────────────────────────────────────
interface CardProps {
  ability: Ability;
  playerMp: number;
  onUse: (ability: Ability) => void;
}

function AbilityCard({ ability, playerMp, onUse }: CardProps) {
  const isPassive = ability.is_passive;
  const isLocked = !ability.is_unlocked;
  const onCooldown = ability.cooldown_seconds_remaining > 0;
  const noMp = playerMp < ability.mp_cost;
  const disabled = isPassive || isLocked || onCooldown || noMp;

  const effectKey = ability.effect_type;
  const effectLabel = EFFECT_LABEL[effectKey] ?? effectKey;
  const effectColorClass = EFFECT_COLOR[effectKey] ?? "text-stone-400 border-stone-700/60";

  const elemIcon = ability.element ? (ELEMENT_ICON[ability.element] ?? "✧") : null;
  const elemColorClass = ability.element ? (ELEMENT_COLOR[ability.element] ?? "text-stone-400") : "";

  let statusText = "";
  let statusColor = "text-stone-500";
  if (isLocked) { statusText = ability.locked_reason; statusColor = "text-stone-600"; }
  else if (isPassive) { statusText = "被動 · 自動生效"; statusColor = "text-stone-600"; }
  else if (onCooldown) { statusText = `冷卻中 ${ability.cooldown_seconds_remaining}s`; statusColor = "text-amber-600"; }
  else if (noMp) { statusText = `MP 不足（需 ${ability.mp_cost}）`; statusColor = "text-red-600"; }

  return (
    <div
      className={`rounded border p-3 transition-all duration-150 ${
        disabled
          ? "border-stone-800/60 bg-stone-900/40 opacity-60"
          : "border-stone-700/60 bg-stone-900/80 hover:border-stone-600/80 hover:bg-stone-800/80"
      }`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          {/* Element icon for spells */}
          {elemIcon && (
            <span className={`text-sm shrink-0 ${elemColorClass}`}>{elemIcon}</span>
          )}
          <span className="font-inter font-semibold text-sm text-stone-200 truncate">
            {ability.name}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {/* Effect badge */}
          <span className={`font-inter text-[10px] px-1.5 py-0.5 rounded border ${effectColorClass}`}>
            {effectLabel}
          </span>
          {/* Lock icon */}
          {isLocked && (
            <svg viewBox="0 0 12 12" className="w-3 h-3 text-stone-600 shrink-0" fill="currentColor">
              <rect x="2" y="5" width="8" height="6" rx="1"/>
              <path d="M4 5V3.5a2 2 0 0 1 4 0V5" fill="none" stroke="currentColor" strokeWidth="1.2"/>
            </svg>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="font-inter text-xs text-stone-400 leading-relaxed mb-2.5 line-clamp-2">
        {ability.description}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* MP cost */}
          {ability.mp_cost > 0 && (
            <span className="font-mono text-[10px] text-blue-400">
              ✦ {ability.mp_cost} MP
            </span>
          )}
          {/* Cooldown */}
          {ability.cooldown_turns > 0 && (
            <span className="font-mono text-[10px] text-stone-500">
              ⏱ {ability.cooldown_turns}回
            </span>
          )}
          {/* Target */}
          <span className="font-inter text-[10px] text-stone-600">
            {TARGET_LABEL[ability.target ?? "self"] ?? ability.target}
          </span>
        </div>

        {/* Status / Use button */}
        {statusText ? (
          <span className={`font-inter text-[10px] ${statusColor}`}>{statusText}</span>
        ) : (
          <button
            onClick={() => onUse(ability)}
            className="font-inter text-[10px] font-semibold px-2.5 py-1 rounded border
              border-violet-600/50 text-violet-300 bg-violet-900/20
              hover:border-violet-500/80 hover:bg-violet-800/30
              transition-all duration-150 cursor-pointer"
          >
            施放
          </button>
        )}
      </div>
    </div>
  );
}

// ── SkillPanel ────────────────────────────────────────────────────────────────
interface Props {
  playerId: string;
  open: boolean;
  onClose: () => void;
  currentNpcs: NPC[];
  playerMp: number;
  onSkillUsed: () => void;
}

export function SkillPanel({ playerId, open, onClose, currentNpcs, playerMp, onSkillUsed }: Props) {
  const [abilities, setAbilities] = useState<Ability[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"skill" | "spell">("skill");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackOk, setFeedbackOk] = useState(true);
  const [targeting, setTargeting] = useState<Ability | null>(null);

  useEffect(() => {
    if (!open) { setTargeting(null); setFeedback(null); return; }
    setLoading(true);
    api.getAbilities(playerId)
      .then((data) => setAbilities(data.abilities))
      .catch(() => setAbilities([]))
      .finally(() => setLoading(false));
  }, [open, playerId]);

  const filtered = abilities.filter((a) => a.ability_type === tab);
  const skillCount = abilities.filter((a) => a.ability_type === "skill").length;
  const spellCount = abilities.filter((a) => a.ability_type === "spell").length;

  async function executeAbility(ability: Ability, targetId?: string) {
    setFeedback(null);
    setTargeting(null);
    try {
      const result = await api.useSkill(playerId, ability.id, ability.ability_type, targetId);
      const msg = result.heal > 0
        ? `✓ 回復 ${result.heal} HP`
        : result.damage > 0
        ? `✓ 造成 ${result.damage} 傷害${result.target_defeated ? "，目標已倒下！" : ""}`
        : `✓ ${result.narrative_hint || "已使用"}`;
      setFeedback(msg);
      setFeedbackOk(true);
      onSkillUsed();
      // Refresh cooldowns
      const fresh = await api.getAbilities(playerId);
      setAbilities(fresh.abilities);
    } catch (err) {
      const raw = err instanceof Error ? err.message : String(err);
      // Strip leading HTTP status code if present
      const msg = raw.replace(/^\d+:\s*/, "").replace(/^\{"detail":"([^"]+)"\}$/, "$1");
      setFeedback(`✗ ${msg}`);
      setFeedbackOk(false);
    }
  }

  function handleUse(ability: Ability) {
    if (needsTarget(ability)) {
      setTargeting(ability);
    } else {
      executeAbility(ability);
    }
  }

  const liveNpcs = currentNpcs.filter((n) => n.behavior_state !== "dead");

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px]"
          onClick={() => { setTargeting(null); onClose(); }}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-96 z-50 flex flex-col
          bg-stone-950 border-l border-stone-700/40
          transition-transform duration-300 ease-out
          ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ boxShadow: open ? "-8px 0 40px rgba(0,0,0,0.7)" : "none" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-stone-700/40 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-violet-400 text-base">✦</span>
            <span className="font-inter font-semibold text-sm text-stone-200 tracking-wide">
              技能與法術
            </span>
          </div>
          <button
            onClick={() => { setTargeting(null); onClose(); }}
            className="text-stone-500 hover:text-stone-300 transition-colors cursor-pointer p-1"
          >
            <svg viewBox="0 0 14 14" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M2 2l10 10M12 2L2 12" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-stone-700/40 shrink-0">
          {(["skill", "spell"] as const).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setTargeting(null); }}
              className={`flex-1 py-2.5 font-inter text-xs font-semibold tracking-wider transition-colors cursor-pointer
                ${tab === t
                  ? "text-violet-300 border-b-2 border-violet-500 bg-violet-900/10"
                  : "text-stone-500 hover:text-stone-300"
                }`}
            >
              {t === "skill" ? `技能 ${skillCount}` : `法術 ${spellCount}`}
            </button>
          ))}
        </div>

        {/* Target selection (overlay within drawer) */}
        {targeting && (
          <div className="border-b border-amber-700/40 bg-amber-950/30 px-4 py-3 shrink-0">
            <div className="flex items-center justify-between mb-2">
              <span className="font-inter text-xs text-amber-300 font-semibold">
                選擇目標 — {targeting.name}
              </span>
              <button
                onClick={() => setTargeting(null)}
                className="font-inter text-[10px] text-stone-500 hover:text-stone-300 cursor-pointer"
              >
                取消
              </button>
            </div>
            {liveNpcs.length === 0 ? (
              <p className="font-inter text-xs text-stone-500">此地沒有可攻擊的目標。</p>
            ) : (
              <div className="flex flex-col gap-1">
                {liveNpcs.map((npc) => (
                  <button
                    key={npc.id}
                    onClick={() => executeAbility(targeting, npc.id)}
                    className="text-left px-3 py-1.5 rounded border border-stone-700/60 bg-stone-900/60
                      hover:border-red-700/60 hover:bg-red-950/30 hover:text-red-300
                      font-inter text-xs text-stone-300 transition-all cursor-pointer"
                  >
                    {npc.name}
                    {npc.npc_type && (
                      <span className="ml-2 text-stone-600 text-[10px]">({npc.npc_type})</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Ability list */}
        <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-2">
          {loading ? (
            <p className="font-inter text-xs text-stone-500 text-center py-8">載入中…</p>
          ) : filtered.length === 0 ? (
            <p className="font-inter text-xs text-stone-500 text-center py-8">
              目前沒有可用的{tab === "skill" ? "技能" : "法術"}。
            </p>
          ) : (
            filtered.map((ability) => (
              <AbilityCard
                key={ability.id}
                ability={ability}
                playerMp={playerMp}
                onUse={handleUse}
              />
            ))
          )}
        </div>

        {/* Feedback bar */}
        {feedback && (
          <div
            className={`shrink-0 px-4 py-2.5 border-t text-xs font-inter
              ${feedbackOk
                ? "border-green-900/40 bg-green-950/30 text-green-300"
                : "border-red-900/40 bg-red-950/30 text-red-400"
              }`}
          >
            {feedback}
          </div>
        )}
      </div>
    </>
  );
}
