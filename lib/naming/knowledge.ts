/**
 * 命名知识库。它的作用不是替模型想名字，而是把“哪些词已经被用烂了”
 * 和“每个行业该从什么具体物件里取材”显式写出来，避免模型回到平均值。
 */

export const BANNED_WORDS = [
  // 被创业命名用烂的抽象词
  "nova", "nexus", "aether", "lumina", "lumen", "orbit", "pulse", "zen",
  "vibe", "spark", "forge", "craft", "bloom", "drift", "loop", "loom",
  "aura", "echo", "vertex", "apex", "atlas", "orion", "helix", "flux",
  "prism", "quantum", "synergy", "elevate", "empower", "seamless",
  "streamline", "catalyst", "beacon", "horizon", "voyage", "ember",
  "solace", "serenity", "haven", "nest", "hive", "tribe", "canvas",
  "mosaic", "tapestry", "odyssey", "aurora", "celestia", "stellar",
  "cosmo", "nebula", "zephyr", "onyx", "obsidian", "sable", "ivory",
  "crimson", "inspire", "innovate", "transform", "revolution", "vision",
  "future", "dream", "passion", "purpose", "impact", "growth", "success",
  "excellence", "quality", "trust", "secure", "simple", "easy", "fast",
  "smart", "bright", "pure", "true", "core", "prime", "peak", "best",
  "first", "next", "new", "meta", "hyper", "ultra", "super", "omni",
  "multi", "uni", "neo", "ever", "always", "infinity", "infinite",
  "unleash", "unlock", "limitless", "boundless", "effortless", "disrupt",
  "revolutionary", "nextgen", "aigc", "gpt", "llm", "neural", "cognition",
  "mind", "brain", "agent", "bot", "copilot", "autopilot", "wizard",
  "ninja", "guru", "rockstar", "magic", "magical", "wonder", "delightful",
  "amazing", "awesome", "perfect", "ultimate", "premier", "elite",
  "flagship", "frontier", "pioneer", "vanguard", "titan", "colossal",
  "mammoth", "phoenix", "dragon", "unicorn", "athena", "apollo", "zeus",
  "hermes", "odin", "thor", "loki", "arcadia", "elysium", "eden",
  "utopia", "nirvana", "oasis", "mirage", "enigma", "cipher", "oracle",
  "sphinx", "labyrinth", "maze", "riddle", "puzzle", "jigsaw", "quilt",
  "patchwork", "kaleidoscope", "spectrum", "rainbow", "eclipse",
  "solstice", "equinox", "zenith", "nadir", "meridian", "azimuth",
];

/**
 * 赛道撞名雷区词根（设计工具赛道实证）。
 *
 * 来源：`research/collision-map-2026-10.md` —— design-tokens / design-system /
 * design-systems 三组 GitHub 搜索并集 108 个仓库的仓库名词频统计。
 * 这些词根是「赛道默认构词法」：命中等于没起名（design* 36/108、token* 12/108、
 * style* 5/108、system 收尾 11/108），或有商标风险（figma*）。
 */
export const RACE_ROOTS = [
  "design",
  "token",
  "style",
  "system",
  "theme",
  "kit",
  "utils",
  "tools",
  "starter",
  "boilerplate",
  "figma",
  "awesome",
  "oh-my",
  "primitives",
  "variables",
  "dna",
  "codex",
  // 用户已点名淘汰（口味否决，不是撞名否决，但生成器同样先过滤）
  "datum",
  "typecase",
  "measure-twice",
];

/** 只作后缀判定的雷区构式（-md 是 2026 年 AI 代理潮新滥后缀）。 */
export const RACE_SUFFIXES = ["md", "agents", "skills", "js", "flow", "stack", "hub"];

/**
 * 清单 / 教程式仓库词：这类名字属于资源列表或课程仓库，不是项目名。
 * 只在「GitHub 项目名」目标下判定——产品名里 Guide、Notes 本身是站得住的名字。
 */
export const REPO_LIST_WORDS = [
  "roadmap",
  "checklist",
  "cheatsheet",
  "cheat-sheet",
  "resources",
  "template",
  "tutorial",
  "handbook",
  "examples",
  "curated",
  "collection",
];

/**
 * 仓库名里站得住的技术缩写。词典里查不到，但在真实仓库名里是常规 token
 * （2,109 个样本里 ui 出现 44 次、cli 19 次、mcp 19 次），真词判定要认它。
 */
export const REPO_TECH_TOKENS = new Set([
  "api",
  "cli",
  "sdk",
  "ui",
  "mcp",
  "llm",
  "db",
  "sql",
  "http",
  "git",
  "oss",
  "ml",
]);

/**
 * 拼音名后面可以接的「实际干的事」词。
 * 用户口径：拼音+横线+用途（it、design、draw、skill），ppt 这类交付物也算，
 * 它们要么不在词典里（ppt、ui），要么太短（it），但放在拼音名后是正常写法。
 */
export const PINYIN_PURPOSE_TOKENS = new Set([
  "it",
  "design",
  "draw",
  "skill",
  "ppt",
  "pptx",
  "cli",
  "ui",
  "web",
  "ai",
  "app",
  "kit",
  "doc",
  "pdf",
  "img",
  "svg",
  "code",
]);

export const GENERIC_STEMS = [
  "cloud", "data", "app", "tech", "smart", "flow", "task", "team", "work",
  "biz", "code", "dev", "web", "net", "info", "sync", "link", "connect",
  "scale", "growth", "market", "sales", "finance", "health", "learn", "edu",
  "travel", "food", "shop", "store", "pay", "bank", "money", "chat", "talk",
  "note", "doc", "file", "page", "site", "build", "make", "run", "ops",
  "base", "stack", "layer", "grid", "node", "byte", "bit", "pixel", "logic",
  "mind", "brain", "bot", "agent", "model", "prompt", "token", "vector",
  "matrix", "signal", "stream", "pipe", "line", "path", "route", "track",
  "map", "geo", "space", "time", "date", "plan", "goal", "habit", "focus",
  "calm", "rest", "sleep", "fit", "meal", "cook", "home", "house", "room",
  "door", "key", "lock", "safe", "guard", "shield", "watch", "view", "look",
  "see", "find", "search", "seek", "get", "take", "give", "send", "post",
  "share", "join", "meet", "follow", "lead", "grow", "rise", "lift", "boost",
  "jump", "move", "go", "start", "launch", "open", "close", "end", "finish",
  "done", "complete", "ready", "set", "now", "today", "next", "new", "old",
  "first", "last", "best", "top", "peak", "prime", "core", "true", "real",
  "pure", "clear", "bright", "light", "dark", "deep", "high", "low", "fast",
  "slow", "easy", "simple", "wise", "kind", "good", "great", "nice", "fine",
  "happy", "joy", "love", "care", "wealth", "rich", "free", "open", "public",
  "social", "group", "crowd", "club", "guild", "league", "union", "network",
  "edge", "system", "platform", "engine", "machine", "robot", "assistant",
  "helper", "guide", "pilot", "captain", "chief", "master", "expert", "pro",
  "architect", "builder", "maker", "creator", "founder", "operator",
  "manager", "planner", "tracker", "finder", "organizer", "analyzer",
  "optimizer", "booster", "accelerator", "incubator", "generator",
  "hub", "tool", "platform", "solution", "system", "studio", "space",
  "box", "kit", "desk", "suite",
  "terminal", "metric", "replica", "service", "product", "project",
  "workspace", "dashboard", "panel", "console", "portal", "analytics",
  "insight", "report", "record", "entry", "item", "list", "table", "log",
  "alert", "monitor", "telemetry", "endpoint", "request", "response",
  "client", "server", "host",
];

export const BANNED_SUFFIXES = [
  "ly", "ify", "io", "ai", "hq", "labs", "lab", "base", "flow", "wise",
  "verse", "gen", "mint", "ora", "eon", "ium",
];

export const ABSTRACT_WORDS = [
  "elevate", "empower", "inspire", "innovate", "transform", "revolutionize",
  "disrupt", "unleash", "unlock", "seamless", "effortless", "limitless",
  "boundless", "infinite", "future", "vision", "dream", "passion", "purpose",
  "impact", "growth", "success", "excellence", "quality", "trust", "secure",
  "simple", "easy", "fast", "smart", "bright", "pure", "true", "core",
  "prime", "peak", "top", "best", "first", "next", "new", "meta", "hyper",
  "ultra", "super", "omni", "multi", "uni", "neo", "ever", "always",
];

/**
 * 通用监控/导航隐喻。它们放在任何监控、安全、效率产品上都成立，
 * 是 AI 命名最舒服的退路，也是“听起来像那么回事但没有信息”的典型。
 */
export const CLICHE_METAPHORS = [
  "lighthouse", "compass", "radar", "sentinel", "beacon", "atlas",
  "watchtower", "guardian", "fortress", "shield", "sentry", "watchdog",
  "lookout", "northstar", "polaris", "navigator", "voyager", "signal",
  "horizon", "pulse", "orbit",
];

export const CHINESE_BANNED_WORDS = [
  "智能", "智慧", "云", "数据", "未来", "互联", "科技", "网络", "数字",
  "极速", "飞越", "腾飞", "星辰", "宇宙", "蓝海", "巅峰", "领航", "赋能",
  "链接", "生态", "平台", "管家", "助手", "专家", "大师", "云链", "数智",
  "智联", "创联", "未来星", "极智", "云智",
];

export const CHINESE_RARE_CHARS = [
  "翀", "龑", "燚", "淼", "焱", "垚", "犇", "骉", "猋", "掱", "赑", "毳",
  "鑫", "龘", "靐", "齉", "爨", "麤", "鱻", "羴", "猋", "驫", "嚞", "壵",
];

export const CHINESE_GENERIC_CHARS = [
  "云", "智", "联", "创", "未", "来", "星", "极", "光", "速", "达", "飞",
  "腾", "鲸", "象", "虎", "豹", "鹰", "龙", "凤", "鼎", "盛", "通", "信",
  "科", "技", "网", "数", "字", "元", "宇", "宙", "蓝", "海", "天", "地",
  "山", "川", "风", "火", "水", "木", "金", "土",
];

/**
 * 口语功能字：虚词、代词、指示词与日常动作词。
 * 白名单实词是「物件/动作」名词式的，口语短语名（叫什么、记在这、哪一页）
 * 一个也落不进去，被判成生造词。能说出口的短句必然带这类功能字，
 * 意象堆叠式生造名（云枢、智域、星图）则不会命中，用它区分这两类。
 */
export const CHINESE_SPOKEN_MARKERS = [
  "的", "了", "着", "过", "在", "这", "那", "哪", "就", "才", "还", "也", "都",
  "什", "么", "怎", "为", "因", "我", "你", "您", "他", "它", "咱", "把", "被",
  "给", "跟", "和", "吧", "呢", "吗", "啊", "不", "没", "要", "会", "能", "得",
  "一", "上", "下", "里", "外", "前", "后", "来", "去", "到", "说", "问", "叫",
  "记", "写", "读", "听", "看", "找", "挑", "选", "翻", "做", "用", "拿", "放",
];

/**
 * 伪拉丁/伪希腊后缀。AI 造词最集中的地方。
 * 只有“不是真实单词”的名字才会命中，真实单词由词典判定。
 */
export const PSEUDO_LATIN_SUFFIXES = [
  "ia", "ora", "ara", "era", "is", "yx", "ix", "ex", "ova", "ika", "ino",
  "ella", "elle", "oria", "aria", "ium", "eon", "ica", "iko", "ana",
  "ena", "ona", "ura", "yra", "aeon", "eus", "ius", "ion", "ora",
  "anta", "tra", "dra",
];

/** 来源解释里出现这些词，说明它没有指向真实事物。 */
export const ABSTRACT_SOURCE_PHRASES = [
  "a feeling", "the feeling", "innovation", "the future", "future of",
  "connection", "journey", "experience", "solution", "platform",
  "ecosystem", "synergy", "empower", "seamless", "next generation",
  "next-generation", "reimagine", "revolutionize", "unlock", "unleash",
  "limitless", "boundless", "possibility", "potential", "transformation",
  "digital", "smart", "intelligent", "modern", "simple", "easy", "fast",
  "better", "best", "world-class", "cutting-edge", "state-of-the-art",
  "game-changing", "disruptive", "一种感觉", "未来感", "创新", "连接",
  "旅程", "体验", "解决方案", "平台", "生态", "赋能", "无缝", "下一代",
  "重新想象", "革命性", "无限", "可能性", "数字化转型", "智能", "简单",
  "高效", "更好", "极致",
];

/** 推荐理由里的空话。命中只扣分，不直接淘汰。 */
export const GENERIC_RATIONALE_PHRASES = [
  "朗朗上口", "易于传播", "简洁有力", "很有科技感", "科技感", "现代感",
  "高级感", "国际化", "好听", "好记", "独特", "创新", "有趣", "优雅",
  "流畅", "自然", "亲切", "专业", "可靠", "值得信赖", "catchy",
  "memorable", "unique", "modern", "clean", "elegant", "professional",
  "trustworthy", "innovative", "powerful", "simple", "easy", "friendly",
  "approachable", "premium", "sleek", "bold", "fresh", "timeless",
  "versatile",
];

/** 中文实词白名单。严格模式下，中文名必须能在里面查到。 */
const CHINESE_REAL_WORDS = [
  // 动作
  "对账", "回车", "刻舟", "拾贝", "拓片", "批注", "朱批", "校勘", "考据",
  "装裱", "裁切", "折页", "配页", "锁线", "胶装", "铸字", "排版", "印刷",
  "装订", "探针", "示踪", "校准", "测量", "称量", "计时", "记账", "开票",
  "对表", "盘库", "分拣", "打包", "贴标", "封箱", "签收", "派件", "揽件",
  // 物件
  "罗盘", "铅字", "活字", "墨线", "尺规", "铆钉", "卡尺", "车床", "刨子",
  "凿子", "墨斗", "账本", "票据", "存根", "印章", "火漆", "封泥", "码头",
  "缆桩", "船坞", "舵盘", "桅杆", "风帆", "浮标", "沙漏", "算盘", "天平",
  "砝码", "墨盒", "镇纸", "砚台", "信封", "邮戳", "铜铃", "燧石", "陶轮",
  "纺锤", "梭子", "染缸", "碑帖", "线装", "册页", "卷轴", "索引", "示波器",
  "万用表", "继电器", "断路器", "保险丝", "信号灯", "黑匣子", "航海日志",
  "六分仪", "海图", "灯塔", "锚点", "缆绳", "齿轮", "轴承", "弹簧",
  "杠杆", "滑轮", "扳手", "螺丝", "焊缝", "砂纸", "锉刀", "锯子", "锤子",
  "钉子", "尺子", "圆规", "量角器", "水平仪", "铅锤", "线锤", "粉线",
  "角尺", "卷尺", "卡钳", "千分尺", "温度计", "压力表", "流量计", "计时器",
  "秒表", "日晷", "水钟", "铜壶", "更漏", "账册", "凭据", "骑缝", "信笺",
  "稿纸", "钢笔", "毛笔", "墨汁", "笔架", "笔洗", "印泥", "拓包", "宣纸",
  "书脊", "封面", "扉页", "目录", "注释", "眉批", "夹批", "圈点", "版本",
  "刻版", "探照灯", "风向标", "气压计", "湿度计", "水平尺", "线坠", "吊线",
  "榫卯", "燕尾榫", "楔子", "销钉", "垫片", "轴套", "法兰", "管钳", "台钳",
  "砂轮", "钻头", "丝锥", "板牙", "铰刀", "冲子", "錾子", "刮刀", "油石",
  "磨石", "砧板", "风箱", "坩埚", "模具", "砂型", "淬火", "回火", "退火",
  "正火", "焊接", "铆接", "螺栓", "螺母", "垫圈", "卡簧", "皮带", "链条",
  "链轮", "凸轮", "曲轴", "飞轮", "联轴器", "减速器", "变速箱", "离合器",
  "制动器", "液压", "气动", "阀门", "泵体", "缸体", "活塞", "密封圈",
  "滤芯", "油标",
];

export const CHINESE_REAL_WORD_SET = new Set(CHINESE_REAL_WORDS);

/**
 * 文化意象词表：只给「文化意象词 + 实字」拼接怪这条规则用。
 *
 * 这是判形态用的词表，不是可检索的词库：不带系列、出处、拼音、行业、情感，
 * 也不参与推荐。收录标准是「有真实出处的文化意象词」，够规则判形态即可。
 */
export const CHINESE_CULTURAL_WORDS = [
  // 二十四节气
  "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满", "芒种",
  "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降",
  "立冬", "小雪", "大雪", "冬至", "小寒", "大寒",
  // 神兽祥瑞
  "麒麟", "凤凰", "鲲鹏", "貔貅", "白泽", "朱雀", "玄武", "青龙", "应龙",
  "玄鸟", "九尾狐", "帝江", "烛龙", "天禄", "辟邪",
  // 星宿天文
  "北斗", "望舒", "羲和", "天枢", "天璇", "天玑", "天权", "玉衡", "开阳",
  "摇光", "织女", "牵牛", "长庚", "启明", "星汉", "天狼",
  // 山川地理
  "昆仑", "蓬莱", "天山", "长白", "泰山", "华山", "嵩山", "峨眉", "黄山",
  "庐山", "武夷", "玉龙", "赤水", "湘江", "太湖", "西湖",
  // 草木花果
  "甘棠", "杜若", "芝兰", "木兰", "青梅", "梧桐", "桃夭", "常棣", "江离",
  "秋兰", "辛夷", "修竹", "松筠", "嘉卉", "木樨", "荼蘼",
  // 诗词典故
  "青云", "扶摇", "星河", "明月", "清风", "沧海", "青山", "乘兴", "窈窕",
  "致远", "流水", "长虹", "白驹", "烂柯", "丹青", "芙蓉", "芳草", "疏影",
  "暗香", "婵娟", "灵犀", "千帆", "逍遥", "北辰", "潇湘", "瀛洲", "洞庭",
  "烟波", "菡萏", "蒹葭", "花朝",
  // 生肖
  "鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪",
  "赤兔", "的卢", "白龙", "玉兔", "白虎", "金牛", "悟空", "哮天",
  // 王朝（单字，只作真词判定，不进意象占比）
  "唐", "汉", "秦", "宋", "明", "周", "清", "夏", "元", "商", "晋", "隋",
];

export const CHINESE_CULTURAL_WORD_SET = new Set(CHINESE_CULTURAL_WORDS);

/**
 * 口语前缀。这类名字把动词放在前面，听起来像在招呼人做事，
 * 是 SaaS 命名里真实存在的一路（getlinear、trycloudflare、meetgoogle 风格）。
 * 前缀本身不承载含义，主体必须是真实单词或真实词组。
 */
const FRIENDLY_PREFIXES = [
  "get", "try", "use", "hey", "hi", "meet", "go", "join", "ask",
  "pick", "run", "with", "onmy",
];

const FRIENDLY_PREFIX_SET = new Set(FRIENDLY_PREFIXES);

/** 剥掉口语前缀后的剩余部分；用于审计时识别主体词。 */
export function stripFriendlyPrefix(name: string): string {
  const lower = name.toLowerCase().replace(/[^a-z]/g, "");
  for (const prefix of FRIENDLY_PREFIXES) {
    if (lower.startsWith(prefix) && lower.length > prefix.length + 2) {
      return lower.slice(prefix.length);
    }
  }
  return lower;
}

/** 常见 AI 中文命名套路。命中即淘汰。 */
export const CHINESE_INVENTED_PATTERNS: RegExp[] = [
  /^[智云星极光速达飞腾创联未蓝]/,
  /[云智联创星极界域枢擎核链脑图]$/,
  /^(未来|智慧|智能|数字|云端|无限|无界|万象|元初|原点|本源|归一|知行|启明|致远|观澜|听云|见山|灵犀|数说)/,
  /^[a-zA-Z]+$/,
];

/** 判断推荐理由和产品描述是否有共同内容时用的停用词。 */
export const STOPWORDS = new Set([
  "the", "a", "an", "and", "or", "but", "for", "to", "of", "in", "on",
  "at", "by", "with", "from", "as", "is", "are", "was", "were", "be",
  "been", "being", "it", "this", "that", "these", "those", "we", "you",
  "they", "he", "she", "i", "my", "our", "your", "their", "its", "can",
  "will", "would", "should", "could", "do", "does", "did", "not", "no",
  "yes", "so", "if", "then", "than", "too", "very", "just", "also",
  "more", "most", "some", "any", "all", "each", "every", "other",
  "another", "such", "only", "own", "same", "up", "down", "out", "off",
  "over", "under", "again", "further", "once", "here", "there", "when",
  "where", "why", "how", "what", "which", "who", "whom", "whose",
  "about", "into", "through", "during", "before", "after", "above",
  "below", "between", "among", "against", "without", "within", "along",
  "across", "behind", "beyond", "plus", "except", "yet", "still", "even",
  "ever", "never", "always", "often", "sometimes", "usually", "already",
  "almost", "enough", "much", "many", "few", "little", "big", "small",
  "new", "old", "good", "bad", "great", "best", "better", "产品", "用户",
  "我们", "你们", "他们", "一个", "这个", "那个", "什么", "怎么", "不是",
  "而是", "可以", "需要", "进行", "通过", "以及", "或者", "但是", "因为",
  "所以", "如果", "就是", "已经", "还是", "没有", "很多", "非常", "比较",
  "更加", "一直", "然后", "这样", "那样", "一些", "这些", "那些", "自己",
  "大家", "东西", "事情", "时候", "地方", "方式", "方法", "问题", "功能",
  "服务", "工具", "系统", "平台", "数据", "信息", "内容", "管理", "支持",
  "帮助", "提供", "使用", "实现", "完成", "开始", "继续", "包括", "例如",
  "比如", "其实", "主要", "重要", "不同", "相同", "相关", "目前", "现在",
  "未来", "她们", "它们",
]);
