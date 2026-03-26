/** TypeScript types mirroring Python server/dm/schemas.py */

export type EffectType =
  | "damage_modifier"
  | "heal"
  | "status_apply"
  | "environment_change"
  | "social_outcome"
  | "item_transform"
  | "no_effect";

export type TierName =
  | "large_success"
  | "medium_success"
  | "small_success"
  | "small_failure"
  | "medium_failure"
  | "large_failure";

export const ALL_TIERS: TierName[] = [
  "large_success", "medium_success", "small_success",
  "small_failure", "medium_failure", "large_failure",
];

export interface OutcomeEntry {
  narrative: string;
  effect_type: EffectType;
  status_to_apply?: string | null;
  status_target?: string | null;
  item_consumed?: string | null;
}

export interface DMRuling {
  feasible: boolean;
  violation_reason?: string;
  action_type?: "combat" | "social" | "explore" | "magic" | "other";
  relevant_stat?: "atk" | "def" | "spd" | "luk";
  difficulty?: number;
  threshold?: number;
  outcomes?: Record<TierName, OutcomeEntry>;
}

export interface DMPromptPacket {
  payload: Record<string, unknown>;
  nonce: string;
  timestamp: number;
  session_id: string;
  signature: string;
}

export interface DMRulingSubmission {
  nonce: string;
  timestamp: number;
  session_id: string;
  signature: string;
  ruling: DMRuling;
}

export interface DMRulingAppliedEvent {
  event_type: "dm_ruling_applied";
  player_id: string;
  feasible: boolean;
  tier?: TierName | "";
  raw_roll?: number;
  final_roll?: number;
  threshold?: number;
  relevant_stat?: string;
  stat_value?: number;
  difficulty?: number;
  effect_type?: EffectType;
  modifier?: number;
  narrative_hint?: string;
  status_applied?: string | null;
  item_consumed?: string | null;
  timestamp: number;
}
