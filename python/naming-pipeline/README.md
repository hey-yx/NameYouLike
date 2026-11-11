# naming-pipeline — 互联网品牌命名案例持续学习管道

定期采集中国新近公开的企业名与知名品牌命名案例，清洗去重后提取命名模式
（音节长度、用字偏好、拼音风格、行业关联），产出**可被生成引擎直接消费的统计权重文件**，
并附完整去重 / 清洗 / 增量更新机制。

## 架构

```
采集 sources.py        清洗 clean.py      去重 dedup.py      特征 features.py
────────────────────► ────────────────► ────────────────► ──────────────────►
eastmoney_ipo            全称→字号          record_id 幂等       音节/首字母/位置
emweb F10 补全           简称去市场标记     精确名称去重          二字组合/lift
cninfo 全市场            (N/*ST/退/A)      语音键去重(同音)      域名拼音风格分类
wiki 中国品牌树                            (淘宝≡桃宝)           (full/abbr/partial/
seed 种子语料(含域名)                                             hybrid/numeric/creative)

       统计 stats.py                     增量 store.py                消费 consumer.py
      ─────────────────────────────────► ──────────────────────────► ──────────────────
      长度分布/用字权重/行业lift/            corpus.jsonl 追加式          schema 校验
      拼音风格分布/碰撞索引                 state.json 水位+版本         （守门唯一职责）
      → output/naming_patterns.v1.json    .lock 防并发
```

## 数据源

| 源 | 内容 | 用途 |
|---|---|---|
| `eastmoney_ipo` | 东方财富数据中心 IPO 申报列表（2024 年至今，近期优先） | 新注册企业名 + 日期 + 证监会行业 |
| `eastmoney_f10` | F10 公司资料（对最近 300 家逐个补全） | 公司全称（清洗链）、注册地址→区域提示、东财行业、**官网域名** |
| `cninfo_all_a` | 巨潮资讯全市场 A 股列表（~5400 家） | 存量基线：碰撞索引 + 命名风格漂移参照 |
| `wiki_zh_brand` | 维基百科「中国品牌」分类树（含子分类，深度 2） | 知名品牌命名案例 |
| `curated_seed` | `seeds/brand_domains.json`（149 个知名品牌 + 官网域名） | 拼音风格分析的主数据（中文名↔域名映射） |

单源失败不阻塞管道：失败记入运行记录 `quality.failures`，其余源照常产出。

## 运行

```bash
uv venv && uv pip install requests pypinyin opencc-python-reimplemented pytest   # 一次性
.venv/bin/python -m pipeline.run                      # 在线全源（真实抓取 + 增量）
.venv/bin/python -m pipeline.run --offline            # 离线冒烟（仅种子语料）
.venv/bin/python -m pipeline.run --rebuild-stats      # 不抓取：清洗逻辑升级后幂等重建统计
.venv/bin/python -m pytest tests/ -q                  # 测试（33 例）
.venv/bin/python -m pipeline.consumer output/naming_patterns.v1.json --validate-only   # schema 校验
```

定期运行（增量 + 互斥锁保证可重复调度）：本机 crontab 已配每日 03:00 调 `scheduled_run.sh`
（增量抓取 → 全量重算统计 → 刷新 brandgen 内置瘦身数据 `brandgen/data/naming_patterns.slim.json`），
日志追加到 `cron.log`：

```cron
0 3 * * *  /Users/mac/workspace/active/NameYouLike/python/naming-pipeline/scheduled_run.sh
```

注意 crontab 在机器睡眠时不会补跑。若要睡眠唤醒后自动补跑，可改用 launchd：先创建
`~/Library/LaunchAgents/com.nameyoulike.pipeline.plist`（每天 03:00，同一脚本；当前尚未创建），
再在系统终端（不要在 Hermes 内置终端）执行一次即可启用，启用后把上面的 crontab 行删掉：

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nameyoulike.pipeline.plist
launchctl kickstart -k gui/$(id -u)/com.nameyoulike.pipeline  # 立即手动跑一次
```

## 增量更新机制

- `data/corpus.jsonl`：追加式清洗后语料（全量事实源）；每条含 `record_id`（source+原始名哈希）。
- 每次运行：抓取 → 对**全量累积语料**去重（record_id / 精确名 / 语音键三层）→ 仅新增入语料
  → 统计每次从全量重算（无增量统计漂移）→ `version_seq` 递增，输出打版本戳，历史快照存
  `output/history/`（**只保留最近 30 份**，旧快照自动清理；**只落盘不入库**，每份约 400KB，
  入库会让仓库按天膨胀）。
- `data/state.json` 记录水位（各源最近抓取量/时间）与最近 30 次运行摘要。
- `runs/run_<ts>/record.{json,md}` 是每次运行的完整记录，仅供本地排查，**不入库**（`.gitignore`）。
- `data/.lock` 互斥（30 分钟陈锁自动失效），cron 场景安全。

## 与主引擎的边界

本目录是**独立子项目**（自带 venv / README / 测试），与主引擎的关系只有一条数据链：
**产出 `output/naming_patterns.v1.json` 供消费**：`python/brandgen/signals.py` 会自动发现它
（管道完整版优先，`python/brandgen/data/naming_patterns.slim.json` 内置瘦身版兜底），
`brandgen` 据此做音节自然度加权与品牌碰撞排雷。管道不 import 主引擎，主引擎也不 import
管道，只认输出文件的 schema（`naming-patterns/v1`，校验在 `pipeline/consumer.py`）。

因此：**不要把管道测试并进 `python/tests/`**（依赖不同：本目录需要 `requests`/`opencc`，
主 venv 只装 `pypinyin`），也不要让主引擎依赖本目录的运行时状态。每日由
`scheduled_run.sh`（crontab / launchd）跑增量，重写的文件只有 `data/corpus.jsonl`、
`data/state.json`、`output/naming_patterns.v1.json`、`output/history/` 与
`../brandgen/data/naming_patterns.slim.json`。

## 输出契约（供生成引擎消费）

`output/naming_patterns.v1.json`，`schema: naming-patterns/v1`：

| 字段 | 内容 | 引擎用法 |
|---|---|---|
| `length_dist` | 音节数(=字数)分布 2/3/4/5+ | 候选长度先验 |
| `char_scores` | Top400 用字：count/freq/weight/首尾位置 | 用字亲和度 |
| `char_pair_scores` | Top300 二字组合：count/lift/weight | 高质量组合加成 |
| `industry_char_affinity` | 行业条件下用字 lift（样本≥8） | 行业用字加权 |
| `industry_length_dist` | 行业×长度分布 | 行业长度先验 |
| `pinyin_initial_dist` / `pinyin_syllable_dist` | 首字母 / 音节分布 | 简拼、全拼生成的先验 |
| `pinyin_style_dist` | 知名品牌 中文名↔域名 映射分类分布 | 域名形式选择（全拼/简拼/破折号…） |
| `collision_index` | exact_names + phonetic_keys（含全市场基线） | 候选排雷：精确撞=剔除，同音撞=强降权 |
| `recommendation_weights` | 上述全部归一化后的 `w_*` 权重块 + 打分公式 | 直接并入打分函数 |

**打分公式**（`recommendation_weights.scoring`；引擎按此消费，参考实现在
`brandgen/stats.py` 的打分与碰撞逻辑）：

```
score = 0.30*char_term + 0.15*pair_term + 0.15*length_term
      + 0.25*industry_term + 0.15*pinyin_term        （缺省项权重再分配）
碰撞: exact -> score=0；phonetic -> score*0.4
```

接入方式：`validate_output(path)`（`pipeline.consumer`）校验通过后，解析与打分
统一走主引擎的 `from brandgen.stats import load_patterns`（完整/瘦身两种 schema
通吃），`PatternStats.collision(name)` 做碰撞排雷。

## 设计决策

- **统计语料 = 新企业 + 知名品牌**；存量全市场基线只进碰撞索引与 `baseline_length_dist`
  （可观察"近年新名 vs 存量老名"的风格漂移，如 4 字名占比 存量 64.7% vs 近期 44%）。
- **主字段 `name_clean` 取上市简称**（市场品牌形态，保留如「宁德时代」）；全称分解出的
  `trade_name` 为法定字号（「宁德|时代」），作为辅助元数据与清洗链证据。
- **所有源的 name_clean 统一过清洗器**：简称去市场标记（N/*ST/退）与组织形式尾词
  （股份/集团：蚂蚁集团→蚂蚁、安达股份→安达）；维基标题繁→简归一（opencc），含组织
  后缀的全称走分解链（泸州老窖股份有限公司→泸州老窖），纯品牌名不动（青岛啤酒原样）。
- **语料持久化 name_raw，清洗可升级**：`--rebuild-stats` 用当前清洗逻辑幂等重清洗全量
  语料并重算统计——清洗规则改进不需要重新抓取。
- **语音键去重**（无声调拼音串）在品牌命名场景有业务含义：避免推荐与既有品牌同音的新名；
  同音记录入语料时保留信息更富者（有域名/行业者优先）。
- **行业样本 < 8 不产出关联**，避免碎样本噪声。
- **单源失败不阻塞**（如维基 429 限流）：失败记入运行记录，其余源照常产出。
