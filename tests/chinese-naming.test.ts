import { describe, expect, it } from "vitest";
import { auditCandidate } from "@/lib/naming/audit";
import { detectSlop } from "@/lib/naming/slop";
import type { GenerateInput, NameCandidate, ProductBrief } from "@/lib/types";

const input: GenerateInput = {
  description: "给中文用户做网页设计和绘图的 skill，把文字说明变成页面和图片。",
  keywords: "归藏、设计、draw、skill",
  market: "zh",
  target: "repo",
  count: 6,
  strictAntiSlop: true,
};

const brief: ProductBrief = {
  category: "design",
  audience: "中文用户",
  coreAction: "做网页设计和绘图",
  differentiator: "",
  productFacts: ["网页设计", "绘图", "文字说明"],
  competitors: [],
  avoidWords: [],
};

function zhPair(name: string, englishName: string): NameCandidate {
  return {
    name,
    englishName,
    lang: "zh",
    kind: "real-word",
    strategy: "chinese",
    sourceType: "action",
    source: `${name}是真实动作，拼音 ${englishName.split("-")[0]}`,
    sourceDetail: `${name}是财务实务里的核对动作，拼音 ${englishName.split("-")[0]}；design 表示网页设计。`,
    productFact: "给中文用户做网页设计和绘图的 skill，把文字说明变成页面和图片",
    rationale: "网页设计和绘图对应 design 和 draw，skill 说明交付的是技能。",
    meaning: "中文主体加用途",
    pronunciation: "dui zhang",
    slopWarnings: [],
  };
}

function latinName(name: string, source: string): NameCandidate {
  return {
    name,
    lang: "en",
    kind: "compound",
    strategy: "compound",
    sourceType: "compound",
    source,
    sourceDetail: `${source}；design 表示网页设计，skill 表示技能。`,
    productFact: "给中文用户做网页设计和绘图的 skill，把文字说明变成页面和图片",
    rationale: "网页设计和绘图对应 design 和 draw，skill 说明交付的是技能。",
    meaning: "中文主体加用途",
    pronunciation: name.replace(/-/g, " "),
    slopWarnings: [],
  };
}

describe("中文主体与拼音用途名", () => {
  it("中文名的配名允许拼音以及拼音-功能词", () => {
    for (const englishName of [
      "duizhang",
      "duizhang-ledger",
      "duizhang-draw",
      "duizhang-it",
    ]) {
      const audit = auditCandidate(zhPair("对账", englishName), brief, input.description);
      expect(audit.passed, `${englishName}: ${audit.issues.join(";")}`).toBe(true);
    }
  });

  it("仓库名允许可验证的拼音-用途-skill 三词结构", () => {
    const audit = auditCandidate(
      latinName("guizang-design-skill", "归藏是中文词，guizang 是其拼音"),
      brief,
      input.description,
      "repo",
      "归藏",
    );
    expect(audit.passed, audit.issues.join(";")).toBe(true);
  });

  it("拼音-用途名认用途词，也认描述里的中文组成词", () => {
    const audit = auditCandidate(
      latinName("guizang-ppt", "归藏是古书《归藏》，guizang 是其拼音"),
      brief,
      input.description,
      "repo",
      "归藏",
    );
    expect(audit.passed, audit.issues.join(";")).toBe(true);

    const describedOnly = auditCandidate(
      latinName("guizang-huitu", "归藏是古书《归藏》，guizang 是其拼音"),
      { ...brief, productFacts: ["绘图"] },
      "把一句话描述变成网页和配图，支持绘图。",
      "repo",
      "归藏",
    );
    expect(describedOnly.passed, describedOnly.issues.join(";")).toBe(true);
  });

  it("来源里没有中文汉字时拼音无法核验，不放行", () => {
    const audit = auditCandidate(
      latinName("guizang-draw", "Guizang is the pinyin of an ancient book"),
      brief,
      "把一句话描述变成网页和配图。",
      "repo",
    );
    expect(audit.passed).toBe(false);
  });

  it("拼音只在模型自述里出现、产品描述里没有时拒掉", () => {
    const audit = auditCandidate(
      latinName("guizang-draw", "归藏是古书《归藏》，guizang 是其拼音"),
      brief,
      "把一句话描述变成网页和配图。",
      "repo",
      "",
    );
    expect(audit.passed).toBe(false);
  });

  it("拼音读不回来源里的中文词时不放行", () => {
    const audit = auditCandidate(
      latinName("duizhang-ledger", "归藏是中文词，guizang 是其拼音"),
      brief,
      input.description,
      "repo",
      "归藏",
    );
    expect(audit.passed).toBe(false);
  });

  it("随机拉丁词不能靠 skill 后缀冒充拼音", () => {
    const audit = auditCandidate(
      latinName("zafuno-skill", "归藏是中文词，guizang 是其拼音"),
      brief,
      input.description,
      "repo",
      "归藏",
    );
    expect(audit.passed).toBe(false);
  });

  it("英文路线仍按原套路规则拦", () => {
    expect(detectSlop("DesignAI", "en", "compound").length).toBeGreaterThan(0);
  });
});

describe("审查发现的规则不对称", () => {
  it("库外真实词靠拼音读回名字本身也能过，生造词仍被套路拦", () => {
    const guizang = auditCandidate(
      {
        ...latinName("guizang-design", "归藏是古书《归藏》，guizang 是其拼音"),
        lang: "zh",
        name: "归藏",
        englishName: "guizang-design",
        strategy: "chinese",
        sourceType: "real-word",
      },
      { ...brief, productFacts: ["网页设计"] },
      "给中文用户做网页设计和绘图的 skill。",
      "product",
      "归藏",
    );
    expect(guizang.passed, guizang.issues.join(";")).toBe(true);

    const coined = auditCandidate(
      {
        ...latinName("zhiyu-design", "智域是自造词"),
        lang: "zh",
        name: "智域",
        englishName: "zhiyu-design",
        strategy: "chinese",
      },
      brief,
      "给中文用户做网页设计和绘图的 skill。",
      "product",
      "智域",
    );
    expect(coined.passed).toBe(false);
  });

  it("中文名合格但配名带技术后缀时同样拒绝", () => {
    const audit = auditCandidate(
      zhPair("对账", "duizhang-cli"),
      { ...brief, productFacts: ["对账", "网页设计"] },
      "给中文用户做网页设计和绘图的 skill。",
      "product",
      "对账",
    );
    expect(audit.passed).toBe(false);
    expect(audit.issues.join(" ")).toContain("cli");
  });

  it("productFact 不引用产品描述时即使理由抄了描述也不算匹配", () => {
    const base = zhPair("对账", "duizhang");
    const audit = auditCandidate(
      {
        ...base,
        productFact: "提升效率，让工作更简单",
        rationale: "网页设计和绘图对应页面和图片，对账是逐笔核对。",
      },
      brief,
      input.description,
      "product",
      "对账",
    );
    expect(audit.productFit).toBeLessThan(50);
    expect(audit.passed).toBe(false);
  });
});
