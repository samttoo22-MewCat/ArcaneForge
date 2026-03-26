import { useEffect, useState } from "react";
import { api } from "../api";
import type { ShopItem } from "../types";

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
  npcId: string;
  npcName: string;
  open: boolean;
  onClose: () => void;
}

const ITEM_ICON: Record<string, string> = {
  sword: "⚔", dagger: "🗡", armor: "🛡", shield: "⛨",
  potion: "⊕", herb: "🌿", key: "⌘", torch: "🕯",
  coin: "◎", scroll: "📜", hide: "🧵", vial: "🧪",
  cloth: "🧶", wood: "🪵",
};

function getIcon(itemId: string): string {
  const lower = itemId.toLowerCase();
  for (const [key, icon] of Object.entries(ITEM_ICON)) {
    if (lower.includes(key)) return icon;
  }
  return "⬡";
}

function estimateSellPrice(item: InvItem): number {
  return Math.max(1, item.quantity);
}

export function ShopPanel({ playerId, npcId, npcName, open, onClose }: Props) {
  const [tab, setTab] = useState<"buy" | "sell">("buy");
  const [shopItems, setShopItems] = useState<ShopItem[]>([]);
  const [invItems, setInvItems] = useState<InvItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [coinBalance, setCoinBalance] = useState(0);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setFeedback(null);

    Promise.all([
      api.getNpcShop(npcId),
      api.getInventory(playerId),
    ]).then(([shopData, invData]) => {
      setShopItems(shopData.shop_inventory);
      setInvItems(invData.items ?? []);
      // Calculate coin balance
      const coins = (invData.items ?? []).filter(i => i.item_id === "coin_copper");
      setCoinBalance(coins.reduce((sum, c) => sum + c.quantity, 0));
    }).catch(() => {
      setShopItems([]);
      setInvItems([]);
    }).finally(() => setLoading(false));
  }, [open, npcId, playerId]);

  async function handleBuy(item: ShopItem) {
    const qty = quantities[item.item_id] ?? 1;
    setFeedback(null);
    try {
      await api.buyItem(playerId, npcId, item.item_id, qty);
      setFeedback(`✓ 購買了 ${item.name} × ${qty}`);
      // Refresh shop and inventory
      const [shopData, invData] = await Promise.all([
        api.getNpcShop(npcId),
        api.getInventory(playerId),
      ]);
      setShopItems(shopData.shop_inventory);
      setInvItems(invData.items ?? []);
      const coins = (invData.items ?? []).filter(i => i.item_id === "coin_copper");
      setCoinBalance(coins.reduce((sum, c) => sum + c.quantity, 0));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setFeedback(`✗ ${msg}`);
    }
  }

  async function handleSell(item: InvItem) {
    setFeedback(null);
    try {
      await api.sellItem(playerId, npcId, item.instance_id);
      setFeedback(`✓ 出售了 ${item.name}`);
      const invData = await api.getInventory(playerId);
      setInvItems(invData.items ?? []);
      const coins = (invData.items ?? []).filter(i => i.item_id === "coin_copper");
      setCoinBalance(coins.reduce((sum, c) => sum + c.quantity, 0));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setFeedback(`✗ ${msg}`);
    }
  }

  const sellableItems = invItems.filter(i => i.item_id !== "coin_copper");

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px]" onClick={onClose} />
      )}

      <div
        className={`fixed top-0 right-0 h-full w-96 z-50 flex flex-col
          bg-stone-950/97 border-l border-stone-700/40
          transition-transform duration-300 ease-in-out
          ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ boxShadow: open ? "-8px 0 32px rgba(0,0,0,0.7)" : "none" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-stone-700/40">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🛒</span>
            <div>
              <span className="font-cinzel text-base font-semibold text-stone-200 tracking-wide">
                {npcName}
              </span>
              <p className="font-inter text-xs text-stone-500">商店</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-inter text-sm text-gold">◎ {coinBalance}</span>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded text-stone-500
                hover:text-stone-200 hover:bg-stone-800/60 transition-colors cursor-pointer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-stone-700/40">
          {(["buy", "sell"] as const).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setFeedback(null); }}
              className={`flex-1 py-2.5 font-inter text-sm font-semibold tracking-wide transition-colors cursor-pointer
                ${tab === t
                  ? "text-gold border-b-2 border-gold bg-gold/5"
                  : "text-stone-500 hover:text-stone-300"
                }`}
            >
              {t === "buy" ? "購買" : "出售"}
            </button>
          ))}
        </div>

        {/* Feedback */}
        {feedback && (
          <div className={`mx-4 mt-3 px-3 py-2 rounded text-xs font-inter
            ${feedback.startsWith("✓")
              ? "bg-forest/20 border border-forest/30 text-green-300"
              : "bg-red-900/20 border border-red-700/30 text-red-300"}`}>
            {feedback}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {loading ? (
            <p className="font-inter text-sm text-stone-600 italic mt-6 text-center">載入中…</p>
          ) : tab === "buy" ? (
            shopItems.length === 0 ? (
              <p className="font-inter text-sm text-stone-600 italic mt-6 text-center">沒有商品。</p>
            ) : (
              shopItems.map((item) => {
                const qty = quantities[item.item_id] ?? 1;
                const totalCost = item.price * qty;
                const canAfford = coinBalance >= totalCost;
                const inStock = item.stock > 0;
                return (
                  <div
                    key={item.item_id}
                    className="flex items-start gap-3 px-3 py-3 rounded border border-stone-700/40 bg-stone-900/60"
                  >
                    <span className="text-2xl mt-0.5 shrink-0">{getIcon(item.item_id)}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <span className="font-inter text-sm font-semibold text-stone-100">{item.name}</span>
                        <span className="font-mono text-xs text-gold shrink-0">◎ {item.price}</span>
                      </div>
                      {item.description && (
                        <p className="font-inter text-xs text-stone-500 mt-0.5 leading-snug">{item.description}</p>
                      )}
                      <div className="flex items-center gap-2 mt-2">
                        <span className="font-inter text-xs text-stone-600">
                          庫存 {item.stock}
                        </span>
                        <div className="flex items-center gap-1 ml-auto">
                          <button
                            onClick={() => setQuantities(q => ({ ...q, [item.item_id]: Math.max(1, (q[item.item_id] ?? 1) - 1) }))}
                            className="w-6 h-6 flex items-center justify-center rounded bg-stone-800 text-stone-400
                              hover:bg-stone-700 hover:text-stone-200 transition-colors cursor-pointer text-sm"
                          >−</button>
                          <span className="font-mono text-sm text-stone-300 w-6 text-center">{qty}</span>
                          <button
                            onClick={() => setQuantities(q => ({ ...q, [item.item_id]: Math.min(item.stock, (q[item.item_id] ?? 1) + 1) }))}
                            className="w-6 h-6 flex items-center justify-center rounded bg-stone-800 text-stone-400
                              hover:bg-stone-700 hover:text-stone-200 transition-colors cursor-pointer text-sm"
                          >+</button>
                          <button
                            onClick={() => handleBuy(item)}
                            disabled={!inStock || !canAfford}
                            className="ml-1 px-3 py-1 rounded border text-xs font-inter font-semibold
                              transition-all duration-150 cursor-pointer
                              border-gold/40 bg-gold/10 text-gold hover:bg-gold/25
                              disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            購買 ◎{totalCost}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )
          ) : (
            sellableItems.length === 0 ? (
              <p className="font-inter text-sm text-stone-600 italic mt-6 text-center">揹包是空的。</p>
            ) : (
              sellableItems.map((item) => {
                const sellPrice = estimateSellPrice(item);
                return (
                  <div
                    key={item.instance_id}
                    className="flex items-start gap-3 px-3 py-3 rounded border border-stone-700/40 bg-stone-900/60"
                  >
                    <span className="text-2xl mt-0.5 shrink-0">{getIcon(item.item_id)}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-inter text-sm font-semibold text-stone-100">{item.name}</span>
                        {item.quantity > 1 && (
                          <span className="font-mono text-xs text-stone-500">×{item.quantity}</span>
                        )}
                      </div>
                      {item.description && (
                        <p className="font-inter text-xs text-stone-500 mt-0.5 leading-snug">{item.description}</p>
                      )}
                      <div className="flex items-center justify-between mt-2">
                        <span className="font-inter text-xs text-stone-600">{item.category}</span>
                        <button
                          onClick={() => handleSell(item)}
                          className="px-3 py-1 rounded border border-stone-600/40 bg-stone-800/40
                            text-xs font-inter font-semibold text-stone-300
                            hover:border-stone-500/60 hover:text-stone-100 hover:bg-stone-700/40
                            cursor-pointer transition-all duration-150"
                        >
                          出售 ◎{sellPrice}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )
          )}
        </div>
      </div>
    </>
  );
}
