import { describe, expect, it } from "vitest";
import { evidenceErrors, type Analysis, type LearningCase } from "@/scripts/learn-naming";

const cases: LearningCase[] = [{
  id: "c1", name: "NameYouLike", group: "user", source_url: null,
  source_type: "user-message", evidence: "用户喜欢自然短语与驼峰写法。", origin_evidence: null,
}];
const valid: Analysis = {
  observations: [{ case_id: "c1", name: "NameYouLike", mechanism: "自然短语",
    analysis: "表面可拆为 Name You Like，具体命名由来未知。",
    evidence_quote: "用户喜欢自然短语", origin_status: "unknown" }],
  patterns: [], limitations: ["只有用户偏好，不证明市场效果。"],
};

describe("模型命名分析的证据校验", () => {
  it("拒绝模型捏造的案例、引文和已证实词源", () => {
    const invented: Analysis = { ...valid, observations: [
      valid.observations[0],
      { ...valid.observations[0], case_id: "missing" },
      { ...valid.observations[0], name: "invented", evidence_quote: "名字保证成功", origin_status: "documented" },
    ], patterns: [{ method: "形态", case_ids: ["c1", "missing"], instruction: "参考", limit: "未核验" }] };
    expect(evidenceErrors(invented, cases).join(" ")).toMatch(/未知案例/);
    expect(evidenceErrors(invented, cases).join(" ")).toMatch(/名称不符/);
    expect(evidenceErrors(invented, cases).join(" ")).toMatch(/引文不在/);
    expect(evidenceErrors(invented, cases).join(" ")).toMatch(/词源没有/);
    expect(evidenceErrors(invented, cases).join(" ")).toMatch(/重复案例/);
  });
  it("接受原始证据内的引文，同时保留词源未知", () => {
    expect(evidenceErrors(valid, cases)).toEqual([]);
  });
});
