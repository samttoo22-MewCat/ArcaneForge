import { useEffect, useState } from "react";
import { api } from "../api";
import type { CraftableItem } from "../types";

const CATEGORY_ICON: Record<string, string> = {
  armor: "🛡", weapon: "⚔", potion: "⊕", consumable: "⊕",
  tool: "🕯", material: "📦", misc: "⬡",
};

function getCategoryIcon(category: string): string {
  for (const [key, icon] of Object.entries(CATEGORY_ICON)) {
    if (category.toLowerCase().includes(key)) return icon;
  }
  return "⬡";
}

interface Props {
  playerId: string;
  open: boolean;
  onClose: () => void;
  onCrafted: () => void;  // refresh inventory / player after craft
}

export function CraftPanel({ playerId, open, onClose, onCrafted }: Props) {
  const [items, setItems] = useState<CraftableItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [crafting, setCrafting] = useState<string | null>(null);  // item_id being crafted
  const [feedback, setFeedback] = useState<{ msg: string; ok: boolean } | null>(null);

  useEffect(() => {
    if (!open) { setFeedback(null); return; }
    setLoading(true);
    api.getCraftable(playerId)
      .then((data) => setItems(data.craftable))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [open, playerId]);

  async function handleCraft(item: CraftableItem) {
    if (!item.can_craft || crafting) return;
    setCrafting(item.item_id);
    setFeedback(null);
    try {
      await api.craftItem(playerId, item.item_id);
      setFeedback({ msg: `✓ 成功製作「${item.name}」！`, ok: true });
      onCrafted();
      // Refresh craftable list to update ingredient counts
      const fresh = await api.getCraftable(playerId);
      setItems(fresh.craftable);
    } catch (err) {
      const raw = err instanceof Error ? err.message : String(err);
      const msg = raw.replace(/^\d+:\s*/, "").replace(/^\{"detail":"([^"]+)"\}$/, "$1");
      setFeedback({ msg: `✗ ${msg}`, ok: false });
    } finally {
      setCrafting(null);
    }
  }

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px]"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-88 z-50 flex flex-col
          bg-stone-950 border-l border-stone-700/40
          transition-transform duration-300 ease-out
          ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ width: "22rem", boxShadow: open ? "-8px 0 40px rgba(0,0,0,0.7)" : "none" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-stone-700/40 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-amber-500 text-sm">⚒</span>
            <span className="font-inter font-semibold text-sm text-stone-200 tracking-wide">
              合成工坊
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-stone-500 hover:text-stone-300 transition-colors cursor-pointer p-1"
          >
            <svg viewBox="0 0 14 14" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M2 2l10 10M12 2L2 12" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* Item list */}
        <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
          {loading ? (
            <p className="font-inter text-xs text-stone-500 text-center py-10">載入配方中…</p>
          ) : items.length === 0 ? (
            <p className="font-inter text-xs text-stone-500 text-center py-10">沒有可製作的物品。</p>
          ) : (
            items.map((item) => (
              <CraftCard
                key={item.item_id}
                item={item}
                crafting={crafting === item.item_id}
                onCraft={() => handleCraft(item)}
              />
            ))
          )}
        </div>

        {/* Feedback bar */}
        {feedback && (
          <div
            className={`shrink-0 px-4 py-2.5 border-t font-inter text-xs
              ${feedback.ok
                ? "border-green-900/40 bg-green-950/30 text-green-300"
                : "border-red-900/40 bg-red-950/30 text-red-400"
              }`}
          >
            {feedback.msg}
          </div>
        )}
      </div>
    </>
  );
}

// ── CraftCard ─────────────────────────────────────────────────────────────────

interface CardProps {
  item: CraftableItem;
  crafting: boolean;
  onCraft: () => void;
}

function CraftCard({ item, crafting, onCraft }: CardProps) {
  const icon = getCategoryIcon(item.category);

  return (
    <div
      className={`rounded-lg border p-4 transition-all duration-150 ${
        item.can_craft
          ? "border-amber-700/40 bg-stone-900/90 hover:border-amber-600/60"
          : "border-stone-800/50 bg-stone-900/50 opacity-75"
      }`}
    >
      {/* Item header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg shrink-0">{icon}</span>
          <div className="min-w-0">
            <span className="font-inter font-bold text-sm text-stone-100 block truncate">
              {item.name}
            </span>
            <span className="font-inter text-[10px] text-stone-500 capitalize">{item.category}</span>
          </div>
        </div>
        <button
          onClick={onCraft}
          disabled={!item.can_craft || crafting}
          className={`shrink-0 px-3 py-1.5 rounded border font-inter text-xs font-semibold transition-all duration-150 cursor-pointer
            ${item.can_craft && !crafting
              ? "border-amber-600/60 bg-amber-900/20 text-amber-300 hover:border-amber-500/80 hover:bg-amber-800/30"
              : "border-stone-700/40 text-stone-600 cursor-not-allowed"
            }`}
        >
          {crafting ? "合成中…" : "合成"}
        </button>
      </div>

      {/* Description */}
      {item.description && (
        <p className="font-inter text-xs text-stone-400 leading-relaxed mb-3">
          {item.description}
        </p>
      )}

      {/* Recipe */}
      <div>
        <p className="font-inter text-[10px] text-stone-500 uppercase tracking-wider mb-1.5">
          所需材料
        </p>
        <div className="flex flex-col gap-1">
          {item.ingredients.map((ing) => (
            <div key={ing.item_id} className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    ing.sufficient ? "bg-green-400" : "bg-red-500"
                  }`}
                />
                <span className={`font-inter text-xs ${ing.sufficient ? "text-stone-300" : "text-stone-500"}`}>
                  {ing.name}
                </span>
              </div>
              <span
                className={`font-mono text-xs tabular-nums ${
                  ing.sufficient ? "text-green-400" : "text-red-400"
                }`}
              >
                {ing.have}/{ing.needed}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
