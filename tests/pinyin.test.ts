import { describe, expect, it } from "vitest";
import {
  latinTokens,
  pinyinInitialsMatches,
  pinyinMatches,
  pinyinTokensIn,
} from "@/lib/naming/pinyin";

describe("拼音读音核验", () => {
  it("多音字、ü 的不同输入写法都能对上", () => {
    expect(pinyinMatches("guizang", "归藏")).toBe(true);
    expect(pinyinMatches("duizhang", "对账")).toBe(true);
    for (const latin of ["lvxing", "lüxing", "luxing"]) {
      expect(pinyinMatches(latin, "旅行"), latin).toBe(true);
    }
  });

  it("读不回、拼不完、空输入都判否", () => {
    expect(pinyinMatches("guizang", "对账")).toBe(false);
    expect(pinyinMatches("zafuno", "归藏")).toBe(false);
    expect(pinyinMatches("gui", "归藏")).toBe(false);
    expect(pinyinMatches("", "旅行")).toBe(false);
    expect(pinyinMatches("lvxing", "")).toBe(false);
    expect(pinyinMatches("lvxing", "㐀行")).toBe(false);
    expect(pinyinMatches("nv", "女")).toBe(true);
    expect(pinyinMatches("nvx", "女")).toBe(false);
    expect(pinyinMatches("n", "女")).toBe(false);
  });

  it("拆词元去重，短词元不算拼音", () => {
    expect(latinTokens("Guizang_Design-Skill")).toEqual([
      "guizang",
      "design",
      "skill",
    ]);
    expect([...pinyinTokensIn("guizang-design-skill", "归藏古书")]).toEqual([
      "guizang",
    ]);
    expect([...pinyinTokensIn("guizang", "")]).toEqual([]);
    expect([...pinyinTokensIn("x-guizang", "归藏")]).toEqual(["guizang"]);
  });

  it("支持专名与编号前缀的 3-6 位简拼核验", () => {
    expect(pinyinInitialsMatches("ccrds", "传承人大赛")).toBe(true);
    expect(pinyinInitialsMatches("sd", "山东")).toBe(true);
    expect(pinyinInitialsMatches("ccrds", "传统文化")).toBe(false);
    expect([
      ...pinyinTokensIn(
        "ccrds-cert",
        "山东省优秀传统文化少年传承人大赛证书查询",
      ),
    ]).toEqual(["ccrds"]);
  });
});
