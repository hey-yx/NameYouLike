import { describe, expect, it } from "vitest";
import type { NameCandidate, ProductBrief } from "@/lib/types";
import { auditCandidate, selectDiverse } from "@/lib/naming/audit";

const BRIEF: ProductBrief = {
  category: "devtool",
  audience: "独立开发者",
  coreAction: "在请求失败时定位到具体请求和依赖",
  differentiator: "给出可排查的上下文",
  productFacts: ["每次请求", "依赖挂了"],
  competitors: ["Datadog", "Sentry"],
  avoidWords: [],
};

const DESCRIPTION =
  "给独立开发者用的 API 监控工具，出问题时告诉我哪一次请求、哪一个依赖挂了。";

const NAMING_DESCRIPTION =
  "一个给独立开发者和小团队用的起名与域名检查工具。每个名字必须有真实来源，拒绝套路名；同时检查域名是否可注册。";

const NAMING_BRIEF: ProductBrief = {
  category: "devtool",
  audience: "独立开发者",
  coreAction: "给产品起名并检查域名",
  differentiator: "用真实来源和审计规则过滤套路名",
  productFacts: ["真实来源", "域名检查"],
  competitors: [],
  avoidWords: [],
};

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

function audited(overrides: Partial<NameCandidate> = {}) {
  const value = candidate(overrides);
  return {
    ...value,
    audit: auditCandidate(value, BRIEF, DESCRIPTION),
  };
}

describe("auditCandidate", () => {
  it("接受真实物件和具体产品事实", () => {
    const audit = auditCandidate(candidate(), BRIEF, DESCRIPTION);
    expect(audit.passed).toBe(true);
    expect(audit.realness).toBeGreaterThanOrEqual(90);
    expect(audit.productFit).toBeGreaterThanOrEqual(75);
  });

  it("拒绝空泛来源和空话理由", () => {
    const audit = auditCandidate(
      candidate({
        name: "Auralis",
        kind: "coined",
        sourceType: "phrase",
        source: "innovation",
        sourceDetail: "A feeling of innovation and future potential.",
        productFact: "提升效率",
        rationale: "它朗朗上口，很有科技感。",
      }),
      BRIEF,
      DESCRIPTION,
    );

    expect(audit.passed).toBe(false);
    expect(audit.issues.length).toBeGreaterThan(0);
    expect(audit.slopScore).toBeGreaterThan(0);
  });

  it("接受中文名的拼音配名，读不回中文的拼音仍拒", () => {
    const base = {
      name: "对账",
      englishName: "Duizhang",
      lang: "zh" as const,
      strategy: "chinese" as const,
      sourceType: "action" as const,
      source: "对账",
      sourceDetail: "对账是逐笔核对账目、找出对不上的那一笔的动作。",
      productFact: "每次请求失败时定位到具体请求和依赖",
      rationale:
        "产品要在 API 请求失败时定位到具体请求和依赖，对账对应逐笔核对。",
      pronunciation: "dui zhang",
    };
    const paired = auditCandidate(candidate(base), BRIEF, DESCRIPTION);
    expect(paired.passed, paired.issues.join(";")).toBe(true);

    const mismatched = auditCandidate(
      candidate({ ...base, englishName: "Guizang" }),
      BRIEF,
      DESCRIPTION,
    );
    expect(mismatched.passed).toBe(false);
  });

  it("拒绝与已知品牌同名", () => {
    const audit = auditCandidate(
      candidate({
        name: "Sentry",
        source: "sentry",
        sourceDetail:
          "A sentry is a guard who keeps watch at an entrance.",
        rationale:
          "产品要在 API 请求失败时定位到具体请求和依赖，Sentry 对应守夜人。",
      }),
      BRIEF,
      DESCRIPTION,
    );

    expect(audit.passed).toBe(false);
    expect(audit.issues.join(" ")).toContain("sentry");
  });

  // NameYouLike 是产品自己的名字：三个常见真词连写。
  // 2026-10-30 起 realness 与元音密度都认「可完整切分成多个真实词」，它应当通过。
  it("产品自己的名字 NameYouLike 按多真词连写通过", () => {
    const audit = auditCandidate(
      candidate({
        name: "NameYouLike",
        kind: "compound",
        sourceType: "compound",
        source: "name + you + like",
        sourceDetail:
          "The product promise in three common English words: you end up with a name you like.",
        productFact:
          "每个名字必须有真实来源，拒绝套路名，并检查域名是否可注册",
        rationale:
          "这个工具给独立开发者和小团队用：每个名字必须有真实来源，同时检查域名是否可注册，NameYouLike 把这句话压成了一个名字。",
      }),
      NAMING_BRIEF,
      NAMING_DESCRIPTION,
    );

    expect(audit.slopWarnings).toEqual([]);
    expect(audit.realness).toBeGreaterThanOrEqual(90);
    expect(audit.passed, audit.issues.join(";")).toBe(true);
  });

  it("中文自然短语不再被判成生造词", () => {
    for (const name of ["叫什么", "就这个", "记在这", "哪一页"]) {
      const audit = auditCandidate(
        candidate({
          name,
          lang: "zh",
          strategy: "chinese",
          kind: "real-word",
          sourceType: "phrase",
          source: name,
          sourceDetail: `${name} 是日常口语里能直接说出口的一句话，不是拼接出来的意象词。`,
          productFact: "每个名字必须有真实来源，拒绝套路名，并检查域名是否可注册",
          rationale:
            "这个工具要帮独立开发者挑名字，名字本身像一个日常问句，读起来直接。",
          pronunciation: name,
        }),
        NAMING_BRIEF,
        NAMING_DESCRIPTION,
      );
      expect(audit.realness, name).toBeGreaterThanOrEqual(70);
      expect(audit.passed, `${name}: ${audit.issues.join(";")}`).toBe(true);
    }
  });

  it("中文泛字拼接仍被判生造", () => {
    for (const name of ["云枢", "智域", "星图"]) {
      const audit = auditCandidate(
        candidate({
          name,
          lang: "zh",
          strategy: "chinese",
          kind: "coined",
          sourceType: "phrase",
          source: name,
          sourceDetail: `${name} 是一种未来的感觉。`,
          productFact: "提升效率",
          rationale: "朗朗上口，很有科技感。",
          pronunciation: name,
        }),
        NAMING_BRIEF,
        NAMING_DESCRIPTION,
      );
      expect(audit.passed, name).toBe(false);
    }
  });

  it("接受口语前缀加具体物件", () => {
    for (const name of ["GetSextant", "TryPlumb", "OnMyProbe", "MeetBuoy"]) {
      const audit = auditCandidate(
        candidate({
          name,
          kind: "compound",
          strategy: "prefix",
          sourceType: "compound",
          source: "口语前缀 + 具体物件",
          sourceDetail:
            "The prefix carries the action (get/try/meet); the主体 is a real instrument the product actually uses.",
          productFact: "每次请求失败时定位到具体请求和依赖",
          rationale:
            "产品要在 API 请求失败时定位到具体请求和依赖，这个名字对应真实的排查动作。",
        }),
        BRIEF,
        DESCRIPTION,
      );
      expect(audit.passed, `${name} should pass`).toBe(true);
    }
  });

  it("前缀加通用词仍然拒绝", () => {
    const audit = auditCandidate(
      candidate({
        name: "TryTool",
        kind: "compound",
        strategy: "prefix",
        sourceType: "compound",
        source: "try + tool",
        sourceDetail: "Try means to attempt; tool is a generic instrument.",
        productFact: "每次请求失败时定位到具体请求和依赖",
        rationale:
          "产品要在 API 请求失败时定位到具体请求和依赖，TryTool 对应排查动作。",
      }),
      BRIEF,
      DESCRIPTION,
    );

    expect(audit.passed).toBe(false);
    expect(audit.issues.join(" ")).toContain("太通用");
  });
});

describe("selectDiverse", () => {
  it("相似名字只保留一个", () => {
    const selected = selectDiverse(
      [
        audited({ name: "Probe" }),
        audited({ name: "Probes" }),
        audited({ name: "Chart" }),
      ],
      2,
    );

    expect(selected).toHaveLength(2);
    expect(selected.map((item) => item.name)).not.toEqual([
      "Probe",
      "Probes",
    ]);
  });

  it("路线配额：直球英文词和造词组合词都进名单，不全是同一气质", () => {
    const realWords = [
      { name: "Probe", sourceType: "object" as const },
      { name: "Chart", sourceType: "object" as const },
      { name: "Buoy", sourceType: "action" as const },
      { name: "Lathe", sourceType: "action" as const },
    ].map((item) =>
      audited({ name: item.name, sourceType: item.sourceType }),
    );
    const coined = [
      { name: "Inkforge", sourceType: "place" as const },
      { name: "Paperbolt", sourceType: "place" as const },
      { name: "Copperloop", sourceType: "person" as const },
      { name: "Saltbridge", sourceType: "person" as const },
    ].map((item) =>
      audited({
        name: item.name,
        kind: "coined" as const,
        sourceType: item.sourceType,
        sourceDetail: `${item.name} combines two real roots: ink and forge, named after a workshop place.`,
      }),
    );

    const selected = selectDiverse([...realWords, ...coined], 4);

    expect(selected).toHaveLength(4);
    const routes = selected.map((item) =>
      item.kind === "real-word" ? "en-real" : "en-coined",
    );
    expect(routes.filter((route) => route === "en-real")).toHaveLength(2);
    expect(routes.filter((route) => route === "en-coined")).toHaveLength(2);
  });

  it("带真实出处的文化意象词视为真词：北斗 / 木兰 / 唐 的词典检查通过", () => {
    // 这类词有据可查，是权威真词表的一部分，审计不能因为词表没收录就判
    // 「不是常见实词」——否则真实的中文名会被成批误杀。
    for (const name of ["北斗", "木兰", "唐", "小满"]) {
      const audit = auditCandidate(
        candidate({
          name,
          englishName: "Polaris",
          lang: "zh",
          source: "北斗七星",
          sourceDetail: `${name} 出自典籍，有真实出处与来历。`,
          rationale: `产品要在 API 请求失败时定位到具体请求和依赖，${name} 对应定位参照。`,
          meaning: "一个具体意象",
          pronunciation: name,
        }),
        BRIEF,
        DESCRIPTION,
      );
      expect(audit.realness, `${name} 的词典检查`).toBeGreaterThanOrEqual(70);
      expect(audit.issues.join("；")).not.toContain("不是常见实词");
    }
  });

  it("自造中文词仍然被词典检查拦下", () => {
    const audit = auditCandidate(
      candidate({
        name: "北星库",
        englishName: "PolarisVault",
        lang: "zh",
        source: "北斗",
        sourceDetail: "把北斗改字成北星库。",
        rationale: "产品要在 API 请求失败时定位到具体请求和依赖，北星库对应定位参照。",
        meaning: "一个具体意象",
        pronunciation: "北星库",
      }),
      BRIEF,
      DESCRIPTION,
    );
    expect(audit.realness).toBeLessThan(70);
  });

  it("TW93 式外语实词：Kaku / Pake 说清词源就不算造词", () => {
    const audit = auditCandidate(
      candidate({
        name: "Kaku",
        strategy: "single-word",
        kind: "real-word",
        sourceType: "real-word",
        source: "日语「書く」",
        sourceDetail: "日语词「書く」（kaku），意思是写；终端里天天在写，名字就是核心动作。",
        rationale: "产品在每次请求失败时定位到具体请求，Kaku 对应把排查过程写下来这个动作。",
        meaning: "日语「写」",
        pronunciation: "KAH-koo",
      }),
      BRIEF,
      DESCRIPTION,
    );
    expect(audit.realness).toBeGreaterThanOrEqual(70);
    expect(audit.issues.join("；")).not.toContain("不是词典里的真实单词");
  });

  it("说不清词源的短造词仍被拦下", () => {
    const audit = auditCandidate(
      candidate({
        name: "Zixo",
        strategy: "single-word",
        kind: "real-word",
        sourceType: "real-word",
        source: "一个听起来顺的词",
        sourceDetail: "读音顺口，没有具体来源。",
        rationale: "产品在每次请求失败时定位到具体请求，Zixo 对应定位动作。",
        meaning: "无",
        pronunciation: "ZIK-so",
      }),
      BRIEF,
      DESCRIPTION,
    );
    expect(audit.realness).toBeLessThan(70);
  });

  it("路线配额：中文系列词不被英文名全部挤掉", () => {
    const english = ["Probe", "Chart", "Buoy", "Lathe"].map((name) =>
      audited({ name }),
    );
    const chinese = [
      { name: "对账", englishName: "Reconcile" },
      { name: "回车", englishName: "Return" },
    ].map((item) =>
      audited({
        name: item.name,
        englishName: item.englishName,
        lang: "zh" as const,
        strategy: "chinese" as const,
        sourceType: "action" as const,
        source: item.name,
        sourceDetail: `${item.name}是日常里真实存在的核对或确认动作。`,
        productFact: "每次请求失败时定位到具体请求和依赖",
        rationale: `产品要在 API 请求失败时定位到具体请求和依赖，${item.name} 对应逐笔核对的排查动作。`,
        meaning: "一个具体动作",
        pronunciation: item.name,
      }),
    );

    const selected = selectDiverse([...english, ...chinese], 3);

    expect(selected).toHaveLength(3);
    expect(selected.filter((item) => item.lang === "zh")).toHaveLength(1);
  });

  it("中文市场下中文名是主体，英文备用名不挤掉中文名", () => {
    const chinese = [
      { name: "对账", englishName: "Reconcile" },
      { name: "盘库", englishName: "Stocktake" },
      { name: "结单", englishName: "Settle" },
      { name: "票据", englishName: "Slip" },
      { name: "流水", englishName: "Ledger" },
      { name: "回车", englishName: "Return" },
    ].map((item) =>
      audited({
        name: item.name,
        englishName: item.englishName,
        lang: "zh" as const,
        strategy: "chinese" as const,
        sourceType: "action" as const,
        source: item.name,
        sourceDetail: `${item.name}是日常里真实存在的核对或确认动作。`,
        productFact: "每次请求失败时定位到具体请求和依赖",
        rationale: `产品要在 API 请求失败时定位到具体请求和依赖，${item.name} 对应逐笔核对的排查动作。`,
        meaning: "一个具体动作",
        pronunciation: item.name,
      }),
    );
    const english = ["Probe", "Pinpoint", "Traceback", "Sextant"].map((name) =>
      audited({ name }),
    );

    const selected = selectDiverse(
      [...english, ...chinese],
      6,
      "product",
      "zh",
    );

    expect(selected).toHaveLength(6);
    const zhCount = selected.filter((item) => item.lang === "zh").length;
    const enCount = selected.filter((item) => item.lang === "en").length;
    // 中文市场：中文名占多数，英文名只是备用席位
    expect(zhCount).toBeGreaterThan(enCount);
  });
});
