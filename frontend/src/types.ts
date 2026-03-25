export interface Player {
  id: string;
  name: string;
  hp: number;
  max_hp: number;
  mp: number;
  max_mp: number;
  atk: number;
  def: number;
  spd: number;
  current_place_id: string;
  is_traveling: boolean;
  travel_destination_id?: string;
  travel_arrives_at?: number;
  inventory?: InventoryItem[];
}

export interface Exit {
  direction: string;
  to_place_id?: string;
  to_place_name?: string;
  destination_name?: string;   // returned by /look endpoint
  exit_description: string;
  travel_time_seconds: number;
  transition_description?: string;
  is_locked?: boolean;
}

export interface Place {
  id: string;
  name: string;
  description: string;
  parent_middle_id?: string;
}

export interface NPC {
  id: string;
  name: string;
  behavior_state?: string;
}

export interface ItemInstance {
  instance_id: string;
  item_id: string;
  quantity: number;
}

export interface InventoryItem {
  instance_id: string;
  item_id: string;
  name: string;
  quantity: number;
  description?: string;
}

export interface LookResult {
  place: Place;
  exits: Exit[];
  npcs: NPC[];
  items: ItemInstance[];
  player_traveling: boolean;
  travel_arrives_at?: number;
}

export type EventKind =
  | "player_traveling"
  | "player_arrived"
  | "player_said"
  | "combat_started"
  | "combat_round"
  | "combat_ended"
  | "npc_action"
  | "world_state_change"
  | "system_announcement"
  | "grab_contest_open"
  | "grab_contest_resolved";

export interface GameEvent {
  id: string;
  event_type: EventKind;
  timestamp: number;
  [key: string]: unknown;
}

export interface GameState {
  player: Player | null;
  look: LookResult | null;
  events: GameEvent[];
  connected: boolean;
}
