import { useState } from "react";

interface Props {
  exits: string[];
  onMove: (direction: string) => void;
  onSay: (msg: string) => void;
  onDo: (action: string) => void;
  onLook: () => void;
  disabled: boolean;
}

const COMPASS: { dir: string; label: string; pos: string }[] = [
  { dir: "north", label: "N",  pos: "col-start-2 row-start-1" },
  { dir: "up",    label: "↑",  pos: "col-start-3 row-start-1" },
  { dir: "in",    label: "⇥",  pos: "col-start-1 row-start-2" },
  { dir: "west",  label: "W",  pos: "col-start-2 row-start-2" },
  { dir: "east",  label: "E",  pos: "col-start-3 row-start-2" },
  { dir: "out",   label: "⇤",  pos: "col-start-4 row-start-2" },
  { dir: "south", label: "S",  pos: "col-start-2 row-start-3" },
  { dir: "down",  label: "↓",  pos: "col-start-3 row-start-3" },
];

export function ActionBar({ exits, onMove, onSay, onDo, onLook, disabled }: Props) {
  const [chatInput, setChatInput] = useState("");
  const [actionInput, setActionInput] = useState("");
  const [tab, setTab] = useState<"say" | "do">("say");

  function submitChat(e: React.FormEvent) {
    e.preventDefault();
    const txt = chatInput.trim();
    if (!txt) return;
    tab === "say" ? onSay(txt) : onDo(txt);
    setChatInput("");
    setActionInput("");
  }

  return (
    <div className="flex items-start gap-4 px-4 py-3 bg-stone-950/80 border-t border-stone-700/30">
      {/* Compass grid */}
      <div className="grid grid-cols-4 grid-rows-3 gap-1 shrink-0">
        {COMPASS.map(({ dir, label, pos }) => {
          const available = exits.includes(dir);
          return (
            <button
              key={dir}
              onClick={() => onMove(dir)}
              disabled={disabled || !available}
              title={dir}
              className={`${pos} w-9 h-9 rounded flex items-center justify-center font-mono text-sm font-bold
                border transition-all duration-150 cursor-pointer
                ${available
                  ? "border-stone-600/60 bg-stone-900/80 text-stone-300 hover:border-gold/50 hover:bg-stone-800/80 hover:text-gold-light"
                  : "border-stone-800/40 bg-stone-950/40 text-stone-700 cursor-not-allowed opacity-40"
                }
                disabled:opacity-30 disabled:cursor-not-allowed`}
            >
              {label}
            </button>
          );
        })}
        {/* Center LOOK button */}
        <button
          onClick={onLook}
          className="col-start-2 row-start-2 w-9 h-9 rounded flex items-center justify-center
            border border-gold/30 bg-gold/10 text-gold-light font-cinzel text-[8px] font-semibold tracking-wider
            hover:border-gold/60 hover:bg-gold/20 cursor-pointer transition-all duration-150"
        >
          LOOK
        </button>
      </div>

      {/* Vertical divider */}
      <div className="w-px self-stretch bg-stone-700/30 shrink-0"/>

      {/* Chat / Action input */}
      <div className="flex-1 flex flex-col gap-2 min-w-0">
        {/* Tab switcher */}
        <div className="flex gap-1">
          {(["say", "do"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded font-cinzel text-[10px] tracking-widest uppercase cursor-pointer transition-colors
                ${tab === t
                  ? "bg-gold/15 border border-gold/40 text-gold-light"
                  : "border border-stone-700/40 text-stone-500 hover:text-stone-300"
                }`}
            >
              {t === "say" ? "Say" : "Do"}
            </button>
          ))}
        </div>

        {/* Input */}
        <form onSubmit={submitChat} className="flex gap-2">
          <input
            value={tab === "say" ? chatInput : actionInput}
            onChange={(e) =>
              tab === "say" ? setChatInput(e.target.value) : setActionInput(e.target.value)
            }
            disabled={disabled}
            placeholder={tab === "say" ? "Say something..." : "Describe your action..."}
            className="flex-1 bg-stone-900/80 border border-stone-600/50 rounded px-3 py-2 font-mono text-xs text-stone-200
              placeholder-stone-600 focus:outline-none focus:border-gold/50 focus:ring-1 focus:ring-gold/20
              disabled:opacity-40 transition-colors"
          />
          <button
            type="submit"
            disabled={disabled || !(tab === "say" ? chatInput : actionInput).trim()}
            className="px-4 py-2 rounded border border-gold/30 bg-gold/10 text-gold-light font-cinzel text-[10px] tracking-wider
              hover:border-gold/60 hover:bg-gold/20 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed
              transition-all duration-150"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
