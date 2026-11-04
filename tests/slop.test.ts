import { describe, expect, it } from "vitest";
import { auditCandidate } from "@/lib/naming/audit";
import { detectSlop } from "@/lib/naming/slop";

describe("detectSlop", () => {
  it("拦截被用烂的抽象词", () => {
    expect(detectSlop("NexusAI", "en").length).toBeGreaterThan(0);
    expect(detectSlop("Lumina", "en").length).toBeGreaterThan(0);
    expect(detectSlop("SynergyFlow", "en").length).toBeGreaterThan(0);
  });

  it("拦截通用词加后缀", () => {
    expect(detectSlop("Cloudify", "en").length).toBeGreaterThan(0);
    expect(detectSlop("Taskly", "en").length).toBeGreaterThan(0);
    expect(detectSlop("InvoiceAI", "en").length).toBeGreaterThan(0);
  });

  it("拦截两个通用词直接拼接", () => {
    expect(detectSlop("CloudSync", "en").length).toBeGreaterThan(0);
    expect(detectSlop("TaskFlow", "en").length).toBeGreaterThan(0);
  });

  it("不误伤具体名词", () => {
    expect(detectSlop("Ledger", "en")).toEqual([]);
    expect(detectSlop("Gauge", "en")).toEqual([]);
    expect(detectSlop("Sextant", "en")).toEqual([]);
  });

  it("拦截中文泛字组合和生僻字", () => {
    expect(detectSlop("智云", "zh").length).toBeGreaterThan(0);
    expect(detectSlop("创联", "zh").length).toBeGreaterThan(0);
    expect(detectSlop("未来星", "zh").length).toBeGreaterThan(0);
    expect(detectSlop("翀龑", "zh").length).toBeGreaterThan(0);
  });

  it("不误伤具体中文动作", () => {
    expect(detectSlop("对账", "zh")).toEqual([]);
    expect(detectSlop("回车", "zh")).toEqual([]);
    expect(detectSlop("罗盘", "zh")).toEqual([]);
  });

  it("拦截伪拉丁造词", () => {
    const isRealWord = (word: string) =>
      ["ledger", "probe", "aria", "camera", "chart", "return"].includes(word);

    for (const name of [
      "Auralis",
      "Elyra",
      "Ovanta",
      "Quorix",
      "Veltra",
      "Zyntra",
    ]) {
      expect(
        detectSlop(name, "en", "coined", { isRealWord }).length,
      ).toBeGreaterThan(0);
    }
  });

  it("不误伤真实单词的拉丁词尾", () => {
    const isRealWord = (word: string) =>
      ["aria", "camera", "area", "formula"].includes(word);

    expect(detectSlop("Aria", "en", "real-word", { isRealWord })).toEqual([]);
    expect(detectSlop("Camera", "en", "real-word", { isRealWord })).toEqual([]);
    expect(detectSlop("Area", "en", "real-word", { isRealWord })).toEqual([]);
  });

  it("拦截 AI 中文命名套路", () => {
    for (const name of ["云枢", "智域", "星图", "元初", "创联", "未来星"]) {
      expect(detectSlop(name, "zh").length).toBeGreaterThan(0);
    }
  });

  it("不误伤真实中文词", () => {
    for (const name of ["索引", "批注", "朱批", "账本", "卡尺"]) {
      expect(detectSlop(name, "zh")).toEqual([]);
    }
  });

  it("允许四个音节以内的真实词组合", () => {
    const isRealWord = (word: string) =>
      ["name", "rubric", "keel", "buoy"].includes(word);

    expect(detectSlop("Namekeel", "en", "compound", { isRealWord })).toEqual(
      [],
    );
  });

  it("多个真实词连写不算随机音节", () => {
    const isRealWord = (word: string) =>
      ["name", "you", "like", "your"].includes(word);

    // NameYouLike / Yourname 由三个或两个常见真词拼成，元音占比虽高，
    // 但能完整切分成真实单词，不属于「随机拼出的音节」。
    expect(detectSlop("NameYouLike", "en", "compound", { isRealWord })).toEqual([]);
    expect(detectSlop("Yourname", "en", "compound", { isRealWord })).toEqual([]);
  });

  it("切不成真词的元音堆叠仍然判为随机音节", () => {
    const isRealWord = (word: string) =>
      ["name", "you", "like", "your"].includes(word);

    expect(detectSlop("Ouimba", "en", "coined", { isRealWord })).toContain(
      "元音过多，读起来像随机拼出的音节",
    );
  });
});

describe("赛道撞名雷区词根", () => {
  it("design / token / style / system 这类默认构词法被判雷区", () => {
    for (const name of ["DesignKit", "Tokenly", "StyleBase", "ThemeUtils", "OhMyDesign"]) {
      const warnings = detectSlop(name, "en", "real-word", { isRealWord: () => true });
      expect(warnings.join("；"), name).toContain("撞名雷区");
    }
  });

  it("用户点名淘汰的 datum / typecase / measure-twice 直接命中", () => {
    for (const name of ["Datum", "Typecase", "MeasureTwice"]) {
      const warnings = detectSlop(name, "en", "real-word", { isRealWord: () => true });
      expect(warnings.join("；"), name).toContain("撞名雷区");
    }
  });

  it("正常名字不被雷区误伤", () => {
    for (const name of ["Caliper", "Gauge", "Sextant", "Plumb", "Kaku"]) {
      const warnings = detectSlop(name, "en", "real-word", { isRealWord: () => true });
      expect(warnings.join("；"), name).not.toContain("撞名雷区");
    }
  });
});

describe("赛道在营竞品品牌碰撞", () => {
  it("Supernova / Zeplin / Storybook / dembrandt 这类同赛道在营产品被判撞名", () => {
    for (const name of ["Supernova", "Zeplin", "Storybook", "Backlight"]) {
      const warnings = detectSlop(name, "en", "real-word", { isRealWord: () => true });
      const audit = auditCandidate(
        {
          name,
          englishName: "",
          kind: "real-word",
          lang: "en",
          strategy: "concrete",
          sourceType: "object",
          source: "一个具体物件",
          sourceDetail: "一个真实存在的物件。",
          productFact: "产品要在 API 请求失败时定位到具体请求",
          meaning: "一个物件",
          rationale: "产品在每次请求失败时定位到具体请求，名字对应那个物件。",
          pronunciation: name,
          riskNotes: "",
          slopWarnings: warnings,
        },
        {
          category: "devtool",
          audience: "独立开发者",
          coreAction: "定位失败请求",
          differentiator: "",
          productFacts: ["每次请求"],
          competitors: [],
          avoidWords: [],
        },
        "给独立开发者用的 API 监控工具，出问题时告诉我哪一次请求、哪一个依赖挂了。",
      );
      expect(audit.evidence.join("；"), name).toContain("品牌碰撞：与");
      expect(audit.passed, name).toBe(false);
    }
  });
});
