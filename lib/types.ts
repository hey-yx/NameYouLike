export type Market = "zh" | "en" | "both";
/** 命名目标：产品名（品牌向，单词为主）或 GitHub 项目名（仓库向，允许 kebab-case）。 */
export type NamingTarget = "product" | "repo";
export type NameKind = "coined" | "compound" | "real-word";
export type NameLang = "en" | "zh";

export type NameStrategy =
  | "concrete"
  | "verb"
  | "metaphor"
  | "coined"
  | "compound"
  | "reference"
  | "prefix"
  | "chinese"
  | "single-word"
  | "plainspoken";

export type SourceType =
  | "object"
  | "action"
  | "place"
  | "person"
  | "real-word"
  | "compound"
  | "phrase";

export interface NameCandidate {
  name: string;
  /** 中文名的拉丁字母配名，可用拼音、英文或两者组合；英文候选本身留空 */
  englishName?: string;
  kind: NameKind;
  lang: NameLang;
  strategy: NameStrategy;
  sourceType: SourceType;
  /** 真实存在的来源：一个物件、动作、地点、人物或真实词组 */
  source: string;
  /** 来源的具体解释，不能写“一种感觉”“未来感” */
  sourceDetail: string;
  /** 产品描述里的具体事实，用于审计理由是否空泛 */
  productFact: string;
  meaning: string;
  rationale: string;
  pronunciation: string;
  riskNotes?: string;
  slopWarnings: string[];
}

export interface CandidateAudit {
  passed: boolean;
  slopScore: number;
  concreteness: number;
  productFit: number;
  realness: number;
  issues: string[];
  evidence: string[];
}

export interface ProductBrief {
  category: string;
  audience: string;
  coreAction: string;
  differentiator: string;
  productFacts: string[];
  competitors: string[];
  avoidWords: string[];
}

export interface GenerateInput {
  description: string;
  keywords?: string;
  market: Market;
  /** 命名目标：产品名或 GitHub 项目名，决定生成取向与审计判据。 */
  target: NamingTarget;
  count: number;
  strictAntiSlop: boolean;
}


