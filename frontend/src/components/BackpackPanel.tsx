import { useEffect, useState } from "react";

interface InvItem {
  instance_id: string;
  item_id: string;
  name: string;
  description: string;
  category: string;
  quantity: number;
  durability: number;
  weight: number;
}

interface Props {
  playerId: string;
  open: boolean;
  onClose: () => void;
}

const ITEM_ICON: Record<string, string> = {
  sword: "⚔", dagger: "🗡", armor: "🛡", shield: "⛨",
  potion: "⊕", herb: "🌿", key: "⌘", torch: "🕯",
  barrel: "🛢", coin: "◎", scroll: "📜",
};

function getIcon(itemId: string): string {
  const lower = itemId.toLowerCase();
  for (const [key, icon] of Object.entries(ITEM_ICON)) {
    if (lower.includes(key)) return icon;
  }
  return "⬡";
}

export function BackpackPanel({ playerId, open, onClose }: Props) {
  const [items, setItems] = useState<InvItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch(`/api/v1/player/${playerId}/inventory`)
      .then((r) => r.json())
      .then((data) => setItems(data.items ?? []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [open, playerId]);

  return (
    <>
      {/* 遮罩 */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px]"
          onClick={onClose}
        />
      )}

      {/* 側邊抽屜 */}
      <div
        className={`fixed top-0 right-0 h-full w-80 z-50 flex flex-col
          bg-stone-950/95 border-l border-stone-700/40
          transition-transform duration-300 ease-in-out
          ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ boxShadow: open ? "-8px 0 32px rgba(0,0,0,0.6)" : "none" }}
      >
        {/* 標題 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-stone-700/40">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🎒</span>
            <span className="font-inter text-base font-semibold text-stone-200 tracking-wide">
              揹包
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded text-stone-500
              hover:text-stone-200 hover:bg-stone-800/60 transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* 內容 */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {loading ? (
            <p className="font-inter text-sm text-stone-600 italic mt-4 text-center">
              載入中…
            </p>
          ) : items.length === 0 ? (
            <p className="font-inter text-sm text-stone-600 italic mt-4 text-center">
              揹包是空的。
            </p>
          ) : (
            items.map((item) => (
              <div
                key={item.instance_id}
                className="flex items-start gap-3 px-3 py-3 rounded border border-stone-700/40 bg-stone-900/60"
              >
                <span className="text-2xl mt-0.5 shrink-0">{getIcon(item.item_id)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-inter text-sm font-semibold text-stone-100">
                      {item.name}
                    </span>
                    {item.quantity > 1 && (
                      <span className="font-mono text-xs text-stone-500">×{item.quantity}</span>
                    )}
                  </div>
                  {item.description && (
                    <p className="font-inter text-xs text-stone-500 mt-1 leading-relaxed">
                      {item.description}
                    </p>
                  )}
                  <div className="flex gap-3 mt-1.5">
                    {item.durability < 999 && (
                      <span className="font-inter text-xs text-stone-600">
                        耐久 {item.durability}
                      </span>
                    )}
                    {item.category && (
                      <span className="font-inter text-xs text-stone-600">
                        {item.category}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* 底部計數 */}
        {!loading && items.length > 0 && (
          <div className="px-5 py-3 border-t border-stone-700/30">
            <span className="font-inter text-xs text-stone-600">
              共 {items.length} 種物品
            </span>
          </div>
        )}
      </div>
    </>
  );
}
