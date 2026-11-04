/**
 * 站点提示词内容：提示词正文在根目录 prompt.txt，构建期由 Vite 以 ?raw 内联，
 * 不依赖 node:fs（前端包要能直接跑在浏览器里）。改 prompt.txt 后重新构建即生效。
 * 提示词文字唯一来源是 prompt.txt；案例数据来自 research/prompt-run/ 的实测记录。
 */
import promptTxt from "@/prompt.txt?raw";
import genEnMerged from "@/research/prompt-run/gen-en-merged-latest.json";
import reviewEnMerged from "@/research/prompt-run/review-en-merged-latest.json";
import genPromptFilledEn from "@/research/prompt-run/gen-prompt-filled-en.txt?raw";

/** 标题下的一句话说明，不放进提示词正文。 */
const PROMPT_DESCRIPTION =
  "给开源产品和项目起英文名：npm 包名、GitHub 仓库名、项目名都能用，每个名字附候选域名。注册状态自己去查，查法写在提示词里的「域名核验」段；提示词本身不查，也不声称查过。";

export type PromptCaseRow = {
  name: string;
  /** 包名或仓库名写法，站点里和展示名并排。 */
  packageName?: string;
  /** 名字对应的产品事实，写在名字下面。 */
  fact?: string;
  /** 评审判词或淘汰理由，写在名字下面。 */
  note?: string;
  /** 推荐主域名，附真实注册状态。 */
  primaryDomain?: string;
  /** 候选域名，站点里列出来供用户去查。 */
  domains?: string[];
};

export type PromptEntry = {
  id: string;
  title: string;
  /** 标题下的一句话说明。 */
  description: string;
  promptLabel: string;
  prompt: string;
  /** 实测输入：整段产品描述。 */
  inputText?: string;
  /** 实测结果：那次跑出来的名字。 */
  caseRows: PromptCaseRow[];
  /** 域名说明：候选只代表可去查。 */
  domainsNote?: string;
};

type NameRecord = {
  name: string;
  packageName?: string;
  productFact?: string;
  primaryDomain?: string;
  domains?: string[];
};

type Verdict = { name: string; decision: string; reason: string };

/** 判词太长时截到句子边界，别断在半句上。 */
function trimNote(reason: string, limit: number): string {
  const text = reason.trim();
  if (text.length <= limit) return text;
  const head = text.slice(0, limit);
  const stop = Math.max(head.lastIndexOf("。"), head.lastIndexOf("；"));
  if (stop > limit * 0.5) return head.slice(0, stop + 1);
  return `${head.trimEnd()}…`;
}

/** 评审输出有两种形态：JSON 的 {"verdicts":[...]}，或 markdown 的「### 名字｜保留/淘汰」小节。 */
function parseVerdicts(content: string): Record<string, Verdict> {
  const raw = content.trim();
  if (raw.startsWith("{")) {
    try {
      const parsed = JSON.parse(raw) as { verdicts?: Verdict[] };
      if (Array.isArray(parsed.verdicts)) {
        return Object.fromEntries(parsed.verdicts.map((v) => [v.name, v]));
      }
    } catch {
      // 落到 markdown 解析
    }
  }
  const out: Record<string, Verdict> = {};
  const decisionMap: Record<string, string> = { 保留: "keep", 待定: "hold", 淘汰: "reject" };
  const chunks = raw.split(/^###\s+/m).slice(1);
  for (const chunk of chunks) {
    const [headRaw, ...restLines] = chunk.split("\n");
    const head = headRaw.replaceAll("**", "").trim();
    const withPair = /^(.*?)[（(].*?[)）]\s*[｜|]\s*(保留|待定|淘汰)/.exec(head);
    const plain = /^(.*?)\s*[｜|]\s*(保留|待定|淘汰)\s*$/.exec(head);
    const matched = withPair ?? plain;
    if (!matched) continue;
    const reason = restLines.join("\n").trim().split("\n\n")[0].trim();
    out[matched[1].trim()] = {
      name: matched[1].trim(),
      decision: decisionMap[matched[2]],
      reason,
    };
  }
  if (Object.keys(out).length === 0) {
    throw new Error("复审结论未解析出评审结论");
  }
  return out;
}

/** 实测输入：从填好的提示词里读回整段产品描述，只取产品本身，不带过程统计。 */
function loadInputText(): string {
  const head = genPromptFilledEn.split("运行时流程", 1)[0];
  const wanted = new Set(["产品是什么", "三个关键动作（做了什么 + 对什么）", "不做的事"]);
  const parts: string[] = [];
  for (const line of head.split("\n")) {
    const trimmed = line.trim();
    const idx = trimmed.indexOf("：");
    if (idx <= 0) continue;
    if (wanted.has(trimmed.slice(0, idx))) parts.push(trimmed.slice(idx + 1));
  }
  return parts.join(" ");
}

function loadGenerateEntry(): PromptEntry {
  const gen = genEnMerged as unknown as { response: { names: NameRecord[] } };
  const review = reviewEnMerged as { content: string };
  const verdicts = parseVerdicts(review.content);
  const names = gen.response.names;

  const caseRows: PromptCaseRow[] = names.map((n) => {
    const keep = verdicts[n.name]?.decision === "keep";
    const packageName = n.packageName;
    const productFact = (n.productFact || "").replace(/；?不做什么：.*$/, "");
    return {
      name: n.name,
      // 展示名与包名一样时只显示一次。
      packageName: packageName && packageName !== n.name ? packageName : undefined,
      fact: productFact || undefined,
      note: keep ? undefined : trimNote(verdicts[n.name]?.reason ?? "", 160),
      primaryDomain: n.primaryDomain,
      domains: Array.isArray(n.domains) ? n.domains : undefined,
    };
  });

  return {
    id: "generate",
    title: "起名提示词",
    description: PROMPT_DESCRIPTION,
    promptLabel: "起名提示词",
    prompt: promptTxt,
    inputText: loadInputText(),
    caseRows,
    domainsNote:
      "域名状态是那次实测（2026-11-03）用 RDAP 与 WHOIS 查的：标「可注册」的是当时查到的空位，注册情况会变，注册前自己再查一遍。",
  };
}

export function getPromptEntries(): PromptEntry[] {
  return [loadGenerateEntry()];
}
