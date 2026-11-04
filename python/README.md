# NameYouLike Python 核心引擎

NameYouLike 的 Python 侧引擎与数据层，两个组件：**品牌名生成引擎（`brandgen/`）** 与
**命名语料管道（`naming-pipeline/`）**。两者以**扁平布局**整合在同一目录下（根
`conftest.py` 把本目录注入 `sys.path`），无需安装即可 `import` 与跑测试。

## 组件矩阵

| 组件 | 目录 / 入口 | 职责 | 详细文档 |
|---|---|---|---|
| brandgen 生成引擎 | `brandgen/` | 种子词 × 5 风格 → 候选品牌名，每候选 7 种拉丁变体（全拼/声调/声母简拼/首字母/破折号/短横线/驼峰）+ 域名形式与可用性核验；v0.2 起消费命名统计（音节自然度 + 品牌碰撞排雷），统计文件**自动发现** | [`brandgen/README.md`](brandgen/README.md) |
| naming-pipeline 语料管道 | `naming-pipeline/` | 互联网品牌命名案例的持续学习（抓取→去重→清洗→统计），产出命名统计先验 `naming_patterns.v1.json`；**独立子项目**，自带 venv / data / output | [`naming-pipeline/README.md`](naming-pipeline/README.md) |

目录速览：

```
python/
  README.md               # 本文件
  pyproject.toml          # 打包（packages=["brandgen"]）
  conftest.py             # pytest 根 conftest：把 python/ 加入 sys.path（扁平 import 的关键，勿改）
  brandgen/               # 生成引擎包（README 随包；data/naming_patterns.slim.json 为内置统计）
  scripts/                # extract_slim.py 刷新内置统计、smoke_real_stats.py 冒烟
  tests/                  # 合并测试集（brandgen 相关 82 + pipeline 相关 48 + 安全相关 47）
  naming-pipeline/        # 语料管道子项目（自带 venv / data / output / tests）
```

`tests/` 由三部分组成：brandgen 相关 8 个测试文件（82 用例：CLI / 统计消费 / 域名核验 /
引擎参数校验 / 拼音与变体 / 统计文件发现）+ naming-pipeline 相关 4 个测试文件（48 用例：
采集→清洗→去重→统计全链路的行为测试）+ 安全相关 6 个测试文件（47 用例：HTTP 层、
管道运行与存储、来源与瘦身提取的注入面守门）= **177 用例**。全部离线、确定性。

## 安装

```bash
cd python
uv venv
uv pip install pypinyin pytest      # 运行依赖仅 pypinyin；pytest 用于测试
```

可选：把本目录作为包安装（editable），用于外部项目 import 或校验打包元数据：

```bash
uv pip install -e .
```

> 需要 Python ≥ 3.10（见 `pyproject.toml`）。不安装也能用：在 `python/` 下
> `python -m pytest` / `python -m brandgen` 直接按文件系统解析。

`naming-pipeline/` 是独立子项目，依赖单独装：

```bash
cd python/naming-pipeline
uv venv && uv pip install requests pypinyin opencc-python-reimplemented pytest
```

## 测试与自检

```bash
cd python
.venv/bin/python -m pytest -q       # 177 passed（brandgen 82 + pipeline 48 + 安全 47）
.venv/bin/python scripts/smoke_real_stats.py   # 命名统计冒烟：内置统计版本、真实碰撞、自然度分布
```

## brandgen 生成引擎

种子词 + 风格参数 → 批量候选品牌名。5 种风格（`tech` / `classic` / `international` /
`playful` / `neutral`）决定前后缀语素与 TLD 优先级；构词池 = 种子直用 / 前后缀 /
语素交叉 / 注入词组合 / 跨种子组合。每个候选附带 7 种拉丁变体（赤兔 → `chitu` /
`chì tù` / `cht` / `ct` / `Chi-Tu` / `chi-tu` / `ChiTu`）与域名形式。

CLI（离线，只生成域名形式，状态为 unknown）：

```bash
.venv/bin/python -m brandgen --seed 麒麟 --style classic --extra-vocab 鲲 --extra-vocab 鹏
```

CLI（在线核验域名可用性，结果落盘 JSON + Markdown）：

```bash
.venv/bin/python -m brandgen --seed 赤兔 --seed 飞跃 --style tech --limit 12 --check-domains --json out.json --md out.md
```

CLI（命名统计：音节自然度加权 + 品牌碰撞排雷）：

```bash
# 不指定 --patterns-file：自动发现
#   显式路径 → 环境变量 PATTERNS_FILE → 仓库内管道统计 → 内置瘦身版
.venv/bin/python -m brandgen --seed 赤兔 --style tech --limit 12

# 显式指定（文件不存在直接报错，不静默降级）
.venv/bin/python -m brandgen --seed 赤兔 --style tech --limit 12 \
    --patterns-file brandgen/data/naming_patterns.slim.json
```

自动发现的回退原因写进输出 JSON 的 `patterns.note`（只在管道文件不可解析等降级
场景出现），便于排查。

Python API：

```python
from brandgen import BrandEngine, StyleParams

engine = BrandEngine(StyleParams(style="tech", limit=12, live_check=True,
                                 extra_vocab=["鲲", "麟"]))   # extra_vocab：外部词汇注入
candidates = engine.generate(["赤兔", "飞跃"])
for c in candidates:
    print(c.name, c.patterns.pinyin, c.patterns.initials, c.patterns.dash)
    for d in c.domains:
        print("  ", d.domain, d.status)
```

命名统计的自动发现也可直接调用：

```python
from brandgen import find_patterns, find_patterns_file

stats, note = find_patterns()          # (PatternStats | None, note | None)
path, note = find_patterns_file()      # (Path | None, note | None)
```

域名状态是**三态如实标注**：`registered`（RDAP 200 或 DNS 有解析）/ `likely_available`
（RDAP 404 或 NXDOMAIN，注册前必须复核 whois）/ `unknown`（网络失败或无 RDAP，
不下结论）。`live_check=False`（默认）时不做在线核验，全部为 `unknown`。构词规则、
排序启发式与集成接口详见 [`brandgen/README.md`](brandgen/README.md)。

## naming-pipeline 语料管道

定期采集中国新近公开的企业名与知名品牌命名案例，清洗去重后提取命名模式（音节长度、
用字偏好、拼音风格、行业关联），产出 `output/naming_patterns.v1.json`：音节自然度先验
（`w_initial` / `w_syllable`）+ 品牌碰撞索引（`collision_index`）。

管道是**独立子项目**（自带 venv / data / output / tests），流程与运维细节见
[`naming-pipeline/README.md`](naming-pipeline/README.md)。

管道统计与引擎的衔接：

- `brandgen.signals` 自动发现 `python/naming-pipeline/output/naming_patterns.v1.json`；
  管道文件不可解析时回退到 `brandgen/data/naming_patterns.slim.json`（随包分发，离线可用）。
- `scripts/extract_slim.py` 把管道最新完整统计提取为内置瘦身版：

```bash
.venv/bin/python scripts/extract_slim.py \
    naming-pipeline/output/naming_patterns.v1.json
```

- 管道侧统计格式由 `naming-pipeline/pipeline/consumer.py` 校验（schema 守门唯一职责），
  引擎侧由 `brandgen.stats.load_patterns` 解析，两边共用同一份字段口径。

## 与 TS 侧（lib/、web/）的关系

当前仓库是「TS 应用层 + Python 引擎层」的双栈结构：

- **TS 侧**：`lib/naming/` 保留知识库与规则审计（测试覆盖），`web/` 是 Vite 单页，
  直接展示 `prompt.txt`；域名查询走 `scripts/domain-check-fast.py`（RDAP/WHOIS）。
  旧 `server/`、`lib/domains/` 已下线删除。
- **Python 侧**（本目录）：确定性算法与数据层：brandgen 的构词、拼音和域名规则，
  以及命名统计的自然度权重与碰撞排雷。不调用模型，结果可复现。当前学习以采集统计
  为主，不代表已经训练模型权重。

旧文档里的 UI 接入方案（Next.js Route Handler 起子进程、`lib/domains/check.ts` 前端即时核验）
基于已删除的 Next.js/server 栈，随栈一起作废。`brandgen --json out.json` 的候选契约仍然有效。

## 边界与免责

- 域名可用性为**建议性信号**（三态如实标注），不是注册承诺；注册前请在注册商处复核。
  域名可注册 ≠ 商标可注册，商标近似检索不在本仓库范围。
- 拼音多音字取 pypinyin 默认读音（ü 统一转 v，如 绿→`lv`），全部变体可直接用作域名；
  需要人工校正读音时在上层替换种子写法。
- 命名统计只影响**排序**（音节自然度加权）与**排雷**（精确重名剔除、同音强降权），
  不构成品牌价值的判断依据。
