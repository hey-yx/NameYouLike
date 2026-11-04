# brandgen —— 品牌名生成引擎

为「现有品牌资源匮乏、好名难注册」的困境提供生成核心：给定种子词与风格参数，
批量产出候选品牌名（企业/产品名），每个候选附带完整的拉丁转写变体与域名可用性建议。

服务中国市场，命名可包含拼音简拼与破折号。

## 核心规则

### 变体模式（任务验收示例：赤兔）

| 模式 | 规则 | 示例 |
|------|------|------|
| `pinyin` 拼音全拼 | 逐字无声调全拼连写，小写 | `chitu` |
| `pinyin_toned` | 带声调显示 | `chì tù` |
| `initials` 声母简拼 | 逐字取**声母**拼接（零声母取读音首字母） | `cht`（ch + t） |
| `letters` 首字母 | 逐字全拼首字母 | `ct` |
| `dash` 破折号组合 | 每字全拼首字母大写，`-` 连接 | `Chi-Tu` |
| `kebab` 全拼短横线 | 全拼小写、`-` 连接 | `chi-tu` |
| `camel` 驼峰 | 每字全拼首字母大写连写 | `ChiTu` |

> 声母简拼与「每字首字母」不同：赤=ch、兔=t，声母拼接为 `cht`，而首字母是 `ct`。
> ü 统一转 v（pypinyin 惯例，如 绿→`lv`），保证全部变体可直接用作域名。

### 构词规则

候选池由种子词按规则展开（全部为确定性、跨进程一致）：

1. 种子词直用
2. 种子词 + 风格后缀（如 赤兔+科技 → 赤兔科技；赤兔+坊 → 赤兔坊）
3. 风格前缀 + 种子词
4. 种子字 × 风格语素交叉（赤+驰 → 赤驰）
5. **注入词**组合（外部词汇经 `extra_vocab` 注入，与种子字交叉）
6. 跨种子组合（赤兔、飞跃 → 赤+飞 等）

### 风格参数（StyleParams）

| 参数 | 说明 | 默认 |
|------|------|------|
| `style` | `tech` / `classic` / `international` / `playful` / `neutral`，控制前后缀语素库与 TLD 优先级 | neutral |
| `lengths` | 允许的名字长度（字） | `(2,3,4)` |
| `limit` | 输出候选数 | 20 |
| `tlds` | 域名 TLD 池 | com,cn,com.cn,io,ai,tech,app,net |
| `live_check` | 在线核验域名可用性 | False |
| `live_per_name` | 每个候选在线核验的域名形式数 | 3 |
| `extra_vocab` | 外部词汇注入 | 无 |
| `include_seed` | 种子词本身是否进入候选 | True |
| `patterns_file` | 命名模式统计文件（启用音节自然度 + 碰撞排雷） | 无（CLI 自动发现） |

### 排序启发式

- 两字名 > 三字名 > 四字名（记忆成本）
- 拼音 ≤6/≤4 字母加分；声母简拼自带元音加分（可作单词发音，如 kimi 型）
- 种子词直用加权（最贴近用户意图）；注入词组合加权（注入词要能浮出）
- 同分段用名字 md5 确定性打散，避免小 limit 被单一种子字挤满
- 在线核验后：疑似可注册 `.com` +3.0，其他 TLD 可注册 +1.0
- **启用命名统计时**：音节自然度 +0~1.2（真实品牌语料先验）；同音已有品牌
  评分 ×0.4 强降权；精确重名直接剔除（不进候选列表）

## 命名统计集成：音节自然度与碰撞排雷

命名模式统计来自数据管道交付的 `naming_patterns.v1.json`（或随包内置的瘦身版），
消费两类输入。CLI 默认自动发现统计文件；库调用方也可显式传
`StyleParams(patterns_file=…)` 或直接传已解析的 `BrandEngine(params, stats=…)`。

### 1. 音节自然度权重

- 先验：真实语料的首字母分布（`w_initial`，如 h 9.6% / s 8.5% / z 8.3%）
  与 Top150 音节分布（`w_syllable`，如 ji / ke / xin / dian / shi）。
- 打分：`0.5 × 首字母分布(归一化) + 0.5 × 音节分布均值(归一化)` ∈ [0,1]，
  作为 +0~1.2 的排序加成——读音贴近真实品牌的候选浮出，生僻组合自然下沉。
- 只影响排序，不构成一票否决。

### 2. 品牌碰撞排雷

| 碰撞类型 | 判据 | 处理 |
|----------|------|------|
| `exact` 精确重名 | 名字命中 7719 个已有品牌名索引 | **直接剔除**，剔除记录进 `last_dropped` / JSON `patterns.dropped_exact_collisions`（可审计） |
| `phonetic` 同音 | 无声调拼音键命中 7655 个已有品牌语音键 | **评分 ×0.4 强降权**并标注 `collision`（通常沉出 top-N，不再打扰用户） |

语音键口径：与管道索引一致，**逐字** `lazy_pinyin` 拼接（多音字取默认读音，
如 银行 → `yinxing`），与本引擎词组级拼音（`yinhang`）可能不同——查索引必须
用逐字口径，`brandgen.stats.collision_key()` 已封装。

真实数据效果（内置 v2026.11.02-029）：

- 精确剔除示例：`极兔`（前缀『极』+种子『兔』构出）、种子词 `飞跃` 本身；
  美团 / 腾讯 / 华为 均能识别。
- 同音降权示例：`翼兔→依图`、`光麒→广汽`、`元麟→园林`、`赤维→驰为`。

### 内置数据与更新

`brandgen/data/naming_patterns.slim.json`（约 327 KB，只含上述四项字段 + 来源
版本号）从管道完整统计提取，离线开箱可用。管道统计更新后：

```bash
.venv/bin/python scripts/extract_slim.py <新的 naming_patterns.v1.json>
```

CLI 不传 `--patterns-file` 时自动发现统计文件（环境变量 `PATTERNS_FILE` →
仓库内管道统计 → 内置瘦身版）；显式指定但文件不存在则直接报错，不静默降级。

### 在线预览

```bash
python -m brandgen --seed 赤兔 --style tech --limit 12 \
    --patterns-file brandgen/data/naming_patterns.slim.json --check-domains
```

## 域名可用性语义（如实标注，不过度承诺）

| 状态 | 判据 | 含义 |
|------|------|------|
| `registered` 已注册/占用 | RDAP 200 或 DNS 有解析 | 被注册或在用 |
| `likely_available` 疑似可注册 | RDAP 404 或 DNS NXDOMAIN | **注册前必须复核 whois** |
| `unknown` 未能验证 | 网络失败 / TLD 无 RDAP | 无证据，不下结论 |

核验链路：`rdap.org`（IANA bootstrap 重定向到注册局 RDAP）优先，失败降级 DNS。
在线核验用线程池并发，但对外仍是同步调用。离线模式只生成域名形式，状态置 `unknown`。

> 注意：域名可注册 ≠ 商标可注册。商标近似检索不在本引擎范围内。

## 安装与使用

```bash
uv venv && uv pip install -e .   # 或 pypinyin 手动安装: uv pip install pypinyin
```

### Python API

```python
from brandgen import BrandEngine, StyleParams

engine = BrandEngine(StyleParams(style="tech", limit=12, live_check=True,
                                 extra_vocab=["鲲", "麟"]))   # 外部词汇注入
candidates = engine.generate(["赤兔", "飞跃"])
for c in candidates:
    print(c.name, c.patterns.pinyin, c.patterns.initials, c.patterns.dash)
    for d in c.domains:
        print("  ", d.domain, d.status)
```

### CLI

```bash
python -m brandgen --seed 赤兔 --seed 飞跃 --style tech --limit 12 \
    --check-domains --json out.json --md out.md
python -m brandgen --seed 麒麟 --style classic --extra-vocab 鲲 --extra-vocab 鹏
# 启用命名统计（自然度 + 碰撞排雷；内置数据随包分发）
python -m brandgen --seed 赤兔 --style tech --limit 12 \
    --patterns-file brandgen/data/naming_patterns.slim.json
# 不指定 --patterns-file：自动发现（管道统计优先，内置瘦身版兜底）
python -m brandgen --seed 赤兔 --style tech --limit 12
```

## 目录结构

```
brandgen/
  pinyin_util.py  # 拼音底层：全拼/声母/韵母/声调（pypinyin）
  patterns.py     # 模式引擎：全拼/声母简拼/破折号等变体
  lexicon.py      # 风格词库（前后缀 + 意象语素）
  stats.py        # 命名统计：自然度权重 + 碰撞排雷（可选）
  signals.py      # 统计文件发现：显式路径 → 环境变量 → 管道统计 → 内置瘦身版
  domains.py      # 域名形式生成 + RDAP/DNS 可用性核验
  engine.py       # 生成编排：构词池 → 变体 → 打分 → 域名
  cli.py          # 命令行入口
  data/naming_patterns.slim.json  # 内置统计（随包分发，从管道完整统计提取）
../scripts/       # 与 brandgen/ 同级（项目 python/scripts/）
  extract_slim.py      # 从管道完整统计刷新内置数据
  smoke_real_stats.py  # 真实统计冒烟（碰撞/自然度）
../tests/         # 与 brandgen/ 同级（项目 python/tests/），brandgen 相关 81 个测试（离线）
```

## 给下游引擎的集成说明

- 主入口：`BrandEngine(StyleParams(...)).generate(seeds) -> list[BrandCandidate]`
- `BrandCandidate.as_dict()` 输出稳定 JSON 结构（name / variants / origin / score / domains）
- 外部词汇用 `StyleParams.extra_vocab` 注入，会获得 +0.8 排序加成以浮出
- `origin` 字段标注构词来源，可用于区分构词路径（注入词直用 / 语素交叉组合等）
- 重排序时可直接改写 `score` 或在外部另行加权；`domains[].status` 可作为可用性权重信号
- **统计模式（v0.2 加性扩展）**：传 `StyleParams(patterns_file=…)` 后，`as_dict()`
  额外带 `phonetic`（音节自然度 0~1，可作排序特征）与 `collision`
  （`null` 或 `{'type':'phonetic','existing':…}`，命中同音的候选已被 ×0.4 降权，
  可直接过滤或再降权）。精确重名候选已在引擎侧剔除，不会出现在返回列表。
  库调用方不传统计时键集与 v1 完全一致（CLI 默认自动发现统计，故 CLI 输出
  默认带这两个字段）。

## 免责与边界

- 多音字取 pypinyin 默认常用读音，生成确定性结果；如需人工校正读音，可在上层调用
  `brandgen.patterns.build()` 前替换种子写法。
- 域名可用性为**建议性信号**，非注册承诺；注册前请在注册商处复核。
- 不包含商标近似检索、工商核名、敏感词过滤（可由上层任务接入）。
