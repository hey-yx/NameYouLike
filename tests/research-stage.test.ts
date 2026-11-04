import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();

describe("当前阶段不在项目内直调模型", () => {
  it("移除客户端与模型专用生成入口", () => {
    for (const file of [
      "lib/llm.ts",
      "lib/naming/generate.ts",
      "lib/naming/brief.ts",
      "lib/naming/prompts",
      "lib/domains",
      "lib/scoring.ts",
    ]) {
      expect(fs.existsSync(path.join(root, file)), file).toBe(false);
    }
  });

  it("已下线的服务层不再回到仓库", () => {
    expect(fs.existsSync(path.join(root, "server")), "server/").toBe(false);
    const source = fs.readFileSync(path.join(root, "web/page.tsx"), "utf8");
    expect(source, "web/page.tsx").not.toMatch(/\/api\/generate|generateNames|handleGenerate/);
  });

  it("已下线的服务型 UI 不再回到仓库", () => {
    expect(fs.existsSync(path.join(root, "components")), "components/").toBe(false);
  });

  it("保留产品本体、采集、规则审计与已经分析的材料", () => {
    for (const file of [
      "prompt.txt",
      "scripts/domain-check-fast.py",
      "python/naming-pipeline/pipeline/run.py",
      "python/naming-pipeline/pipeline/lexicon.py",
      "lib/naming/audit.ts",
      "research/命名方法学习-案例.json",
      "research/命名方法学习-结果/agent-analysis-zh.json",
      "research/命名方法学习-结果/agent-analysis-en.json",
      "research/命名方法学习-结果/生成提示词.md",
    ]) {
      expect(fs.existsSync(path.join(root, file)), file).toBe(true);
    }
  });
});
