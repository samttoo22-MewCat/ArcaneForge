import { useState } from "react";

interface Props {
  npcId: string;
  npcName: string;
  npcType: string;
  dialogue: string;
  opensShop: boolean;
  onOpenShop: () => void;
  onClose: () => void;
  onSay: (msg: string) => void;
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

export function DialogueModal({
  npcName,
  npcType,
  dialogue,
  opensShop,
  onOpenShop,
  onClose,
  onSay,
}: Props) {
  const [input, setInput] = useState("");

  function submitSay(e: React.FormEvent) {
    e.preventDefault();
    const txt = input.trim();
    if (!txt) return;
    onSay(txt);
    setInput("");
  }

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

          {/* Say input */}
          <form onSubmit={submitSay} className="px-5 pb-4 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`對 ${npcName} 說...`}
              className="flex-1 bg-stone-900/80 border border-stone-600/50 rounded px-3 py-2
                font-inter text-sm text-stone-100 placeholder-stone-600
                focus:outline-none focus:border-gold/40 focus:ring-1 focus:ring-gold/20 transition-colors"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="px-4 py-2 rounded border border-gold/40 bg-gold/10 text-gold
                font-inter text-sm font-semibold hover:bg-gold/20
                cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150"
            >
              說
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
