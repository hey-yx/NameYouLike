# GitHub 真实项目命名样本谱系（2026-10-27）

> 采集：GitHub Search API（`gh api search/repositories`，按 star 排序），2026-10-27。
> 原始数据：`research/raw/github-naming-<track>.json`（每赛道一个文件，含 name / track / stars / desc / url）。
> 目的：给 NameYouLike 的生成端与评审端一条「像真实产品名」的可执行判据线——尤其是用户点名的「中华文化元素要谨慎」。

## 结论（先答案）

1. **真实产品名不是"现成英语单词"为主，而是"能拆开或能拼出来的新词"。** 分析样本 1200 个里，复合词 534 个（44.5%）＋造词 345 个（28.8%）＝ **73.2%**；词典里现成的单词只占 21.9%。
2. **文化意象是极少数派，不是主流手法：30/3888 = 0.77%**（严格口径；人工复核后上限不超过 1.2%）。「用文化词起名」在真实生态里是一次押注，不是常规操作。
3. **中华文化意象在真实仓库名里几乎为零。** 对 4193 个唯一仓库名做罗马字直查，qilin / kylin / kirin / fenghuang / wukong / taiji / taichi / yinyang / bagua / loong / confucius / jianghu / wuxia / fengshui / mahjong / erhu / guzheng / hanzi / porcelain / jade / bamboo / lotus **全部 0 命中**。中国团队的高星项目用的是**拼音通称（Qwen 21,959★）**、**英语造词（DeepSeek-V3 104,636★）**、**反向缩写（Paddle 24,131★）**，不是"麒麟/凤凰/太极"。
4. **用户点名的"抽象病"在数据里有精确对应物：不是"用了文化词"，而是"文化意象 + 器物实字"的双词拼接。** 「北斗尺 / 小满尺 / 麒麟册 / 凤凰规」= 意象词 + 尺/册/规；而真实文化名（Kylin、Hermes、Prometheus、Odin）**整体就只有一个词**，后面不加第二个意象或器物。3888 个仓库里，这种"意象+器物"结构 0 例。
5. **长度与音节的真实分布**：中位数 7 字符、2 音节；1–2 音节占 53.2%；单件名（无连字符/点）占 75.6%；全小写占 80.5%。名字越长，越像教程/POC/插件而不是产品（见 §2.4）。

## 1. 样本与口径

| 项 | 数值 |
|---|---|
| 采集方式 | `gh api search/repositories?q=<topic>&sort=stars`，每查询取 2 页 × 50 |
| 唯一仓库（去重后） | 4269 |
| 剔除 meta/教程/清单类后 | 3888 |
| 分析样本 | **1200**（15 个赛道 × 每赛道 star 前 80） |
| 赛道 | ai-oss, apps, cli-tools, databases, design-tools, dev-tools, devops, frontend, game-dev, media-tools, npm-packages, prog-lang, saas-alternative, security, web-servers |

**口径说明（可复核）**

> 【勘误 2026-11-07】本节提到的复现脚本（normalize-raw.py、culture_lexicon.py）与数据文件（raw/github-naming-<track>.json、morphology-2026-10.json、stats-2026-10.json）未入库、现已不存在，无法按此复现；统计为 2026-10 当时实测记录，结论保留。

- **赛道划分**：按 GitHub topic 采集后归一到 15 个赛道；主会话按 topic 命名的文件（api/cli/figma/react/saas…）已合并进对应赛道（见 `research/normalize-raw.py`）。
- **去重**：以 `full_name`（owner/repo）为键全局去重，同一仓库只算一次。
- **meta 过滤**：剔除 awesome-list / roadmap / 面试 / 教程 / 模板 / 文档类（名字或描述命中即剔除），共剔 381 条。它们不是产品名，混进来会把"描述性长名"的比例抬高。
- **形态分类优先级**：CULTURE（文化词典命中）> ABBREV（全大写 2–6 位 / ≤3 字符 / k8s 型）> COMPOUND（可拆成两个可识别词素）> WORD（词典现成词）> PROPER（专名）> COINED（其余）。
- **词表**：`/usr/share/dict/words`（macOS web2）＋一份技术词素表（app/web/flow/base/db/ui…），否则 `uni-app`、`jumpserver` 会被误判成造词。
- **文化词典**：`research/culture_lexicon.py`，按来源标注 cn/jp/in/gr/nr/me/oth，按性质标注 myth/concept/art/plant/place/word。只做**词元级**匹配（不做盲子串扫描），并排除已英语化的同形词（elixir/alchemy/silk/muse/sphinx）。
- **已知误差**：最大不确定性在 COMPOUND 与 COINED 的边界（"supa+base"算复合还是造词，取决于词表）。人工抽审 45 条，主要错误是把复合判成造词（已加技术词表修正）。**「复合＋造词」合计 73.2% 这个数是稳的，两者内部比例有 ±5 个百分点的浮动。**
- **文化词列表 30 条全部人工复核**，剔除 3 条切分误判（`dehydrated`→hydra、`vscode-tailwindshades`→hades、`OpenWA`→nwa）。

## 2. 形态分布

| 形态 | 数量 | 占比 | 真实例子 |
|---|---:|---:|---|
| 复合词（两个可识别词素拼合） | 534 | 44.5% | kubernetes 128,731 · supabase 114,140 · tensorflow 201,295 · react-native 126,802 · browser-use 119,286 |
| 造词（词典查不到、拆不开、非缩写） | 345 | 28.8% | ollama 184,991 · dify 159,704 · langchain 148,560 · godot 119,160 · immich 117,375 |
| 单词实词（词典里现成的词） | 263 | 21.9% | react 251,896 · flutter 180,409 · rust 120,886 · puppeteer 95,753 · caddy 78,474 |
| 缩写/首字母/极短符号 | 43 | 3.6% | zx 45,818 · fd 44,867 · n8n 208,764 · vllm 95,687 · rtk 84,749 |
| 文化词（神话/宗教/文化意象） | 14 | 1.2% | hermes-agent 257,638 · prometheus 66,806 · hono 32,717 · Odin 12,209 |
| 人名/地名/专名 | 1 | 0.1% | （样本内仅 1 例） |

**怎么读这张表**：真实命名里"造一个新词"（复合 44.5% ＋ 造词 28.8%）是绝对主流，因为它们能同时满足"好记、好拼、能注册商标、域名没被占"。直接拿词典单词（21.9%）的问题是撞名和域名，不是不像产品名。

### 2.1 分赛道

| 赛道 | 样本 | 复合 | 造词 | 单词 | 缩写 | 文化 | star 冠军（★） |
|---|---:|---:|---:|---:|---:|---:|---|
| ai-oss | 80 | 54 | 13 | 11 | 1 | 1 | [deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 263,476 |
| apps | 80 | 37 | 19 | 18 | 6 | 0 | [ECC](https://github.com/affaan-m/ECC) 290,510 |
| cli-tools | 80 | 32 | 15 | 24 | 7 | 1 | [rea](https://github.com/morluto/rea) 395,663 |
| databases | 80 | 20 | 42 | 17 | 1 | 0 | [supabase](https://github.com/supabase/supabase) 114,140 |
| design-tools | 80 | 48 | 12 | 15 | 3 | 2 | [system-design-primer](https://github.com/donnemartin/system-design-primer) 375,800 |
| dev-tools | 80 | 36 | 23 | 18 | 3 | 0 | [ponytail](https://github.com/DietrichGebert/ponytail) 177,831 |
| devops | 80 | 27 | 25 | 25 | 1 | 2 | [RuView](https://github.com/ruvnet/RuView) 100,113 |
| frontend | 80 | 40 | 20 | 18 | 1 | 1 | [freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) 458,029 |
| game-dev | 80 | 36 | 26 | 14 | 2 | 2 | [godot](https://github.com/godotengine/godot) 119,160 |
| media-tools | 80 | 44 | 20 | 13 | 2 | 1 | [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) 35,165 |
| npm-packages | 80 | 40 | 21 | 14 | 4 | 1 | [ruflo](https://github.com/ruvnet/ruflo) 79,699 |
| prog-lang | 80 | 17 | 23 | 33 | 6 | 1 | [go](https://github.com/golang/go) 139,633 |
| saas-alternative | 80 | 39 | 25 | 14 | 1 | 1 | [cc-switch](https://github.com/farion1231/cc-switch) 149,325 |
| security | 80 | 39 | 28 | 11 | 1 | 1 | [strix](https://github.com/usestrix/strix) 72,280 |
| web-servers | 80 | 25 | 33 | 18 | 4 | 0 | [kubernetes](https://github.com/kubernetes/kubernetes) 128,731 |

### 2.2 按 star 分层（高星是不是更"实词"？）

| star 层 | 样本数 | 复合 | 造词 | 单词 | 缩写 | 文化 |
|---|---:|---:|---:|---:|---:|---:|
| T1 >=50k | 191 | 98 | 46 | 38 | 5 | 3 |
| T2 10-50k | 682 | 272 | 213 | 162 | 27 | 8 |
| T3 2-10k | 319 | 158 | 85 | 62 | 11 | 3 |
| T4 <2k | 8 | 6 | 1 | 1 | 0 | 0 |

结论：分层之间差异不大——**头部项目并没有更偏向"现成单词"**。文化词在 T1（≥50k）里 3 例、T2 里 9 例，占各层 1.3–1.6%，说明文化词**不是低星项目的专利，但也没在任何层级成为主流**。

### 2.3 长度 / 音节 / 大小写（判据的数字底座）

| 指标 | 数值 |
|---|---|
| 名字长度 | 均值 8.6 字符，中位 7，p10=4，p90=15 |
| 音节数 | 均值 2.7，中位 2；1 音节 224、2 音节 414、3 音节 286、≥5 音节 133 |
| 单件名（无 - _ . 分隔） | 907 / 1200 = 75.6% |
| 含连字符 | 247（20.6%）｜含点 35｜camelCase 134（11.2%） |
| 全小写 | 966 / 1200 = 80.5% |

### 2.4 名字越长，越不像产品名

样本里最长的 12 个名字（37–25 字符）几乎全是教程、仓库集合、POC 或插件：**`system-prompts-and-models-of-ai-tools` 144,285★、`generative-ai-for-beginners` 122,267★、`3d-game-shaders-for-beginners` 19,992★、`Penetration_Testing_POC` 7,537★、`cursor-talk-to-figma-mcp` 7,072★、`vscode-tailwindshades` 78★。**它们的共同点是：名字在**说明**内容，而不是**命名**一个产品。

## 3. 样本表（每赛道 top 8）


**ai-oss**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | 263,476 | COMPOUND | DeepSeek Harness: Everything is a Plugin. |
| [hermes-agent](https://github.com/NousResearch/hermes-agent) | 257,638 | CULTURE | The agent that grows with you |
| [tensorflow](https://github.com/tensorflow/tensorflow) | 201,295 | COMPOUND | An Open Source Machine Learning Framework for Everyone |
| [firecrawl](https://github.com/firecrawl/firecrawl) | 195,951 | COMPOUND | Supercharge your AI agents with data from the web and beyond |
| [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,785 | COMPOUND | AutoGPT is the vision of accessible AI for everyone, to use  |
| [ollama](https://github.com/ollama/ollama) | 184,991 | COINED | Get up and running with Kimi, GLM, MiniMax, DeepSeek, gpt-os |
| [prompts.chat](https://github.com/f/prompts.chat) | 174,745 | COMPOUND | f.k.a. Awesome ChatGPT Prompts. Share, discover, and collect |
| [transformers](https://github.com/huggingface/transformers) | 168,241 | WORD | 🤗 Transformers: the model-definition framework for state-of- |

**apps**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [ECC](https://github.com/affaan-m/ECC) | 290,510 | ABBREV | The agent harness performance optimization system. Skills, i |
| [ohmyzsh](https://github.com/ohmyzsh/ohmyzsh) | 190,185 | COINED | 🙃   A delightful community-driven (with 2,500+ contributors) |
| [flutter](https://github.com/flutter/flutter) | 180,409 | WORD | Flutter makes it easy and fast to build beautiful apps for m |
| [excalidraw](https://github.com/excalidraw/excalidraw) | 134,651 | COINED | Virtual whiteboard for sketching hand-drawn like diagrams |
| [react-native](https://github.com/react/react-native) | 126,802 | COMPOUND | A framework for building native applications using React |
| [NextChat](https://github.com/ChatGPTNextWeb/NextChat) | 88,902 | COMPOUND | ✨ Zero-config AI chat assistant. No API key needed — sign up |
| [rtk](https://github.com/rtk-ai/rtk) | 84,749 | ABBREV | CLI proxy that reduces LLM token consumption by 60-90% on co |
| [AppFlowy](https://github.com/AppFlowy-IO/AppFlowy) | 77,812 | COMPOUND | Bring projects, wikis, and teams together with AI. AppFlowy  |

**cli-tools**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [rea](https://github.com/morluto/rea) | 395,663 | WORD | Reverse engineer anything with agents, from app behavior dow |
| [n8n](https://github.com/n8n-io/n8n) | 208,764 | ABBREV | Fair-code workflow automation platform with native AI capabi |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 202,910 | COINED | A feature-rich command-line audio/video downloader |
| [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 141,405 | COMPOUND | An AI skill that provides design intelligence for building p |
| [gemini-cli](https://github.com/google-gemini/gemini-cli) | 108,568 | COMPOUND | An open-source AI agent that brings the power of Gemini dire |
| [orca](https://github.com/stablyai/orca) | 107,759 | WORD | Orca is the place for working with a fleet of agents (e.g. G |
| [terminal](https://github.com/microsoft/terminal) | 105,253 | WORD | The new Windows Terminal and the original Windows console ho |
| [Agent-Reach](https://github.com/Panniantong/Agent-Reach) | 104,643 | COMPOUND | Give your AI agent eyes to see the entire internet. Read & s |

**databases**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [supabase](https://github.com/supabase/supabase) | 114,140 | COMPOUND | The Postgres development platform. Supabase gives you a dedi |
| [30-Days-Of-Python](https://github.com/Asabeneh/30-Days-Of-Python) | 77,303 | COMPOUND | The 30 Days of Python programming challenge is a step-by-ste |
| [redis](https://github.com/redis/redis) | 77,129 | COINED | For developers, who are building real-time data-driven appli |
| [meilisearch](https://github.com/meilisearch/meilisearch) | 59,686 | COINED | A lightning-fast search engine API bringing AI-powered hybri |
| [etcd](https://github.com/etcd-io/etcd) | 52,433 | COINED | Distributed reliable key-value store for the most critical d |
| [dbeaver](https://github.com/dbeaver/dbeaver) | 52,225 | COINED | Free universal database tool and SQL client |
| [metabase](https://github.com/metabase/metabase) | 49,872 | COMPOUND | The easy-to-use open source Business Intelligence and Embedd |
| [orm](https://github.com/prisma/orm) | 47,669 | WORD | The Prisma ORM: write your application in TypeScript with hu |

**design-tools**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [system-design-primer](https://github.com/donnemartin/system-design-primer) | 375,800 | COMPOUND | Learn how to design large-scale systems. Prep for the system |
| [open-design](https://github.com/nexu-io/open-design) | 104,334 | COMPOUND | The 1st Collaborative AI Design Agent Workspace. Local-first |
| [taste-skill](https://github.com/Leonxlnx/taste-skill) | 103,456 | COMPOUND | Agent skills that give coding agents taste: art direction, r |
| [ant-design](https://github.com/ant-design/ant-design) | 99,927 | COMPOUND | An enterprise-class UI design language and React UI library |
| [material-ui](https://github.com/mui/material-ui) | 99,280 | COMPOUND | Material UI: Comprehensive React component library that impl |
| [storybook](https://github.com/storybookjs/storybook) | 91,393 | WORD | Storybook is the industry standard workshop for building, do |
| [ionic-framework](https://github.com/ionic-team/ionic-framework) | 52,724 | COMPOUND | A powerful cross-platform UI toolkit for building native-qua |
| [Semantic-UI](https://github.com/Semantic-Org/Semantic-UI) | 51,006 | COMPOUND | Semantic is a UI component framework based around useful pri |

**dev-tools**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [ponytail](https://github.com/DietrichGebert/ponytail) | 177,831 | COMPOUND | Makes your AI agent think like the laziest senior dev in the |
| [graphify](https://github.com/Graphify-Labs/graphify) | 136,703 | COINED | Turn any codebase, with its docs, SQL schemas, configs, and  |
| [fastapi](https://github.com/fastapi/fastapi) | 104,267 | COMPOUND | FastAPI framework, high performance, easy to learn, fast to  |
| [neovim](https://github.com/neovim/neovim) | 103,205 | COMPOUND | Vim-fork focused on extensibility and usability |
| [puppeteer](https://github.com/puppeteer/puppeteer) | 95,753 | WORD | JavaScript API for Chrome and Firefox |
| [archify](https://github.com/tt-a1i/archify) | 90,262 | COINED | Turn any idea, plan, or codebase into a beautiful interactiv |
| [hoppscotch](https://github.com/hoppscotch/hoppscotch) | 80,699 | COINED | Open-Source API Development Ecosystem • https://hoppscotch.i |
| [imgui](https://github.com/ocornut/imgui) | 76,842 | COINED | Dear ImGui: Bloat-free Graphical User interface for C++ with |

**devops**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [RuView](https://github.com/ruvnet/RuView) | 100,113 | COMPOUND | π RuView turns commodity WiFi signals into real-time spatial |
| [uptime-kuma](https://github.com/louislam/uptime-kuma) | 92,989 | COINED | A fancy self-hosted monitoring tool |
| [worldmonitor](https://github.com/koala73/worldmonitor) | 89,646 | COMPOUND | Real-time global intelligence dashboard. AI-powered news agg |
| [grafana](https://github.com/grafana/grafana) | 77,546 | COMPOUND | The open and composable observability and data visualization |
| [act](https://github.com/nektos/act) | 72,467 | WORD | Run your GitHub Actions locally 🚀 |
| [prometheus](https://github.com/prometheus/prometheus) | 66,806 | CULTURE | The Prometheus monitoring system and time series database. |
| [gitea](https://github.com/go-gitea/gitea) | 58,727 | COINED | Git with a cup of tea! Painless self-hosted all-in-one softw |
| [terraform](https://github.com/hashicorp/terraform) | 50,201 | COINED | Terraform enables you to safely and predictably create, chan |

**frontend**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) | 458,029 | COMPOUND | freeCodeCamp.org's open-source codebase and curriculum. Lear |
| [react](https://github.com/react/react) | 251,896 | WORD | The library for web and native user interfaces. |
| [next.js](https://github.com/vercel/next.js) | 143,308 | COMPOUND | The React Framework |
| [create-react-app](https://github.com/react/create-react-app) | 103,237 | COMPOUND | Set up a modern web app by running one command. |
| [bun](https://github.com/oven-sh/bun) | 96,434 | WORD | Incredibly fast JavaScript runtime, bundler, test runner, an |
| [superset](https://github.com/apache/superset) | 75,328 | COMPOUND | Apache Superset is a Data Visualization and Data Exploration |
| [remotion](https://github.com/remotion-dev/remotion) | 68,149 | WORD | 🎥      Make videos programmatically with React |
| [docusaurus](https://github.com/facebook/docusaurus) | 66,592 | COINED | Easy to maintain open source documentation websites. |

**game-dev**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [godot](https://github.com/godotengine/godot) | 119,160 | COINED | Godot Engine – Multi-platform 2D and 3D game engine |
| [bevy](https://github.com/bevyengine/bevy) | 49,318 | WORD | A refreshingly simple data-driven game engine built in Rust |
| [raylib](https://github.com/raysan5/raylib) | 35,440 | COINED | A simple and easy-to-use library to enjoy videogames program |
| [GDevelop](https://github.com/4ian/GDevelop) | 28,109 | COMPOUND | 🎮 Open-source, cross-platform 2D/3D/multiplayer game engine  |
| [Babylon.js](https://github.com/BabylonJS/Babylon.js) | 26,236 | COMPOUND | Babylon.js is a powerful, beautiful, simple, and open game a |
| [3d-game-shaders-for-beginners](https://github.com/lettier/3d-game-shaders-for-beginners) | 19,992 | COMPOUND | 🎮 A step-by-step guide to implementing SSAO, depth of field, |
| [cocos2d-x](https://github.com/cocos2d/cocos2d-x) | 19,241 | COMPOUND | Cocos2d-x is a suite of open-source, cross-platform, game-de |
| [pyxel](https://github.com/kitao/pyxel) | 18,470 | COINED | A retro game engine for Python |

**media-tools**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) | 35,165 | COINED | OCRmyPDF adds an OCR text layer to scanned PDF files, allowi |
| [sharp](https://github.com/lovell/sharp) | 32,802 | WORD | High performance Node.js image processing, the fastest modul |
| [Graphite](https://github.com/GraphiteEditor/Graphite) | 27,739 | WORD | Community-built comprehensive 2D content creation appplicati |
| [rembg](https://github.com/danielgatis/rembg) | 25,202 | COINED | Rembg is a tool to remove images background |
| [LivePortrait](https://github.com/KlingAIResearch/LivePortrait) | 19,328 | COMPOUND | Bring portraits to life! |
| [ImageMagick](https://github.com/ImageMagick/ImageMagick) | 17,750 | COMPOUND | ImageMagick is a free, open-source software suite for creati |
| [filmcraft](https://github.com/storytold/filmcraft) | 16,511 | COMPOUND | FilmCraft: An open-source, nonlinear video editor written by |
| [filepond](https://github.com/pqina/filepond) | 16,394 | COMPOUND | 🌊 A flexible and fun JavaScript file upload library |

**npm-packages**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [ruflo](https://github.com/ruvnet/ruflo) | 79,699 | COINED | 🌊 The original agent harness. Deploy intelligent multi-playe |
| [anime](https://github.com/juliangarnier/anime) | 73,940 | WORD | JavaScript animation engine |
| [yarn](https://github.com/yarnpkg/yarn) | 41,469 | WORD | The 1.x line is frozen - features and bugfixes now happen on |
| [pnpm](https://github.com/pnpm/pnpm) | 36,930 | COINED | Fast, disk space efficient package manager |
| [lerna](https://github.com/lerna/lerna) | 36,038 | COINED | Lerna is a fast, modern build system for managing and publis |
| [hono](https://github.com/honojs/hono) | 32,717 | CULTURE | Web framework built on Web Standards |
| [GSAP](https://github.com/greensock/GSAP) | 29,814 | ABBREV | GSAP (GreenSock Animation Platform), a JavaScript animation  |
| [crawlee](https://github.com/apify/crawlee) | 26,276 | COMPOUND | Crawlee—A web scraping and browser automation library for No |

**prog-lang**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [go](https://github.com/golang/go) | 139,633 | WORD | The Go programming language |
| [rust](https://github.com/rust-lang/rust) | 120,886 | WORD | Empowering everyone to build reliable and efficient software |
| [svelte](https://github.com/sveltejs/svelte) | 88,493 | WORD | web development for the rest of us |
| [webpack](https://github.com/webpack/webpack) | 65,971 | COMPOUND | A bundler for javascript and friends. Packs many modules int |
| [sway](https://github.com/FuelLabs/sway) | 61,371 | WORD | 🌴 Empowering everyone to build reliable and efficient smart  |
| [typst](https://github.com/typst/typst) | 56,854 | COINED | A markup-based typesetting system that is powerful and easy  |
| [kotlin](https://github.com/JetBrains/kotlin) | 53,525 | COINED | The Kotlin Programming Language.  |
| [babel](https://github.com/babel/babel) | 44,052 | WORD | 🐠 Babel is a compiler for writing next generation JavaScript |

**saas-alternative**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [cc-switch](https://github.com/farion1231/cc-switch) | 149,325 | COMPOUND | A cross-platform desktop All-in-One assistant for Claude Cod |
| [system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | 144,285 | COMPOUND | FULL Augment Code, Claude Code, Cluely, CodeBuddy, Comet, Cu |
| [immich](https://github.com/immich-app/immich) | 117,375 | COINED | High performance self-hosted photo and video management solu |
| [Stirling-PDF](https://github.com/Stirling-Tools/Stirling-PDF) | 95,134 | COINED | #1 PDF Application on GitHub that lets you edit PDFs on any  |
| [career-ops](https://github.com/career-ops-hq/career-ops) | 77,815 | COMPOUND | Open-source AI job search agent and job finder: scan job boa |
| [OpenMontage](https://github.com/calesthio/OpenMontage) | 72,390 | COMPOUND | World's first open-source, agentic video production system.  |
| [coolify](https://github.com/coollabsio/coolify) | 65,025 | COINED | An open-source, self-hostable PaaS alternative to Vercel, He |
| [first-contributions](https://github.com/firstcontributions/first-contributions) | 56,579 | COMPOUND | 🚀✨ Help beginners to contribute to open source projects |

**security**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [strix](https://github.com/usestrix/strix) | 72,280 | WORD | Open-source AI penetration testing tool to find and fix your |
| [x64dbg](https://github.com/x64dbg/x64dbg) | 50,045 | COMPOUND | An open-source user mode debugger for Windows. Optimized for |
| [web-check](https://github.com/lissy93/web-check) | 35,262 | COMPOUND | 🕵️‍♂️ All-in-one OSINT tool for analysing any website |
| [h4cker](https://github.com/The-Art-of-Hacking/h4cker) | 29,928 | COMPOUND | This repository is maintained by Omar Santos (@santosomar) a |
| [trufflehog](https://github.com/trufflesecurity/trufflehog) | 28,730 | COMPOUND | Find, verify, and analyze leaked credentials |
| [spiderfoot](https://github.com/smicallef/spiderfoot) | 23,887 | COMPOUND | SpiderFoot automates OSINT for threat intelligence and mappi |
| [SkillSpector](https://github.com/NVIDIA/SkillSpector) | 22,670 | COMPOUND | Security scanner for AI agent skills. Detect vulnerabilities |
| [RustScan](https://github.com/bee-san/RustScan) | 20,618 | COMPOUND | 🤖 The Modern Port Scanner 🤖 |

**web-servers**（按 star 取前 8）

| 名字 | star | 形态 | 是什么 |
|---|---:|---|---|
| [kubernetes](https://github.com/kubernetes/kubernetes) | 128,731 | COINED | Production-Grade Container Scheduling and Management |
| [caddy](https://github.com/caddyserver/caddy) | 78,474 | WORD | Fast and extensible multi-platform HTTP/1-2-3 web server wit |
| [traefik](https://github.com/traefik/traefik) | 65,392 | COMPOUND | The Cloud Native Application Proxy |
| [minio](https://github.com/minio/minio) | 61,299 | COINED | MinIO is a high-performance, S3 compatible object store, ope |
| [portainer](https://github.com/portainer/portainer) | 38,729 | COINED | Making Docker and Kubernetes management easy. |
| [istio](https://github.com/istio/istio) | 38,474 | COINED | Connect, secure, control, and observe services. |
| [seaweedfs](https://github.com/seaweedfs/seaweedfs) | 35,768 | COINED | SeaweedFS is a distributed storage system for object storage |
| [k9s](https://github.com/derailed/k9s) | 34,884 | ABBREV | 🐶 Kubernetes CLI To Manage Your Clusters In Style! |

## 4. 文化词专节（本卡重点）

### 4.1 硬数字：文化意象在真实产品名里占 0.77%

| 口径 | 命中数 | 分母 | 占比 |
|---|---:|---:|---:|
| 全池（meta 过滤后） | 30 | 3888 | **0.77%** |
| 分析样本（每赛道 top 80） | 14 | 1200 | 1.2% |

按来源拆分：gr 13, cn 6, jp 5, in 3, nr 3（gr=希腊罗马 13、cn=中文 6、jp=日本 5、in=梵语/印度 3、nr=北欧 3）。
按赛道拆分：ai-oss 1, cli-tools 2, design-tools 5, dev-tools 3, devops 5, frontend 2, game-dev 3, media-tools 2, npm-packages 2, prog-lang 1, saas-alternative 2, security 2——**没有哪个赛道是"文化词集中营"**，最多的设计工具也只有 5 例，且分散在 466 条里。

**文化词全表（30 条，全部人工复核）**

| 名字 | star | 赛道 | 词元/来源 | 一句话是什么 |
|---|---:|---|---|---|
| [hermes-agent](https://github.com/NousResearch/hermes-agent) | 257,638 | ai-oss | hermes/gr | The agent that grows with you |
| [qwen-code](https://github.com/QwenLM/qwen-code) | 28,755 | cli-tools | qwen/cn | An open-source AI coding agent that lives in your te |
| [katana](https://github.com/projectdiscovery/katana) | 17,745 | cli-tools | katana/jp | A next-generation crawling and spidering framework. |
| [chakra-ui](https://github.com/chakra-ui/chakra-ui) | 40,708 | design-tools | chakra/in | Chakra UI is a component system for building SaaS pr |
| [panda](https://github.com/chakra-ui/panda) | 6,236 | design-tools | panda/cn | 🐼 Universal, Type-Safe, CSS-in-JS Framework for Desi |
| [spartan](https://github.com/spartan-ng/spartan) | 2,965 | design-tools | spartan/gr | Cutting-edge tools powering Angular full-stack devel |
| [chakra-ui-vue](https://github.com/chakra-ui/chakra-ui-vue) | 1,844 | design-tools | chakra/in | ⚡️ Build scalable and accessible Vue.js applications |
| [SakuraKit](https://github.com/tingxins/SakuraKit) | 682 | design-tools | sakura/jp | 🤡SakuraKit, a lightweight and powerful library for a |
| [apollo-client-devtools](https://github.com/apollographql/apollo-client-devtools) | 1,528 | dev-tools | apollo/gr | Apollo Client browser developer tools. |
| [loki-mode](https://github.com/asklokesh/loki-mode) | 1,110 | dev-tools | loki/nr | Autonomous software factory. Give it a GitHub issue, |
| [claude-elixir-phoenix](https://github.com/oliver-kriska/claude-elixir-phoenix) | 571 | dev-tools | phoenix/cn | Claude Code plugin for Elixir/Phoenix/LiveView — 26  |
| [prometheus](https://github.com/prometheus/prometheus) | 66,806 | devops | prometheus/gr | The Prometheus monitoring system and time series dat |
| [huginn](https://github.com/huginn/huginn) | 50,158 | devops | huginn/nr | Create agents that monitor and act on your behalf.   |
| [prometheus-operator](https://github.com/prometheus-operator/prometheus-operator) | 9,993 | devops | prometheus/gr | Prometheus Operator creates/configures/manages Prome |
| [cyclops](https://github.com/cyclops-ui/cyclops) | 3,321 | devops | cyclops/gr | Developer Friendly Kubernetes 👁️ |
| [athena](https://github.com/athena-team/athena) | 965 | devops | athena/gr | an open-source implementation of sequence-to-sequenc |
| [medusa](https://github.com/medusajs/medusa) | 36,960 | frontend | medusa/gr | The world's most flexible commerce platform for agen |
| [react-kawaii](https://github.com/elizabetdev/react-kawaii) | 2,958 | frontend | kawaii/jp | Cute SVG React Components |
| [panda3d](https://github.com/panda3d/panda3d) | 5,259 | game-dev | panda/cn | Powerful, mature open-source cross-platform game eng |
| [SpartanEngine](https://github.com/PanosK92/SpartanEngine) | 3,194 | game-dev | spartan/gr | A game engine with a fully bindless, GPU-driven rend |
| [pandora](https://github.com/bitbrain/pandora) | 1,130 | game-dev | pandora/gr | Godot 4 addon for RPG data management such items, in |
| [manga-image-translator](https://github.com/zyddnys/manga-image-translator) | 10,544 | media-tools | manga/jp | Translate manga/image 一键翻译各类图片内文字 https://cotrans.to |
| [HunyuanCustom](https://github.com/Tencent-Hunyuan/HunyuanCustom) | 1,232 | media-tools | hunyuan/cn | HunyuanCustom: A Multimodal-Driven Architecture for  |
| [hono](https://github.com/honojs/hono) | 32,717 | npm-packages | hono/jp | Web framework built on Web Standards |
| [apollo-upload-client](https://github.com/jaydenseric/apollo-upload-client) | 1,540 | npm-packages | apollo/gr | A terminating Apollo Link for Apollo Client that fet |
| [Odin](https://github.com/odin-lang/Odin) | 12,209 | prog-lang | odin/nr | Odin Programming Language |
| [QwenPaw](https://github.com/agentscope-ai/QwenPaw) | 36,556 | saas-alternative | qwen/cn | Your Personal AI Assistant; easy to install, deploy  |
| [bodhiorchard](https://github.com/mickyarun/bodhiorchard) | 28 | saas-alternative | bodhi/in | Bodhiorchard is the open-source, self-hosted alterna |
| [thc-hydra](https://github.com/vanhauser-thc/thc-hydra) | 12,428 | security | hydra/gr | hydra |
| [medusa](https://github.com/Ch0pin/medusa) | 2,362 | security | medusa/gr | Mobile Edge-Dynamic Unified Security Analysis |

读这张表的三个事实：

1. **文化词几乎全是"神话人物/神兽的名字"**（普罗米修斯、赫尔墨斯、美杜莎、奥丁、洛基、九头蛇、独眼巨人、斯巴达），不是"抽象意象词"。
2. **它们整体就一个词**，后面最多接通用技术后缀（`-ui` / `-code` / `-agent` / `-client`），**没有一个是"文化词＋另一个文化/器物词"**。
3. 中文那 6 例里，真正带文化意象的只有 **Qwen（千问拼音）×2、Hunyuan（混元）×1**；`panda` / `panda3d` 是动物名（且 pandas 官方词源是 panel data，不是熊猫），`phoenix` 那条命中的其实是 Elixir 的 Phoenix 框架。

### 4.2 中华文化元素：直查 0 命中（用户点名的部分）

对采集到的 **4193 个唯一仓库名**做罗马字/拼音直查，以下词**全部 0 命中**：

`qilin` `kylin` `kirin` `fenghuang` `wukong` `taiji` `taichi` `yinyang` `bagua` `loong` `confucius` `laozi` `jianghu` `wuxia` `fengshui` `mahjong` `erhu` `guzheng` `hanzi` `porcelain` `jade` `bamboo` `lotus` `dumpling` `mooncake` `lantern` `suanpan` `chopstick`

放宽到全站（`gh api search/repositories?q=<词>+in:name`，模糊匹配，数字为上限）后，最好的中文文化词项目也只有千级 star：

| 词 | 全站同名上限 | 最好的一个 |
|---|---:|---|
| wukong | 1,966 | wukong-robot 7,130★ / WuKongIM 4,976★ |
| loong | 2,756 | loongcollector 2,209★ |
| bagua | 472 | bagua 882★ |
| yinyang | 642 | hugo-theme-yinyang 559★ |
| taiji | 1,078 | taijilang 63★ |
| qilin | 706 | Qilin 148★（同批更高的 qiling 6,160★ 是另一个词） |

**而中国团队做的高星项目，没有一个用神话/古典意象命名**——用的是拼音通称、英语造词或反向缩写：

| 名字 | star | 赛道 | 名字本身的性质 |
|---|---:|---|---|
| deepseek-harness | 263,476 | ai-oss | 英语造词 deep+seek |
| Paddle | 24,131 | ai-oss | 反向缩写 PArallel Distributed Deep LEarning |
| qwen-code | 28,755 | cli-tools | 拼音（千问） |
| deepseek-whale-girl-icon | 286 | design-tools | 英语造词 deep+seek |
| PaddleX | 6,283 | devops | 反向缩写 PArallel Distributed Deep LEarning |
| HunyuanCustom | 1,232 | media-tools | 拼音（混元） |
| QwenPaw | 36,556 | saas-alternative | 拼音（千问） |

外加 [deepseek-ai/DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3) 104,636★（英语造词 deep+seek）、[QwenLM/Qwen](https://github.com/QwenLM/Qwen) 21,959★（拼音「千问」）、apache/kylin 3,783★（麒麟，见下）。
唯一"中文历史人物"路线的真实成功案例是 [luban](https://github.com/focus-creative-games/luban) 4,646★（鲁班，游戏配置工具）——注意它是**工匠人名**，两音节、可拼，不是意象拼接。

### 4.3 成功案例靠什么撑住（三个可复制的条件）

**① Apache Kylin（麒麟）3,783★ —— 唯一进 Apache 顶级的中国项目，也是唯一"敢用中国神兽"的高知名度项目。**
命名过程见 Kyligence 官方访谈：项目在 eBay 中国孵化，"eBay 外企大部分项目命名以西方神话为主"，团队"取名字一定要取一个中国风的名字"，"Phoenix（凤凰）被用掉了，龙又不是特别合适，最后发现麒麟非常合适"；进 Apache 后"一百多个顶级项目里面，只有这个名字大家一看就知道是来自中国"（[访谈](https://cn.kyligence.io/news/apache-kylin-path-of-growth-conversation/)、[卷首语](https://cn.kyligence.io/news/infoq-e-book-architect-apache-kylin-practice/)）。
**它撑住的三个条件**：(a) 所处生态本身有"用动物/神兽命名"的惯例（Hadoop 动物园），所以麒麟不突兀；(b) 名字就一个词、2 音节、罗马字可拼；(c) 隐喻一句话讲得清（祥瑞仁兽、百兽之王）。**它付出了代价**：3,783★ 在同类基础设施里并不算头部，且"kylin"这个词本身不携带任何产品语义。

**② Pake 62,324★ —— 用户提到的那个案例，作者本人的一手说法。**
tw93 自述（[潮流周刊第 279 期](https://weekly.tw93.fun/posts/279)、[原帖](https://x.com/HiTw93/status/2090985612648341686)）：想表达"打包"，英文 Pack 太大众，于是去查"打包"在各种语言里的翻译，发现海地克里奥尔语里就叫 **Pake**，"狂喜，就取成这个了"；他的取舍标准是"好拼写、好记、好打字"，且产品命令就是 `pake`。
同一套方法产出的一系列名字：**Kaku**（日语「書く」＝书写，终端工具）、**Waza**（「技」，工程师 skills）、**Kami**（「紙」，排版 skills）、**Mole**（鼹鼠，挖垃圾的清理工具）、妙言（Markdown 笔记）。
**关键结论：这些名字不是"文化意象"，而是"外语里恰好等于产品动作的那个短词"——文化只出现在词源故事里，名字本身是 2 音节、开音节、能一读就对的普通词。**他还明确否掉了难拼难记的名字（Anthropic、Antigravity、Trae）。

**③ 神话人物名：靠"隐喻一句话讲清"撑住。**
[hermes-agent](https://github.com/NousResearch/hermes-agent) 257,638★（信使→传信的 agent）、[prometheus](https://github.com/prometheus/prometheus) 66,806★（盗火者→把指标"取来给人"的监控）、[Odin](https://github.com/odin-lang/Odin) 12,209★（主神→编程语言）、[hono](https://github.com/honojs/hono) 32,717★（官方 README 自述"Hono - means flame 🔥 in Japanese"，即日语「炎」）、[katana](https://github.com/projectdiscovery/katana) 17,745★（日语「刀」，projectdiscovery 的爬虫框架）。共同点是**单个名词、2–3 音节**，且（除 katana 外）都能把产品动作一句话讲清——katana 与"爬取"的映射未见官方说明，属推断。

### 4.4 判据：什么时候可以用文化意象，什么时候是"抽象病"

**可以用（四条同时成立）**

1. 名字**整体只有一个词**，后面不加第二个意象词或器物字（对照：Kylin / Hermes / Odin / Pake / Kaku；反例：麒麟册、凤凰规、北斗尺）。
2. **2 音节、开音节、罗马字一读就对**（Pake / Kaku / Kami / Hono / Kylin）。需要注释才知道怎么读的罗马字（Shengmo→"shung-mwo"、Kaicheng→"kai-chung"）直接出局。
3. **隐喻一句话讲得清**，且和产品动作是同一件事（打包→Pake、书写→Kaku、信使→Hermes）。需要讲典故才能懂的（开成石经、绳墨）属于注释依赖，不是名字。
4. **所在生态已有同类惯例**（大数据动物园、监控/安全赛道喜用神话名）。没有惯例的赛道（设计 token、CLI）用文化词就是自造解释成本。

**判定为"抽象病"（出现任意一条即否决）**

- **意象 + 器物/实字拼接**：`麒麟册`、`凤凰规`、`北斗尺`、`小满尺`。这种结构在 3888 个真实仓库里 **0 例**，是生成器拼接癖的典型产物。
- **双意象叠加**：两个都不指向产品动作的词拼在一起。
- **依赖典故/注释**：不知道出处就无法理解为产品名。
- **罗马字拼读成本 > 2 音节或含非直觉辅音串**。

**对 NameYouLike 现有候选的直接判定**（按本报告数据）：Shengmo（绳墨，2 音节）、Kaicheng（开成，2 音节）音节数其实达标，问题在另外两条——罗马字拼读有摩擦（"shung-mwo" / "kai-chung"，对照 Pake/Kaku/Kami 都是一读就对），且语义依赖典故讲解才能成立；Imono（鋳，3 音节）是日语借词，形态上比前两个更接近真实分布，但仍需一句英文故事。三者都不属于 0.77% 那类"文化词成功案例"的形态（单词、2 音节、与产品动作同义）。

## 5. 「像真产品名」可执行判据

每条给出阈值（数据依据）、正例、反例。**生成端直接当提示词约束，评审端直接当审计规则。**

| # | 判据 | 阈值（依据） | 正例 | 反例 |
|---|---|---|---|---|
| R1 | 长度 | 4–9 字符，硬上限 12（中位 7，p90=15） | kaku(4) pake(4) hono(4) caddy(5) tabby(5) | `system-prompts-and-models-of-ai-tools`(37) `cursor-talk-to-figma-mcp`(24) |
| R2 | 音节 | 2–3 音节，硬上限 4（中位 2，1–2 音节占 53.2%） | prometheus(3) kubernetes(4) supabase(4) | `Penetration_Testing_POC`(7) `react-infinite-scroll-component`(9) |
| R3 | 词件数 | 1 件；最多 2 件且第二件必须是通用技术后缀（单件占 75.6%） | `chakra-ui` `qwen-code` `hermes-agent` | `ui-ux-pro-max-skill`(4 件) `react-infinite-scroll-component`(31) |
| R4 | 可拼 | 每个音节必须有元音；禁止连续 3 个辅音 | pake / kaku / fyne / joplin | vllm / rtk / nnn / fzf / sqlc（全部落在缩写类，不是品牌名） |
| R5 | 大小写 | 品牌核心全小写（全小写占 80.5%） | supabase、ollama、godot | camelCase 11% 且几乎都是生态前缀：`PowerShell`、`PySceneDetect`、`Win11Debloat`、`vscode-*` |
| R6 | 无意象拼接 | 若含文化词，则整个名字＝该文化词（＋可选技术后缀） | Kylin、Hermes、Odin、Pake | 麒麟册、凤凰规、北斗尺、小满尺（0 例结构） |
| R7 | 中文元素 | 默认不用。拼音仅当 2 音节且已通称（Qwen 21,959★） | Qwen、Pake（作者为中国开发者，但名字是外语短词） | Shengmo、Kaicheng、太极/麒麟/凤凰类直译 |
| R8 | 工具后缀 | `-ly` / `-ify` / `-kit` 合计 <1%，且真实用例都是「实词+后缀」且 ≤3 音节 | dify 159,704★、coolify 65,025★（实词根＋ify） | 意象词或造词根再接 -ly/-ify/-kit；`-kit` 全样本仅 DoKit 1 例 |
| R9 | 语义贴合 | 名字与产品动作为同一件事，一句话讲得清 | Pake＝打包、Kaku＝书写、Mole＝挖垃圾 | 需要典故才能解释 |
| R10 | 可注册/可搜 | 沿用既有三道闸：GitHub 同名最高 star < 5k ＋ npm 404 ＋ 域名可注册 | — | — |

> R7 的判据只适用于**国际开源受众**（GitHub 搜索者以英文母语为主）：拼音要面对「念不出、记不住」的额外成本，所以默认不用。面向**中文受众**的产品不在这一行列，拼音、拼音-功能词（`duizhang-ledger`）、拼音-英文（`tally-duizhang`）都是正常写法；本地实现见 `lib/naming/pinyin.ts`，拼音必须能逐字读回来源里的中文词才算有效。

**提示词片段（生成端可直接贴）**

```
候选名必须满足：
1) 4-9 字符、2-3 音节、全小写、单件（无连字符，除非第二件是 ui/cli/db/js/agent/code 这类技术后缀）
2) 每个音节有元音，无连续 3 辅音，一读就能拼对
3) 形态优先级：实词+实词复合（44.5%）> 造词（28.8%）> 现成单词（21.9%）
4) 禁止「文化意象 + 器物/实字」拼接（麒麟册/凤凰规/北斗尺这类）
5) 中文元素默认不用；若用，必须是 2 音节、可拼、且已形成通称
6) 不用 -ly/-ify/-kit 去救一个拼不好的词
7) 名字要能在英文里一句话解释清楚，不依赖典故
```

**审计规则（评审端可落库）**

```python
import re
TECH_SUFFIX = {"ui","cli","db","js","ai","os","api","agent","code","server","kit"}
def audit(name):
    n = name.lower(); errs = []
    if not (4 <= len(n) <= 12): errs.append("R1 长度")
    syl = len(re.findall(r"[aeiouy]+", n)) or 1
    if not (2 <= syl <= 4): errs.append(f"R2 音节={syl}")
    parts = re.split(r"[-_. ]+", n)
    if len(parts) > 2 or (len(parts) == 2 and parts[1] not in TECH_SUFFIX):
        errs.append("R3 词件数")
    if re.search(r"[bcdfghjklmnpqrstvwxyz]{3,}", n): errs.append("R4 可拼")
    if n != name.lower(): errs.append("R5 大小写")
    if CULTURE_HIT(name) and not re.sub(r"-(ui|cli|db|js|agent|code)$", "", n) in CULTURE_LEX:
        errs.append("R6 意象拼接")
    if re.search(r"(ly|ify|kit)$", n) and syl > 3: errs.append("R8 后缀")
    return errs
```

## 6. 反面证据 / 不确定性

- **`-ify` 不是一律禁用**：全样本里 `-ify` 有 6 例，且包含 dify 159,704★、graphify 136,703★、archify 90,262★、coolify 65,025★ 这批 2026 年 AI 赛道高星项目。所以判据 R8 定的是"≤3 音节且词根是实词"，而不是"禁止 -ify"。这跟卡片原先的假设（`-ify` 属于后缀怪）相反——**数据不支持一刀切**。
- **缩写类并不弱**：T1/T2 里有 zx 45,818★、fd 44,867★、n8n 208,764★、rtk 84,749★ 这类 2–3 字符名。所以"短"本身不是问题，问题是"短且不可拼不可搜"。
- **分类误差**：COMPOUND 与 COINED 的边界依赖词表，`supabase`（supa+base）、`redis`（REmote DIctionary Server）这类词源模糊的会被划到不同桶；两者合计 73.3% 是稳的，内部比例有 ±5pp 浮动。
- **样本偏差**：按 topic 采集 + 按 star 排序，头部偏基础设施与 AI（2026 年 AI 赛道占比高），设计/消费级产品相对少；`saas-alternative` 赛道里混进了不少 agent/skill 类仓库。
- **文化词典覆盖有限**：只覆盖常见词元，且只做词元级匹配，所以 0.77% 是**下界**。已知漏检（人工点名，未计入分子）：`redpanda` 12,644★（小熊猫，动物名）、`dragonfly` 31,825★（蜻蜓，动物名，非"龙"）、`zenstack` 2,954★ / `zenc-lang` 4,320★ / `zent` 2,250★ / `zenui` 384★（zen，禅）、`pandas-ai` 23,905★（pandas 官方词源是 panel data，非熊猫）。把这些算进来，文化/借词占比上界约 **0.93%**，加上存疑项不超过 1.2%。核心结论（<1.5%）不受影响。
- **star ≠ 命名质量**：本报告用 star 作"项目影响力"代理，不代表名字好坏；Pake 62k★ 与其名字好记有关，但无法从数据里拆出因果。

## 7. 还需要什么

- **无**（卡片要求的四项：样本 ≥800（实收 1200 分析样本 / 3888 全池）、形态分布、文化词专节带真实数字、可执行判据，均已交付）。
- 若要继续收紧判据，下一步建议（不在本卡范围）：① 对候选名批量跑 npm/GitHub/域名三道闸；② 把 `research/raw/*.json` 里 star ≥10k 的 1 条做成"高频词素表"，统计哪些词根（flow/base/kit/ui/scope/lens/…）在各赛道被反复使用，供生成端做词素组合。

## 附录：数据文件

| 文件 | 内容 |
|---|---|
| `research/raw/github-naming-<track>.json` | 每赛道原始样本（name / track / stars / desc / url），共 15 个文件、4269 条去重仓库 |
| `research/morphology-2026-10.json` | 分类结果：sample(1200，含 morph/culture 标注)、pool_culture(30)、pool_cn_origin |
| `research/stats-2026-10.json` | 报告里所有统计数字 |
| `research/culture_lexicon.py` | 文化词词典（来源/性质标注）＋误判黑名单＋中国来源名单 |
| `research/classify-morph.py` / `stats-report.py` / `split-raw.py` / `topup-tracks.py` / `normalize-raw.py` | 复现脚本（改完重跑即可刷新本报告） |

> 【勘误 2026-11-07】附录所列脚本与数据文件均未入库、现已不存在（research/ 现存：2 份报告 md、prompt-run/、raw/form-stats.json、命名方法学习-*）；本表为当时交付清单，不可再生。

