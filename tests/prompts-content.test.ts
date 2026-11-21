import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { auditCandidate } from "@/lib/naming/audit";
import { PROMPT_ENTRY } from "@/lib/prompts-content";
import type { NameCandidate, ProductBrief } from "@/lib/types";
import genEnMerged from "@/research/prompt-run/gen-en-merged-latest.json";
import { PromptsPage } from "@/web/page";

const promptTxt = fs.readFileSync(path.join(process.cwd(), "prompt.txt"), "utf8");

describe("站点命名提示词", () => {
  it("站点只展示一份可复制全文，与 prompt.txt 逐字一致", () => {
    expect(PROMPT_ENTRY.title).toBe("起名提示词");
    expect(PROMPT_ENTRY.prompt).toBe(promptTxt);
  });

  it("提示词只出英文名，并写明缺项先问、默认 8 个与补齐", () => {
    const prompt = promptTxt;
    expect(prompt).toContain("起英文名字");
    expect(prompt).toContain("本项目不做汉字名");
    expect(prompt).toContain("数量留空默认 8 个");
    expect(prompt).toContain("一次列出问题");
    expect(prompt).toContain("过审不足名额时，换来源或角度补新名");
  });

  it("输入段用一段完整描述，不再是分字段表格", () => {
    const prompt = promptTxt;
    expect(prompt).toContain("产品描述（一段话，写清产品是什么、关键动作和不做什么）：{{产品描述}}");
    expect(prompt).toContain("名字数量：{{数量}}");
    expect(prompt).not.toContain("给谁用");
    expect(prompt).not.toContain("替代的旧办法");
    expect(prompt).not.toContain("目标受众");
  });

  it("页面默认仅预览提示词，展开按钮关联全文且复制仍包含全文", () => {
    const html = renderToStaticMarkup(createElement(PromptsPage));
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain('aria-controls="generate-prompt"');
    expect(html).toContain('id="generate-prompt"');
    expect(html).toContain('class="pp-prompt pp-prompt-clamp"');
    expect(html).toContain('class="pp-fold-icon" aria-hidden="true"');
    expect(html).toContain('data-copy="');
    expect(html).not.toContain("<details");
    expect(html).not.toContain("pp-prompt-open");
    expect(html).toContain("过审不足名额时，换来源或角度补新名");
  });

  it("案例区展示实测输入与实测结果", () => {
    const html = renderToStaticMarkup(createElement(PromptsPage));
    expect(html).toContain("pp-case");
    expect(html).toContain("实测输入");
    expect(html).toContain("实测结果");
    // 域名只显示结论，核验方式（·rdap / ·whois）不进页面
    expect(html).not.toContain("·rdap");
    expect(html).not.toContain("·whois");
  });

  it("提示词允许非字典式英文名，并明确包含 try 与 ohmy 路线", () => {
    const prompt = promptTxt;
    expect(prompt).toContain("不等于只能选英语字典词");
    expect(prompt).toContain("亲切互动");
    expect(prompt).toContain("产品动作");
    expect(prompt).toContain("归属感");
    expect(prompt).toContain("招呼式");
    expect(prompt).toContain("ohmy-");
    expect(prompt).toContain("自然造词");
    expect(prompt).toContain("ohmy 占用很高");
    expect(prompt).toContain("每个名字给 2-3 个域名候选");
  });

  it("提示词明确名字与定位句分工、命令行测试与规格标签拦截", () => {
    const prompt = promptTxt;
    expect(prompt).toContain("名字与定位句分工");
    expect(prompt).toContain("命令行与首屏测试");
    expect(prompt).toContain("no-store");
    expect(prompt).toContain("direct-link");
    expect(prompt).toContain("json-envelope");
    expect(prompt).toContain("不硬拆连字符");
  });

  it("实测案例 8 个保留名全部通过审计且页面不透出核验方式后缀", () => {
    const input = PROMPT_ENTRY.inputText ?? "";
    expect(input).toContain("allparse");
    expect(PROMPT_ENTRY.caseRows).toHaveLength(8);

    const brief: ProductBrief = {
      category: "devtool",
      audience: "开发者",
      coreAction: "解析分享链接返回无水印视频或图集直链",
      differentiator: "只做解析不存储不转存任何内容，服务器零带宽，九平台统一输出 JSON 信封",
      productFacts: [
        "解析分享链接",
        "无水印视频或图集直链",
        "不存储不转存",
        "服务器零带宽",
        "统一输出同一种 JSON 信封",
        "纯 HTTP 为主通道",
      ],
      competitors: ["yt-dlp", "cobalt", "snapany", "allparse"],
      avoidWords: [],
    };

    for (const item of genEnMerged.response.names) {
      const cand: NameCandidate = {
        name: item.name,
        kind: item.packageName.includes("-")
          ? "compound"
          : item.source.includes("自然造词")
            ? "coined"
            : item.source.includes("复合词")
              ? "compound"
              : "real-word",
        lang: "en",
        strategy: item.packageName.includes("-") ? "prefix" : "compound",
        sourceType: item.source.includes("复合词") ? "compound" : "action",
        source: item.source,
        sourceDetail: `${item.source}；${item.associations.join("；")}`,
        productFact: item.productFact,
        meaning: item.source,
        rationale: item.rationale,
        pronunciation: item.pronunciation,
        slopWarnings: [],
      };
      const audit = auditCandidate(cand, brief, input, "product");
      expect(audit.passed, `${item.name}: ${[...audit.slopWarnings, ...audit.issues].join(";")}`).toBe(true);
    }

    const html = renderToStaticMarkup(createElement(PromptsPage));
    expect(html).not.toContain("·rdap");
    expect(html).not.toContain("·whois");
    expect(html).not.toContain("·doh-ns");
  });

  it("domain-check-fast --brand-only 离线精准检出中外品牌与拼音冲突", () => {
    const outFile = path.join(os.tmpdir(), `brand-check-${Date.now()}.json`);
    try {
      execFileSync(
        "python3",
        [
          "scripts/domain-check-fast.py",
          "--variants",
          "stripe,taobao,feishu,linkpeel,bareclip",
          "--brand-only",
          "--json",
          outFile,
        ],
        { cwd: process.cwd(), encoding: "utf8" },
      );
      const data = JSON.parse(fs.readFileSync(outFile, "utf8")) as {
        brandChecks: Array<{
          name: string;
          trademark: {
            status: string;
            localGlobalHit: string | null;
            localCnHit: string | null;
          };
        }>;
      };
      const byName = Object.fromEntries(data.brandChecks.map((item) => [item.name, item]));
      expect(byName.stripe.trademark.status).toBe("conflict");
      expect(byName.stripe.trademark.localGlobalHit).toBe("stripe");
      expect(byName.taobao.trademark.status).toBe("conflict");
      expect(byName.taobao.trademark.localCnHit).toContain("淘宝");
      expect(byName.feishu.trademark.status).toBe("conflict");
      expect(byName.feishu.trademark.localCnHit).toContain("飞书");
      expect(byName.linkpeel.trademark.status).toBe("clean");
      expect(byName.bareclip.trademark.status).toBe("clean");
    } finally {
      if (fs.existsSync(outFile)) fs.unlinkSync(outFile);
    }
  });
});
