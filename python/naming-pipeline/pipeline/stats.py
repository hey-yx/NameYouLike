"""统计模型：从清洗后的语料聚合命名模式，产出推荐引擎可直接消费的权重文件。

统计口径:
  - 品牌域（进统计）= famous_brand + brand_tradename + 形态合格的 new_enterprise 简称。
    IPO 上市简称是公司名形态（南方乳业/力勤资源），直接进统计会把「科技/汽车/新材」
    这类行业词顶进高频字对；只保留剥不出行业尾、长度合规的简称。
  - 公司域（只进碰撞）= baseline + 其余 new_enterprise 简称 + 全量 name_clean。
  - 行业表启用阈值 = 200 条样本（8 条时电子商务 top 字是「巴、多」，纯噪声）。
  - 长度按汉字数（= 音节数）分桶 2/3/4/5+。
  - 用字统计带位置（首/中/尾）；二元组带提升度(lift)。
  - 行业关联 = 行业条件下用字 lift（行业样本 >= 8 才参与，避免碎样本）。
  - 拼音风格 = 知名品牌中文名 <-> 官网域名 的映射分类分布。
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable

from .clean import cjk_chars
from .features import classify_pinyin_style, name_features
from .lexicon import build_lexicon

# IPO 简称要进品牌域统计必须先剥成这种形态：2-4 字、剥不出行业尾巴。
# 简称里的行业词（乳业/资源/光电/半导体）是公司分类标签，不是品牌构词成分。
_IPO_SHORTNAME_TAILS = [
    "半导体", "新能源", "新材料", "数控技术", "激光", "智能装备", "智能制造",
    "光电", "生物", "医药", "药业", "乳业", "酒业", "食品", "饮料", "资源",
    "能源", "环保", "电子", "电气", "网络", "软件", "通信", "材料", "装备",
    "重工", "轻工", "数控", "精密", "机械", "汽车", "航空", "钢铁", "矿业",
    "化工", "纺织", "服装", "物流", "港口", "银行", "证券", "保险", "地产",
    "科技", "技术", "新材", "数码", "信息", "数据", "传媒", "文化", "旅游",
    "农业", "牧业", "渔业", "制药", "医疗", "健康", "教育", "体育", "传媒",
]

# 4 字简称追不完枚举（智能/高科/复材/应材/硬科/新能/微电子...），改用「构词后缀字」兜底：
# 这些字出现在 4 字简称末位时，该名大概率是「字号 + 行业字」的公司形态而非品牌。
_COMPANY_SUFFIX_CHARS = frozenset(
    "科技技智能能材科新微光子电机驱传动力重工控合晶威特仪环保储络迅联通讯达汽液"
    "纤缆药医食饮乳酒水电气油煤金钢铜铝塑橡陶玻瓷纺布服饰装鞋帽纸印刷新媒游戏"
)

# 头部机构词：以这些字开头的简称（中国铀业/中科仪/浙江华业）是机构名，不是品牌
_ORG_HEADS = ("中国", "中科", "国家", "电科", "国机", "国药", "中航", "中船", "中车",
              "中核", "中兵", "浙江", "江苏", "广东", "山东", "上海", "深圳", "北京",
              "苏州", "无锡", "杭州", "南京", "四川", "湖南", "湖北", "安徽", "福建",
              "交大", "清华", "北大", "复旦")

def is_brandlike_shortname(name: str) -> bool:
    """IPO 简称是否够「品牌形态」：2-4 字、不带行业尾词、末字不是行业构词字、非机构头。"""
    from .clean import cjk_chars
    s = cjk_chars(name)
    if not 2 <= len(s) <= 4:
        return False
    if any(s.endswith(t) and len(s) > len(t) for t in _IPO_SHORTNAME_TAILS):
        return False
    if len(s) == 4 and s[-1] in _COMPANY_SUFFIX_CHARS:
        return False
    if s.startswith(_ORG_HEADS):
        return False
    return True


def stats_domain(rec: dict) -> str:
    """记录归入哪个统计域：brand（进统计）/ company（只进碰撞）。

    famous_brand 也不是全收：维基抓回的「吉利汽车」「全志科技」是品牌+品类
    整体名，把它当构词样本会把「汽车/科技」顶进高频字对。整体名进公司域
    （仍参与碰撞），name_clean 去品类尾后仍 >= 2 字的才留品牌域。
    """
    kind = rec.get("kind")
    if kind == "brand_tradename":
        return "brand"
    if kind in ("famous_brand", "new_enterprise", "product_app"):
        return "brand" if is_brandlike_shortname(rec.get("name_clean", "")) else "company"
    return "company"
STYLE_ORDER = ("full", "abbr", "partial", "hybrid", "abbr_compound", "numeric", "creative")


def _bucket(length: int) -> str:
    return str(length) if length <= 4 else "5+"


def _proportions(counter: dict) -> dict:
    total = sum(counter.values())
    if not total:
        return {}
    return {k: round(v / total, 4) for k, v in sorted(counter.items(), key=lambda x: -x[1])}


def _weight_from_count(count: int, max_count: int) -> float:
    """次数 -> [0,1] 平滑权重（平方根压缩，兼顾长尾可见性）。"""
    if max_count <= 0:
        return 0.0
    return round(min(1.0, math.sqrt(count / max_count)), 4)


def build_patterns(all_records: Iterable[dict], run_meta: dict) -> dict:
    all_records = list(all_records)
    stats_recs = [r for r in all_records
                  if r.get("name_clean") and stats_domain(r) == "brand"]
    baseline_recs = [r for r in all_records
                     if r.get("name_clean") and stats_domain(r) == "company"]

    # ---- 语料概况
    corpus = {
        "total_records": len(all_records),
        "stats_records": len(stats_recs),
        "baseline_records": len(baseline_recs),
        "by_kind": _proportions(dict(Counter(r.get("kind") for r in all_records))),
        "by_source_counts": dict(sorted(Counter(r.get("source") for r in stats_recs).items(),
                                        key=lambda x: -x[1])),
        "with_domain": sum(1 for r in stats_recs if r.get("domain")),
        "with_industry": sum(1 for r in stats_recs if r.get("industry")),
        "by_stats_domain": _proportions(dict(
            Counter(stats_domain(r) for r in all_records if r.get("name_clean")))),
        "brand_domain_by_source": dict(sorted(
            Counter(r.get("source") for r in stats_recs).items(), key=lambda x: -x[1])),
    }

    # ---- 长度分布（近期统计语料 vs 存量基线，可观察命名风格漂移）
    len_counter = Counter()
    for r in stats_recs:
        len_counter[_bucket(len(cjk_chars(r["name_clean"])))] += 1
    length_dist = _proportions(dict(len_counter))
    base_len = Counter()
    for r in baseline_recs:
        base_len[_bucket(len(cjk_chars(r["name_clean"])))] += 1

    # ---- 用字统计（带位置）
    char_count: Counter = Counter()
    char_first: Counter = Counter()
    char_last: Counter = Counter()
    char_industry: defaultdict = defaultdict(Counter)
    grams2: Counter = Counter()
    industry_recs: Counter = Counter()
    industry_len: defaultdict = defaultdict(Counter)

    for r in stats_recs:
        chars = cjk_chars(r["name_clean"])
        if not chars:
            continue
        feats = name_features(r["name_clean"])
        for ch in feats["chars"]:
            char_count[ch] += 1
            char_industry[r.get("industry")][ch] += 1
        char_first[feats["chars"][0]] += 1
        char_last[feats["chars"][-1]] += 1
        for g in feats["grams2"]:
            grams2[g] += 1
        ind = r.get("industry")
        if ind:
            industry_recs[ind] += 1
            industry_len[ind][_bucket(feats["length"])] += 1
    total_chars = sum(char_count.values()) or 1
    char_freq = {ch: c / total_chars for ch, c in char_count.items()}
    max_char = max(char_count.values(), default=0)

    char_scores = {}
    for ch, c in char_count.most_common(400):
        char_scores[ch] = {
            "count": c,
            "freq": round(char_freq[ch], 5),
            "weight": _weight_from_count(c, max_char),
            "pos_first": char_first.get(ch, 0),
            "pos_last": char_last.get(ch, 0),
        }

    # ---- 二字组合（带 lift）
    gram_scores = {}
    top_grams = [g for g, c in grams2.most_common(300) if c >= 3]
    for g in top_grams:
        expected = char_freq.get(g[0], 1e-9) * char_freq.get(g[1], 1e-9)
        lift = (grams2[g] / total_chars) / expected if expected > 0 else 1.0
        gram_scores[g] = {"count": grams2[g], "lift": round(lift, 2)}
    max_gram = grams2[top_grams[0]] if top_grams else 0
    for g in gram_scores:
        gram_scores[g]["weight"] = _weight_from_count(gram_scores[g]["count"], max_gram)

    # ---- 行业关联（条件用字 lift + 行业长度分布）
    industry_affinity = {}
    industry_length = {}
    INDUSTRY_MIN_SAMPLES = 200
    eligible = [i for i, n in industry_recs.items() if n >= INDUSTRY_MIN_SAMPLES]
    for ind in eligible:
        n_ind = industry_recs[ind]
        ind_total = sum(char_industry[ind].values()) or 1
        lifts = {}
        for ch, c in char_industry[ind].items():
            if c < 2:
                continue
            p_ind = c / ind_total
            p_all = char_freq.get(ch, 0)
            lift = p_ind / p_all
            if lift >= 1.3:
                lifts[ch] = round(min(lift, 6.0), 2)
        industry_affinity[ind] = dict(sorted(lifts.items(), key=lambda x: -x[1])[:15])
        industry_length[ind] = _proportions(dict(industry_len[ind]))
    industry_sample_sizes = {i: industry_recs[i] for i in eligible}

    # ---- 拼音特征
    initial_counter: Counter = Counter()
    syllable_counter: Counter = Counter()
    for r in stats_recs:
        feats = name_features(r["name_clean"])
        if feats["length"] < 2:
            continue
        initial_counter[feats["first_initial"]] += 1
        for s in feats["syllables"]:
            syllable_counter[s] += 1
    initial_dist = _proportions(dict(initial_counter))
    syllable_top = {s: round(c / (sum(syllable_counter.values()) or 1), 5)
                    for s, c in syllable_counter.most_common(150)}

    # ---- 拼音风格（品牌名 <-> 域名）
    style_counter: Counter = Counter()
    style_examples: defaultdict = defaultdict(list)
    hyphen_count = 0
    domain_total = 0
    for r in stats_recs:
        if not r.get("domain"):
            continue
        res = classify_pinyin_style(r["name_clean"], r["domain"])
        if not res.get("style"):
            continue
        domain_total += 1
        style_counter[res["style"]] += 1
        if res["has_hyphen"]:
            hyphen_count += 1
        if len(style_examples[res["style"]]) < 10:
            style_examples[res["style"]].append(
                {"name": r["name_clean"], "domain": r["domain"], "root": res["root"]})
    style_dist = _proportions({k: style_counter.get(k, 0) for k in STYLE_ORDER if style_counter.get(k)})

    # ---- 碰撞索引（全部记录：新企业 + 知名品牌 + 存量基线）
    exact_names = sorted({r["name_clean"] for r in all_records if r.get("name_clean")})
    from .dedup import phonetic_key  # 局部导入避免循环依赖
    phonetic_keys = {}
    for r in all_records:
        key = phonetic_key(r["name_clean"]) if r.get("name_clean") else None
        if key and key not in phonetic_keys:
            phonetic_keys[key] = r["name_clean"]

    # ---- 推荐引擎权重块（全部归一化，可直接并入打分）
    recommendation_weights = {
        "w_char": {ch: v["weight"] for ch, v in char_scores.items()},
        "w_char_pair": {g: v["weight"] for g, v in gram_scores.items()},
        "w_length": length_dist,
        "w_industry_char": industry_affinity,
        "w_initial": initial_dist,
        "w_syllable": syllable_top,
        "w_pinyin_style": style_dist,
        "industry_sample_sizes": industry_sample_sizes,
        "scoring": {
            "formula": (
                "score = 0.30*char_term + 0.15*pair_term + 0.15*length_term "
                "+ 0.25*industry_term + 0.15*pinyin_term; "
                "industry_term 缺省时按剩余权重归一化"
            ),
            "char_term": "mean(w_char[c]) over 名称用字",
            "pair_term": "mean(w_char_pair[2-gram])",
            "length_term": "w_length[字数桶]",
            "industry_term": "mean(min(lift,6)/6) of w_industry_char[industry][char]",
            "pinyin_term": "0.5*w_initial[首字母] + 0.5*mean(w_syllable[音节])",
            "collision_penalty": {"exact": 1.0, "phonetic": 0.6},
            "notes": "所有 w_* 来自真实语料统计；exact/phonetic 碰撞用 collision_index 检测",
        },
    }

    # ---- 生成端词库：词根表 + 意象分布（只对品牌域语料，且过滤品类/机构残留）
    lexicon = build_lexicon([r["name_clean"] for r in stats_recs])

    return {
        "schema": "naming-patterns/v1",
        "version": run_meta.get("version"),
        "generated_at": run_meta.get("generated_at"),
        "run_id": run_meta.get("run_id"),
        "corpus": corpus,
        "length_dist": length_dist,
        "baseline_length_dist": _proportions(dict(base_len)),
        "char_scores": char_scores,
        "char_pair_scores": gram_scores,
        "industry_char_affinity": industry_affinity,
        "industry_length_dist": industry_length,
        "industry_sample_sizes": industry_sample_sizes,
        "pinyin_initial_dist": initial_dist,
        "pinyin_syllable_dist": syllable_top,
        "pinyin_style_dist": style_dist,
        "pinyin_style_examples": {k: v for k, v in style_examples.items()},
        "domain_style_sample_size": domain_total,
        "hyphen_domain_rate": round(hyphen_count / domain_total, 4) if domain_total else 0.0,
        "collision_index": {
            "exact_names": exact_names,
            "phonetic_keys": phonetic_keys,
            "note": "推荐引擎生成候选后应先查碰撞：exact -> 剔除; phonetic -> 强降权或剔除",
        },
        "recommendation_weights": recommendation_weights,
        "lexicon": lexicon,
        "provenance": run_meta.get("provenance", {}),
        "quality": run_meta.get("quality", {}),
    }
