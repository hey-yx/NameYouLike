"""真实内置统计冒烟：验证自然度分布与真实碰撞（离线，确定性）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brandgen import BrandEngine, StyleParams, build, load_patterns  # noqa: E402

BUNDLED = (
    Path(__file__).resolve().parent.parent / "brandgen" / "data" / "naming_patterns.slim.json"
)

stats = load_patterns(str(BUNDLED))
print(f"内置统计版本: {stats.version}")
print(f"索引规模: exact={len(stats.exact_names)} phonetic={len(stats.phonetic_keys)}")

for name in ("麒麟", "赤兔", "美团", "腾讯", "华为"):
    print(f"  {name}: exact={name in stats.exact_names} collision={stats.collision(name)}")

print("\n--- 赤兔/飞跃 tech 全池统计模式 ---")
eng = BrandEngine(StyleParams(style="tech", limit=15, patterns_file=str(BUNDLED)))
cands = eng.generate(["赤兔", "飞跃"])
print(f"剔除精确重名: {eng.last_dropped}")
for c in cands:
    coll = f" ⚠同音[{c.collision['existing']}]" if c.collision else ""
    print(f"  {c.name:<4} score={c.score:<5} phonetic={c.phonetic}{coll}")

print("\n--- 全池碰撞扫描（limit=500）---")
eng2 = BrandEngine(StyleParams(style="tech", limit=500, patterns_file=str(BUNDLED)))
all_c = eng2.generate(["赤兔", "飞跃", "麒麟"])
ph = [c for c in all_c if c.collision]
print(f"池规模={len(all_c)} 精确剔除={len(eng2.last_dropped)} 同音碰撞={len(ph)}")
for c in ph[:8]:
    print(f"  {c.name} → 同音『{c.collision['existing']}』 score={c.score}")
for d in eng2.last_dropped[:8]:
    print(f"  剔除: {d['name']}（{d['origin'][:30]}…）")
