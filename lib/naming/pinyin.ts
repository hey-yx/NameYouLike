/**
 * 汉字读音表与拼音匹配。
 *
 * 数据来源：pypinyin（mozillazg，MIT License）的 PINYIN_DICT，取 CJK 基本区
 * 每个汉字的多读音（无声调）。用途：判断一个拉丁词串是不是某个中文词的拼音，
 * 例如 guizang ↔ 归藏、duizhang ↔ 对账。
 *
 * 只做「这个拉丁串能不能读成这段中文」的精确匹配，不生成拼音、不猜读音。
 */
import raw from "./pinyin-map.json";

const READINGS = raw as Record<string, string[]>;

const TONE_MAP: Record<string, string> = {
  ā: "a", á: "a", ǎ: "a", à: "a",
  ē: "e", é: "e", ě: "e", è: "e",
  ī: "i", í: "i", ǐ: "i", ì: "i",
  ō: "o", ó: "o", ǒ: "o", ò: "o",
  ū: "u", ú: "u", ǔ: "u", ù: "u",
  ǖ: "ü", ǘ: "ü", ǚ: "ü", ǜ: "ü",
  ê: "e", ň: "n", ń: "n", ǹ: "n",
};

function normalizeSyllable(syllable: string): string {
  return Array.from(syllable.toLowerCase())
    .map((char) => TONE_MAP[char] ?? char)
    .join("")
    .replace(/ü/g, "v")
    .replace(/[^a-z]/g, "");
}

/** 每个字的所有可接受写法（ü 允许输入成 v 或 u）。 */
function optionsFor(char: string): string[] | null {
  const readings = READINGS[char];
  if (!readings) return null;
  const options: string[] = [];
  for (const reading of readings) {
    const normalized = normalizeSyllable(reading);
    // ü 在键盘上有 v、u 两种常见输入（lǚ → lv / lu）。
    for (const variant of [normalized, normalized.replace(/v/g, "u")]) {
      if (variant && !options.includes(variant)) options.push(variant);
    }
  }
  return options.length > 0 ? options : null;
}

/** latin 是否正好是 chinese 的拼音（逐字拼完，允许多音字）。 */
export function pinyinMatches(latin: string, chinese: string): boolean {
  const target = normalizeSyllable(latin);
  const chars = Array.from(chinese);
  if (!target) return false;
  if (chars.length === 0 || chars.some((char) => !READINGS[char])) return false;

  let positions = new Set([0]);
  for (const char of chars) {
    const options = optionsFor(char);
    if (!options) return false;
    const next = new Set<number>();
    for (const position of positions) {
      for (const option of options) {
        if (target.startsWith(option, position)) next.add(position + option.length);
      }
    }
    if (next.size === 0) return false;
    positions = next;
  }
  return positions.has(target.length);
}

/** 把拉丁名拆成小写词元（连字符、下划线、空格都算分隔）。 */
export function latinTokens(value: string): string[] {
  return value
    .toLowerCase()
    .split(/[^a-z]+/)
    .filter(Boolean);
}

/** 中文文本里的连续汉字片段（长度 1 到 4）。 */
function chineseRuns(text: string): string[] {
  const segments = text.match(/[\u4e00-\u9fa5]+/g) ?? [];
  const runs = new Set<string>();
  for (const segment of segments) {
    const chars = Array.from(segment);
    for (let start = 0; start < chars.length; start += 1) {
      for (let end = start + 1; end <= Math.min(chars.length, start + 4); end += 1) {
        runs.add(chars.slice(start, end).join(""));
      }
    }
  }
  return Array.from(runs);
}

/** 拉丁名里哪些词元是文本中某个中文片段的拼音。 */
export function pinyinTokensIn(latin: string, chineseText: string): Set<string> {
  const runs = chineseRuns(chineseText);
  const hits = new Set<string>();
  if (runs.length === 0) return hits;
  for (const token of latinTokens(latin)) {
    if (token.length < 2) continue;
    if (runs.some((run) => pinyinMatches(token, run))) hits.add(token);
  }
  return hits;
}
