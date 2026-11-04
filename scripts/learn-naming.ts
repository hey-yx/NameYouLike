import { z } from "zod";
import { readFileSync } from "node:fs";

export const caseSchema = z.object({
  id: z.string(),
  name: z.string(),
  group: z.string(),
  source_url: z.string().nullable(),
  source_type: z.string(),
  evidence: z.string(),
  origin_evidence: z.string().nullable(),
});
export type LearningCase = z.infer<typeof caseSchema>;

export const analysisSchema = z.object({
  observations: z.array(z.object({
    case_id: z.string(),
    name: z.string(),
    mechanism: z.string(),
    analysis: z.string(),
    evidence_quote: z.string(),
    origin_status: z.enum(["documented", "unknown"]),
  })),
  patterns: z.array(z.object({
    method: z.string(),
    case_ids: z.array(z.string()).min(2),
    instruction: z.string(),
    limit: z.string(),
  })),
  limitations: z.array(z.string()),
});
export type Analysis = z.infer<typeof analysisSchema>;

export function evidenceErrors(analysis: Analysis, cases: LearningCase[]): string[] {
  const index = new Map(cases.map((item) => [item.id, item]));
  const seen = new Set<string>();
  const errors: string[] = [];
  for (const observation of analysis.observations) {
    if (seen.has(observation.case_id)) errors.push(`重复案例 ${observation.case_id}`);
    seen.add(observation.case_id);
    const item = index.get(observation.case_id);
    if (!item) {
      errors.push(`未知案例 ${observation.case_id}`);
      continue;
    }
    if (observation.name !== item.name) errors.push(`名称不符 ${item.id}`);
    if (!observation.evidence_quote.trim() || !item.evidence.includes(observation.evidence_quote)) {
      errors.push(`引文不在原始证据 ${item.id}`);
    }
    if (observation.origin_status === "documented" && !item.origin_evidence) {
      errors.push(`词源没有一手证据 ${item.id}`);
    }
  }
  for (const item of cases) {
    if (!seen.has(item.id)) errors.push(`遗漏案例 ${item.id}`);
  }
  for (const pattern of analysis.patterns) {
    if (new Set(pattern.case_ids).size < 2) errors.push(`方法缺少两个不同案例 ${pattern.method}`);
    for (const id of pattern.case_ids) {
      if (!index.has(id)) errors.push(`未知案例 ${id}`);
    }
  }
  return errors;
}

/** 校验会话模型已经落盘的分析，不联网、不调模型、不覆写研究结果。 */
function main(): void {
  const source = process.argv[2] ?? "research/命名方法学习-案例.json";
  const analysisFiles = process.argv.slice(3);
  if (analysisFiles.length === 0) {
    analysisFiles.push(
      "research/命名方法学习-结果/agent-analysis-zh.json",
      "research/命名方法学习-结果/agent-analysis-en.json",
    );
  }
  const cases = z.object({ cases: z.array(caseSchema) })
    .parse(JSON.parse(readFileSync(source, "utf8"))).cases;
  const analyses = analysisFiles.map((file) =>
    analysisSchema.parse(JSON.parse(readFileSync(file, "utf8"))),
  );
  const combined: Analysis = {
    observations: analyses.flatMap((analysis) => analysis.observations),
    patterns: analyses.flatMap((analysis) => analysis.patterns),
    limitations: analyses.flatMap((analysis) => analysis.limitations),
  };
  const errors = evidenceErrors(combined, cases);
  if (errors.length) throw new Error(`证据校验未通过：${errors.join("；")}`);
  console.log(JSON.stringify({ cases: cases.length, observations: combined.observations.length, patterns: combined.patterns.length, errors: 0 }));
}

if (import.meta.main) {
  try {
    main();
  } catch (error: unknown) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
