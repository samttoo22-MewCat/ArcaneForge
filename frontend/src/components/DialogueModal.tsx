import { useState } from "react";

type Intent = "say" | "persuade" | "threaten" | "bribe";

interface Props {
  npcId: string;
  npcName: string;
  npcType: string;
  dialogue: string;
  opensShop: boolean;
  onOpenShop: () => void;
  onClose: () => void;
  onSay: (msg: string) => void;
  onPersuade?: (message: string, intent: string) => Promise<void>;
}

const NPC_TYPE_ICON: Record<string, string> = {
  merchant: "🛒",
  guard: "⚔",
  monster: "👹",
};

const NPC_TYPE_ZH: Record<string, string> = {
  merchant: "商人",
  guard: "衛兵",
  monster: "怪物",
};

const INTENT_LABEL: Record<Intent, string> = {
  say: "普通說",
  persuade: "說服 CHA",
  threaten: "威脅 STR",
  bribe: "賄賂 LUK",
};

const INTENT_COLOR: Record<Intent, string> = {
  say: "border-stone-600/40 text-stone-400 bg-stone-800/40",
  persuade: "border-amber-500/50 text-amber-400 bg-amber-900/20",
  threaten: "border-red-500/50 text-red-400 bg-red-900/20",
  bribe: "border-yellow-500/50 text-yellow-400 bg-yellow-900/20",
};

const INTENT_ACTIVE: Record<Intent, string> = {
  say: "border-stone-500/60 text-stone-200 bg-stone-700/50",
  persuade: "border-amber-400/70 text-amber-300 bg-amber-800/40",
  threaten: "border-red-400/70 text-red-300 bg-red-800/40",
  bribe: "border-yellow-400/70 text-yellow-300 bg-yellow-800/40",
};

const TIER_COLOR: Record<string, string> = {
  large_success: "#40C080",
  medium_success: "#60A870",
  small_success: "#8AAA60",
  small_failure: "#9A9070",
  medium_failure: "#C86840",
  large_failure: "#E84040",
};

const TIER_ZH: Record<string, string> = {
  large_success: "大成功",
  medium_success: "成功",
  small_success: "小成功",
  small_failure: "小失敗",
  medium_failure: "失敗",
  large_failure: "大失敗",
};

export function DialogueModal({
  npcId,
  npcName,
  npcType,
  dialogue,
  opensShop,
  onOpenShop,
  onClose,
  onSay,
  onPersuade,
}: Props) {
  const [input, setInput] = useState("");
  const [intent, setIntent] = useState<Intent>("say");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ tier: string; narrative: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const txt = input.trim();
    if (!txt || loading) return;

    if (intent === "say" || !onPersuade) {
      onSay(txt);
      setInput("");
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      await onPersuade(txt, intent);
      // result will show via SSE npc_persuasion event; show placeholder
      setResult({ tier: "", narrative: "裁決進行中…" });
      setInput("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setResult({ tier: "large_failure", narrative: `錯誤：${msg}` });
    } finally {
      setLoading(false);
    }
  }

  const submitLabel = loading ? "裁決中…" : intent === "say" ? "說" : INTENT_LABEL[intent].split(" ")[0];

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-[2px]"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
        <div
          className="pointer-events-auto w-96 max-w-[90vw] rounded-lg border border-stone-600/50
            bg-stone-950/98 shadow-2xl"
          style={{ boxShadow: "0 0 40px rgba(0,0,0,0.8), 0 0 1px rgba(200,148,30,0.3)" }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-stone-700/40">
            <span className="text-2xl shrink-0">
              {NPC_TYPE_ICON[npcType] ?? "👤"}
            </span>
            <div className="flex-1 min-w-0">
              <p className="font-cinzel text-base font-semibold text-stone-100 truncate">
                {npcName}
              </p>
              <p className="font-inter text-xs text-stone-500">
                {NPC_TYPE_ZH[npcType] ?? npcType}
              </p>
            </div>
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded text-stone-600
                hover:text-stone-300 hover:bg-stone-800/60 transition-colors cursor-pointer shrink-0"
            >
              ✕
            </button>
          </div>

          {/* Dialogue text */}
          <div className="px-5 py-5">
            <div className="relative pl-4">
              <div
                className="absolute left-0 top-0 bottom-0 w-0.5 rounded-full"
                style={{ backgroundColor: "#C8941E", opacity: 0.6 }}
              />
              <p className="font-inter text-base text-stone-200 leading-relaxed">
                「{dialogue}」
              </p>
            </div>
          </div>

          {/* Intent selector */}
          {onPersuade && (
            <div className="px-5 pb-3 flex gap-1.5 flex-wrap">
              {(["say", "persuade", "threaten", "bribe"] as Intent[]).map((i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => { setIntent(i); setResult(null); }}
                  className={`px-2.5 py-1 rounded border font-inter text-xs font-semibold transition-colors cursor-pointer
                    ${intent === i ? INTENT_ACTIVE[i] : INTENT_COLOR[i]}`}
                >
                  {INTENT_LABEL[i]}
                </button>
              ))}
            </div>
          )}

          {/* Result display */}
          {result && (
            <div
              className="mx-5 mb-3 px-3 py-2.5 rounded border font-inter text-sm leading-snug"
              style={{
                borderColor: result.tier ? `${TIER_COLOR[result.tier]}60` : "#9A907E60",
                backgroundColor: result.tier ? `${TIER_COLOR[result.tier]}15` : "#9A907E15",
                color: result.tier ? TIER_COLOR[result.tier] : "#9A907E",
              }}
            >
              {result.tier && (
                <span className="font-semibold mr-1.5">[{TIER_ZH[result.tier] ?? result.tier}]</span>
              )}
              {result.narrative}
            </div>
          )}

          {/* Say input */}
          <form onSubmit={handleSubmit} className="px-5 pb-4 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`對 ${npcName} 說...`}
              disabled={loading}
              className="flex-1 bg-stone-900/80 border border-stone-600/50 rounded px-3 py-2
                font-inter text-sm text-stone-100 placeholder-stone-600
                focus:outline-none focus:border-gold/40 focus:ring-1 focus:ring-gold/20 transition-colors
                disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="px-4 py-2 rounded border border-gold/40 bg-gold/10 text-gold
                font-inter text-sm font-semibold hover:bg-gold/20
                cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150"
            >
              {submitLabel}
            </button>
          </form>

          {/* Action buttons */}
          <div className="flex gap-3 px-5 pb-5">
            {opensShop && (
              <button
                onClick={onOpenShop}
                className="flex-1 py-2.5 rounded border border-gold/40 bg-gold/10
                  font-inter text-sm font-semibold text-gold hover:bg-gold/20
                  cursor-pointer transition-all duration-150"
              >
                🛒 交易
              </button>
            )}
            <button
              onClick={onClose}
              className="flex-1 py-2.5 rounded border border-stone-600/40 bg-stone-800/40
                font-inter text-sm text-stone-400 hover:text-stone-200 hover:border-stone-500/60
                cursor-pointer transition-all duration-150"
            >
              離開
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
