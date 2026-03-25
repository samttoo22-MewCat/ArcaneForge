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

export function InventoryPanel({ items, npcs, onPickup, disabled }: Props) {
  return (
    <div className="flex border-t border-stone-700/30 bg-stone-950/70 shrink-0">
      {/* Items on the ground */}
      <div className="flex-1 px-4 py-2.5">
        <p className="font-cinzel text-[9px] tracking-widest text-stone-500 uppercase mb-2">
          Items in room
        </p>
        {items.length === 0 ? (
          <p className="font-mono text-[11px] text-stone-700 italic">Nothing of interest.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {items.map((item) => (
              <button
                key={item.instance_id}
                onClick={() => onPickup(item.instance_id)}
                disabled={disabled}
                className="flex items-center gap-2 px-3 py-1.5 rounded border border-stone-600/40 bg-stone-900/60
                  hover:border-xp/40 hover:bg-stone-800/60 cursor-pointer
                  disabled:opacity-40 disabled:cursor-not-allowed
                  transition-all duration-150 group"
              >
                <span className="text-sm text-stone-400 group-hover:text-xp-bright transition-colors">
                  {getIcon(item.item_id)}
                </span>
                <span className="font-mono text-[11px] text-stone-300">{item.item_id}</span>
                {item.quantity > 1 && (
                  <span className="font-mono text-[10px] text-stone-600">×{item.quantity}</span>
                )}
                <span className="font-mono text-[9px] text-xp/60 opacity-0 group-hover:opacity-100 transition-opacity">
                  pick up
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* NPCs present */}
      {npcs.length > 0 && (
        <>
          <div className="w-px self-stretch bg-stone-700/30"/>
          <div className="px-4 py-2.5 min-w-0">
            <p className="font-cinzel text-[9px] tracking-widest text-stone-500 uppercase mb-2">
              Present
            </p>
            <div className="flex flex-wrap gap-2">
              {npcs.map((npc) => {
                const stateColor = NPC_STATE_COLOR[npc.behavior_state ?? "idle"] ?? "#5A5248";
                return (
                  <div key={npc.id}
                    className="flex items-center gap-2 px-3 py-1.5 rounded border border-stone-700/40 bg-stone-900/40">
                    <div className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: stateColor, boxShadow: `0 0 4px ${stateColor}` }}/>
                    <span className="font-inter text-[11px] text-stone-300">{npc.name}</span>
                    {npc.behavior_state && (
                      <span className="font-mono text-[9px]" style={{ color: stateColor }}>
                        {npc.behavior_state}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
