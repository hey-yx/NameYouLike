<div align="center">

# NameYouLike · 取名台

**起名提示词与命名数据工作区**。产品是一块拿走即用的起名提示词，交给任意 AI agent 就能跑完起名、评审与域名核验；仓库同时保留命名采集、规则审计与已分析材料。

[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vite.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178c6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org)
[![pnpm](https://img.shields.io/badge/pnpm-workspace-f69220?logo=pnpm&logoColor=white)](https://pnpm.io)

[特性](#特性) · [快速开始](#快速开始) · [使用](#使用) · [工作原理](#工作原理) · [项目结构](#项目结构) · [测试](#测试) · [已知边界](#已知边界)

</div>

项目不再直调大语言模型 API。采集与规则计算在本地脚本里完成；案例分析、方法归纳和提示词整理在 Hermes 会话中完成，结果落盘后可离线校验。已有语料、历史快照、研究分析和提示词保留。这里的学习指案例分析与方法整理，不代表已经训练了模型权重。

项目的目的与验收标准写在 [`user-input.md`](user-input.md)，以那份为准。

## 特性

- **起名提示词**：`prompt.txt` 单块提示词，起名、评审、补齐一体化，默认出 8 个词，评审不满足就重跑一轮去重。复制给任意 AI agent 即可自动跑。
- **域名查询链**：`scripts/domain-check-fast.py` 实现 DoH 预筛、权威 RDAP、WHOIS 兜底，输出可用状态、注册商、创建与到期时间；提示词点名使用这套查询链。
- **命名采集与审计**：`python/naming-pipeline/` 抓取公开命名案例产出统计先验；`lib/naming/audit.ts` 做反套路、拼音、品牌碰撞的规则审计；`research/` 保存来源案例与逐例分析。
- **品牌名生成引擎**：`python/brandgen/` 用种子词 × 5 种风格产出候选品牌名，每个名字带全拼 / 声母简拼 / 破折号 / 驼峰 / 连字符等拉丁变体与域名形式，离线可跑。

## 快速开始

```bash
pnpm install
pnpm dev    # 提示词文档页：Vite + React，端口 5173
pnpm test   # TS 单元测试，不联网
```

提示词本体在仓库根 `prompt.txt`，拿走即用：把整段产品描述发给 agent，agent 按提示词起名并逐名评审，需要查域名时跑 `python3 scripts/domain-check-fast.py --variants link-parse,direct-fetch --json out.json`。

### 数据采集与学习

- `python/naming-pipeline/` 保留抓取、清洗、去重与统计入口，行业小样本与公司名仍按原规则分流。
- `research/命名方法学习-案例.json` 保存来源案例，`research/命名方法学习-结果/` 保存逐例分析与提示词。
- 在 Hermes 会话中按原始名字和来源分析，不用截断名字推断词源。分析完先保存 JSON，再核验引文与案例覆盖。

```bash
pnpm run learn:check    # 校验现有 27 个案例的分析，不联网、不调模型
```

无需模型密钥，现有代码不读取模型配置。

### Python 引擎环境

Python 侧引擎（brandgen / naming-pipeline）需要各自的 venv，与 Web 应用互不依赖：

```bash
# 环境准备（两个独立 venv；.venv 不入库，重复执行无副作用）
cd python && uv venv --allow-existing && uv pip install pypinyin pytest && cd ..
cd python/naming-pipeline && uv venv --allow-existing && uv pip install requests pypinyin opencc-python-reimplemented pytest && cd ../..

# 引擎测试（177 passed）
cd python
.venv/bin/python -m pytest -q

# 生成引擎：种子词 + 风格（离线只生成域名形式，状态为 unknown）
.venv/bin/python -m brandgen --seed 麒麟 --style classic --limit 5

# 语料管道：离线冒烟（只跑种子语料，不联网）+ 测试（33 例）
cd naming-pipeline
.venv/bin/python -m pipeline.run --offline
.venv/bin/python -m pytest tests/ -q
```

`brandgen` / `pipeline.run` 都用 `-m` 从包入口跑；`--json` / `--md` 可把候选结果落盘。

## 使用

主页 `/` 是一页提示词文档：一块可复制内容（起名提示词，含逐名评审与补齐）。提示词正文在仓库根 `prompt.txt`（拿走即用），页面直读它，标题下的说明写死在 `lib/prompts-content.ts`，改完文件刷新即生效，没有生成步骤。提示词下附实测案例：只放整段产品描述与结果，不展示过程统计。

## 工作原理

### 规则审计与模型分析分开

`lib/naming/audit.ts`、离线词典、拼音检查、品牌碰撞与套路规则保留，用于研究候选检查。它们只证明规则满足与否，不证明用户喜欢。旧在线简报提取、模型生成与模型评审编排已经移除。

### 拉丁字母配名与拼音写法

名字支持全拼、声母简拼、破折号等拉丁变体，常见形态是拼音-横线-实际干的事，例如 `guizang-ppt-skill`。只做英文命名，不做汉字名；域名按拉丁字母配名查。

### 域名查询

查询链由 `scripts/domain-check-fast.py` 实现（DoH 预筛、权威 RDAP、WHOIS 兜底）：

- **RDAP**：`.com .net .org .ai .app .dev` 等有 RDAP 的后缀。已注册返回 200，未注册返回 404。
- **WHOIS**：`.io .co .me .cn` 等没有 RDAP 的后缀，按注册局串行查询。
- **状态**：枚举 `available / registered / premium / reserved / unknown / error`。同一后缀不并发轰炸；同一域名两次结论一致才写状态。

> [!WARNING]
> 注册局返回 404 只代表没有记录，保留词和溢价词可能仍需高价注册。可用性不等于可注册。

## 项目结构

```
web/
  page.tsx                 纯提示词文档页：一块提示词全文 + 复制按钮（当前唯一页面）
  globals.css              Cobalt 皮肤 token 与排版
prompt.txt                 起名提示词正文（拿走即用，站点直读）
scripts/
  domain-check-fast.py     域名查询链（DoH 预筛 / RDAP / WHOIS 兜底），提示词点名使用
  learn-naming.ts          案例分析离线校验
lib/
  prompts-content.ts       站点直读 prompt.txt 与实测案例数据
  naming/                  知识库、反套路规则、审计
tests/                     单元测试
python/
  README.md                两个组件的 API 与命令（Python 侧先读这份）
  brandgen/                品牌名生成引擎：种子词 × 风格 → 7 种拉丁变体 + 域名形式与核验
  naming-pipeline/         命名语料管道（独立子项目，自带 venv / data / output）
  tests/                   177 个 pytest 用例
```

### Python 引擎侧

两个组件承担确定性部分：构词/拼音/域名规则、命名统计先验，不调模型、结果可复现。

| 组件 | 入口 | 作用 |
|---|---|---|
| brandgen 生成引擎 | `python/brandgen/` | 种子词 × 5 种风格 → 候选品牌名，每个名字 7 种拉丁变体（全拼 / 声调 / 声母简拼 / 首字母 / 破折号 / 短横线 / 驼峰）+ 域名形式与三态可用性核验；可消费命名统计做音节自然度加权与品牌碰撞排雷 |
| naming-pipeline 语料管道 | `python/naming-pipeline/` | 互联网品牌命名案例的持续学习：抓取 → 清洗去重 → 统计，产出 `naming_patterns.v1.json` 供生成引擎消费；独立子项目，自带 venv / data / output |

生成引擎的调用链路：CLI `python -m brandgen --seed ... --json out.json` 输出候选与域名形式；命名统计文件由 `brandgen/signals.py` 自动发现（显式路径 → 环境变量 `PATTERNS_FILE` → 仓库内管道统计 → 内置瘦身版）。主页是纯提示词文档页，不调引擎。

## 测试

测试入口如下，用例数和覆盖率以本轮运行结果为准：

| 入口 | 覆盖 | 联网 | 环境前置 |
|---|---|---|---|
| `pnpm test` | TS 单元测试与证据校验 | 否 | `pnpm install` |
| `pnpm run learn:check` | 校验会话产出的案例分析 | 否 | 已保存的案例与分析 JSON |
| `cd python && .venv/bin/python -m pytest -q` | Python 引擎（177 例） | 否 | `python/.venv`（见 python/README.md） |
| `cd python/naming-pipeline && .venv/bin/python -m pytest tests/ -q` | 语料管道（33 例，**不被主 pytest 收集**） | 否 | `python/naming-pipeline/.venv`（独立子项目） |

全部用例离线，不需要 Python 环境：`pnpm dev` 与 `pnpm test` 在没有 `python/.venv` 时同样可用。

```bash
pnpm test        # 单元测试，不联网（看覆盖率：npx vitest run --coverage）
pnpm build       # 生产构建
```

## 已知边界

- 可用性不等于可注册：保留词、溢价词需要去注册商页面确认。
- 商标不自动核查：只给 USPTO / CNIPA 搜索入口。
- 不支持国际化域名（IDN）；域名按拉丁字母配名查，可用拼音、拼音-英文用途词或英文名。
- 规则审计不等于审美评价。
- 不做账号、付费与在线模型生成。
- 不代注册、不代付款。
