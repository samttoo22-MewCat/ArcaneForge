import { useState } from "react";
import type { Exit } from "../types";

interface Props {
  exits: Exit[];
  onMove: (direction: string) => void;
  onSay: (msg: string) => void;
  onDo: (action: string) => void;
  onLook: () => void;
  onBackpack: () => void;
  onSkills: () => void;
  onCraft: () => void;
  disabled: boolean;
}

// 佈局：5 列 × 3 行 grid
// col: 0=入  1=北  2=觀察  3=南  4=出  (實際 east/west 用行)
// 改用更清晰的十字：北上/南下在 col2，東西在 row2 兩側，入出在 col0/col4
// 最終設計：3 行 × 5 列 grid
//   col: 0=入/出  1=北/西  2=中(觀察)  3=南/東  4=出/入
// 簡化版：中央十字 + 入出在兩側
const CARD_DIRS: { dir: string; label: string; col: number; row: number }[] = [
  { dir: "north", label: "北", col: 2, row: 1 },
  { dir: "west",  label: "西", col: 1, row: 2 },
  { dir: "east",  label: "東", col: 3, row: 2 },
  { dir: "south", label: "南", col: 2, row: 3 },
  { dir: "up",    label: "上", col: 3, row: 1 },
  { dir: "down",  label: "下", col: 3, row: 3 },
  { dir: "in",    label: "入", col: 1, row: 1 },
  { dir: "out",   label: "出", col: 1, row: 3 },
];

export function ActionBar({ exits, onMove, onSay, onDo, onLook, onBackpack, onSkills, onCraft, disabled }: Props) {
  const [chatInput, setChatInput] = useState("");
  const [actionInput, setActionInput] = useState("");
  const [tab, setTab] = useState<"say" | "do">("say");

  // 從 exits 物件陣列取方向字串集合
  const exitDirSet = new Set(exits.map((e) => e.direction));

  function submitChat(e: React.FormEvent) {
    e.preventDefault();
    const txt = (tab === "say" ? chatInput : actionInput).trim();
    if (!txt) return;
    tab === "say" ? onSay(txt) : onDo(txt);
    setChatInput("");
    setActionInput("");
  }

  return (
    <div className="flex items-start gap-5 px-5 py-4 bg-stone-950/80 border-t border-stone-700/30">
      {/* 方向盤格：3 行 × 3 列，入出放在角落 */}
      <div
        className="grid gap-1.5 shrink-0"
        style={{ gridTemplateColumns: "repeat(3, 3rem)", gridTemplateRows: "repeat(3, 3rem)" }}
      >
        {CARD_DIRS.map(({ dir, label, col, row }) => {
          const available = exitDirSet.has(dir);
          if (!available) return null; // 無出口直接不渲染
          return (
            <button
              key={dir}
              onClick={() => onMove(dir)}
              disabled={disabled}
              style={{ gridColumn: col, gridRow: row }}
              className="w-12 h-12 rounded flex items-center justify-center font-inter text-lg font-bold
                border border-stone-600/60 bg-stone-900/80 text-stone-200
                hover:border-forest/60 hover:bg-forest/10 hover:text-forest-light
                disabled:opacity-40 disabled:cursor-not-allowed
                cursor-pointer transition-all duration-150"
            >
              {label}
            </button>
          );
        })}
        {/* 中央觀察按鈕，固定在 col2 row2 */}
        <button
          onClick={onLook}
          style={{ gridColumn: 2, gridRow: 2 }}
          className="w-12 h-12 rounded flex items-center justify-center
            border border-forest/50 bg-forest/15 text-forest-light font-inter text-sm font-bold tracking-wide
            hover:border-forest/80 hover:bg-forest/25 cursor-pointer transition-all duration-150"
        >
          觀察
        </button>
      </div>


      {/* 分隔線 */}
      <div className="w-px self-stretch bg-stone-700/30 shrink-0"/>

      {/* 說話 / 行動輸入 */}
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        <div className="flex items-center gap-2">
          {(["say", "do"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded font-inter text-base font-semibold cursor-pointer transition-colors
                ${tab === t
                  ? "bg-forest/15 border border-forest/50 text-forest-light"
                  : "border border-stone-700/40 text-stone-500 hover:text-stone-300"
                }`}
            >
              {t === "say" ? "說話" : "行動"}
            </button>
          ))}

          {/* 揹包按鈕 — 與分頁同列 */}
          <button
            onClick={onBackpack}
            className="flex items-center gap-1.5 px-3 py-2 rounded border border-stone-700/40 bg-stone-900/60
              font-inter text-sm text-stone-400
              hover:border-amber-600/50 hover:bg-amber-900/20 hover:text-amber-300
              cursor-pointer transition-all duration-150 ml-1"
            title="開啟揹包"
          >
            <span>🎒</span>
            <span className="font-semibold">揹包</span>
          </button>

          {/* 技能按鈕 */}
          <button
            onClick={onSkills}
            className="flex items-center gap-1.5 px-3 py-2 rounded border border-stone-700/40 bg-stone-900/60
              font-inter text-sm text-stone-400
              hover:border-violet-600/50 hover:bg-violet-900/20 hover:text-violet-300
              cursor-pointer transition-all duration-150"
            title="開啟技能面板"
          >
            <span>✦</span>
            <span className="font-semibold">技能</span>
          </button>

          {/* 合成按鈕 */}
          <button
            onClick={onCraft}
            className="flex items-center gap-1.5 px-3 py-2 rounded border border-stone-700/40 bg-stone-900/60
              font-inter text-sm text-stone-400
              hover:border-amber-600/50 hover:bg-amber-900/20 hover:text-amber-300
              cursor-pointer transition-all duration-150"
            title="開啟合成工坊"
          >
            <span>⚒</span>
            <span className="font-semibold">合成</span>
          </button>
        </div>

        {/* 輸入框 */}
        <form onSubmit={submitChat} className="flex gap-3">
          <input
            value={tab === "say" ? chatInput : actionInput}
            onChange={(e) =>
              tab === "say" ? setChatInput(e.target.value) : setActionInput(e.target.value)
            }
            disabled={disabled}
            placeholder={tab === "say" ? "說些什麼..." : "描述你的行動..."}
            className="flex-1 bg-stone-900/80 border border-stone-600/50 rounded px-4 py-3 font-inter text-base text-stone-100
              placeholder-stone-600 focus:outline-none focus:border-forest/50 focus:ring-1 focus:ring-forest/20
              disabled:opacity-40 transition-colors"
          />
          <button
            type="submit"
            disabled={disabled || !(tab === "say" ? chatInput : actionInput).trim()}
            className="px-6 py-3 rounded border border-forest/40 bg-forest/15 text-forest-light font-inter text-base font-semibold
              hover:border-forest/70 hover:bg-forest/25 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed
              transition-all duration-150"
          >
            送出
          </button>
        </form>
      </div>
    </div>
  );
}
