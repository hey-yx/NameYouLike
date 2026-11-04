"""命名特征提取：音节长度、用字（分位置）、拼音音节/首字母、二字组合、域名拼音风格。"""
from __future__ import annotations

import re
from typing import Optional

from pypinyin import lazy_pinyin

from .clean import cjk_chars, is_cjk

_SECOND_LEVEL_TLD_PARENTS = ("com", "net", "org", "gov", "edu", "ac")
_COUNTRY_TLDS = ("cn", "hk", "tw", "jp", "uk")
_SCHEME_RE = re.compile(r"^[a-zA-Z]+://")


def domain_root(domain: str) -> Optional[str]:
    """从官网地址提取可对比的域名根（小写、去协议/www/公共后缀）。

    规则：去公共后缀后，若剩余多个标签则取最左侧（品牌承载标签）。
    www.moutaichina.com -> moutaichina；weixin.qq.com -> weixin；
    163.com -> 163；sina.com.cn -> sina；ele.me -> ele。
    """
    if not domain:
        return None
    s = _SCHEME_RE.sub("", domain.strip().lower())
    s = s.split("/", 1)[0].split(":", 1)[0]
    if s.startswith("www."):
        s = s[4:]
    if not s or "." not in s:
        return None
    labels = s.split(".")
    if len(labels) >= 3 and labels[-2] in _SECOND_LEVEL_TLD_PARENTS and labels[-1] in _COUNTRY_TLDS:
        labels = labels[:-2]      # sina.com.cn -> [sina]
    else:
        labels = labels[:-1]      # 163.com -> [163]; weixin.qq.com -> [weixin, qq]
    if not labels or not labels[0]:
        return None
    return labels[0]


def name_features(name: str) -> dict:
    """提取单个品牌名的基础特征。"""
    cjk = cjk_chars(name)
    n = len(cjk)
    chars = [ch for ch in cjk]
    syllables = [lazy_pinyin(ch)[0] for ch in chars]
    initials = "".join(s[0] for s in syllables)
    grams2 = [cjk[i: i + 2] for i in range(n - 1)]
    return {
        "length": n,                      # 音节长度（汉字数即音节数）
        "chars": chars,
        "positions": {ch: i for i, ch in enumerate(chars)},
        "syllables": syllables,
        "initials": initials,             # 简拼（首字母串），如 赤兔 -> ct
        "first_initial": initials[0] if initials else "",
        "first_syllable": syllables[0] if syllables else "",
        "last_syllable": syllables[-1] if syllables else "",
        "grams2": grams2,
        "has_latin": bool(re.search(r"[A-Za-z]", name)) or bool(re.search(r"[0-9]", name)),
    }


def classify_pinyin_style(name: str, domain: str) -> dict:
    """判定 品牌名 <-> 官网域名 的拼音风格映射。

    类别:
      full            域名根 == 全拼串（taobao <- 淘宝）
      abbr            域名根 == 首字母简拼（jd <- 京东）
      partial         域名根是全拼的子串/前缀（mi <- 小米 xiaomi）
      hybrid          域名根 = 首字母 + 尾音节（xpeng <- 小鹏 xiaopeng）
      abbr_compound   域名根以简拼开头 + 英文词（jtexpress <- 极兔）
      numeric         域名根为数字（163 <- 网易）
      creative        其余（创造性拼写/英文意译，ctrip <- 携程）
    附带 has_hyphen 标记（chi-tu 式破折号域名）。
    """
    root = domain_root(domain)
    out = {"domain": domain, "root": root, "style": None, "has_hyphen": bool(root and "-" in domain.lower())}
    if not root:
        return out
    feats = name_features(name)
    if feats["length"] < 2:
        out["style"] = "creative"
        return out
    py = "".join(feats["syllables"])
    abbr = feats["initials"]
    root_nh = root.replace("-", "").replace("_", "")
    if root_nh.isdigit():
        out["style"] = "numeric"
        return out
    if root_nh == py:
        out["style"] = "full"
        return out
    if root_nh == abbr:
        out["style"] = "abbr"
        return out
    if len(root_nh) >= 2 and (root_nh in py or py.startswith(root_nh) or root_nh.startswith(py)):
        out["style"] = "partial"
        return out
    if (
        len(root_nh) >= 3
        and root_nh[0] == py[0]
        and py.endswith(root_nh[1:])
    ):
        out["style"] = "hybrid"            # 首字母 + 尾音节：xpeng <- 小鹏
        return out
    if abbr and len(abbr) >= 2 and root_nh.startswith(abbr):
        out["style"] = "abbr_compound"     # 简拼 + 英文词：jtexpress <- 极兔
        return out
    # 数字开头的混合（3songshu <- 三只松鼠）
    stripped = re.sub(r"^[0-9]+", "", root_nh)
    if stripped and stripped in py:
        out["style"] = "partial"
        out["numeric_prefix"] = True
        return out
    out["style"] = "creative"
    return out
