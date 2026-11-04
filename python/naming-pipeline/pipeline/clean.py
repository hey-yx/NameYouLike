"""企业名清洗：全称 → 字号（品牌核心名）。

全称结构约定：[行政区划] + 字号 + [行业描述] + [组织形式]。
清洗顺序：去括号 → 去组织形式后缀 → 去行政区划前缀（优先用注册地址提示）→ 迭代去行业尾巴。
简称清洗（上市简称）：去 N/C/ST/*ST/退 前缀与 A/B 尾标，不剥离行业词（简称本身即品牌形态）。
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
PAREN_RE = re.compile(r"[（(][^（）()]*[)）]")

# 组织形式后缀（长者优先）
ORG_SUFFIXES = [
    "股份有限公司", "有限责任公司", "有限公司", "合伙企业",
    "集团公司", "集团", "公司", "企业",
]

# 行政区划前缀：国家层级 + 省份 + 常见大中城市（非穷举；配合 REG_ADDRESS 提示使用）
REGION_PREFIXES = [
    "中国", "中华", "国家", "全国",
    "北京", "上海", "天津", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建", "江西",
    "山东", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西",
    "甘肃", "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆",
    "深圳", "广州", "杭州", "南京", "成都", "武汉", "西安", "苏州", "合肥", "长沙",
    "厦门", "青岛", "大连", "宁波", "无锡", "佛山", "东莞", "珠海", "中山", "惠州",
    "常州", "嘉兴", "绍兴", "金华", "温州", "泉州", "福州", "济南", "烟台", "沈阳",
    "哈尔滨", "长春", "石家庄", "太原", "郑州", "南昌", "贵阳", "昆明", "南宁", "海口",
    "兰州", "西宁", "银川", "乌鲁木齐", "拉萨", "呼和浩特",
]
REGION_PREFIXES.sort(key=len, reverse=True)

# 行业/经营特征尾巴（长者优先；仅在剥离后剩余 >= 2 个汉字时剥离）
INDUSTRY_TAILS = [
    # 组合词
    "新能源科技", "新材料科技", "网络科技", "信息科技", "信息技术", "电子科技", "智能科技",
    "生物科技", "生物医药", "智能制造", "智能装备", "装备制造", "精密制造", "电子商务",
    "数据科技", "数字科技", "科技发展", "实业发展", "高新材料", "文化传播", "文化传媒",
    "影视文化", "汽车科技", "汽车电子", "汽车零部件", "食品饮料", "光电科技", "光学科技",
    "通信科技", "通信技术", "软件科技", "环保科技", "教育科技", "医疗科技", "医疗器械",
    "健康科技", "材料科技", "能源科技", "精密仪器", "精密机械", "家居用品", "餐饮管理",
    "企业管理", "管理咨询", "汽车服务", "供应链管理", "置业有限公司",
    # 单词
    "科技", "实业", "贸易", "商贸", "传媒", "文化", "广告", "教育", "物流", "投资",
    "控股", "环保", "医药", "制药", "药业", "白酒", "酒业", "食品", "饮料", "乳业",
    "纺织", "服装", "服饰", "家纺", "家具", "家居", "珠宝", "光电", "光学", "显示",
    "半导体", "芯片", "电子", "电气", "仪表", "仪器", "机械", "装备", "化工", "材料",
    "能源", "新能源", "新材料", "通信", "网络", "软件", "数据", "汽车", "航空", "航海",
    "医疗", "健康", "农业", "渔业", "牧业", "矿业", "钢铁", "冶金", "建筑", "地产",
    "置业", "物业", "酒店", "旅游", "休闲", "娱乐", "游戏", "动漫", "影视", "出版",
    "印刷", "包装", "皮革", "造纸", "玻璃", "陶瓷", "酿酒", "茶业", "水产", "环保工程", "酒",
]
INDUSTRY_TAILS = sorted(set(INDUSTRY_TAILS), key=len, reverse=True)

# 上市简称的市场标记
MARKET_PREFIX_RE = re.compile(r"^([NnCcXdD]+|\*?ST|退市|退)")
MARKET_SUFFIX_RE = re.compile(r"[ABHＡＢ]+$")
# 简称中的组织形式尾词（品牌形态提取：蚂蚁集团->蚂蚁，安达股份->安达）
BRAND_FORM_SUFFIXES = ["股份", "集团"]


def is_cjk(ch: str) -> bool:
    return bool(CJK_RE.match(ch))


def cjk_chars(s: str) -> str:
    return "".join(ch for ch in s if is_cjk(ch))


def has_enough_cjk(s: str, minimum: int = 2) -> bool:
    return len(cjk_chars(s)) >= minimum


def clean_short_name(name: str) -> Tuple[Optional[str], dict]:
    """清洗上市简称：去市场标记/空白/尾标。返回 (清洗后名称或 None, 元信息)。"""
    meta: dict = {"raw": name, "ops": []}
    if not name:
        return None, meta
    s = name.strip()
    if MARKET_PREFIX_RE.match(s):
        # N通则 -> 通则；*ST慧辰 -> 慧辰；退市海润 -> 海润
        new = MARKET_PREFIX_RE.sub("", s)
        if has_enough_cjk(new, 2):
            s = new
            meta["ops"].append("strip_market_prefix")
    if MARKET_SUFFIX_RE.search(s):
        new = MARKET_SUFFIX_RE.sub("", s)
        if has_enough_cjk(new, 2):
            s = new
            meta["ops"].append("strip_share_class")
    for brand_suf in BRAND_FORM_SUFFIXES:
        if s.endswith(brand_suf) and has_enough_cjk(s[: -len(brand_suf)], 2):
            s = s[: -len(brand_suf)]
            meta["ops"].append("strip_org_form:" + brand_suf)
    s = s.replace(" ", "").replace("*", "").replace("\u3000", "")
    if not has_enough_cjk(s, 2):
        return None, meta
    meta["ops"].append("normalize")
    return s, meta


def _parse_region_hints(reg_address: Optional[str]) -> list:
    """从注册地址提取行政区划提示，如 '贵州省仁怀市茅台镇' -> [贵州, 仁怀]。"""
    if not reg_address:
        return []
    hints = []
    m = re.match(r"^(..?)(省|自治区)", reg_address)
    if m:
        hints.append(m.group(1))
        m2 = re.match(r"^(..?)(省|自治区)(..?)(市|地区|盟|州)", reg_address)
        if m2:
            hints.append(m2.group(3))
    else:
        m = re.match(r"^(..?)(市)", reg_address)
        if m:
            hints.append(m.group(1))
    return hints


def clean_full_name(full_name: str, reg_address: Optional[str] = None) -> Tuple[Optional[str], dict]:
    """清洗公司全称 -> 字号。返回 (字号或 None, 元信息)。"""
    meta: dict = {"raw": full_name, "ops": [], "region": None}
    if not full_name:
        return None, meta
    s = PAREN_RE.sub("", full_name.strip())
    if s != full_name.strip():
        meta["ops"].append("strip_parenthetical")
    # 1) 组织形式后缀
    for suf in ORG_SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)]
            meta["ops"].append("strip_org:" + suf)
            break
    # 2) 行政区划前缀：先用注册地址提示（能覆盖长尾城市，如 芜湖），再回退固定列表
    hints = _parse_region_hints(reg_address) + REGION_PREFIXES
    for reg in hints:
        if reg and s.startswith(reg) and len(cjk_chars(s)) - len(reg) >= 2:
            s = s[len(reg):]
            meta["region"] = reg
            meta["ops"].append("strip_region:" + reg)
            break
    # 3) 迭代剥离行业尾巴
    while True:
        for tail in INDUSTRY_TAILS:
            if s.endswith(tail) and len(cjk_chars(s)) - len(tail) >= 2:
                s = s[: -len(tail)]
                meta["ops"].append("strip_tail:" + tail)
                break
        else:
            break
    s = s.replace(" ", "")
    if not has_enough_cjk(s, 2):
        return None, meta
    return s, meta
