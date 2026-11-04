import fs from "node:fs";
import { createRequire } from "node:module";
import type {
  CandidateAudit,
  Market,
  NameCandidate,
  NamingTarget,
  ProductBrief,
} from "@/lib/types";
import { KNOWN_BRAND_SET } from "./brands";
import {
  ABSTRACT_SOURCE_PHRASES,
  CHINESE_CULTURAL_WORD_SET,
  CHINESE_GENERIC_CHARS,
  CHINESE_RARE_CHARS,
  CHINESE_REAL_WORD_SET,
  CHINESE_SPOKEN_MARKERS,
  CLICHE_METAPHORS,
  GENERIC_RATIONALE_PHRASES,
  GENERIC_STEMS,
  REPO_TECH_TOKENS,
  PINYIN_PURPOSE_TOKENS,
  STOPWORDS,
  stripFriendlyPrefix,
} from "./knowledge";
import { productFormIssues } from "./form";
import { latinTokens, pinyinTokensIn } from "./pinyin";
import { splitRealWords } from "./segments";
import { detectSlop } from "./slop";

const GENERIC_STEM_SET = new Set(GENERIC_STEMS);

const require = createRequire(import.meta.url);

let englishWordSet: Set<string> | undefined;

function getEnglishWordSet(): Set<string> {
  if (!englishWordSet) {
    const wordsPath = require.resolve("an-array-of-english-words");
    const words = JSON.parse(fs.readFileSync(wordsPath, "utf8")) as string[];
    englishWordSet = new Set(words.map((word) => word.toLowerCase()));
  }
  return englishWordSet;
}

export function isRealEnglishWord(name: string): boolean {
  return getEnglishWordSet().has(name.toLowerCase());
}

function findCompoundParts(name: string): [string, string] | null {
  const lower = name.toLowerCase().replace(/[^a-z]/g, "");
  for (let i = 3; i <= lower.length - 3; i += 1) {
    const left = lower.slice(0, i);
    const right = lower.slice(i);
    if (isRealEnglishWord(left) && isRealEnglishWord(right)) {
      return [left, right];
    }
  }
  return null;
}

/**
 * 把整个名字切分成两个以上真实单词（name|you|like）。
 * 三个以上真词连写的短语（NameYouLike）以前落在「两个词根组合」的缝隙里被判生造，
 * 这里按完整切分判定。
 */
function findWordParts(name: string): string[] | null {
  return splitRealWords(name, isRealEnglishWord);
}

const CHINESE_RARE_CHAR_SET = new Set(CHINESE_RARE_CHARS);
const CHINESE_GENERIC_CHAR_SET = new Set(CHINESE_GENERIC_CHARS);
const CHINESE_SPOKEN_MARKER_SET = new Set(CHINESE_SPOKEN_MARKERS);

/**
 * 中文自然短语：2-4 字、无生僻字、泛字少于两个，且带口语功能字。
 * 审计只认「实词」，口语短语名（叫什么、记在这、哪一页）一个也查不到；
 * 但能说出口的短句必然带虚词、代词或日常动作词，意象堆叠的生造名不会。
 * 这是形状判据，不是词义判据：只能说明「像一句人话」，不证明名字好不好。
 */
function naturalChinesePhrase(name: string): boolean {
  const chars = Array.from(name);
  if (chars.length < 2 || chars.length > 4) return false;
  if (chars.some((char) => CHINESE_RARE_CHAR_SET.has(char))) return false;
  const generic = chars.filter((char) => CHINESE_GENERIC_CHAR_SET.has(char)).length;
  if (generic >= 2) return false;
  return chars.some((char) => CHINESE_SPOKEN_MARKER_SET.has(char));
}

/** 2-6 个字母、含元音的短词：TW93 式名字的外形约束（Kaku / Kami / Pake / Mole）。 */
function isShortForeignWord(name: string): boolean {
  const lower = name.toLowerCase().replace(/[^a-z]/g, "");
  return lower.length >= 2 && lower.length <= 6 && /[aeiouy]/.test(lower);
}

const FOREIGN_SOURCE_HINTS = [
  "日语",
  "日文",
  "中文",
  "汉语",
  "克里奥尔",
  "德语",
  "法语",
  "拉丁",
  "希腊",
  "韩语",
  "希伯来",
  "梵语",
  "西班牙语",
  "意大利语",
  "俄语",
];

/** 来源说明里是否点明了「哪国语言的什么词」——说不清词源就不算真词。 */
function declaresForeignSource(sourceDetail: string): boolean {
  const text = sourceDetail || "";
  return FOREIGN_SOURCE_HINTS.some((hint) => text.includes(hint));
}

function countRealMorphemes(text: string): number {
  const words = text.toLowerCase().match(/[a-z]{3,}/g) ?? [];
  return new Set(words.filter((word) => isRealEnglishWord(word))).size;
}

function chineseRealness(name: string): number {
  // 带真实出处的文化意象词（北斗 / 木兰 / 唐）也是真词表的一部分——
  // 审计要认它，否则这类词会被词典检查误杀。
  if (CHINESE_REAL_WORD_SET.has(name) || CHINESE_CULTURAL_WORD_SET.has(name)) {
    return 100;
  }
  // 口语自然短语（叫什么、记在这）不在实词白名单里，但它是能说出口的一句话。
  if (naturalChinesePhrase(name)) {
    return 78;
  }
  const chars = Array.from(name);
  for (let i = 0; i <= chars.length - 2; i += 1) {
    const pair = chars.slice(i, i + 2).join("");
    if (CHINESE_REAL_WORD_SET.has(pair) || CHINESE_CULTURAL_WORD_SET.has(pair)) {
      return 70;
    }
  }
  return 15;
}

/**
 * 意象堆叠：三字以上的中文名里塞了一个文化意象词，再补一个字凑成名字
 * （北斗尺、麒麟册式）。真实产品名里文化意象只占 0.2%，这种拼接在产品名
 * 类别下要扣住。
 */
function stackedImagery(name: string): boolean {
  const chars = Array.from(name);
  if (chars.length < 3) return false;
  if (CHINESE_REAL_WORD_SET.has(name) || CHINESE_CULTURAL_WORD_SET.has(name)) {
    return false;
  }
  for (let i = 0; i <= chars.length - 2; i += 1) {
    if (CHINESE_CULTURAL_WORD_SET.has(chars.slice(i, i + 2).join(""))) return true;
  }
  return false;
}

/** kebab-case 仓库名：每个 token 都得是真实单词，或站得住的技术缩写。 */
function isRealKebab(name: string): boolean {
  const tokens = name
    .toLowerCase()
    .split("-")
    .filter((token) => token.length > 0);
  if (tokens.length < 2) return false;
  return tokens.every(
    (token) => isRealEnglishWord(token) || REPO_TECH_TOKENS.has(token),
  );
}

function levenshtein(a: string, b: string): number {
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;

  const previous = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i += 1) {
    const current = [i];
    for (let j = 1; j <= b.length; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      current[j] = Math.min(
        current[j - 1] + 1,
        previous[j] + 1,
        previous[j - 1] + cost,
      );
    }
    for (let j = 0; j <= b.length; j += 1) previous[j] = current[j];
  }
  return previous[b.length];
}

function normalizeForBrand(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function findBrandCollision(
  name: string,
  competitors: string[],
): string | undefined {
  const normalized = normalizeForBrand(name);
  if (!normalized) return undefined;

  const brands = [
    ...KNOWN_BRAND_SET,
    ...competitors.map(normalizeForBrand).filter(Boolean),
  ];

  for (const brand of brands) {
    if (normalized === brand) return brand;
    if (
      normalized.length >= 5 &&
      brand.length >= 5 &&
      levenshtein(normalized, brand) <= 1
    ) {
      return brand;
    }
  }
  return undefined;
}

function tokenize(text: string): string[] {
  const lower = text.toLowerCase();
  const tokens: string[] = [];

  for (const word of lower.match(/[a-z]{3,}/g) ?? []) {
    if (!STOPWORDS.has(word)) tokens.push(word);
  }

  for (const segment of lower.match(/[\u4e00-\u9fa5]+/g) ?? []) {
    const chars = Array.from(segment);
    for (let i = 0; i < chars.length - 1; i += 1) {
      const bigram = chars.slice(i, i + 2).join("");
      if (!STOPWORDS.has(bigram)) tokens.push(bigram);
    }
  }

  return tokens;
}

function overlapCount(a: string, b: string): number {
  const setB = new Set(tokenize(b));
  return new Set(tokenize(a).filter((token) => setB.has(token))).size;
}

function clamp(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function sourceTypeLabel(type: NameCandidate["sourceType"]): string {
  switch (type) {
    case "object":
      return "具体物件";
    case "action":
      return "具体动作";
    case "place":
      return "真实地点";
    case "person":
      return "真实人物";
    case "real-word":
      return "真实词语";
    case "compound":
      return "真实词组合";
    case "phrase":
      return "真实短语";
  }
}

/**
 * 反套路审计：不是看名字“像不像品牌”，而是检查它有没有指向真实事物、
 * 有没有引用产品事实、能不能在词典里查到、会不会撞上已有品牌。
 */
export function auditCandidate(
  candidate: NameCandidate,
  brief: ProductBrief,
  description: string,
  target: NamingTarget = "product",
  evidenceText = "",
): CandidateAudit & { slopWarnings: string[] } {
  const isReal = (word: string) => isRealEnglishWord(word);
  // 拼音名的读音证据只能来自产品本身（描述、关键词、产品事实），
  // 不能来自模型自己写的 sourceDetail：否则模型随便编一个中文词再配拼音就能自证。
  const pinyinSource =
    candidate.lang === "zh"
      ? candidate.name
      : `${description} ${evidenceText} ${brief.productFacts.join(" ")}`;
  const pinyinTokens = pinyinTokensIn(
    candidate.lang === "zh" ? (candidate.englishName ?? "") : candidate.name,
    pinyinSource,
  );
  const slopWarnings = detectSlop(candidate.name, candidate.lang, candidate.kind, {
    isRealWord: isReal,
    target,
    pinyinTokens,
  });
  const slopScore = Math.min(100, slopWarnings.length * 20);

  const nameTokens = latinTokens(candidate.name);
  const isPurposeToken = (token: string) =>
    isRealEnglishWord(token) ||
    REPO_TECH_TOKENS.has(token) ||
    PINYIN_PURPOSE_TOKENS.has(token);
  const pinyinName =
    pinyinTokens.size > 0 &&
    nameTokens.every(
      (token) => pinyinTokens.has(token) || isPurposeToken(token),
    );

  let realness = 15;
  if (candidate.lang === "zh") {
    realness = chineseRealness(candidate.name);
    if (candidate.englishName) {
      const englishReal =
        isRealEnglishWord(candidate.englishName) ||
        Boolean(findCompoundParts(candidate.englishName)) ||
        Boolean(findWordParts(candidate.englishName));
      // 拼音配名：每个词元要么能逐字对上中文读音，要么本身是真词
      // （duizhang、guizang-design、guizang-draw 都算有效拉丁写法）。
      const pinyinPair =
        pinyinTokens.size > 0 &&
        latinTokens(candidate.englishName).every(
          (token) => pinyinTokens.has(token) || isPurposeToken(token),
        );
      realness = Math.round(
        realness * 0.6 + (englishReal ? 100 : pinyinPair ? 92 : 15) * 0.4,
      );
      // 拼音能逐字读回名字本身时，库外真实词（归藏、营造这类）不再被小白名单判死；
      // 生造词仍由中文套路规则（生造模式、生僻字）拦在前面。
      if (pinyinPair) realness = Math.max(realness, 70);
    }
  } else if (isRealEnglishWord(candidate.name)) {
    realness = 100;
  } else if (pinyinName) {
    // 拼音名（duizhang / guizang-design-skill）：拉丁串能逐字对上来源里的
    // 中文读音，按真词一样的证据强度处理，不再当造词判死。
    realness = 90;
  } else if (target === "repo" && isRealKebab(candidate.name)) {
    // 仓库名的 kebab-case 写法（probe-relay、trace-ledger）：每个 token 都是
    // 真实单词或技术缩写才算真词，整体查词典查不到不按造词判死。
    realness = 88;
  } else if (
    // TW93 式单词体系：Kaku（日语「書く」）/ Kami（「紙」）/ Pake（海地克里奥尔语）
    // 这类名字在英文词典里查不到，但词源是真实存在的词，不能按造词判死。
    // 只看证据（短词形 + 来源点明是哪国语言的什么词），不看模型填的 strategy。
    isShortForeignWord(candidate.name) &&
    declaresForeignSource(candidate.sourceDetail)
  ) {
    realness = 80;
  } else {
    // 口语前缀名（GetSextant、TryPlumb 之类）：主体词是真实单词或真实
    // 词组合就算通过；前缀本身是常用口语词，不要求也在词典判定里成立。
    const lower = candidate.name.toLowerCase().replace(/[^a-z]/g, "");
    const stem = stripFriendlyPrefix(candidate.name);
    const hasPrefix = stem !== lower;
    const wordParts = findWordParts(candidate.name);
    if (hasPrefix && isRealEnglishWord(stem)) {
      realness = 88;
    } else if (hasPrefix && findCompoundParts(stem)) {
      realness = 85;
    } else if (wordParts && wordParts.length >= 3) {
      // 三个以上真词连写的短语（NameYouLike）：每个词元都是词典里的真词，
      // 整体是一句能读懂的话，不是拼出来的音节。
      realness = 90;
    } else if (findCompoundParts(candidate.name)) {
      realness = 90;
    } else if (
      candidate.kind === "coined" &&
      countRealMorphemes(candidate.sourceDetail) >= 2
    ) {
      realness = 70;
    }
  }

  let concreteness = 80;
  const sourceDetail = candidate.sourceDetail.toLowerCase();
  if (sourceDetail.length < 20) concreteness -= 30;
  if (ABSTRACT_SOURCE_PHRASES.some((phrase) => sourceDetail.includes(phrase))) {
    concreteness -= 35;
  }
  if (
    GENERIC_RATIONALE_PHRASES.some((phrase) =>
      candidate.rationale.toLowerCase().includes(phrase),
    )
  ) {
    concreteness -= 15;
  }
  if (
    candidate.sourceType === "object" ||
    candidate.sourceType === "action" ||
    candidate.sourceType === "place" ||
    candidate.sourceType === "person"
  ) {
    concreteness += 10;
  }
  if (candidate.source.trim().length < 2) concreteness -= 20;
  concreteness = clamp(concreteness);

  // 关联分数只看模型自己的因果说明（rationale），再单独要求 productFact 引用原词：
  // 把产品描述整段抄进 productFact 不再能抬高分数。
  const overlap = overlapCount(candidate.rationale, description);
  const factOverlap = overlapCount(candidate.productFact, description);
  const productFit =
    factOverlap === 0
      ? 15
      : overlap >= 3
        ? 95
        : overlap === 2
          ? 75
          : overlap === 1
            ? 45
            : 15;

  const brand =
    findBrandCollision(candidate.name, brief.competitors) ??
    (candidate.englishName
      ? findBrandCollision(candidate.englishName, brief.competitors)
      : undefined);

  const lowerName = candidate.name.toLowerCase();
  const stem = candidate.lang === "en" ? stripFriendlyPrefix(lowerName) : lowerName;
  const genericName =
    candidate.lang === "en" && GENERIC_STEM_SET.has(stem);
  const clicheName =
    candidate.lang === "en" &&
    CLICHE_METAPHORS.some(
      (word) => lowerName === word || lowerName.includes(word),
    );

  const issues: string[] = [];
  if (genericName) {
    issues.push("这个词太通用，缺少品牌辨识度");
  }
  if (clicheName) {
    issues.push("这是通用监控或导航隐喻，放在任何产品上都成立");
  }
  if (target === "product") {
    if (candidate.lang === "en" && (candidate.name.match(/-/g) ?? []).length > 1) {
      issues.push(
        "产品名最多一个连字符：可以「功能词-特征词」（skill-design），但连太多像包名",
      );
    }
    if (candidate.lang === "zh" && stackedImagery(candidate.name)) {
      issues.push(
        "意象堆叠：文化意象词再加一个字拼成的名字（北斗尺、麒麟册式），不像产品名",
      );
    }
    if (candidate.lang === "en") {
      issues.push(
        ...productFormIssues(candidate.name, "en", {
          isRealWord: isReal,
          pinyinTokens,
        }),
      );
    }
    if (candidate.lang === "zh" && candidate.englishName) {
      // 配名也要过同一套产品名形态：不能主名合格、配名带技术后缀或过长。
      issues.push(
        ...productFormIssues(candidate.englishName, "en", {
          isRealWord: isReal,
          pinyinTokens,
        }),
      );
    }
  }
  if (realness < 70) {
    issues.push(
      candidate.lang === "zh"
        ? "中文名不是常见实词，或配的英文名不是真实英文单词（可能是拼音）"
        : "不是词典里的真实单词，也不是两个真实词根的组合",
    );
  }
  if (concreteness < 70) {
    issues.push("来源解释不够具体，像空泛描述");
  }
  if (productFit < 50) {
    issues.push("推荐理由没有引用产品描述里的具体事实");
  }
  if (brand) {
    issues.push(`与已有品牌“${brand}”同名或只差一个字母`);
  }

  const evidence = [
    `来源类型：${sourceTypeLabel(candidate.sourceType)}，指向“${candidate.source}”`,
    `词典检查：${realness >= 70 ? "通过" : "未通过"}`,
    `通用度检查：${genericName ? "太通用" : "通过"}`,
    `通用隐喻检查：${clicheName ? "命中" : "通过"}`,
    `产品事实匹配：${overlap} 个关键词`,
    `套路检查：${slopWarnings.length === 0 ? "通过" : `命中 ${slopWarnings.length} 条`}`,
    `品牌碰撞：${brand ? `与 ${brand} 接近` : "未发现"}`,
  ];

  return {
    passed: issues.length === 0 && slopWarnings.length === 0,
    slopWarnings,
    slopScore,
    concreteness,
    productFit,
    realness,
    issues,
    evidence,
  };
}

function similar(
  a: { name: string; lang: "en" | "zh" },
  b: { name: string; lang: "en" | "zh" },
): boolean {
  if (a.lang !== b.lang) return false;
  if (a.lang === "zh") {
    const charsA = new Set(Array.from(a.name));
    const overlap = Array.from(b.name).filter((char) => charsA.has(char)).length;
    return overlap >= 2;
  }

  const left = a.name.toLowerCase();
  const right = b.name.toLowerCase();
  if (left.slice(0, 3) === right.slice(0, 3)) return true;
  if (left.slice(-3) === right.slice(-3)) return true;
  return levenshtein(left, right) <= 2;
}

type NamingRoute = "en-real" | "en-coined" | "zh-series";

/**
 * 路线抽签：把候选按来源气质分桶——
 * en-real 直球英文词（含口语前缀）、en-coined 造词与真实词组合、zh-series 中文系列词。
 * 每桶一个配额，防止最终名单全是同一气质（I4，偷自 hallmark 的主题抽签）。
 */
function candidateRoute(candidate: {
  name: string;
  lang: "en" | "zh";
  kind: NameCandidate["kind"];
}): NamingRoute {
  if (candidate.lang === "zh") return "zh-series";
  return candidate.kind === "real-word" ? "en-real" : "en-coined";
}

/**
 * 去重选样：相似的名字、同一后缀、同一来源类型、同一路线
 * （直球英文词 / 造词组合词 / 中文系列词）都不超过配额，
 * 防止模型换几个元音就交差或 20 个候选全是同一气质。
 */
export function selectDiverse<
  T extends {
    name: string;
    lang: "en" | "zh";
    kind: NameCandidate["kind"];
    sourceType: string;
    audit: CandidateAudit;
  },
>(
  candidates: T[],
  count: number,
  target: NamingTarget = "product",
  market: Market = "both",
): T[] {
  const ranked = [...candidates].sort(
    (a, b) =>
      b.audit.concreteness +
      b.audit.productFit +
      b.audit.realness -
      (a.audit.concreteness + a.audit.productFit + a.audit.realness),
  );

  // 中英交替取样，避免英文名把中文名全部挤掉；中文市场反过来以中文名为主，
  // 每轮先取两个中文名再取一个英文名（英文名是配对的备用名，不是主体）。
  const langOrder: ReadonlyArray<"en" | "zh"> =
    market === "zh" ? ["zh", "zh", "en"] : ["en", "zh"];
  const groups = new Map<"en" | "zh", T[]>();
  for (const candidate of ranked) {
    const group = groups.get(candidate.lang) ?? [];
    group.push(candidate);
    groups.set(candidate.lang, group);
  }
  const order: T[] = [];
  let added = true;
  while (added) {
    added = false;
    for (const lang of langOrder) {
      const next = groups.get(lang)?.shift();
      if (next) {
        order.push(next);
        added = true;
      }
    }
  }

  const selected: T[] = [];
  const suffixCounts = new Map<string, number>();
  const typeCounts = new Map<string, number>();
  const routeCounts = new Map<string, number>();
  // 中文市场里中文名是主体，气质/来源配额只约束英文备用名；
  // 其他市场维持原配额，防止最终名单全是同一气质。
  const typeLimit = (typeKey: string): number =>
    market === "zh" && typeKey.startsWith("zh:")
      ? count
      : Math.max(2, Math.ceil(count * 0.4));
  const routeLimit = (route: NamingRoute): number =>
    market === "zh" && route === "zh-series"
      ? count
      : Math.max(1, Math.ceil(count / 3));

  const tryAdd = (candidate: T, enforceLimits: boolean): boolean => {
    if (selected.some((existing) => similar(existing, candidate))) return false;

    const typeKey = `${candidate.lang}:${candidate.sourceType}`;
    const routeKey = candidateRoute(candidate);
    if (enforceLimits) {
      if ((typeCounts.get(typeKey) ?? 0) >= typeLimit(typeKey)) {
        return false;
      }
      if ((routeCounts.get(routeKey) ?? 0) >= routeLimit(routeKey)) {
        return false;
      }
    }

    selected.push(candidate);
    if (candidate.lang === "en") {
      const suffix = candidate.name.slice(-3).toLowerCase();
      suffixCounts.set(suffix, (suffixCounts.get(suffix) ?? 0) + 1);
    }
    typeCounts.set(typeKey, (typeCounts.get(typeKey) ?? 0) + 1);
    routeCounts.set(routeKey, (routeCounts.get(routeKey) ?? 0) + 1);
    return true;
  };

  for (const candidate of order) {
    if (selected.length >= count) break;
    tryAdd(candidate, true);
  }

  if (selected.length < count) {
    for (const candidate of order) {
      if (selected.length >= count) break;
      tryAdd(candidate, false);
    }
  }

  // 项目名取向：仓库风格要看得出来。单词名的真词分天然更高（整体是词典词），
  // 连字符名会被挤到最后一位之外，所以给 kebab 留一半席位——不够就用池子里
  // 分数最高的连字符名替掉排在最后的单词名。
  if (target === "repo") {
    const kebab = (item: T) => item.lang === "en" && item.name.includes("-");
    const floor = Math.ceil(count / 2);
    for (const candidate of order) {
      if (selected.filter(kebab).length >= floor) break;
      if (!kebab(candidate) || selected.includes(candidate)) continue;
      // 补位也要过相似度检查，不能为了凑连字符席位塞一个和已有名字太像的。
      if (selected.some((existing) => similar(existing, candidate))) continue;
      let last = -1;
      for (let i = selected.length - 1; i >= 0; i -= 1) {
        if (!kebab(selected[i])) {
          last = i;
          break;
        }
      }
      if (last === -1) break;
      selected[last] = candidate;
    }
  }

  return selected;
}
