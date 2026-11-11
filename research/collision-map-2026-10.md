# 撞名与域名雷区图：设计工具赛道（2026-10）

> 交付日期：2026-10-26。用途：**候选池过滤器**——新候选名先过 §1 雷区清单，再过 §2 黑名单，域名成本按 §3 行情判断。
> 数据快照：GitHub 搜索 3 组（2026-10-26，`gh search repos`，并集 108 仓库，原始数据 `research/raw/gh-*.json`）；Cloudflare 注册局成本价快照（cfdomainpricing.com/prices.json，2026-10 更新）；Porkbun/Namecheap 官网价（Google 索引快照，2026-10 在售价）。
> 汇率假设：$1 ≈ ¥7.12；预算口径 ¥240/年 ≈ $34/年。价格为非溢价（non-premium）域名价格，含 ICANN 费。
>
> 【勘误 2026-11-07】快照所引原始数据 research/raw/gh-*.json、gh-dt-topic50.json 未入库、现已不可核；正文表格为当时实测记录，以正文为准。

## 结论

1. **赛道三大词根全部阵亡**：`design`（108 仓库样本中出现 36 次，33%）、`system`（11 次）、`token`（12 次）、`style`（5 次）被 Style Dictionary、Tokens Studio、Specify、Supernova、styled-system、stylelint 等头部产品焊死。任何以这三类词做主词根的名字都是死名或高危近名。
2. **最大的时效警报**：「给 AI 代理用的设计规范」这个定位的名字正在 2026 年被疯狂抢注——`awesome-design-md`（2026-03 建仓，7 个月 12.4 万星）、`design-extract`（2026-04，4.4 千星）、`design-dna`（2026-03，2 千星）、`dembrandt`（2025-11，3.8 千星）。定位与本项目几乎相同的名字正在被大流量项目占掉，**候选名确定后必须立即查重注册**。
3. **域名：预算内唯一行业正确的后缀是 `.dev`**（Porkbun 常价 $12.87/年 ≈ ¥92，Cloudflare 续费 $12.2 ≈ ¥87；web.dev、go.dev、stripe.dev、github.dev 等先例丰沛）。`.design` 续费 $46.86 ≈ ¥334/年，超预算 39%（核实结论：任务书所引 "$35-50/yr" 落在区间上沿，实际 ~$45-50）。`.io`/`.sh`/`.so` 全部超预算。`.moe`/`.cc`/`.wtf` 便宜但气质与开发者工具错位。
4. **`.so` 的旗舰先例刚跑路**：Notion 于 2026-06-03 完成迁移到 notion.com，`notion.so` 变 307 跳转——最著名的 .so 域名黑客案例最终买回 .com，这是 ccTLD 品牌黑客路线最直接的警示。

---

## 一、赛道撞名雷区清单

判定分级：
- **死**：同赛道同名或主词根相同——候选名命中即弃。
- **高危**：同赛道近名（共享主词根、仅前后缀不同、谐音、缩写）——默认弃，除非产品定位刻意区分且法务可接受。
- **记录**：跨赛道同名——不弃，留档供顺带排查。

### 1.1 「死」：同赛道同名/同词根（任务书点名产品 + GitHub 样本头部仓库）

| 名字 | 赛道位置 | 证据 | 状态 |
|---|---|---|---|
| Style Dictionary | 设计 token 构建系统，事实标准（Amazon 开源） | styledictionary.com · [style-dictionary/style-dictionary](https://github.com/style-dictionary/style-dictionary) ★4,869 | 死 |
| Design Tokens / DTCG | 行业术语本身（W3C 社区组格式） | [design-tokens/community-group](https://github.com/design-tokens/community-group) ★2,156 | 术语，禁作品牌 |
| Tokens Studio（Studio + Figma 插件） | token 管理平台 | tokens.studio · [tokens-studio/figma-plugin](https://github.com/tokens-studio/figma-plugin) ★1,628 | 死 |
| Specify | design token 同步/分发平台 | specifyapp.com | 死 |
| Supernova | design system 管理 + MCP 代理分发 | supernova.io（官网明说 "agents... served over MCP"） | 死，且是**最直接竞品** |
| Backlight | design system 在线构建平台 | backlight.dev | 死 |
| Zeplin | design delivery 平台（已带 MCP server） | zeplin.io | 死 |
| Figma Variables | Figma 官方 token 实现机制 | help.figma.com《Guide to variables》 | 术语，禁作品牌 |
| Tailwind / Tailwind CSS | 原子化 CSS 框架 | tailwindcss.com | 死 |
| Panda CSS | CSS-in-JS 设计系统框架 | panda-css.com · [chakra-ui/panda](https://github.com/chakra-ui/panda) ★6,235 | 死 |
| Stylelint | CSS linter | stylelint.io ★9k+ | 死 |
| Storybook | 组件工作坊/文档标准 | storybook.js.org ★91,379 | 死 |
| Theme UI | 主题化 styled API | [system-ui/theme-ui](https://github.com/system-ui/theme-ui) ★5,409 | 死 |
| styled-system | 响应式样式工具 | [styled-system/styled-system](https://github.com/styled-system/styled-system) ★7,860 | 死 |
| Theo | token 转换器（Salesforce，已归档但名字仍占） | [salesforce-ux/theo](https://github.com/salesforce-ux/theo) ★1,989（archived） | 死 |
| Diez | 跨平台设计 token 工具包 | [diez/diez](https://github.com/diez/diez) ★1,238 | 死 |
| Figmagic | Figma→token 代码生成 | [mikaelvesavuori/figmagic](https://github.com/mikaelvesavuori/figmagic) ★864 | 死 |
| Primer Primitives | GitHub 设计系统 token 层 | [primer/primitives](https://github.com/primer/primitives) ★416 | 死 |
| HashiCorp Design System | 企业设计系统 | [hashicorp/design-system](https://github.com/hashicorp/design-system) ★518 | 死 |
| dembrandt | 品牌 token 分发（2025-11 建仓） | [dembrandt/dembrandt](https://github.com/dembrandt/dembrandt) ★3,841 | 死，定位几乎相同 |
| Supernova Portal / Token Flow 等 | 上述产品的子功能名 | supernova.io、documentation.tokens.studio | 记录：子命名空间也被占 |
| Polaris / Vitamin / Atomium | Shopify、Decathlon、juntossomosmais 的设计系统 | research/raw/gh-dt-topic50.json | 死（企业内部系统名） |

> 本节为「这个名字已死」清单正文；108 仓库**全量名单**见附录 A。

### 1.2 「高危」：同赛道近名（词根重叠/构式近似）

| 近名构式 | 样本内实例 | 为什么高危 |
|---|---|---|
| `token*` 任意组合 | material-tokens、polaris-tokens、ColorTokensKit-Swift、storybook-design-token、postcss-design-token-utils、token-weaver、TokenParser、design-tokens-utils | token 词根被工具链用尽；`tokenX` 一律撞 |
| `style*` 任意组合 | style-dictionary(-utils)、styled-system、stylekit（★673）、styleseed（2026-04，★989） | `styleX` 同上 |
| `design + 名词` 构式 | design-dna、design-extract、design-md、design-codex、design-taste、design.how、design-system(-ops/-utils)、oh-my-design、better-design、anydesign、open-design、pre-design-md | 样本中 36/108 含 design；该构式是赛道默认构词法，等于没起名 |
| `X-dna` | design-dna（2026-03，★2,038）、engramma 之外的 dna 系 | `dna` 已被抢且与任务书姊妹卡主题撞车 |
| `awesome-*` | awesome-design-md、Awesome-Design-Tokens、awesome-design-systems、Awesome-Design-Tools 等 7 个 | awesome 前缀专属于榜单（awesome-list 惯例），品牌用它=自降为清单 |
| `oh-my-*` | oh-my-design、oh-my-palette 系（oh-my-zsh 模板） | 玩梗模板已烂大街 |
| `*-md` | awesome-design-md、official-design-md、pre-design-md、design-md 系（2026 新潮） | 2026 年 AI 代理潮的新烂大街后缀，见 §1.3 |
| `*-kit` | stylekit、ColorTokensKit | -kit 是任务书点名后缀；样本内外都在用 |
| `*-primitives` / `*-variables` | primer/primitives、theme-specification、Figma Variables | 与行业标准词汇撞车 |

### 1.3 时效警报：AI 代理潮正在抢名（2026 年新仓库）

| 仓库 | 创建时间 | 星标 | 说明 |
|---|---|---|---|
| VoltAgent/awesome-design-md | 2026-03-31 | ★123,598（7 个月） | 「设计规范 md 分发给 AI 代理」榜单，流量爆炸 |
| Manavarya09/design-extract | 2026-04-15 | ★4,378 | 从设计稿提取规范 |
| zanwei/design-dna | 2026-03-23 | ★2,038 | 与本项目定位字面重合 |
| plugin87/ux-ui-agent-skills | 2026-03-16 | ★3,019 | AI 代理的 UX/UI 技能包 |
| bitjaru/styleseed | 2026-04-07 | ★989 | token/样式起点 |
| dembrandt/dembrandt | 2025-11-22 | ★3,841 | 品牌分发，定位几乎相同 |

（创建时间/星标取自 2026-10-26 `gh api repos/<name>` 实测。）

**推断**：本项目目标定位（设计规范/token 分发库、AI 代理为主要消费方）正是这批 2026 年项目在抢的空间。命名上意味着两件事：① 候选名一旦入围要立即查 GitHub/域名并注册占位；② 「design+名词」「X-md」「X-dna」这类一眼像该赛道默认构词的名字，不仅撞名风险高，而且会淹没在同名新项目里——这正是用户「设计了跟没设计一样」抱怨的另一种形态。

### 1.4 「记录」：跨赛道同名（留档，不否决）

| 名字 | 赛道 | 备注 |
|---|---|---|
| Notion | 协作文档 | 2026-06-03 从 notion.so 迁至 notion.com（见 §3.2 .so 行） |
| Atomium | 比利时原子塔/juntossomosmais 设计系统 | 样本内 |
| Tinte / Huetone / Pinceau | 配色与样式工具（样本内 ★625/★456/★690） | 非英语词根，冲突面小，但属同赛道非头部 |
| Engramma | [TrySound/engramma](https://github.com/TrySound/engramma) ★197 | 同赛道小项目 |
| Supernova | 天文/游戏等跨行业大量使用 | 同名主要看赛道，本赛道已被占（§1.1） |

### 1.5 过滤规则（直接给候选池用）

1. 候选名精确命中 §1.1 或 §1.2 任一实例 → **弃**。
2. 候选名含 `token`/`style`/`design`/`theme` 主词根，或以 §2 A 类后缀收尾 → **弃**。
3. 候选名与 §1.1 任一名字仅差前后缀/单复数/连字符 → **弃**。
4. 候选名在 GitHub 无同名仓库、无同名 npm 包、目标域名可注册 → 保留，进黑名单 §2 复查。

---

## 二、命名模板黑名单（词根/后缀级）

### 2.1 统计口径

样本 = `gh search repos --topic=design-tokens top50` + `gh search repos "design token" top30` + `--topic=design-systems top40` 的**并集 108 个仓库**（去重后），对仓库名做分词统计。原始数据与逐仓库表见 `research/raw/gh-*.json` 与附录 A。

### 2.2 GitHub 样本实证词频（top 20）

| 词根 | 出现仓库数 | 占比 | 圈内实例 |
|---|---|---|---|
| design | 36 | 33% | design-tokens、design-system、design-dna、oh-my-design… |
| system | 11 | 10% | design-system(-ops/-utils)、unity-ui-toolkit-design-system |
| token(s) | 12 | 11% | design-tokens、material-tokens、polaris-tokens |
| ui | 8 | 7% | unity-ui-toolkit、ux-ui-agent-skills、css.gui |
| style | 5 | 5% | style-dictionary、styled-system、stylekit、styleseed |
| awesome | 7 | 6% | 榜单专用 |
| md | 5 | 5% | 2026 AI 代理潮新贵 |
| figma | 4 | 4% | figmagic、figma-tokens 系 |
| theme | 3 | 3% | theme-ui、theme-specification |
| utils | 3 | 3% | design-system-utils、style-dictionary-utils |
| starter | 2 | 2% | starter-kit 类仓库 |
| primitives | 2 | 2% | primer/primitives |
| react / ios / css | 各 2-3 | — | 平台限定词 |

**样本内为 0 但需单列的后缀**（重要）：`-ly`、`-ify`、`-base`、`lab(s)` 在 108 个仓库名中**一次都没出现**——这些不是 GitHub 开源圈的模板，而是泛互联网 SaaS 的命名俗套。它们照样该进黑名单，但证据性质不同：前者是「圈内实证泛滥」，后者是「圈外俗套、圈内低频」，列入 B 类并标注。

### 2.3 A 类：硬禁（命中即弃）

| 词根/构式 | 证据 | 原因 |
|---|---|---|
| `design*` 作主词 | 36/108 | 赛道默认构词法，等于没起名（任务书原话「设计了跟没设计一样」） |
| `token*` 作主词 | 12/108 + 圈外无数 | 被 Style Dictionary 生态用尽 |
| `style*` 作主词 | 5/108 | styled-system/stylelint/stylekit 全占 |
| `system` 收尾 | 11/108 | design-system 是品类名不是品牌名 |
| `theme*` | 3/108 + Theme UI | 词义被 Theme UI 占据 |
| `-kit` | stylekit、ColorTokensKit | 任务书点名；工具箱俗套 |
| `-utils` / `-tools` | 5/108 | 工具集合命名，无品牌力 |
| `awesome-` | 7/108 | 榜单专属前缀 |
| `oh-my-` | 样本 2 个 + oh-my-zsh 文化 | 玩梗模板已烂 |
| `-starter` / `boilerplate` | 样本 2+ | 模板仓库命名 |
| `figma*` | 4/108 | 第三方平台名，商标风险 |

### 2.4 B 类：高危（圈内低频但泛互联网 SaaS 俗套 / 新兴泛滥）

| 词根/构式 | 证据边界 | 原因 |
|---|---|---|
| `-ly` | GitHub 样本 0，SaaS 圈泛滥（泛互联网常识） | SaaS 起名第一俗套 |
| `-ify` | 同上 | 同上 |
| `-base` | GitHub 样本 0，数据库/SaaS 常用 | 同上 |
| `lab(s)` | GitHub 样本 0，公司部门名常用 | 无产品感 |
| `-craft` | 样本 1 | 任务书点名；手作人俗套 |
| `-md` | 5/108 且全部 2026 新仓 | AI 代理潮新滥后缀，用=追热点 |
| `-dna` | design-dna（2026-03） | 已被抢注且是姊妹卡主题词 |
| `-primitives` / `-variables` | 2/108 + Figma 官方词汇 | 与 DTCG/Figma 术语撞车 |
| `-X for AI` / `*-agents` / `*-skills` | ux-ui-agent-skills、designer-skills、refactoring-ui-skill | 2026 抢注潮构式 |
| `-spec` / `-codex` | design-codex、theme-specification、pre-design-md | spec 类词已有强关联产品（Codex 系） |

### 2.5 C 类：过气或气质错位

| 构式 | 原因 |
|---|---|
| `-js` 后缀 | 框架专用（非 JS 库强行 -js 显得蹭） |
| `-flow` / `-stack` / `-hub` | 上一代 SaaS 俗套 |
| `get-` / `try-` 前缀 | 营销跳转域习惯，可作域名不作品牌 |

### 2.6 D 类：用户已点名淘汰

`datum`、`typecase`、`measure-twice` 及整个抽象黑话系（任务书指定淘汰）——与上表不同，这是用户口味否决，不是撞名否决，但生成器同样先过滤。

---

## 三、域名后缀行情（2026-10）

### 3.1 价格总表

CF = Cloudflare Registrar 批发成本价（cfdomainpricing.com/prices.json，2026-10 快照）；PB = Porkbun（官网价快照：促销首年 / 常价；Porkbun 常价=续费价）；NC = Namecheap。人民币按 $1≈¥7.12 折算。¥ 判定列以「常价续费」对 ¥240/年 预算。

| 后缀 | CF 首年/续费 | PB 常价（首年促销） | NC 续费参考 | 强制 HTTPS | 预算判定（¥/年） |
|---|---|---|---|---|---|
| **.dev** | $8.2 / $12.2 | $12.87（促销 $8.75） | ~$14 | 是 | **$12.87 ≈ ¥92 ✅ 唯一推荐** |
| .design | $45.2 / $45.2 | $46.86（促销 $10.81） | $51.98 | 否 | $46.86 ≈ ¥334 ❌ 超预算 39% |
| .io | $32 / $50 | $51.80（促销 $28.12） | ~$56 | 否 | $51.80 ≈ ¥369 ❌ |
| .sh | $45 / $45 | $46.65（促销 $31.20） | — | 否 | $46.65 ≈ ¥332 ❌ |
| .so | CF 不卖 | — | $68.98 | 否 | $54-65 ≈ ¥385-460 ❌❌ |
| .cc | $8 / $8 | $8.55（促销 $3.40） | — | 否 | $8.55 ≈ ¥61 ✅ 但气质杂 |
| .moe | CF 不卖 | $13.05（促销 $6.69） | $17.88 | 否 | $13.05 ≈ ¥93 ✅ 但二次元专属 |
| .wtf | $28.2 / $28.2 | $32.44（促销 $2.57） | $41 | 否 | $32.44 ≈ ¥231 ⚠️ 压线但玩梗 |

核实结论：任务书所引「.design 约 $35-50/yr」**属实且落在上沿**——Cloudflare 批发 $45.2、Porkbun 常价 $46.86、Namecheap $49.98-51.98。首年促销价（$3.98-10.98）是钩子，续费才是真实成本。

### 3.2 使用案例与气质

| 后缀 | 开发者工具实际案例 | 气质与判断 |
|---|---|---|
| **.dev** | web.dev、go.dev、flutter.dev、stripe.dev、github.dev、workers.dev、mdn.dev、nodejs.dev、pptr.dev、bit.dev、v8.dev、svelte.dev、cube.dev（Google Registry 官方 showcase + awesome-dev-sites 清单） | 开发者工具第一后缀，案例最密；Google Registry 运营、强制 HTTPS。**本产品与 .dev 语义完全对齐** |
| .design | 本次检索**未见头部开发者工具案例**；Porkbun 定位文案面向设计人群（"built for people who make things beautiful"），多为设计工作室/作品集 | 语义对齐但贵且缺工程圈先例；作为主域超预算，可作防御性注册 |
| .io | github.io、socket.io、itch.io、hashnode.io | 经典但已通胀（续费 $50+），且英国印度洋领地主权争议是长期尾部风险 |
| .sh | brew.sh、ohmyz.sh、bun.sh | 极强的 CLI/终端气质（.sh=shell script），但三巨头把最好名字占了；贵 |
| .so | notion.so（2026-06-03 迁往 notion.com，现 307 跳转）、hiro.so、hey.so 类短词 | Notion 迁移是最直接警示：.so 品牌黑客的旗舰案例最终买回 .com。贵、注册局集中度低 |
| .cc | arduino.cc、tiny.cc、taplink.cc、postimg.cc、reurl.cc、neurips.cc | 便宜好注册，但存量站气质杂（大量内容/灰色站），专业感弱 |
| .moe | catbox.moe、bangumi.moe、animethemes.moe、mywaifulist.moe | 硬绑定日语御宅文化，放开发者工具上是错位 |
| .wtf | vole.wtf、nouns.wtf、lemmy.wtf、charity.wtf、colorfonts.wtf | 玩梗/幽默/社区项目专用，正式产品慎用；top 100 万站里仅 71 个 .wtf |

案例来源：Google Registry .dev 页与官方博客（registry.google/domains/dev、blog.google）、qballer/awesome-dev-sites、namefi.io 各 TLD 页、networksolutions.com 博客、stackscan.com、domaintyper.com，链接见 §四。

### 3.3 给本项目的判定

1. **主域选 `.dev`**：预算内（¥92/年）、行业语义最准（AI 代理消费方=开发者工具）、案例密度最高。候选名定稿后立即查 `name.dev` 可用性。
2. **`.design` 不做主域**：续费 ¥334 超预算 39%，且工程圈先例为零。若品牌名恰是设计向词汇，可首年促销价注册做跳转，但要把续费成本计入或接受次年放弃。
3. **`.io`/`.sh`/`.so` 放弃**：全部超预算；`.so` 另有 Notion 迁移的前车之鉴。
4. **`.moe`/`.cc`/`.wtf` 只在品牌名天然适配时考虑**（如名字以 moe/cc/wtf 音收尾的域名黑客），否则气质错位。

---

## 四、数据与方法 + 局限

**检索**（2026-10-26，Asia/Shanghai）：
- `gh search repos --topic=design-tokens --sort=stars --limit 50`；`gh search repos "design token" --sort=stars --limit 30`；`--topic=design-systems --limit 40`；补充 `gh search repos "figma tokens" --limit 25`。原始 JSON 存 `research/raw/`。
- 价格：`https://cfdomainpricing.com/prices.json`（Cloudflare 各注册局成本聚合，2026-10 更新）；Porkbun 官网 tld 页快照（porkbun.com/tld/design、/tld/sh、/tld/cc、/tld/wtf、/tld/moe、/products/domains/pricing）；Namecheap 注册页快照；EasyTLDs/DomScan 聚合页交叉核对 .so/.moe。
- 案例：registry.google/domains/dev、blog.google（.dev 一周年）、help.figma.com、qballer/awesome-dev-sites、namefi.io（.sh/.so/.dev TLD 页）、domaindetails.com、domydomains.com、networksolutions.com、webatla.com、stackscan.com、domaintyper.com、smarthost.ie、hipposerve.com。
- 时效核查：`gh api repos/<name>` 取创建时间（2026-10-26 实测）。

**局限**：
1. Porkbun 精确价格走的是搜索引擎索引快照（其 API 与页面直抓被 403/出口拦截），促销价随时变动；**下单前以注册商结算页为准**。
2. GitHub 样本按星标排序，天然偏向头部与（近期）爆发项目；`-ly`/`-ify` 等后缀「样本为 0」只能说 GitHub 开源圈不用，不能证明商业产品圈不用（故归 B 类并标注）。
3. `.design` 头部案例的「未检索到」是负面结论，受检索面限制，不等于绝对不存在。
4. 汇率固定按 7.12 计算，未跟踪波动。
5. npm 包名占用未核查（本卡范围只到 GitHub + 域名）；下一步起名前建议补 `npm view <name>` 查重。

## 附录 A：GitHub 样本全量名单（108 仓库，按星标降序）

| 仓库 | ★ | 归档 | 描述 |
|---|---|---|---|
| [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | 123598 | 否 | A collection of DESIGN.md files analysis by popular brand design systems. Drop o |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | 104042 | 否 | The 1st Collaborative AI Design Agent Workspace. Local-first and open source. Cr |
| [ant-design/ant-design](https://github.com/ant-design/ant-design) | 99901 | 否 | An enterprise-class UI design language and React UI library |
| [storybookjs/storybook](https://github.com/storybookjs/storybook) | 91379 | 否 | Storybook is the industry standard workshop for building, documenting, and testi |
| [saadeghi/daisyui](https://github.com/saadeghi/daisyui) | 42678 | 否 | 🌼 🌼 🌼 🌼 🌼  The most popular, free and open-source Tailwind CSS component library |
| [goabstract/Awesome-Design-Tools](https://github.com/goabstract/Awesome-Design-Tools) | 41625 | 否 | The best design tools and plugins for everything 👉 |
| [alexpate/awesome-design-systems](https://github.com/alexpate/awesome-design-systems) | 26212 | 否 | 💅🏻 ⚒ A collection of awesome design systems |
| [checkcheckzz/system-design-interview](https://github.com/checkcheckzz/system-design-interview) | 23863 | 否 | System design interview for IT companies |
| [iview/iview](https://github.com/iview/iview) | 23748 | 否 | A high quality UI Toolkit built on Vue.js 2.0 |
| [radix-ui/primitives](https://github.com/radix-ui/primitives) | 19432 | 否 | Radix Primitives is an open-source UI component library for building high-qualit |
| [adobe/react-spectrum](https://github.com/adobe/react-spectrum) | 15986 | 否 | A collection of libraries and tools that help you build adaptive, accessible, an |
| [kgrzybek/modular-monolith-with-ddd](https://github.com/kgrzybek/modular-monolith-with-ddd) | 14094 | 否 | Full Modular Monolith application with Domain-Driven Design approach. |
| [mdbootstrap/TW-Elements](https://github.com/mdbootstrap/TW-Elements) | 13183 | 否 | 𝙃𝙪𝙜𝙚 collection of Tailwind MIT licensed (free) components, sections and templat |
| [primer/css](https://github.com/primer/css) | 13041 | 否 | Primer is GitHub's design system. This is the CSS implementation |
| [segmentio/evergreen](https://github.com/segmentio/evergreen) | 12427 | 否 | 🌲 Evergreen React UI Framework by Segment |
| [mehdihadeli/awesome-software-architecture](https://github.com/mehdihadeli/awesome-software-architecture) | 11738 | 否 | 📚 A curated list of awesome articles, videos, and other resources to learn and p |
| [tachyons-css/tachyons](https://github.com/tachyons-css/tachyons) | 11726 | 否 | Functional css for humans |
| [microsoft/fast](https://github.com/microsoft/fast) | 9684 | 否 | The adaptive interface system for modern web experiences. |
| [uber/baseweb](https://github.com/uber/baseweb) | 9023 | 否 | A React Component library implementing the Base design language |
| [radix-ui/themes](https://github.com/radix-ui/themes) | 8796 | 否 | Radix Themes is an open-source component library optimized for fast development, |
| [styled-system/styled-system](https://github.com/styled-system/styled-system) | 7860 | 否 | ⬢ Style props for rapid UI development |
| [uswds/uswds](https://github.com/uswds/uswds) | 7229 | 否 | The U.S. Web Design System helps the federal government build fast, accessible,  |
| [plasmicapp/plasmic](https://github.com/plasmicapp/plasmic) | 7127 | 否 | Visual builder for React. Build apps, websites, and content. Integrate with your |
| [chakra-ui/panda](https://github.com/chakra-ui/panda) | 6235 | 否 | 🐼 Universal, Type-Safe, CSS-in-JS Framework for Design Systems ⚡️ |
| [Shopify/polaris-react-archive](https://github.com/Shopify/polaris-react-archive) | 6164 | 是 | Shopify's Polaris Design System - React implementation (Deprecated) |
| [system-ui/theme-ui](https://github.com/system-ui/theme-ui) | 5409 | 否 | Build consistent, themeable React apps based on constraint-based design principl |
| [chakra-ui/zag](https://github.com/chakra-ui/zag) | 5239 | 否 | Build your design system in React, Solid, Vue, Svelte or Vanilla. Powered by fin |
| [style-dictionary/style-dictionary](https://github.com/style-dictionary/style-dictionary) | 4869 | 否 | A build system for creating cross-platform styles. |
| [microsoft/fluentui-blazor](https://github.com/microsoft/fluentui-blazor) | 4853 | 否 | Microsoft Fluent UI Blazor components library. For use with ASP.NET Core Blazor  |
| [seek-oss/playroom](https://github.com/seek-oss/playroom) | 4597 | 否 | Design with JSX, powered by your own component library. |
| [geist-org/geist-ui](https://github.com/geist-org/geist-ui) | 4554 | 是 | A design system for building modern websites and applications. |
| [Manavarya09/design-extract](https://github.com/Manavarya09/design-extract) | 4378 | 否 | Extract any website's complete design system with one command. DTCG tokens, sema |
| [dembrandt/dembrandt](https://github.com/dembrandt/dembrandt) | 3841 | 否 | Extract any website’s design system into tokens in seconds: logo, colors, typogr |
| [BuilderIO/figma-html](https://github.com/BuilderIO/figma-html) | 3710 | 否 | Convert any website to editable Figma designs |
| [salesforce-ux/design-system](https://github.com/salesforce-ux/design-system) | 3705 | 是 | Salesforce Lightning Design System |
| [MarsX-dev/floatui](https://github.com/MarsX-dev/floatui) | 3591 | 否 | Beautiful and responsive UI components and templates for React and Vue (soon) wi |
| [Owl-Listener/designer-skills](https://github.com/Owl-Listener/designer-skills) | 3104 | 否 | Designer Skills Collection: agentic skills, commands, and plugins for design — f |
| [kgrzybek/sample-dotnet-core-cqrs-api](https://github.com/kgrzybek/sample-dotnet-core-cqrs-api) | 3061 | 否 | Sample .NET Core REST API CQRS implementation with raw SQL and DDD using Clean A |
| [plugin87/ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) | 3019 | 否 | Turn Claude into a senior design architect: DTCG tokens, 52 components, WCAG 2.2 |
| [view-design/ViewUI](https://github.com/view-design/ViewUI) | 2625 | 否 | A high quality UI Toolkit built on Vue.js 2.0 |
| [southleft/figma-console-mcp](https://github.com/southleft/figma-console-mcp) | 2602 | 否 | Your design system as an API. Connect AI to Figma for extraction, creation, and  |
| [Inkloom-art/inkloom](https://github.com/Inkloom-art/inkloom) | 2534 | 否 | Specialised AI models for logo design — a brand-analysis model turns a business  |
| [itmeo/webgradients](https://github.com/itmeo/webgradients) | 2495 | 否 | 180 free CSS3, Figma, Sketch & PSD gradients — plus a JSON dataset for design to |
| [creativetimofficial/argon-design-system](https://github.com/creativetimofficial/argon-design-system) | 2478 | 否 | Argon - Design System for Bootstrap 4 by Creative Tim |
| [airbnb/Showkase](https://github.com/airbnb/Showkase) | 2324 | 否 | 🔦 Showkase is an annotation-processor based Android library that helps you organ |
| [arcsin1/oh-my-ppt](https://github.com/arcsin1/oh-my-ppt) | 2205 | 否 | Describe what you need — a presentation, lesson, or story — and let the AI build |
| [design-tokens/community-group](https://github.com/design-tokens/community-group) | 2156 | 否 | This is the official DTCG repository for the design tokens site and specificatio |
| [zanwei/design-dna](https://github.com/zanwei/design-dna) | 2038 | 否 | Turn reference UIs (images, screenshots, URLs) into quantified Design DNA JSON—t |
| [salesforce-ux/theo](https://github.com/salesforce-ux/theo) | 1989 | 是 | Theo is a an abstraction for transforming and formatting Design Tokens |
| [tokens-studio/figma-plugin](https://github.com/tokens-studio/figma-plugin) | 1628 | 否 | Official repository of the plugin 'Tokens Studio for Figma' (Figma Tokens) |
| [sturobson/Awesome-Design-Tokens](https://github.com/sturobson/Awesome-Design-Tokens) | 1298 | 否 | A list of resources on all things to do with Design Tokens |
| [diez/diez](https://github.com/diez/diez) | 1238 | 否 | The Design Token Framework — Adopt a unified design language across platforms, c |
| [lukasoppermann/design-tokens](https://github.com/lukasoppermann/design-tokens) | 1129 | 否 | 🎨 Figma plugin to export design tokens to json in an amazon style dictionary com |
| [bitjaru/styleseed](https://github.com/bitjaru/styleseed) | 989 | 否 | Open-source design-method engine for Claude Code, Codex & Cursor. 23 agent skill |
| [klaufel/awesome-design-systems](https://github.com/klaufel/awesome-design-systems) | 904 | 否 | 📒 A curated list of bookmarks, resources and articles about design systems focus |
| [mikaelvesavuori/figmagic](https://github.com/mikaelvesavuori/figmagic) | 864 | 否 | Figmagic is the missing piece between DevOps and design: Generate design tokens, |
| [patternfly/patternfly-react](https://github.com/patternfly/patternfly-react) | 859 | 否 | A set of React components for the PatternFly project.  |
| [Tahul/pinceau](https://github.com/Tahul/pinceau) | 690 | 否 | 🖌️ Make your <script> lighter and your <style> smarter |
| [UX-and-I/storybook-design-token](https://github.com/UX-and-I/storybook-design-token) | 682 | 否 | Display design token documentation generated from your stylesheets and icon file |
| [AnxForever/stylekit](https://github.com/AnxForever/stylekit) | 673 | 否 | Open-source visual style library for AI-generated UI — 148 curated styles with d |
| [Railly/tinte](https://github.com/Railly/tinte) | 625 | 否 | Compile your design system into an Agent Plugin. Extract an identity from any re |
| [Meliwat/awesome-ios-design-md](https://github.com/Meliwat/awesome-ios-design-md) | 620 | 否 | 200 production-grade DESIGN.md design systems for the world's best apps. Framewo |
| [components-ai/css.gui](https://github.com/components-ai/css.gui) | 585 | 否 | Visual development environment for CSS |
| [sinanata/unity-ui-toolkit-design-system](https://github.com/sinanata/unity-ui-toolkit-design-system) | 561 | 否 | Drop-in design system for Unity 6 UI Toolkit (UIDocument + PanelRenderer, UXML + |
| [system-ui/theme-specification](https://github.com/system-ui/theme-specification) | 551 | 否 | A specification for defining theme objects & design tokens for use with UI compo |
| [kwakseongjae/oh-my-design](https://github.com/kwakseongjae/oh-my-design) | 549 | 否 | Give your AI coding agent a design system. One command installs 500+ quality-gra |
| [mrmartineau/design-system-utils](https://github.com/mrmartineau/design-system-utils) | 542 | 否 | 👩‍🎨 Access your design tokens with ease |
| [marvkr/better-design](https://github.com/marvkr/better-design) | 534 | 否 | 🎨 Open-source design MCP server + shadcn/ui registry — AI design systems for Cla |
| [VoltAgent/official-design-md](https://github.com/VoltAgent/official-design-md) | 528 | 否 | Official DESIGN.md files published by companies themselves. First-party design s |
| [hashicorp/design-system](https://github.com/hashicorp/design-system) | 518 | 否 | Helios Design System |
| [terrazzoapp/terrazzo](https://github.com/terrazzoapp/terrazzo) | 481 | 否 | Use DTCG tokens JSON to generate code for web, mobile, native apps, and more |
| [ardov/huetone](https://github.com/ardov/huetone) | 456 | 否 | A tool to create accessible color systems |
| [primer/primitives](https://github.com/primer/primitives) | 416 | 否 | Color, typography, and spacing primitives in json. |
| [B3nnyL/figgo](https://github.com/B3nnyL/figgo) | 307 | 否 | 👯‍♀️A cli tool makes your Figma and local design token stay in sync 👯‍♂️  |
| [edisonmbli/refactoring-ui-skill](https://github.com/edisonmbli/refactoring-ui-skill) | 293 | 否 | Unofficial Claude Skill derived from the book Refactoring UI — a design rulebook |
| [Decathlon/vitamin-web](https://github.com/Decathlon/vitamin-web) | 289 | 否 | Decathlon Design System UI components for web applications |
| [material-foundation/material-tokens](https://github.com/material-foundation/material-tokens) | 285 | 是 | Material Design DSP |
| [arvindrk/extract-design-system](https://github.com/arvindrk/extract-design-system) | 256 | 否 | Extract design tokens (colors, typography, spacing, border radius, shadows) from |
| [elreco/coderocket-ui](https://github.com/elreco/coderocket-ui) | 248 | 否 | Open-source React and Vue component library: 48 components, 26 UI blocks, TypeSc |
| [Shopify/polaris-tokens](https://github.com/Shopify/polaris-tokens) | 245 | 是 | Design tokens for Polaris, Shopify’s design system |
| [uxKero/anydesign](https://github.com/uxKero/anydesign) | 229 | 否 | Claude skill that analyzes images, websites, and Figma files and generates a str |
| [lukasoppermann/style-dictionary-utils](https://github.com/lukasoppermann/style-dictionary-utils) | 228 | 否 | A package of transforms, formats, filters, etc. to use in your style dictionary  |
| [metasidd/ColorTokensKit-Swift](https://github.com/metasidd/ColorTokensKit-Swift) | 226 | 否 | The most complete color system for SwiftUI: 740 colors, 20 semantic tokens, dark |
| [murphytrueman/design-system-ops](https://github.com/murphytrueman/design-system-ops) | 211 | 否 | Claude Code skills for the work that keeps a design system alive |
| [TrySound/engramma](https://github.com/TrySound/engramma) | 197 | 否 | Design tokens style guide and editor |
| [madebymustafa/design-taste](https://github.com/madebymustafa/design-taste) | 196 | 否 | 24 open-source agent skills that turn taste into instructions — ten genre identi |
| [arla6ka/design.how](https://github.com/arla6ka/design.how) | 195 | 否 | Agent skills and design systems from design.how. Build a design system from your |
| [universal-design-tokens/udt](https://github.com/universal-design-tokens/udt) | 183 | 否 | Universal Design Tokens (UDT) is a collection of libraries and utilities for wor |
| [juntossomosmais/atomium](https://github.com/juntossomosmais/atomium) | 180 | 否 | Atomium is an internal design system for 'Juntos Somos Mais' using Web Component |
| [lustre-labs/ui](https://github.com/lustre-labs/ui) | 174 | 否 | A collection of components and design tokens for building Lustre apps. |
| [sugarcube-sh/sugarcube](https://github.com/sugarcube-sh/sugarcube) | 128 | 否 | Design tokens in, CSS and components out. |
| [wikimedia/design-codex](https://github.com/wikimedia/design-codex) | 112 | 否 | Codex is the Design System for Wikimedia. Codex features a toolkit for building  |
| [opentable/design-tokens](https://github.com/opentable/design-tokens) | 84 | 是 | A place where OpenTable engineers and designers openly work together |
| [digital-go-jp/design-tokens](https://github.com/digital-go-jp/design-tokens) | 78 | 否 | デジタル庁デザインシステムのデザイントークン |
| [salesforce-ux/design-system-ios](https://github.com/salesforce-ux/design-system-ios) | 71 | 是 | Salesforce Lightning Design Tokens for iOS |
| [drobins25/craft](https://github.com/drobins25/craft) | 69 | 否 | Craft is a Claude Code plugin that asks you the product questions and works out  |
| [Jeromski62/SCALES-Design-Tokens-Starter-Set](https://github.com/Jeromski62/SCALES-Design-Tokens-Starter-Set) | 67 | 否 | Design tokens starter set for your design system |
| [userFRM/egui-charts](https://github.com/userFRM/egui-charts) | 56 | 否 | Financial charting engine for egui: candlesticks and other chart types, drawing  |
| [nuxt-modules/design-tokens](https://github.com/nuxt-modules/design-tokens) | 51 | 否 | Design tokens module for Nuxt |
| [zendeskgarden/tailwindcss](https://github.com/zendeskgarden/tailwindcss) | 50 | 否 | :tickets: garden design tokens |
| [saneef/postcss-design-token-utils](https://github.com/saneef/postcss-design-token-utils) | 44 | 否 | PostCSS plugin to convert design tokens to CSS custom properties and utility cla |
| [ubie-oss/design-tokens](https://github.com/ubie-oss/design-tokens) | 41 | 否 | This package provides design tokens for Ubie's products, managed in JSON and con |
| [LekoArts/gatsby-starter-specimens](https://github.com/LekoArts/gatsby-starter-specimens) | 39 | 是 | Leverage the wide variety of powerful React components to build your design syst |
| [albertzhangz10/figma-design-system-to-design-md](https://github.com/albertzhangz10/figma-design-system-to-design-md) | 39 | 否 | Figma to design.md — Convert Figma design tokens into structured design.md for A |
| [roseg43/vscode-wp-theme-json-autocomplete](https://github.com/roseg43/vscode-wp-theme-json-autocomplete) | 39 | 否 | A VS Code extension that adds CSS autocomplete for design tokens added to your W |
| [Moddingflow/better-design](https://github.com/Moddingflow/better-design) | 37 | 否 | UI/UX and frontend design skill for AI coding agents: Codex, Claude Code, Cursor |
| [aka-kika/hig-mcp](https://github.com/aka-kika/hig-mcp) | 36 | 否 | MCP server serving Apple Human Interface Guidelines as structured design tokens  |
| [Sangun-Kang/pre-design-md](https://github.com/Sangun-Kang/pre-design-md) | 33 | 否 | Decide your design tokens visually. Export as DESIGN.md, AI prompt, or CSS. |

