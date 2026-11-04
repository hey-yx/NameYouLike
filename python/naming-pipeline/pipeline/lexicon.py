"""命名词库：把品牌域语料变成生成端能直接用的资产。

统计文件里的 char_scores / char_pair_scores 是原始频次，里面混着「股份/国际/
香烟」这类品类词和公司名残留，直接喂给生成端等于把噪声当规律。本模块做两件事：

1. 词根表（morpheme_bank / bigram_bank）：过滤掉品类尾、机构头、虚词后，
   留下可复用的构词语素，带首/尾位置倾向。
2. 意象分布（imagery_dist）：品牌名按自然/动物/器物等意象分类，给出真实
   市场偏好比例，供生成端分配取材方向。

输出进 naming_patterns.v1.json 的 lexicon / imagery_dist 两段，生成端消费入口。
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from .clean import cjk_chars

# ---------------------------------------------------------------- 过滤词表

# 进不了词根表的字：品类尾字（公司形态残留）、机构头、虚词与量词
MORPHEME_STOP_CHARS = set(
    # 行业/品类
    "科技电汽机车医药物食饮乳酒茶烟油煤钢铜铝土砂石水泥玻璃陶瓷纺布服鞋帽"
    "纸印刷包装皮革箱包家居家具灯珠钟表眼镜厨卫五金机械轴承阀门泵管线缆"
    # 机构与通名
    "中国华省市县区镇乡村局厂店行会学院所部总分公司集团控股股份厂坊社苑阁"
    # 虚词与量词
    "的了和与及在其之乎者也焉哉又再还就很太最更都也者所第老小大多少上下"
)

# 意象类别：按字归类的粗分类，一个名字可落多个类（统计按命中计数）
IMAGERY_CLASSES: dict[str, str] = {
    "自然": "山水云风雨雪天海江河湖溪峰岭林森石泉阳月星辰霜露雷霞波涛洲岸野原川谷泉潮沙田",
    "动物": "龙虎马鹿鹤雀鹰燕雁鸳鸯蝶蚕牛羊鸡犬鱼龟猿鹏麒麟凤凰蝉蛇蚂蚁驹骏鸿鹄鹭鸥鲸鲲",
    "植物": "花草树木兰竹菊梅松柏柳桃李荷莲杏梨枣茶桑麻稻麦禾苗藤芝莲蓉蓉荷蒲苇苔苓",
    "器物": "金银玉石铜铁珠宝钟鼎镜剑笔墨纸砚琴棋书画印扇帘灯壶杯盘碗瓶桶盒箱刀弓车舟帆桥门楼台亭阁窗",
    "方位": "东西南北中上下左右前后内外天地乾坤阴阳顶底侧畔",
    "数字": "一二三四五六七八九十百千万亿双两半单",
    "颜色": "红黄蓝白黑青紫绿赤朱墨银金彩黛素",
    "情感品质": "安泰康宁福寿喜乐和顺永远长兴隆昌盛茂盛德仁义礼智信诚真实善美佳新优良精雅淳",
    "人物": "王王子公伯翁师傅哥弟姐妹娃儿郎君仙佛神童叟翁婆",
}

# 判定优先级：数字/颜色最具体，先判；自然与器物其次
IMAGERY_ORDER = ("数字", "颜色", "方位", "动物", "植物", "器物", "自然", "情感品质", "人物")

_CHAR_TO_CLASS = {ch: cls for cls, chars in IMAGERY_CLASSES.items() for ch in chars}


def is_stop_char(ch: str) -> bool:
    return ch in MORPHEME_STOP_CHARS


def classify_imagery(name: str) -> list[str]:
    """返回名字命中的意象类别（可多类），无命中返回空列表。"""
    hits: list[str] = []
    for ch in cjk_chars(name):
        cls = _CHAR_TO_CLASS.get(ch)
        if cls and cls not in hits:
            hits.append(cls)
    return sorted(hits, key=lambda c: IMAGERY_ORDER.index(c))


# ---------------------------------------------------------------- 词根表

def _pos_ratio(first: int, last: int) -> float:
    total = first + last
    return round(first / total, 3) if total else 0.5


def build_lexicon(brand_names: Iterable[str], min_char: int = 3,
                  min_bigram: int = 2, top_char: int = 120,
                  top_bigram: int = 80) -> dict:
    """从品牌名列表抽词根表与意象分布。

    brand_names 应为品牌域语料（已过形态闸）的 name_clean。
    """
    names = [cjk_chars(n) for n in brand_names]
    names = [n for n in names if len(n) >= 2]

    char_count: Counter = Counter()
    char_first: Counter = Counter()
    char_last: Counter = Counter()
    bigram: Counter = Counter()
    imagery_hits: Counter = Counter()
    imagery_pairs: Counter = Counter()

    for n in names:
        for ch in n:
            char_count[ch] += 1
        char_first[n[0]] += 1
        char_last[n[-1]] += 1
        for i in range(len(n) - 1):
            bigram[n[i:i + 2]] += 1
        hits = classify_imagery(n)
        for cls in hits:
            imagery_hits[cls] += 1
        if len(hits) >= 2:
            imagery_pairs["+".join(hits[:2])] += 1

    total = len(names)
    morphemes = {}
    for ch, c in char_count.most_common():
        if len(morphemes) >= top_char:
            break
        if c < min_char or is_stop_char(ch):
            continue
        morphemes[ch] = {
            "count": c,
            "freq": round(c / total, 4),
            "head_ratio": _pos_ratio(char_first.get(ch, 0), char_last.get(ch, 0)),
        }

    bigrams = {}
    for g, c in bigram.most_common():
        if len(bigrams) >= top_bigram:
            break
        if c < min_bigram:
            continue
        if is_stop_char(g[0]) or is_stop_char(g[1]):
            continue
        bigrams[g] = {"count": c, "freq": round(c / total, 4)}

    imagery = {
        "sample_size": total,
        "by_class": {k: round(v / total, 4) for k, v in
                     sorted(imagery_hits.items(), key=lambda x: -x[1])},
        "by_class_count": dict(imagery_hits.most_common()),
        "top_pairs": dict(imagery_pairs.most_common(10)),
        "note": "一个名字可命中多个意象，by_class 各项之和不等于 1；按品牌名条数计",
    }
    return {
        "morpheme_bank": morphemes,
        "bigram_bank": bigrams,
        "imagery_dist": imagery,
        "lexicon_sample_size": total,
    }
