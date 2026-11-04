import type { NameKind, NameLang, NamingTarget } from "@/lib/types";
import {
  ABSTRACT_WORDS,
  BANNED_SUFFIXES,
  BANNED_WORDS,
  CHINESE_BANNED_WORDS,
  CHINESE_GENERIC_CHARS,
  CHINESE_INVENTED_PATTERNS,
  CHINESE_RARE_CHARS,
  GENERIC_STEMS,
  PSEUDO_LATIN_SUFFIXES,
  RACE_ROOTS,
  RACE_SUFFIXES,
  REPO_LIST_WORDS,
  stripFriendlyPrefix,
} from "./knowledge";
import { splitRealWords } from "./segments";

/** 功能用途词：可作「功能词+特征词」组合的部件（design-ledger、skill-design）。 */
const FUNCTION_ROOTS = new Set(["design", "skill"]);

const BANNED_SET = new Set(BANNED_WORDS);
const SHORT_BANNED = BANNED_WORDS.filter((word) => word.length <= 4);
const LONG_BANNED = BANNED_WORDS.filter((word) => word.length > 4);
const GENERIC_STEM_SET = new Set(GENERIC_STEMS);
const ABSTRACT_SET = new Set(ABSTRACT_WORDS);
const REPO_LIST_FLAT = REPO_LIST_WORDS.map((word) => word.replace(/[^a-z]/g, ""));
const AGENT_VERBS = new Set([
  "build", "make", "track", "plan", "find", "help", "manage", "organize",
  "analyze", "optimize", "boost", "accelerate", "incubate", "generate",
  "create", "design", "develop", "monitor", "schedule", "sync", "connect",
  "share", "learn", "teach", "shop", "pay", "bank", "save", "invest",
]);

interface SlopOptions {
  /** 传进来一个词典判断，伪拉丁规则才不会误伤 camera、aria 这类真实单词 */
  isRealWord?: (name: string) => boolean;
  /** 命名目标：项目名取向要放宽连字符（仓库名里 38% 带连字符），产品名不放宽 */
  target?: NamingTarget;
  /** 已被读音表确认的拼音词元（guizang、duizhang）：按中文读音处理，不套英文规则 */
  pinyinTokens?: Set<string>;
}

function normalizeEnglish(name: string): string {
  return name.toLowerCase().replace(/[^a-z]/g, "");
}

function countSyllables(word: string): number {
  const groups = word.match(/[aeiouy]+/g);
  let count = groups?.length ?? 1;
  if (word.endsWith("e") && count > 1) count -= 1;
  return Math.max(1, count);
}

function hasGenericSplit(name: string): string | null {
  for (let i = 2; i <= name.length - 2; i += 1) {
    const left = name.slice(0, i);
    const right = name.slice(i);
    if (GENERIC_STEM_SET.has(left) && GENERIC_STEM_SET.has(right)) {
      return `${left} + ${right}`;
    }
  }
  return null;
}

function vowelRatio(word: string): number {
  const vowels = (word.match(/[aeiouy]/g) ?? []).length;
  return vowels / Math.max(1, word.length);
}

/**
 * 多真词连写的元音占比天然偏高（NameYouLike），但它不是随机音节：
 * 元音密度这条启发式只对切不开的拼字生效。
 */

function detectEnglish(name: string, options: SlopOptions): string[] {
  const warnings: string[] = [];
  const lower = normalizeEnglish(name);
  if (!lower) return ["名字里没有可读的英文字母"];

  const isReal = options.isRealWord?.(lower) ?? false;

  if (BANNED_SET.has(lower)) {
    warnings.push(`“${lower}”是被过度使用的词`);
  }
  for (const word of LONG_BANNED) {
    if (lower.includes(word)) {
      warnings.push(`含有被过度使用的词根“${word}”`);
    }
  }
  for (const word of SHORT_BANNED) {
    if (lower === word) {
      warnings.push(`“${word}”是被过度使用的词`);
    }
  }

  for (const suffix of BANNED_SUFFIXES) {
    if (!lower.endsWith(suffix) || lower.length <= suffix.length) continue;
    const stem = lower.slice(0, -suffix.length);
    if (GENERIC_STEM_SET.has(stem)) {
      warnings.push(`通用词“${stem}”加 -${suffix} 后缀，像批量生成的 SaaS 名`);
    } else if (stem.length <= 3) {
      warnings.push(`词根太短，-${suffix} 后缀没有带来具体含义`);
    }
  }

  const genericSplit = hasGenericSplit(lower);
  if (genericSplit) {
    warnings.push(`两个通用词直接拼接（${genericSplit}）`);
  }

  for (const word of ABSTRACT_SET) {
    if (lower === word || lower.includes(word)) {
      warnings.push(`抽象词“${word}”没有具体所指`);
    }
  }

  // 赛道撞名雷区：108 个设计工具仓库样本里的默认构词法，命中等于没起名
  // （去掉连字符再比，MeasureTwice 这类才不会漏）。
  // 功能词例外：design 这类「功能用途词」作「功能词+特征词」组合的部件时允许
  //（design-ledger、skill-design），单独用或拼通用词仍拒——雷区图的原意是
  // 「design 作主词等于没起名」，不是「禁用这个字眼」。
  const flat = lower.replace(/[^a-z]/g, "");
  const parts = name.toLowerCase().split(/[-_.\s]+/).filter(Boolean);
  for (const root of RACE_ROOTS) {
    const flatRoot = root.replace(/[^a-z]/g, "");
    if (!flat.includes(flatRoot)) continue;
    if (FUNCTION_ROOTS.has(root)) {
      const others = parts.filter((part) => part !== root);
      const hasConcrete = others.some(
        (part) => part.length >= 3 && !RACE_ROOTS.includes(part),
      );
      if (parts.length >= 2 && hasConcrete) continue;
    }
    warnings.push(
      `撞名雷区词根“${root}”：设计工具赛道 108 个样本仓库里用烂的构词法，等于没起名`,
    );
    break;
  }
  for (const suffix of RACE_SUFFIXES) {
    if (lower.length > suffix.length && lower.endsWith(suffix)) {
      warnings.push(
        `撞名雷区后缀“-${suffix}”：2026 年 AI 代理潮 / 上一代 SaaS 的泛滥构式`,
      );
      break;
    }
  }

  if (lower.endsWith("ai") && lower.length > 4) {
    const stem = lower.slice(0, -2);
    if (/^[a-z]{3,}$/.test(stem)) {
      warnings.push("类别词或普通词加 AI 后缀，缺乏辨识度");
    }
  }

  if (lower.endsWith("er") && lower.length > 4) {
    const stem = lower.slice(0, -2);
    if (AGENT_VERBS.has(stem)) {
      warnings.push(`“${stem} + er”是工具类命名的常见套路`);
    }
  }

  const hasPinyin = parts.some((part) =>
    (options.pinyinTokens ?? new Set<string>()).has(part.replace(/[^a-z]/g, "")),
  );

  if (!isReal) {
    // 口语前缀名（GetSextant、MeetBuoy 之类）整体元音天然偏多，
    // 这两条启发式只对剥掉前缀后的主体词生效。
    const stem = stripFriendlyPrefix(lower);
    const prefixReal = stem !== lower && (options.isRealWord?.(stem) ?? false);
    // 拼音词元按中文读音判断（拼音的元音比例天然高），不套英文伪拉丁规则。
    if (!prefixReal && !hasPinyin) {
      for (const suffix of PSEUDO_LATIN_SUFFIXES) {
        if (lower.endsWith(suffix) && lower.length > suffix.length) {
          warnings.push(`以 -${suffix} 结尾，像批量生成的伪拉丁名`);
          break;
        }
      }
      if (vowelRatio(lower) > 0.6 && !splitRealWords(lower, (word) => options.isRealWord?.(word) ?? false)) {
        warnings.push("元音过多，读起来像随机拼出的音节");
      }
    }
  }

  if (options.target === "repo") {
    // 仓库名里 kebab-case 是常规写法，连字符不算问题；数字、下划线和过长名字才是，
    // 另外清单 / 教程式名字属于资源列表，不是项目名。
    if (/\d/.test(name)) {
      warnings.push("含数字，口头传播时容易出错");
    }
    if (/_/.test(name)) {
      warnings.push("下划线在仓库名里不常见，用连字符");
    }
    if (REPO_LIST_FLAT.some((word) => lower.includes(word))) {
      warnings.push(
        "清单或教程式仓库名（roadmap、checklist、resources 这类），不像一个项目的名字",
      );
    }
    const maxLength = hasPinyin ? 24 : 20;
    if (name.length > maxLength) {
      warnings.push(`超过 ${maxLength} 个字符，输入和传播成本偏高`);
    }
  } else {
    // 产品名允许一个连字符连接两个词件（skill-design），两个以上像包名；
    // 拼音名天生更长（拼音-功能词-用途），字数上限放宽。
    const maxHyphens = hasPinyin ? 2 : 1;
    if ((name.match(/-/g) ?? []).length > maxHyphens) {
      warnings.push(
        hasPinyin
          ? "超过两个连字符：拼音名最多「拼音-功能词-用途」三段"
          : "超过一个连字符：产品名最多一个连字符连接两个词件",
      );
    }
    if (/\d/.test(name)) {
      warnings.push("含数字，口头传播时容易出错");
    }
    const maxLetters = hasPinyin ? 24 : 12;
    if (lower.length > maxLetters) {
      warnings.push(`超过 ${maxLetters} 个字母，输入和传播成本偏高`);
    }
  }
  const totalSyllables = parts.reduce(
    (sum, part) => sum + countSyllables(part.replace(/[^a-z]/g, "")),
    0,
  );
  const maxSyllables = hasPinyin ? 7 : 4;
  if (totalSyllables > maxSyllables) {
    warnings.push(`超过 ${maxSyllables} 个音节，不容易一次记住`);
  }

  return warnings;
}

function detectChinese(name: string): string[] {
  const warnings: string[] = [];
  const chars = Array.from(name);

  if (chars.length > 4) {
    warnings.push("超过四个字，口头传播成本偏高");
  }
  if (/[a-z0-9]/i.test(name)) {
    warnings.push("中英混排会让读法和拼写都变复杂");
  }

  for (const word of CHINESE_BANNED_WORDS) {
    if (name.includes(word)) {
      warnings.push(`含有被过度使用的词“${word}”`);
    }
  }

  for (const pattern of CHINESE_INVENTED_PATTERNS) {
    if (pattern.test(name)) {
      warnings.push("符合常见 AI 中文命名套路");
      break;
    }
  }

  const genericHits = chars.filter((char) => CHINESE_GENERIC_CHARS.includes(char));
  if (genericHits.length >= 2) {
    warnings.push(`“${genericHits.join("")}”这类泛字堆在一起，没有具体信息`);
  }

  for (const char of chars) {
    if (CHINESE_RARE_CHARS.includes(char)) {
      warnings.push(`“${char}”是生僻字，很多人不会读也不会打`);
    }
  }

  if (chars.length === 2 && genericHits.length === 2) {
    warnings.push("两个泛字组合，放在任何行业都成立");
  }

  return warnings;
}

/**
 * 确定性反套路检查。模型提示词只能降低概率，这里负责兜底。
 * 返回的每一条都会显示在结果里；严格模式下有任何一条就淘汰。
 */
export function detectSlop(
  name: string,
  lang: NameLang,
  _kind?: NameKind,
  options: SlopOptions = {},
): string[] {
  const warnings =
    lang === "zh"
      ? detectChinese(name)
      : detectEnglish(name, options);
  return Array.from(new Set(warnings));
}

