import { describe, expect, it } from "vitest";
import type { NameCandidate, ProductBrief } from "@/lib/types";
import { auditCandidate } from "@/lib/naming/audit";
import {
  PRODUCT_MAX_LETTERS,
  CULTURE_MAX_SHARE,
  enforceCultureShare,
  isCultureFlavored,
  productFormIssues,
} from "@/lib/naming/form";

// 只认这几个词的假词典：真词典要读磁盘，单测里没必要。
const fakeDict = new Set(["score", "encore", "gauge", "caliper", "plumb"]);
const isRealWord = (word: string) => fakeDict.has(word.toLowerCase());

describe("productFormIssues：产品名形态判据", () => {
  it("像真产品名的候选完全通过", () => {
    for (const name of ["Caliper", "Gauge", "Plumb", "Vercel", "Loom"]) {
      expect(productFormIssues(name, "en", { isRealWord })).toEqual([]);
    }
  });

  it("超过 10 个字母要给出长度理由", () => {
    const issues = productFormIssues("Observability", "en", { isRealWord });
    expect(issues).toHaveLength(1);
    expect(issues[0]).toContain("13");
    expect(issues[0]).toContain("产品名");
  });

  it("10 个字母以内放行（品牌 p90 = 9）", () => {
    expect(productFormIssues("Characters", "en", { isRealWord })).toEqual([]);
  });

  it("包名的技术后缀要被拦下并说清理由", () => {
    for (const name of ["gaugekit", "measure-sdk", "trace-utils"]) {
      const issues = productFormIssues(name, "en", { isRealWord });
      expect(issues.some((issue) => issue.includes("0 次"))).toBe(true);
    }
  });

  it("整名是词典里的真词时不按后缀误伤（score / encore）", () => {
    expect(productFormIssues("Score", "en", { isRealWord })).toEqual([]);
    expect(productFormIssues("Encore", "en", { isRealWord })).toEqual([]);
  });

  it("中文候选不套用英文形态规则", () => {
    expect(productFormIssues("卡尺", "zh")).toEqual([]);
  });
});

const BRIEF: ProductBrief = {
  category: "devtool",
  audience: "独立开发者",
  coreAction: "在请求失败时定位到具体请求和依赖",
  differentiator: "给出可排查的上下文",
  productFacts: ["每次请求", "依赖挂了"],
  competitors: [],
  avoidWords: [],
};

const DESCRIPTION =
  "给独立开发者用的 API 监控工具，出问题时告诉我哪一次请求、哪一个依赖挂了。";

function candidate(overrides: Partial<NameCandidate> = {}): NameCandidate {
  return {
    name: "Probe",
    kind: "real-word",
    lang: "en",
    strategy: "concrete",
    sourceType: "object",
    source: "probe",
    sourceDetail:
      "A probe is a physical instrument used to test or measure something.",
    productFact: "每次请求失败时定位到具体请求和依赖",
    meaning: "探针",
    rationale:
      "产品要在 API 请求失败时定位到具体请求和依赖，Probe 对应排查动作。",
    pronunciation: "probe",
    slopWarnings: [],
    ...overrides,
  };
}

describe("接进审计层：命中形态判据要给明确理由", () => {
  it("超过长度上限的英文名在产品名目标下被拒，理由带统计数字", () => {
    const name = "Instrumentationis";
    expect(name.length).toBeGreaterThan(PRODUCT_MAX_LETTERS);
    const audit = auditCandidate(
      candidate({ name, kind: "coined" }),
      BRIEF,
      DESCRIPTION,
      "product",
    );
    expect(audit.passed).toBe(false);
    expect(
      audit.issues.some((issue) => issue.includes("真实产品名的长度中位是 7")),
    ).toBe(true);
  });

  it("技术后缀的英文名被按「像包名不像产品名」拒掉", () => {
    const audit = auditCandidate(
      candidate({ name: "measurekit", kind: "compound" }),
      BRIEF,
      DESCRIPTION,
      "product",
    );
    expect(audit.passed).toBe(false);
    expect(
      audit.issues.some((issue) => issue.includes("出现 0 次")),
    ).toBe(true);
  });

  it("「文化意象词 + 实字」的拼接怪在产品名目标下被拒", () => {
    const audit = auditCandidate(
      candidate({
        name: "北斗尺",
        lang: "zh",
        source: "北斗",
        sourceDetail: "北斗七星是一架 detectors.",
        productFact: "每次请求失败时定位到具体请求和依赖",
        meaning: "用北斗七星的指向做一把尺",
        rationale: "出问题时像北斗一样给方向，尺对应量出具体哪次请求。",
        pronunciation: "bei dou chi",
      }),
      BRIEF,
      DESCRIPTION,
      "product",
    );
    expect(audit.passed).toBe(false);
    expect(audit.issues.some((issue) => issue.includes("意象堆叠"))).toBe(true);
  });

  it("同一个名字在 GitHub 项目名目标下不按产品名形态拦", () => {
    const audit = auditCandidate(
      candidate({ name: "Instrumentationis", kind: "compound" }),
      BRIEF,
      DESCRIPTION,
      "repo",
    );
    expect(
      audit.issues.some((issue) => issue.includes("真实产品名的长度中位是 7")),
    ).toBe(false);
  });
});

interface Pick {
  name: string;
  lang: "en" | "zh";
  source: string;
  sourceDetail: string;
}

const item = (name: string, lang: "en" | "zh", source = "", detail = ""): Pick => ({
  name,
  lang,
  source,
  sourceDetail: detail,
});

describe("enforceCultureShare：文化意象降权但不为零", () => {
  const pool: Pick[] = [
    item("Caliper", "en", "卡尺", "游标卡尺的英文名"),
    item("Gauge", "en", "量规", "塞规英文名"),
    item("Plumb", "en", "铅垂", "铅垂线英文名"),
    item("Sizing", "en", "套号", "工业件套号"),
    item("Tempo", "en", "节拍", "节拍器"),
  ];

  it("意象当选测办法认得出：名字咬住文化意象词或来源就是它", () => {
    expect(isCultureFlavored(item("北斗尺", "zh", "北斗", "北斗七星"))).toBe(true);
    expect(isCultureFlavored(item("汉", "zh", "", ""))).toBe(false);
    expect(isCultureFlavored(item("Gauge", "en", "量规", "塞规英文名"))).toBe(false);
    expect(isCultureFlavored(item("Kylin", "en", "麒麟", "麒麟这句！"))).toBe(true);
  });

  it("意象占比超配额时用同批候选替下来，且总数不变", () => {
    const selected: Pick[] = [
      item("北斗", "zh", "北斗", "北斗七星"),
      item("甘棠", "zh", "甘棠", "召南"),
      item("赤兔", "zh", "赤兔", "吕布的马"),
      item("Caliper", "en", "卡尺", "游标卡尺"),
      item("Gauge", "en", "量规", "塞规"),
      item("Plumb", "en", "铅垂", "铅垂线"),
    ];
    const quota = Math.max(1, Math.ceil(selected.length * CULTURE_MAX_SHARE));
    expect(quota).toBe(1);

    const result = enforceCultureShare(selected, pool);
    expect(result).toHaveLength(selected.length);
    const cultureCount = result.filter((candidate) =>
      isCultureFlavored(candidate),
    ).length;
    expect(cultureCount).toBeLessThanOrEqual(quota);
    expect(cultureCount).toBeGreaterThan(0);
  });

  it("本来就没超配额时不改动结果", () => {
    const selected = pool.slice(0, 3);
    expect(enforceCultureShare(selected, pool)).toEqual(selected);
  });

  it("全是意象且没有替代候选人时保留配额内的意象，不空手而归", () => {
    const selected = [
      item("北斗", "zh", "北斗", "北斗七星"),
      item("甘棠", "zh", "甘棠", "召南"),
    ];
    const result = enforceCultureShare(selected, []);
    expect(result).toHaveLength(1);
    expect(isCultureFlavored(result[0])).toBe(true);
  });
});
