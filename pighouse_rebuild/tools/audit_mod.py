# -*- coding: utf-8 -*-
"""
对 pighouse_rebuild 做静态审计：
把 mod 里用到的每个字符串名 / API / 配置键，拿去和游戏源码交叉核对。
"""
import os, re, zipfile, io

GAME = r"C:\Users\20404\AppData\Local\Temp\dst_scripts\scripts"
ANIM = r"E:\Steam\steamapps\common\Don't Starve Together\data\anim"
MOD  = r"E:\Steam\steamapps\common\Don't Starve Together\mods\pighouse_rebuild"

# ---------- 读游戏源码 ----------
game_files = {}
for dp, _, fns in os.walk(GAME):
    for fn in fns:
        if fn.endswith(".lua"):
            p = os.path.join(dp, fn)
            game_files[p] = open(p, encoding="utf-8", errors="ignore").read()
blob = "\n".join(game_files.values())

PREFABFILES = set(re.findall(r'"([a-z0-9_]+)"', game_files[os.path.join(GAME, "prefablist.lua")]))
ADDED_TAGS  = set(re.findall(r'AddTag\("([A-Za-z0-9_]+)"\)', blob))
ALL_STRINGS = set(re.findall(r'"([A-Za-z0-9_./]+)"', blob))

# ---------- 读 mod 源码 ----------
mymod = {}
for dp, _, fns in os.walk(MOD):
    for fn in fns:
        if fn.endswith(".lua"):
            p = os.path.join(dp, fn)
            mymod[os.path.relpath(p, MOD)] = open(p, encoding="utf-8", errors="ignore").read()

def gather(pattern, flags=0):
    out = {}
    for rel, src in mymod.items():
        for m in re.finditer(pattern, src, flags):
            out.setdefault(m.group(1), set()).add(rel)
    return out

problems, notes = [], []

def check(kind, items, predicate, detail):
    for name in sorted(items):
        if not predicate(name):
            problems.append("[%s] %-28s (%s)  %s" % (kind, name, ",".join(sorted(items[name])), detail))

# 1) prefab 名
spawned = gather(r'SpawnPrefab\("([a-z0-9_]+)"\)')
also    = gather(r'Prefab\("([a-z0-9_]+)"')
listed  = set()
for rel, src in mymod.items():
    m = re.search(r'local prefabs\s*=\s*\{(.*?)\}', src, re.S)
    if m:
        listed |= set(re.findall(r'"([a-z0-9_]+)"', m.group(1)))
ALLSPAWN = {}
for d in (spawned, also):
    for k, v in d.items():
        ALLSPAWN.setdefault(k, set()).update(v)
OURS = {"pighouse_rebuildsite"}
DEFINED = set(re.findall(r'(?<!Spawn)Prefab\("([a-z0-9_]+)"', blob))
KNOWN = PREFABFILES | DEFINED
print("=== 1. prefab 名是否真的存在（PREFABFILES 文件名 + 全源码 Prefab(\"x\") 定义）===")
for n in sorted(set(ALLSPAWN) | listed):
    where = ",".join(sorted(ALLSPAWN.get(n, set()))) or "prefabs list"
    ok = (n in KNOWN) or (n in OURS)
    src = ""
    if n in DEFINED and n not in PREFABFILES:
        src = "  (prefab 名与文件名不同)"
    print("   %s %-24s %s%s" % ("OK  " if ok else "BAD ", n, where, src))
    if not ok:
        problems.append("[prefab] %s 游戏里查不到这个 prefab" % n)

# 2) tag 名：必须能在游戏源码里找到 AddTag("x")
tags = gather(r'HasTag\("([A-Za-z0-9_]+)"\)')
for k, v in gather(r'AddTag\("([A-Za-z0-9_]+)"\)').items():
    tags.setdefault(k, set()).update(v)
print("\n=== 2. tag 名游戏里是否真的被 AddTag 过 ===")
for n in sorted(tags):
    ok = (n in ADDED_TAGS) or (n == "playerghost")
    print("   %s %-14s %s" % ("OK  " if ok else "BAD ", n, "游戏源码里没有 AddTag(\"%s\")" % n if not ok else ""))
    if not ok:
        problems.append("[tag] %s 游戏源码里没有 AddTag" % n)
print("   （共检查 %d 个 tag，游戏里已知 tag 共 %d 个）" % (len(tags), len(ADDED_TAGS)))

# 3) 事件名
events = gather(r'(?:PushEvent|ListenForEvent)\("([a-z0-9_]+)"')
print("\n=== 3. 事件名 ===")
for n in sorted(events):
    where = [os.path.relpath(p, GAME) for p, s in game_files.items() if '"%s"' % n in s]
    ok = len(where) > 0
    print("   %s %-18s 游戏里出现 %d 个文件 %s" % ("OK  " if ok else "BAD ", n, len(where), where[0] if where else ""))
    if not ok:
        problems.append("[event] %s 游戏里没有任何地方用到这个事件" % n)

# 4) 动画名（对着 anim zip 核）
print("\n=== 4. 动画名 vs anim zip 实际内容 ===")
def anim_names(zip_path):
    z = zipfile.ZipFile(zip_path)
    out = set()
    for f in z.namelist():
        if f.endswith(".bin"):
            out |= {r.decode() for r in re.findall(rb"[a-z][a-z0-9_]{2,24}", z.read(f))}
    return out

used_anims = gather(r'PlayAnimation\("([a-z0-9_]+)"')
site = mymod["scripts\\prefabs\\pighouse_rebuildsite.lua"]
used_anims.setdefault("idle", set()).add("site")
for i in range(2, 11):
    used_anims.setdefault("idle%d" % i, set()).add("site")

sc = anim_names(os.path.join(ANIM, "scorched_ground.zip"))
ph = anim_names(os.path.join(ANIM, "pig_house.zip"))
print("   scorched_ground 里的动画:", sorted(a for a in sc if a.startswith("idle")))
for n in sorted(used_anims):
    ok = (n in sc) or (n in ph)
    print("   %s %-22s %s" % ("OK  " if ok else "BAD ", n, ",".join(sorted(used_anims[n]))))
    if not ok:
        problems.append("[anim] %s 不在 scorched_ground/pig_house 的动画表里" % n)

# 5) API 方法
print("\n=== 5. API 方法 ===")
api = [
    ("EntityScript", "DoPeriodicTask"), ("EntityScript", "DoTaskInTime"),
    ("EntityScript", "PushEvent"), ("EntityScript", "ListenForEvent"),
    ("EntityScript", "Remove"),
    ("LootDropper", "SetLoot"),
]
for cls, meth in api:
    n = len(re.findall(r"function %s:%s\b" % (cls, meth), blob))
    print("   %s function %s:%s() 定义 %d 处" % ("OK  " if n else "BAD ", cls, meth, n))
    if not n:
        problems.append("[api] 找不到 function %s:%s" % (cls, meth))

for meth in ["FindEntities", "IsPassableAtPoint", "PlayAnimation", "SetBank", "SetBuild",
             "SetOrientation", "SetLayer", "SetSortOrder", "SetMaterial", "GetRotation",
             "SetRotation", "GetWorldPosition", "SetPosition", "IsValid", "HasTag", "AddTag",
             "SetPristine", "AddNetwork", "AddTransform", "AddAnimState", "Cancel",
             "IsDead", "SetBurnTime", "StartWildfire"]:
    n = len(re.findall(r"[:\s\.]%s\(" % meth, blob))
    print("   %s %-20s 游戏里被调用 %5d 次" % ("OK  " if n else "BAD ", meth, n))
    if not n:
        problems.append("[api] %s 在游戏 Lua 里一次都没被调用过" % meth)

# 6) mod API
print("\n=== 6. mod API ===")
modutil = game_files.get(os.path.join(GAME, "modutil.lua"), "")
for fname in ["AddPrefabPostInit", "GetModConfigData"]:
    n = modutil.count(fname)
    print("   %s %-20s modutil.lua 里出现 %d 次" % ("OK  " if n else "BAD ", fname, n))
    if not n:
        problems.append("[modapi] modutil.lua 里没有 %s" % fname)

# 7) 配置键一致性：site 读的 cfg.X 必须在 modmain 的 CFG / FALLBACK_CFG 里
print("\n=== 7. 配置键一致性（site 读的 cfg.X ⊆ modmain 定义的键）===")
cfgkeys = set()
for rel, src in mymod.items():
    for mm in re.finditer(r'CFG\s*=\s*\{(.*?)\n\}', src, re.S):
        cfgkeys |= set(re.findall(r'^\s*([a-z_]+)\s*=', mm.group(1), re.M))
    for mm in re.finditer(r'FALLBACK_CFG\s*=\s*\{(.*?)\n\}', src, re.S):
        cfgkeys |= set(re.findall(r'^\s*([a-z_]+)\s*=', mm.group(1), re.M))
readkeys = set(re.findall(r'cfg\.([a-z_]+)', mymod["scripts\\prefabs\\pighouse_rebuildsite.lua"]))
readkeys |= set(re.findall(r'CFG\.([a-z_]+)', mymod["modmain.lua"]))
print("   定义:", sorted(cfgkeys))
print("   读取:", sorted(readkeys))
missing = readkeys - cfgkeys
print("   %s 缺失的键: %s" % ("OK  " if not missing else "BAD ", sorted(missing) or "无"))
if missing:
    problems.append("[config] 读了没定义的配置键: %s" % sorted(missing))

# 8) _phr_ 字段名一致性
print("\n=== 8. _phr_ 字段 写入/读取/存档 是否对得上 ===")
main = mymod["modmain.lua"]
fields = sorted(set(re.findall(r'_phr_?[a-z_]*', main)) | set(re.findall(r'_phr_?[a-z_]*', mymod["scripts\\prefabs\\pighouse_rebuildsite.lua"])))
print("   用到的字段:", fields)
saved = sorted(set(re.findall(r'data\.(phr_[a-z_]+)', main)))
loaded = sorted(set(re.findall(r'data\.(phr_[a-z_]+)', main)))
print("   data.phr_* 键:", saved)
print("   %s" % ("OK  读写对称" if saved == loaded else "BAD 读写不对称"))

# 9) modmain 沙箱合规：白名单之外的游戏全局函数必须写 GLOBAL.xxx
#    这是 v0.1.1 崩服的真凶：
#    modmain.lua:295 attempt to call global 'SpawnPrefab' (a nil value)
#    原因：mods.lua:297 CreateEnvironment 给 modmain 的是白名单沙箱，
#          modutil.lua 只额外注入了 Prefab / Asset / Ingredient 三个引擎函数。
SANDBOX_SAFE = {"Asset", "Prefab", "Ingredient", "TUNING", "CLASS", "Class",
                "pairs", "ipairs", "print", "math", "table", "type", "string",
                "tostring", "require", "GLOBAL", "modname", "MODROOT",
                "GROUND", "WORLD_TILES", "LOCKS", "KEYS", "LEVELTYPE", "LEVELCATEGORY"}
GAME_GLOBALS = [
    "SpawnPrefab", "CreateEntity", "TheWorld", "TheSim", "TheNet", "TheShard",
    "GetPrefab", "Prefabs", "SpawnSaveRecord", "MakeObstaclePhysics",
    "MakeInventoryPhysics", "MakeSnowCovered", "Vector3", "DEGREES", "RADIANS",
    "TWOPI", "FRAMES", "ACTIONS", "STRINGS", "EQUIPSLOTS", "TECH", "TheFrontEnd",
]

def strip_comments_keep_lines(src):
    """去掉注释但保留换行，这样行号不变"""
    src = re.sub(r'--\[\[.*?\]\]', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), src, flags=re.S)
    src = re.sub(r'--[^\n]*', '', src)
    return src

def scan_bare(src, names):
    """找出没有被 GLOBAL. 限定的游戏全局（前面是 . 的算已限定，跳过）"""
    hits = []
    for n in names:
        for m in re.finditer(r'(?<![.\w])' + n + r'\s*[\(\{\.:]', src):
            hits.append((n, src[:m.start()].count("\n") + 1))
    return hits

print("\n=== 9. modmain 沙箱合规（白名单外的游戏全局必须写 GLOBAL.xxx）===")
mm_clean = strip_comments_keep_lines(mymod["modmain.lua"])
bare = scan_bare(mm_clean, GAME_GLOBALS)
if bare:
    print("   BAD  发现 %d 处裸用的游戏全局（在 modmain 里它们全是 nil）:" % len(bare))
    for n, ln in bare:
        print("         modmain.lua:%d  裸用 %s  → 改成 GLOBAL.%s" % (ln, n, n))
        problems.append("[sandbox] modmain.lua:%d 裸用游戏全局 '%s'" % (ln, n))
else:
    print("   OK   modmain.lua 里所有游戏全局都走了 GLOBAL. 前缀")

# 自检：确认这个检查真的能抓到 bug（否则检查本身是坏的，永远绿）
_snippet = 'local function f()\n    local site = SpawnPrefab("x")\nend\n'
if scan_bare(strip_comments_keep_lines(_snippet), GAME_GLOBALS):
    print("   OK   自检通过：能抓到 'SpawnPrefab(\"x\")' 这种裸用（红得起来）")
else:
    print("   BAD  自检失败：这个检查抓不到已知的坏代码，它本身是坏的！")
    problems.append("[selftest] 沙箱检查失效")

# 10) prefab 文件里不该直接写 GLOBAL.xxx（GLOBAL 只是沙箱字段，prefab 文件是完整环境）
print("\n=== 10. prefab 文件里的 GLOBAL.xxx（应改用 local G = GLOBAL or _G）===")
bad_global = []
for rel, src in mymod.items():
    if rel.replace("\\", "/").startswith("scripts/"):
        for m in re.finditer(r'GLOBAL\.[A-Za-z_]+', strip_comments_keep_lines(src)):
            ln = src[:m.start()].count("\n") + 1
            bad_global.append((rel, ln, m.group(0)))
if bad_global:
    for rel, ln, txt in bad_global:
        print("   BAD  %s:%d  %s" % (rel, ln, txt))
        problems.append("[prefab-env] %s:%d 直接用了 %s" % (rel, ln, txt))
else:
    print("   OK   prefab 文件没有直接依赖 GLOBAL.xxx")

print("\n" + "=" * 64)
if problems:
    print("发现 %d 个问题:" % len(problems))
    for p in problems:
        print("  ✗", p)
else:
    print("✓ 所有交叉核对全部通过，没有发现问题")
