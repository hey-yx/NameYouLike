import fs from "node:fs";
import path from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { getPromptEntries } from "@/lib/prompts-content";
import { PromptsPage } from "@/web/page";

const promptTxt = fs.readFileSync(path.join(process.cwd(), "prompt.txt"), "utf8");

describe("站点命名提示词", () => {
  it("站点只展示一份可复制全文，与 prompt.txt 逐字一致", () => {
    const entries = getPromptEntries();
    expect(entries).toHaveLength(1);
    expect(entries[0].title).toBe("起名提示词");
    expect(entries[0].prompt).toBe(promptTxt);
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
});
