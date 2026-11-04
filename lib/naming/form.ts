import type { NameLang } from "@/lib/types";
import { CHINESE_CULTURAL_WORDS } from "./knowledge";

/**
 * 「像真产品名」的形态判据。
 *
 * 数字来源：
 * - research/raw/form-stats.json（npm top400 + PyPI top200 + SaaS 品牌 100）：
 *   产品名长度中位 7、p75 = 8、p90 = 9；音节均值 2.18、≥4 音节只占 6%；
 *   连字符 0%、技术后缀 0%、含数字 1%。
 * - research/github-naming-samples-2026-10.md §2.3（1200 个仓库名）：
 *   长度中位 7、音节中位 2、单件名 75.6%。
 *
 * 分工：slop.ts 拦 >12 字母与 ≥5 音节，
 * audit.ts 拦连字符与意象堆叠。这里补的是剩下的两条——10 字符上限与技术后缀，
 * 以及「文化意象占比」的下调配额。
 */

/** 产品名的字母数上限（不含连字符）：品牌名 p90 = 9；允许「功能词+特征词」组合后放宽到 12。 */
export const PRODUCT_MAX_LETTERS = 12;

/**
 * 技术后缀：npm/PyPI 包名里占 3~6%，100 个真实产品名里出现 0 次。
 * 出现在候选里说明名字是按包名的思路拼的，不是按产品名的思路起的。
 */
export const TECH_SUFFIXES = [
  "js",
  "py",
  "lib",
  "core",
  "utils",
  "kit",
  "sdk",
  "client",
  "api",
  "cli",
  "types",
  "toolkit",
  "server",
  "engine",
];

export interface ProductFormOptions {
  /** 词典判断：整名是词典里的真词时技术后缀规则要放行（score / encore 这类）。 */
  isRealWord?: (word: string) => boolean;
  /** 读音表确认过的拼音词元：拼音名天生更长，词件与字母上限按它放宽。 */
  pinyinTokens?: Set<string>;
}

/**
 * 生成端的形态约束原话。数字都与上面的判据同源，拼进生成提示词与评审提示词。
 */
export const PRODUCT_FORM_BRIEF =
  "候选必须是一个完整的产品名——念出来像一个产品的名字（Caliper、Gauge、Plumb、Loom " +
  "这种），不是一段功能描述，也不是「意象词 + 实字」的拼接。" +
  "形体：1-2 个词件，可用一个连字符连接（skill-design、design-ledger 这种）；" +
  "英文总长 ≤12 个字母、2-4 个音节" +
  "（94% 的真实品牌落在 3 音节以内）。" +
  "不要用泛泛的常见英文单词（tool、easy、fast、simple 这种没辨识度的），" +
  "也不要用已烂大街的工具类实词；优先「功能用途词 + 特征词」的组合——" +
  "功能词如 design、skill、code、data、doc、note，特征词是具体、有画面的词。" +
  "不带空格、数字，不带 -kit/-sdk/-utils/-lib/-core/-api/-cli 这类技术后缀" +
  "（100 个真实产品名里出现 0 次）。" +
  "中文 2-4 个常用汉字，是字本身站得住的一个词；不要把两个抽象字拼成一个词（智域、云枢）。" +
  "文化意象（星宿、草木、朝代、节气、诗词、瑞兽）可用但要谨慎：整个名字就是那一个词" +
  "（北斗、甘棠、赤兔），不要拼成「北斗尺」「甘棠册」「麒麟册」「凤凰规」三字组合——" +
  "真实生态里这种拼接结构 0 例。";

function lettersOnly(name: string): string {
  return name.toLowerCase().replace(/[^a-z]/g, "");
}

/**
 * 产品名取向的形态检查。返回空数组代表通过；每条都是给用户看的一句话理由。
 * 只在「产品名」目标下调用——GitHub 项目名有另一套形态（kebab-case、可带赛道词）。
 */
export function productFormIssues(
  name: string,
  lang: NameLang,
  options: ProductFormOptions = {},
): string[] {
  if (lang === "zh") return [];
  const lower = lettersOnly(name);
  if (!lower) return [];

  const issues: string[] = [];
  // 词件数：1-2 件，中间可用一个连字符连接（skill-design、design-ledger）；
  // 拼音名按「拼音-功能词-用途」放宽到 3 件。
  const parts = name.split(/[-_.\s]+/).filter(Boolean);
  const pinyinTokens = options.pinyinTokens ?? new Set<string>();
  const hasPinyin = parts.some((part) =>
    pinyinTokens.has(part.toLowerCase()),
  );
  const maxParts = hasPinyin ? 3 : 2;
  const hyphens = (name.match(/-/g) ?? []).length;
  if (parts.length > maxParts) {
    issues.push(
      `${parts.length} 个词件：产品名最多${
        hasPinyin ? "三个（拼音-功能词-用途）" : "两个词件（skill-design 这种）"
      }，拆太碎像包名或功能描述`,
    );
  }
  const maxLetters = hasPinyin ? 24 : PRODUCT_MAX_LETTERS;
  if (lower.length > maxLetters) {
    issues.push(
      `${lower.length} 个字母：真实产品名的长度中位是 7、p90 是 9，` +
        "这么长听起来像包名或功能描述，不像一个产品的名字",
    );
  }

  const isWholeWord = options.isRealWord?.(lower) ?? false;
  if (!isWholeWord) {
    for (const suffix of TECH_SUFFIXES) {
      if (lower.length <= suffix.length + 2 || !lower.endsWith(suffix)) continue;
      issues.push(
        `以 -${suffix} 结尾：100 个真实产品名里这个后缀出现 0 次，是包名的写法不是产品名的写法`,
      );
      break;
    }
  }

  return issues;
}

/** 双字以上的文化意象词（北斗、甘棠、赤兔这类）。 */
const CULTURAL_WORDS = CHINESE_CULTURAL_WORDS.filter(
  (word) => Array.from(word).length >= 2,
);

/** 文化意象类候选的上限占比：真实生态里 0.77%，这里放宽到六分之一。 */
export const CULTURE_MAX_SHARE = 1 / 6;

interface CultureishCandidate {
  name: string;
  englishName?: string;
  source?: string;
  sourceDetail?: string;
}

/**
 * 候选是不是「文化意象派」：名字咬住了文化意象词，或来源干脆就是从它来的。
 * 中文名取汉字部分比对，英文名不比对意象词（它的中文来源写在 sourceDetail 里）。
 */
export function isCultureFlavored(candidate: CultureishCandidate): boolean {
  const texts = [
    Array.from(candidate.name)
      .filter((char) => /[一-龥]/.test(char))
      .join(""),
    candidate.source ?? "",
    candidate.sourceDetail ?? "",
    candidate.englishName ?? "",
  ];
  return CULTURAL_WORDS.some((word) =>
    texts.some((text) => text.includes(word)),
  );
}

/**
 * 把选出来的结果里文化意象类的占比压到 CULTURE_MAX_SHARE（至少一个保留，不为零），
 * 挤掉的位置用同一批候选里非意象的同语种候选顶上。
 */
export function enforceCultureShare<T extends CultureishCandidate>(
  selected: T[],
  pool: T[],
): T[] {
  if (selected.length === 0) return selected;
  const quota = Math.max(1, Math.ceil(selected.length * CULTURE_MAX_SHARE));

  const kept: T[] = [];
  const excess: T[] = [];
  for (const candidate of selected) {
    const culture = isCultureFlavored(candidate);
    const taken = kept.filter((item) => isCultureFlavored(item)).length;
    if (culture && taken >= quota) excess.push(candidate);
    else kept.push(candidate);
  }
  if (excess.length === 0) return kept;

  const used = new Set(kept.map((candidate) => candidate.name.toLowerCase()));
  const replacements = pool.filter(
    (candidate) =>
      !used.has(candidate.name.toLowerCase()) &&
      !isCultureFlavored(candidate) &&
      !excess.some(
        (dropped) => dropped.name.toLowerCase() === candidate.name.toLowerCase(),
      ),
  );

  // 填补顺序跟随原有池子的先后，前面的经过了评审层与去重排序。
  for (const candidate of replacements) {
    if (kept.length >= selected.length) break;
    kept.push(candidate);
    used.add(candidate.name.toLowerCase());
  }

  return kept;
}
