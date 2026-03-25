import type { ItemInstance, NPC } from "../types";

interface Props {
  items: ItemInstance[];
  npcs: NPC[];
  onPickup: (instanceId: string) => void;
  disabled: boolean;
}

const ITEM_ICON: Record<string, string> = {
  default: "⬡",
  sword: "⚔",
  shield: "⛨",
  potion: "⊕",
  gold: "◎",
  key: "⌘",
  scroll: "⊞",
  armor: "⛧",
};

function getIcon(itemId: string): string {
  for (const [key, icon] of Object.entries(ITEM_ICON)) {
    if (itemId.toLowerCase().includes(key)) return icon;
  }
  return ITEM_ICON.default;
}

const NPC_STATE_COLOR: Record<string, string> = {
  idle: "#5A5248",
  hostile: "#C03030",
  friendly: "#2A8A2A",
  trading: "#C8941E",
};

const NPC_STATE_ZH: Record<string, string> = {
  idle: "待機",
  hostile: "敵對",
  friendly: "友好",
  trading: "交易中",
};

export function InventoryPanel({ items, npcs, onPickup, disabled }: Props) {
  return (
    <div className="w-48 shrink-0 flex flex-col border-l border-stone-700/30 bg-stone-950/70 overflow-y-auto">
      {/* 房間物品 */}
      <div className="px-3 py-3 border-b border-stone-700/20">
        <p className="font-inter text-xs font-semibold tracking-wide text-stone-500 mb-2 uppercase">
          房間物品
        </p>
        {items.length === 0 ? (
          <p className="font-inter text-xs text-stone-600 italic">空無一物</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {items.map((item) => (
              <button
                key={item.instance_id}
                onClick={() => onPickup(item.instance_id)}
                disabled={disabled}
                className="flex items-center gap-2 px-2.5 py-2 rounded border border-stone-600/40 bg-stone-900/60
                  hover:border-forest/50 hover:bg-forest/10 cursor-pointer text-left w-full
                  disabled:opacity-40 disabled:cursor-not-allowed
                  transition-all duration-150 group"
              >
                <span className="text-base text-stone-400 group-hover:text-forest-light transition-colors shrink-0">
                  {getIcon(item.item_id)}
                </span>
                <span className="font-inter text-sm text-stone-200 truncate">
                  {item.name ?? item.item_id}
                </span>
                {item.quantity > 1 && (
                  <span className="font-mono text-xs text-stone-500 shrink-0">×{item.quantity}</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 在場者 */}
      {npcs.length > 0 && (
        <div className="px-3 py-3">
          <p className="font-inter text-xs font-semibold tracking-wide text-stone-500 mb-2 uppercase">
            在場者
          </p>
          <div className="flex flex-col gap-1.5">
            {npcs.map((npc) => {
              const stateColor = NPC_STATE_COLOR[npc.behavior_state ?? "idle"] ?? "#5A5248";
              const stateZh = NPC_STATE_ZH[npc.behavior_state ?? "idle"] ?? npc.behavior_state;
              return (
                <div key={npc.id}
                  className="flex items-center gap-2 px-2.5 py-2 rounded border border-stone-700/40 bg-stone-900/40">
                  <div className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: stateColor, boxShadow: `0 0 5px ${stateColor}` }}/>
                  <span className="font-inter text-sm text-stone-200 truncate">{npc.name}</span>
                  {npc.behavior_state && (
                    <span className="font-inter text-xs font-medium shrink-0" style={{ color: stateColor }}>
                      {stateZh}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
