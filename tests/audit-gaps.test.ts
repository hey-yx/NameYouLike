import { describe, expect, it } from "vitest";
import { auditCandidate, selectDiverse } from "@/lib/naming/audit";
import type { CandidateAudit, NameCandidate, ProductBrief } from "@/lib/types";

const brief = {
  category: "devtool",
  audience: "独立开发者",
  coreAction: "定位失败请求",
  differentiator: "",
  productFacts: ["每次请求"],
  competitors: [],
  avoidWords: [],
} as unknown as ProductBrief;

function candidate(extra: Record<string, unknown>): NameCandidate {
  return {
    name: "Probe",
    lang: "en",
    kind: "real-word",
    strategy: "concrete",
    sourceType: "object",
    source: "probe",
    sourceDetail: "A probe is a physical instrument used to test things.",
    productFact: "每次请求失败时定位到具体请求和依赖",
    meaning: "探针",
    rationale: "产品要在 API 请求失败时定位到具体请求和依赖。",
    pronunciation: "probe",
    slopWarnings: [],
    ...extra,
  } as unknown as NameCandidate;
}

describe("auditCandidate 未覆盖分支", () => {
  it("意象堆叠判定不误伤三字真词", () => {
    const audit = auditCandidate(
      candidate({ name: "黑匣子", lang: "zh", strategy: "chinese" }),
      brief,
      "描述",
      "product",
    );
    expect(audit.issues).not.toContain(
      "意象堆叠：文化意象词再加一个字拼成的名字（北斗尺、麒麟册式），不像产品名",
    );
  });

  it("口语前缀 + 两个真词根的主体按 85 分判真词", () => {
    const audit = auditCandidate(
      candidate({ name: "TryDrumChart", kind: "coined" }),
      brief,
      "描述",
      "product",
    );
    expect(audit.realness).toBe(85);
    expect(
      audit.issues.some((issue) => issue.includes("不是词典里的真实单词")),
    ).toBe(false);
  });

  it("来源只有一两个字符时扣具体度", () => {
    const short = auditCandidate(
      candidate({ source: "x" }),
      brief,
      "alpha beta gamma delta",
      "product",
    );
    const longer = auditCandidate(
      candidate({ source: "xy" }),
      brief,
      "alpha beta gamma delta",
      "product",
    );
    expect(longer.concreteness - short.concreteness).toBe(20);
  });

  it("理由与描述重叠 3 个词给 95 分、2 个给 75 分，事实必须引用原词", () => {
    const three = auditCandidate(
      candidate({
        productFact: "alpha beta",
        rationale: "alpha beta gamma delta",
      }),
      brief,
      "the alpha beta gamma delta",
      "product",
    );
    expect(three.productFit).toBe(95);
    const two = auditCandidate(
      candidate({ productFact: "alpha", rationale: "alpha beta" }),
      brief,
      "the alpha beta gamma delta",
      "product",
    );
    expect(two.productFit).toBe(75);
    const emptyFact = auditCandidate(
      candidate({ productFact: "提升效率", rationale: "alpha beta gamma delta" }),
      brief,
      "the alpha beta gamma delta",
      "product",
    );
    expect(emptyFact.productFit).toBe(15);
  });

  it("理由与描述只重叠 1 个词时给 45 分", () => {
    const one = auditCandidate(
      candidate({ productFact: "alpha", rationale: "alpha" }),
      brief,
      "the alpha beta gamma delta",
      "product",
    );
    expect(one.productFit).toBe(45);
  });

  it("短外来词说不清词源不算真词", () => {
    const audit = auditCandidate(
      candidate({ name: "kaku", sourceDetail: "" }),
      brief,
      "描述",
      "product",
    );
    expect(audit.realness).toBe(15);
  });

  it("造词的词根统计找不到词根时不加分", () => {
    const audit = auditCandidate(
      candidate({ name: "kaku", kind: "coined", sourceDetail: "123" }),
      brief,
      "描述",
      "product",
    );
    expect(audit.realness).toBe(15);
  });
});

describe("selectDiverse 相似与限额分支", () => {
  const cand = (
    name: string,
    scores: [number, number, number],
    extra: Record<string, unknown> = {},
  ) =>
    ({
      name,
      lang: "en",
      kind: "real-word",
      sourceType: "object",
      audit: {
        concreteness: scores[0],
        productFit: scores[1],
        realness: scores[2],
        issues: [],
        evidence: [],
        passed: true,
        slopScore: 0,
      } satisfies CandidateAudit,
      ...extra,
    }) as never;

  it("空名字与长名字比较走 levenshtein 两端兜底", () => {
    const first = selectDiverse(
      [cand("", [100, 100, 100]), cand("abcdef", [1, 1, 1])],
      2,
    );
    expect(first.map((item: { name: string }) => item.name)).toContain("");

    const second = selectDiverse(
      [cand("abcdef", [100, 100, 100]), cand("", [1, 1, 1])],
      2,
    );
    expect(second.map((item: { name: string }) => item.name)).toContain(
      "abcdef",
    );
  });

  it("后三字母相同的英文名视为相似，只留一个", () => {
    const selected = selectDiverse(
      [cand("blender", [100, 100, 100]), cand("render", [1, 1, 1])],
      2,
    );
    expect(selected.map((item: { name: string }) => item.name)).toEqual([
      "blender",
    ]);
  });

  it("同来源类型超配额的候选第一轮被拦、第二轮补上", () => {
    const selected = selectDiverse(
      [
        cand("quartz", [90, 90, 90], { kind: "real-word" }),
        cand("mellow", [80, 80, 80], { kind: "coined" }),
        cand("brothy", [70, 70, 70], { kind: "real-word" }),
      ],
      5,
    );
    expect(selected.map((item: { name: string }) => item.name).sort()).toEqual(
      ["brothy", "mellow", "quartz"],
    );
  });

  it("仓库名取向下 kebab 名凑不齐半数时也不硬塞相似名", () => {
    const selected = selectDiverse(
      [
        cand("probe-relay", [100, 100, 100], { kind: "compound" }),
        cand("probe-relays", [1, 1, 1], { kind: "compound" }),
      ],
      4,
      "repo",
    );
    expect(selected.map((item: { name: string }) => item.name)).toEqual([
      "probe-relay",
    ]);
  });
});
