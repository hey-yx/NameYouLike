"""数据源：全部可插拔，单源失败不阻塞管道（失败记录进运行日志）。

源清单:
  EastmoneyIpoApplySource  东方财富数据中心 IPO 申报/申购列表 —— 新近公开的中国企业名（带日期/板块/证监会行业）
  enrich_with_f10          东方财富 F10 资料页 —— 公司全称、注册地址（行政区划提示）、官网域名、东财行业
  CninfoStockListSource    巨潮资讯全市场股票列表 —— 存量企业名基线（碰撞索引）
  WikiCategorySource       维基百科「中国品牌」分类树 —— 知名品牌命名案例
  SeedCorpusSource         本地种子语料 —— 知名互联网品牌 + 官网域名（拼音风格分析的主要来源）
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

from . import http
from .clean import (ORG_SUFFIXES, clean_full_name, clean_short_name, cjk_chars,
                     is_cjk, PAREN_RE)
from .dedup import record_id


def _t2s(text: str) -> str:
    """繁体标题归一为简体（opencc 缺失时降级为原样返回）。"""
    try:
        from opencc import OpenCC
        global _CC
        try:
            cc = _CC
        except NameError:
            cc = _CC = OpenCC("t2s")
        return cc.convert(text)
    except Exception:  # noqa: BLE001
        return text


def clean_wiki_title(title: str) -> Optional[str]:
    """维基标题清洗：繁体归一 + 公司全称（含组织形式后缀）走全称分解链；品牌名原样保留。

    「泸州老窖股份有限公司」-> 泸州老窖；「青岛啤酒」-> 青岛啤酒（品牌形态不动）；
    繁体标题「青島啤酒股份有限公司」-> 青岛啤酒。
    """
    base = PAREN_RE.sub("", title).strip()
    base = _t2s(base)
    if len(cjk_chars(base)) < 2:
        return None
    if any(suf in base for suf in ORG_SUFFIXES):
        cleaned, meta = clean_full_name(base)
        # 区域剥离把字号剥到 2 字以下时，剥掉的多半是品牌地名
        # （「青島啤酒股份有限公司」→「啤酒」），回退到只剥组织后缀。
        if meta.get("region") and (cleaned is None or len(cjk_chars(cleaned)) < 3):
            for suf in ORG_SUFFIXES:
                if base.endswith(suf):
                    base = base[: -len(suf)]
                    break
            return base if len(cjk_chars(base)) >= 2 else None
        return cleaned
    return base

# ---------------------------------------------------------------- IPO 申报（新企业名）

_DC_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_DC_PARAMS_BASE = {
    "reportName": "RPTA_APP_IPOAPPLY",
    "columns": "SECURITY_CODE,SECUCODE,SECURITY_NAME,APPLY_DATE,LISTING_DATE,MARKET_TYPE_NEW,INDUSTRY_NAME",
    "sortColumns": "APPLY_DATE",
    "sortTypes": "-1",
    "source": "WEB",
    "client": "WEB",
}


class EastmoneyIpoApplySource:
    source = "eastmoney_ipo"
    kind = "new_enterprise"
    priority = 3

    def __init__(self, pages: int = 3, page_size: int = 200, min_date: str = "2024-01-01"):
        self.pages = pages
        self.page_size = page_size
        self.min_date = min_date

    def fetch(self, log) -> list[dict]:
        records: list[dict] = []
        rejected = 0
        for page in range(1, self.pages + 1):
            params = dict(_DC_PARAMS_BASE, pageSize=self.page_size, pageNumber=page)
            data = http.get_json(_DC_URL, params=params, interval=0.6)
            rows = (data.get("result") or {}).get("data") or []
            if not rows:
                break
            for row in rows:
                apply_date = (row.get("APPLY_DATE") or "")[:10]
                if apply_date and apply_date < self.min_date:
                    continue
                name, _meta = clean_short_name(row.get("SECURITY_NAME") or "")
                if not name:
                    rejected += 1
                    continue
                records.append({
                    "record_id": record_id(self.source, row.get("SECUCODE") or row.get("SECURITY_NAME", "")),
                    "source": self.source,
                    "source_priority": self.priority,
                    "kind": self.kind,
                    "name_raw": row.get("SECURITY_NAME"),
                    "name_clean": name,
                    "secucode": row.get("SECUCODE"),
                    "industry": row.get("INDUSTRY_NAME") or None,
                    "industry_raw": row.get("INDUSTRY_NAME") or None,
                    "apply_date": apply_date or None,
                    "listing_date": (row.get("LISTING_DATE") or "")[:10] or None,
                    "market": row.get("MARKET_TYPE_NEW"),
                })
            log(f"[{self.source}] page {page}: +{len(rows)} rows (cum {len(records)} records)")
        log(f"[{self.source}] accepted={len(records)} rejected={rejected}")
        return records


def enrich_with_f10(records: list[dict], max_count: int, log) -> dict:
    """对最近的 IPO 记录逐个补全 F10 资料：全称/区域/行业/官网域名。就地修改并返回统计。"""
    _F10_URL = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax"
    ok = fail = 0
    for rec in records[:max_count]:
        code = rec.get("secucode") or ""
        if "." not in code:
            continue
        try:
            sym, mkt = code.split(".", 1)
            data = http.get_json(_F10_URL, params={"code": mkt + sym}, interval=0.35, retries=2)
            jb = (data.get("jbzl") or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            fail += 1
            log(f"[f10] {code} failed: {exc}")
            continue
        full = jb.get("ORG_NAME")
        if full:
            rec["company_full_name"] = full
            trade, meta = clean_full_name(full, jb.get("REG_ADDRESS"))
            rec["trade_name"] = trade
            rec["region"] = meta.get("region")
            rec["clean_ops"] = meta.get("ops")
            # F10 字号是比上市简称更真的品牌名（皇冠新材->皇冠）。剥得干净且
            # 够品牌形态时把统计身份升级为 brand_tradename，简称降级为别名。
            from .stats import is_brandlike_shortname
            if trade and trade != rec.get("name_clean") and is_brandlike_shortname(trade):
                rec["kind"] = "brand_tradename"
                rec["short_name_alias"] = rec.get("name_clean")
                rec["name_clean"] = trade
        web = jb.get("ORG_WEB")
        if web and "." in web:
            rec["domain"] = web.strip()
        em = jb.get("EM2016")
        if em and "-" in em:
            parts = em.split("-")
            rec["industry"] = parts[0]          # 东财一级行业，如 食品饮料
            rec["industry_raw"] = em
        rec["f10"] = True
        ok += 1
    stats = {"f10_enriched": ok, "f10_failed": fail}
    log(f"[f10] enriched={ok} failed={fail}")
    return stats


# ---------------------------------------------------------------- 存量市场基线（碰撞索引）

_CNINFO_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"


class CninfoStockListSource:
    source = "cninfo_all_a"
    kind = "baseline"
    priority = 1

    def __init__(self, limit: Optional[int] = None):
        self.limit = limit

    def fetch(self, log) -> list[dict]:
        data = http.get_json(_CNINFO_URL)
        stocks = data.get("stockList") or []
        records, rejected = [], 0
        for st in stocks:
            cat = st.get("category") or ""
            if cat in ("B股", "退市", "债券", "基金"):
                continue
            name, _meta = clean_short_name(st.get("zwjc") or "")
            if not name:
                rejected += 1
                continue
            records.append({
                "record_id": record_id(self.source, st.get("code", name)),
                "source": self.source,
                "source_priority": self.priority,
                "kind": self.kind,
                "name_raw": st.get("zwjc"),
                "name_clean": name,
                "secucode": st.get("code"),
            })
            if self.limit and len(records) >= self.limit:
                break
        log(f"[{self.source}] accepted={len(records)} rejected={rejected}")
        return records


# ---------------------------------------------------------------- 维基百科品牌分类

_WIKI_API = "https://zh.wikipedia.org/w/api.php"
_TITLE_BLACKLIST_RE = re.compile(r"(列表|之最|模板|分类|索引|消歧)")


class WikiCategorySource:
    source = "wiki_zh_brand"
    kind = "famous_brand"
    priority = 2

    BASE_CATS = ["中国品牌", "中国商标", "中華人民共和國的老字號"]
    MAX_API_CALLS = 150
    MAX_PAGES = 2500
    WIKI_INTERVAL = 2.0        # 维基 API 限流较严，慢速轮询
    CONSECUTIVE_FAIL_LIMIT = 3  # 连续失败即放弃整个源（防 429 雪崩）

    def __init__(self, depth: int = 2):
        self.depth = depth

    def _cat_title(self, cat: str) -> str:
        return "Category:" + cat

    def _query(self, cat: str, cmtype: str, log) -> list[dict]:
        members, cont = [], None
        while True:
            params = {
                "action": "query", "list": "categorymembers", "format": "json",
                "cmtitle": self._cat_title(cat), "cmtype": cmtype,
                "cmlimit": 500, "cmnamespace": 0 if cmtype == "page" else 14,
            }
            if cont:
                params["cmcontinue"] = cont
            data = http.get_json(_WIKI_API, params=params, interval=self.WIKI_INTERVAL,
                                 retries=2, backoff=5.0, wait_429=15.0)
            self._calls += 1
            q = data.get("query") or {}
            members += q.get("categorymembers") or []
            cont = (data.get("continue") or {}).get("cmcontinue")
            if not cont or self._calls >= self.MAX_API_CALLS:
                break
        return members

    def fetch(self, log) -> list[dict]:
        self._calls = 0
        seen_pages: dict[str, dict] = {}
        queue = [(c, 0) for c in self.BASE_CATS]
        visited_cats = set()
        consecutive_fails = 0
        while queue:
            cat, depth = queue.pop(0)
            if cat in visited_cats or self._calls >= self.MAX_API_CALLS:
                continue
            visited_cats.add(cat)
            try:
                pages = self._query(cat, "page", log)
                consecutive_fails = 0
            except Exception as exc:  # noqa: BLE001
                consecutive_fails += 1
                log(f"[{self.source}] category {cat} failed ({consecutive_fails}/{self.CONSECUTIVE_FAIL_LIMIT}): {exc}")
                if consecutive_fails >= self.CONSECUTIVE_FAIL_LIMIT:
                    raise RuntimeError(f"wiki 连续 {consecutive_fails} 个分类失败（疑似限流），放弃该源: {exc}")
                continue
            for p in pages:
                title = p.get("title", "")
                base = clean_wiki_title(title)
                if not base or _TITLE_BLACKLIST_RE.search(title):
                    continue
                if base in seen_pages:
                    continue
                seen_pages[base] = {
                    "record_id": record_id(self.source, title),
                    "source": self.source,
                    "source_priority": self.priority,
                    "kind": self.kind,
                    "name_raw": title,
                    "name_clean": base,
                }
            if len(seen_pages) >= self.MAX_PAGES:
                break
            if depth < self.depth:
                try:
                    subs = self._query(cat, "subcat", log)
                except Exception:  # noqa: BLE001
                    continue
                for s in subs:
                    sub = s.get("title", "").replace("Category:", "")
                    if sub and sub not in visited_cats:
                        queue.append((sub, depth + 1))
        records = list(seen_pages.values())
        log(f"[{self.source}] categories={len(visited_cats)} api_calls={self._calls} accepted={len(records)}")
        return records


# ---------------------------------------------------------------- App Store 榜单（产品名语域）

_ITUNES_FEEDS = [
    # 榜单 feed（中国区）。游戏类（6014）不收：游戏名多为玄幻造词（向僵尸开炮），
    # 会把「开炮/冒险」这类词带进用字统计，与产品品牌不是同一个语域。
    "topfreeapplications",
    "topgrossingapplications",
]
_ITUNES_GENRES = [6000, 6001, 6002, 6003, 6005, 6006, 6007, 6008, 6009,
                  6010, 6011, 6012, 6013, 6015, 6016, 6017, 6018, 6020]
_ITUNES_URL = "https://itunes.apple.com/cn/rss/{feed}/limit=200/genre={genre}/json"
_APP_SUFFIX_RE = re.compile(r"\s*[-—–|·•:：（(].*$")
_APP_TAILWORDS = ("App", "应用", "版", "官方", "旗舰", "手机版", "最新版")


_APP_ORG_HEADS = (
    # 政务 / 机构类 app 不是品牌名：铁路12306、交管12123、皖事通、学信网
    "铁路", "交管", "公安", "政务", "通办", "学信", "国聘", "公务", "天府",
    "皖事", "智桂", "辽宁", "中国移动", "中国联通", "中国电信", "一汽",
    "国家", "税务局", "人社", "医保", "公积金",
)

_APP_CATEGORY_TAILS = (
    # 产品品类尾：剥掉后剩下的才是品牌（高德地图->高德、夸克网盘->夸克）。
    # 与 IPO 行业尾同机制，只是词表换成消费产品品类。
    "浏览器", "播放器", "输入法", "网盘", "云盘", "邮箱", "地图", "导航", "音乐",
    "视频", "直播", "商城", "外卖", "团购", "招聘", "旅行", "旅游", "出行",
    "速运", "快递", "钱包", "支付", "金融", "理财", "记账", "证券", "炒股",
    "读书", "小说", "阅读", "文档", "表格", "会议", "投屏", "加速", "远程",
    "时钟", "日历", "万年历", "备忘录", "待办", "翻译", "词典", "扫描",
    "修图", "剪辑", "相机", "相册", "修图", "打印", "助手", "管家", "极速",
    "商城", "超市", "生鲜", "医药", "课堂", "题库", "单词", "识字", "教育",
    "房产", "租房", "装修", "家政", "洗车", "加油", "停车", "打车", "代驾",
    "健身", "减肥", "菜谱", "社区", "论坛", "资讯", "新闻", "天气", "办公",
    "协作", "直聘", "众包", "商城", "小店", "店铺", "商家", "管家",
)


def clean_app_name(raw: str) -> Optional[str]:
    """App 展示名 -> 品牌名：砍营销尾巴，再剥品类尾。

    「抖音商城-下单返积分、退货包运费」-> 抖音商城 -> 抖音；「红果短剧 - 海量热门短剧」-> 红果短剧。
    剥完不是品牌形态（长度/机构头/行业尾不过闸）的整条丢弃。
    """
    from .stats import is_brandlike_shortname
    from .clean import cjk_chars
    s = _APP_SUFFIX_RE.sub("", raw.strip())
    for w in _APP_TAILWORDS:
        s = s.replace(w, "")
    s = s.strip().strip("-—– ")
    if not s:
        return None
    for tail in sorted(_APP_CATEGORY_TAILS, key=len, reverse=True):
        if s.endswith(tail) and len(cjk_chars(s)) - len(tail) >= 2:
            s = s[: -len(tail)]
            break
    # 拉丁/数字混排：取 CJK 前缀（小米WiFi -> 小米、番茄ToDo -> 番茄）；
    # 拉丁或数字在前的丢弃（OPPO 互联、ToDesk远程控制、58同城 这类不再单列）。
    body = cjk_chars(s)
    idx = min([len(s)] + [s.index(ch) for ch in s
                          if not is_cjk(ch) and not ch.isspace()])
    if idx < len(s):
        body = cjk_chars(s[:idx])
    if len(body) < 2:
        return None
    s = body
    if s.startswith(_APP_ORG_HEADS):
        return None
    if not is_brandlike_shortname(s):
        return None
    return s


class ItunesAppSource:
    """App Store 中国区榜单：产品级中文名（豆包/元宝/夸克/剪映/唯品会）。

    与 IPO 简称、公司名录不同，这类名字是真正面向消费者的产品名，
    是本管道最接近「产品取名」目标的语域。榜单接口公开、无需鉴权。
    """

    source = "itunes_apps"
    kind = "product_app"
    priority = 2

    def __init__(self, genres: Optional[list] = None, interval: float = 1.0):
        self.genres = genres or _ITUNES_GENRES
        self.interval = interval

    def fetch(self, log) -> list[dict]:
        seen: dict[str, dict] = {}
        feeds = [(f, None) for f in _ITUNES_FEEDS] + [
            ("topfreeapplications", g) for g in self.genres]
        for feed, genre in feeds:
            url = _ITUNES_URL.format(feed=feed, genre=genre) if genre else \
                f"https://itunes.apple.com/cn/rss/{feed}/limit=200/json"
            try:
                data = http.get_json(url, interval=self.interval, retries=2)
            except Exception as exc:  # noqa: BLE001
                log(f"[{self.source}] feed {feed}/{genre} failed: {exc}")
                continue
            entries = (data.get("feed") or {}).get("entry") or []
            for e in entries:
                raw = (e.get("im:name") or {}).get("label") or ""
                name = clean_app_name(raw)
                if name and name not in seen:
                    seen[name] = {
                        "record_id": record_id(self.source, name),
                        "source": self.source,
                        "source_priority": self.priority,
                        "kind": self.kind,
                        "name_raw": raw,
                        "name_clean": name,
                    }
        log(f"[{self.source}] feeds={len(feeds)} accepted={len(seen)}")
        return list(seen.values())


# ---------------------------------------------------------------- 种子语料（知名互联网品牌 + 域名）

class SeedCorpusSource:
    source = "curated_seed"
    kind = "famous_brand"
    priority = 5

    def __init__(self, seeds_path: str):
        self.seeds_path = seeds_path

    def fetch(self, log) -> list[dict]:
        with open(self.seeds_path, encoding="utf-8") as f:
            seeds = json.load(f)
        records = []
        for item in seeds:
            name = item.get("name", "").strip()
            if len(cjk_chars(name)) < 2:
                continue
            clean, _meta = clean_short_name(name)   # 统一走清洗器（剥离 股份/集团 等组织词）
            if not clean:
                continue
            records.append({
                "record_id": record_id(self.source, name),
                "source": self.source,
                "source_priority": self.priority,
                "kind": self.kind,
                "name_raw": name,
                "name_clean": clean,
                "domain": item.get("domain"),
                "industry": item.get("industry"),
            })
        log(f"[{self.source}] accepted={len(records)}")
        return records


def default_seeds_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seeds", "brand_domains.json")
