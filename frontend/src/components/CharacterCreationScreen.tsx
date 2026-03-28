import { useState } from "react";
import { api } from "../api";

interface ClassDef {
  id: string;
  name: string;
  description: string;
  primary_stats: string[];
  hp_bonus_per_level: number;
  mp_bonus_per_level: number;
  unlock_hint: string;
}

const CLASSES: ClassDef[] = [
  { id: "warrior",   name: "戰士",   description: "精通近戰武器與護甲的職業戰士。高耐久度，擅長正面交鋒，是隊伍的防線核心。", primary_stats: ["str", "con"], hp_bonus_per_level: 6, mp_bonus_per_level: 0,  unlock_hint: "在訓練場完成基礎戰鬥訓練" },
  { id: "berserker", name: "狂戰士", description: "以憤怒為燃料的野性戰士，進入狂暴狀態後攻擊力大幅提升，但防禦相應下降。",   primary_stats: ["str"],        hp_bonus_per_level: 5, mp_bonus_per_level: 0,  unlock_hint: "在競技場中連續勝利五場" },
  { id: "ranger",    name: "遊俠",   description: "行動迅速的野外獵人，擅長遠程攻擊、追蹤與自然魔法。靈活但防禦較薄。",         primary_stats: ["dex", "wis"], hp_bonus_per_level: 4, mp_bonus_per_level: 2,  unlock_hint: "在森林中完成生存試煉" },
  { id: "rogue",     name: "盜賊",   description: "行事低調的暗影職業，擅長偷竊、暗殺與解鎖陷阱。在暗處能力倍增，突襲傷害極高。", primary_stats: ["dex", "cha"], hp_bonus_per_level: 3, mp_bonus_per_level: 1,  unlock_hint: "獲得盜賊公會的認可" },
  { id: "mage",      name: "法師",   description: "鑽研奧術的學者，能施放強大的元素魔法。魔力充沛但體力脆弱。",                   primary_stats: ["int"],        hp_bonus_per_level: 2, mp_bonus_per_level: 8,  unlock_hint: "在魔法學院通過入學考核" },
  { id: "cleric",    name: "聖職者", description: "信奉神明的使者，以神聖魔法治癒盟友並驅逐黑暗。在聖地附近力量倍增。",         primary_stats: ["wis"],        hp_bonus_per_level: 4, mp_bonus_per_level: 5,  unlock_hint: "在神殿完成奉獻儀式" },
  { id: "bard",      name: "吟遊詩人", description: "以音樂與言語影響世界的全能支援者。社交與輔助能力卓越，多職兼容性極強。",    primary_stats: ["cha"],        hp_bonus_per_level: 3, mp_bonus_per_level: 4,  unlock_hint: "在酒館精彩表演並獲得人群認可" },
];

const STAT_LABEL: Record<string, string> = {
  str: "STR", dex: "DEX", int: "INT", wis: "感知", cha: "CHA", luk: "LUK", con: "CON",
};

// Class color accents
const CLASS_ACCENT: Record<string, string> = {
  warrior:   "rgba(212,160,48,0.15)",
  berserker: "rgba(200,60,60,0.15)",
  ranger:    "rgba(60,160,80,0.15)",
  rogue:     "rgba(100,80,180,0.15)",
  mage:      "rgba(80,120,220,0.15)",
  cleric:    "rgba(220,190,80,0.15)",
  bard:      "rgba(180,80,160,0.15)",
};

const CLASS_BORDER: Record<string, string> = {
  warrior:   "rgba(212,160,48,0.5)",
  berserker: "rgba(200,60,60,0.5)",
  ranger:    "rgba(60,160,80,0.5)",
  rogue:     "rgba(100,80,180,0.5)",
  mage:      "rgba(80,120,220,0.5)",
  cleric:    "rgba(220,190,80,0.5)",
  bard:      "rgba(180,80,160,0.5)",
};

function HpBar({ n }: { n: number }) {
  return (
    <span className="inline-flex gap-0.5">
      {Array.from({ length: Math.min(n, 6) }).map((_, i) => (
        <span key={i} className="text-red-400 text-[10px]">♥</span>
      ))}
      {n > 6 && <span className="text-red-400 text-[10px]">+</span>}
    </span>
  );
}

function MpBar({ n }: { n: number }) {
  if (n === 0) return <span className="text-stone-600 text-[10px]">—</span>;
  return (
    <span className="inline-flex gap-0.5">
      {Array.from({ length: Math.min(n, 8) }).map((_, i) => (
        <span key={i} className="text-blue-400 text-[10px]">✦</span>
      ))}
      {n > 8 && <span className="text-blue-400 text-[10px]">+</span>}
    </span>
  );
}

interface Props {
  playerId: string;
  onCreated: () => void;
  onBack: () => void;
}

export function CharacterCreationScreen({ playerId, onCreated, onBack }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    if (!selected || creating) return;
    setCreating(true);
    setError(null);
    try {
      await api.createPlayer(playerId, selected, name.trim() || playerId);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "建立角色失敗");
      setCreating(false);
    }
  }

  return (
    <div className="min-h-screen bg-void flex flex-col items-center justify-start overflow-y-auto py-10 px-4">
      {/* Ambient glow */}
      <div className="fixed inset-0 pointer-events-none"
        style={{ background: "radial-gradient(ellipse 70% 50% at 50% 30%, rgba(46,112,72,0.05) 0%, transparent 70%)" }} />

      {/* Rune grid */}
      <div className="fixed inset-0 opacity-[0.025] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%232E7048' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      <div className="relative w-full max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 mb-4 rounded-full border border-gold/30 bg-stone-900"
            style={{ boxShadow: "0 0 30px rgba(46,112,72,0.15), inset 0 0 15px rgba(0,0,0,0.7)" }}>
            <svg viewBox="0 0 48 48" className="w-7 h-7 animate-pulse-gold" fill="none">
              <polygon points="24,4 44,36 4,36" fill="none" stroke="#2E7048" strokeWidth="1.8"/>
              <polygon points="24,12 38,34 10,34" fill="rgba(46,112,72,0.12)" stroke="#2E7048" strokeWidth="0.8" strokeDasharray="3 2"/>
              <circle cx="24" cy="23" r="4" fill="#2E7048" opacity="0.9"/>
              <line x1="24" y1="4" x2="24" y2="44" stroke="#2E7048" strokeWidth="0.6" opacity="0.4"/>
              <line x1="4" y1="24" x2="44" y2="24" stroke="#2E7048" strokeWidth="0.6" opacity="0.4"/>
            </svg>
          </div>
          <h1 className="font-cinzel text-3xl font-black tracking-widest text-gold-light"
            style={{ textShadow: "0 0 20px rgba(212,160,48,0.6), 0 2px 6px rgba(0,0,0,0.9)" }}>
            選擇你的職業
          </h1>
          <p className="mt-2 font-inter text-sm text-stone-500 tracking-wide">
            玩家 <span className="text-stone-400 font-mono">{playerId}</span> · 選擇職業以踏上旅途
          </p>
        </div>

        {/* Class cards grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
          {CLASSES.map((cls) => {
            const isSelected = selected === cls.id;
            return (
              <button
                key={cls.id}
                onClick={() => setSelected(cls.id)}
                className="text-left rounded-lg border p-4 transition-all duration-200 cursor-pointer"
                style={{
                  background: isSelected ? CLASS_ACCENT[cls.id] : "rgba(28,25,23,0.8)",
                  borderColor: isSelected ? CLASS_BORDER[cls.id] : "rgba(68,64,60,0.6)",
                  boxShadow: isSelected ? `0 0 20px ${CLASS_ACCENT[cls.id]}, inset 0 1px 0 rgba(255,255,255,0.05)` : "inset 0 1px 0 rgba(255,255,255,0.03)",
                }}
              >
                {/* Class name + selected indicator */}
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-inter font-bold text-base"
                    style={{ color: isSelected ? "#F0C060" : "#D6D3D1" }}>
                    {cls.name}
                  </span>
                  {isSelected && (
                    <svg viewBox="0 0 12 12" className="w-4 h-4 shrink-0" fill="none">
                      <polyline points="1.5,6 4.5,9 10.5,3" stroke="#F0C060" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </div>

                {/* Description */}
                <p className="font-inter text-xs text-stone-400 leading-relaxed mb-3 line-clamp-2">
                  {cls.description}
                </p>

                {/* Stats row */}
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-inter text-[10px] text-stone-500 uppercase tracking-wider">主屬性</span>
                  <div className="flex gap-1">
                    {cls.primary_stats.map((s) => (
                      <span key={s}
                        className="font-mono text-[10px] px-1.5 py-0.5 rounded border"
                        style={{
                          color: isSelected ? "#F0C060" : "#A8A29E",
                          borderColor: isSelected ? "rgba(212,160,48,0.4)" : "rgba(68,64,60,0.8)",
                          background: isSelected ? "rgba(212,160,48,0.08)" : "rgba(28,25,23,0.5)",
                        }}>
                        {STAT_LABEL[s] ?? s.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>

                {/* HP / MP scaling */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <span className="font-inter text-[10px] text-stone-500">HP/Lv</span>
                    <HpBar n={cls.hp_bonus_per_level} />
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="font-inter text-[10px] text-stone-500">MP/Lv</span>
                    <MpBar n={cls.mp_bonus_per_level} />
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Name input + actions */}
        <div className="bg-stone-900 border border-stone-700/70 rounded-lg p-5"
          style={{ boxShadow: "0 4px 24px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.04)" }}>
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
            <div className="flex-1">
              <label className="block font-inter text-xs font-semibold text-stone-500 mb-1.5 uppercase tracking-wider">
                角色名稱（選填）
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={playerId}
                className="w-full bg-stone-900 border border-stone-700 rounded px-3 py-2
                  text-stone-100 font-inter text-sm placeholder-stone-600
                  focus:outline-none focus:border-forest/60 focus:ring-1 focus:ring-forest/30
                  transition-colors"
              />
            </div>

            <button
              onClick={handleCreate}
              disabled={!selected || creating}
              className="shrink-0 px-8 py-2.5 font-inter text-sm font-bold tracking-widest uppercase rounded cursor-pointer
                bg-forest/20 border border-forest/60 text-forest-light
                hover:bg-forest/35 hover:border-forest/90
                disabled:opacity-35 disabled:cursor-not-allowed
                transition-all duration-200"
              style={{ boxShadow: selected ? "0 0 14px rgba(46,112,72,0.3)" : "none" }}
            >
              {creating ? "建立中…" : "踏上旅途"}
            </button>
          </div>

          {error && (
            <p className="mt-3 font-inter text-xs text-red-400">{error}</p>
          )}

          {selected && (
            <p className="mt-3 font-inter text-xs text-stone-500">
              已選擇：<span className="text-gold/80">{CLASSES.find(c => c.id === selected)?.name}</span>
              　·　主屬性各 +3
            </p>
          )}
        </div>

        {/* Back link */}
        <div className="text-center mt-4">
          <button
            onClick={onBack}
            className="font-inter text-xs text-stone-600 hover:text-stone-400 transition-colors cursor-pointer"
          >
            ← 返回登入
          </button>
        </div>
      </div>
    </div>
  );
}
