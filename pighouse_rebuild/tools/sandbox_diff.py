# -*- coding: utf-8 -*-
"""
DST mod 环境合规检查（AST 版）—— 两个文件跑在**两种不同环境**里，规矩不同：

  (A) modmain.lua  → 白名单沙箱（scripts/mods.lua:297 CreateEnvironment）
      SpawnPrefab / CreateEntity / TheWorld / TheSim / TheNet 全是 nil，
      必须写 GLOBAL.xxx。白名单外的名字读到 nil（沙箱没有 metatable，不报错），调用即崩。

  (B) scripts/prefabs/*.lua → 完整环境 _G（scripts/mainfunctions.lua:145
      LoadPrefabFile 用 loadfile()，没有 setfenv），裸名才是对的。
      但 DST 开着 scripts/strict.lua，它的 __index 会对**未声明**的全局直接
      error("variable 'X' is not declared")，而不是返回 nil。
      典型陷阱：`local G = GLOBAL or _G`
        —— GLOBAL 只存在于 modmain 的沙箱里（全游戏只有 mods.lua:328 有
           `GLOBAL = _G`，而且它是**沙箱表的字段**，不是 _G 的字段），
           在 prefab 文件（环境=_G）里读它 → strict 报错 → 整个 mod 被禁用。

所以本脚本有两条硬规则：
  (A) modmain 里出现的引擎全局必须 GLOBAL. 限定
  (B) prefab 文件里**绝不能**读未声明的全局；GLOBAL 单独特殊对待（永远是错的）

用法：
    python sandbox_diff.py [mod目录]     # 默认检查 pighouse_rebuild
"""
import os, re, sys
from luaparser import ast

GAME = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\20404\AppData\Local\Temp\dst_scripts\scripts"
if not os.path.isdir(GAME):
    sys.exit("！！！ 找不到游戏源码目录 %s\n"
             "    先用 [IO.Compression.ZipFile] 把 data\\databundles\\scripts.zip 解出来，"
             "或者用第二个参数指定，例如：\n"
             "    python sandbox_diff.py <mod目录> <游戏scripts目录>" % GAME)
MOD  = sys.argv[1] if len(sys.argv) > 1 else r"E:\Steam\steamapps\common\Don't Starve Together\mods\pighouse_rebuild"

def strip_comments(src):
    """去注释但保留换行（行号不变）。注意：扫"名字是否存在于游戏里"时也必须先去注释，
    否则注释里的词会被误判成真代码 —— 上一版就是这么给 GLOBAL 判了假的 OK。"""
    src = re.sub(r'--\[\[.*?\]\]', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), src, flags=re.S)
    src = re.sub(r'--[^\n]*', '', src)
    return src

mods_lua    = open(os.path.join(GAME, "mods.lua"), encoding="utf-8", errors="ignore").read()
modutil_lua = open(os.path.join(GAME, "modutil.lua"), encoding="utf-8", errors="ignore").read()

# ---------------- 1) modmain 白名单（沙箱）----------------
sandbox = {"pairs", "ipairs", "print", "math", "table", "string", "type",
           "tostring", "require", "Class"}
m = re.search(r'local env\s*=\s*\{(.*?)\n\t\}', mods_lua, re.S)
env_keys = re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=', m.group(1), re.M) if m else []
sandbox |= set(env_keys)
injected = set(re.findall(r'env\.([A-Za-z_][A-Za-z0-9_]*)\s*=', modutil_lua))
injected |= set(re.findall(r'env\["([A-Za-z_][A-Za-z0-9_]*)"\]\s*=', modutil_lua))
sandbox |= injected
print("【A】modmain 沙箱白名单：Lua基础库10 + CreateEnvironment %d + modutil注入 %d = %d 个"
      % (len(env_keys), len(injected), len(sandbox)))
print("      其中引擎函数只有: %s" % ", ".join(sorted(injected & {"Prefab", "Asset", "Ingredient"})))

# ---------------- 2) prefab 文件的 _G 里有什么 ----------------
# 判定依据：**去掉注释后**名字在游戏源码里裸用过（排除 mod 系统文件，那里的 GLOBAL 是沙箱字段）
MOD_SYSTEM_FILES = {"mods.lua", "modutil.lua", "modindex.lua"}
game_blob = ""
for dp, _, fns in os.walk(GAME):
    for fn in fns:
        if fn.endswith(".lua") and fn not in MOD_SYSTEM_FILES:
            game_blob += strip_comments(open(os.path.join(dp, fn), encoding="utf-8", errors="ignore").read())

BASE_LUA = {  # 完整环境里 Lua 标准库都在
    "pairs", "ipairs", "print", "math", "table", "string", "type", "tostring",
    "tonumber", "require", "rawget", "rawset", "_G", "next", "select", "unpack",
    "pcall", "xpcall", "error", "assert", "setmetatable", "getmetatable",
    "loadfile", "dofile", "collectgarbage", "os", "io", "coroutine", "debug",
}
# 这个只能在 modmain 沙箱里读到，prefab 文件（环境=_G）里读它就是 strict 报错
SANDBOX_ONLY = {"GLOBAL"}
print("【B】prefab 文件的 _G：Lua标准库 %d 个 + 游戏源码（已去注释）里出现过的名字" % len(BASE_LUA))
print("      永远禁止出现在 prefab 文件里的名字: %s" % ", ".join(sorted(SANDBOX_ONLY)))

# ---------------- 3) 通用：抽出"全局读" ----------------
def collect_globals(src):
    tree = ast.parse(src)
    nodes = list(ast.walk(tree))
    field_or_method, locals_, store = set(), set(), set()

    def add_names(seq):
        for a in seq or []:
            if type(a).__name__ == "Name":
                locals_.add(a.id)

    for n in nodes:
        t = type(n).__name__
        if t == "Index":
            idx = getattr(n, "idx", None)
            if idx is not None and type(idx).__name__ == "Name":
                field_or_method.add(idx.id)
        elif t == "Invoke":
            fn = getattr(n, "func", None)
            if fn is not None and type(fn).__name__ == "Name":
                field_or_method.add(fn.id)
        elif t == "Field":
            key = getattr(n, "key", None)
            if key is not None and type(key).__name__ == "Name":
                field_or_method.add(key.id)
        elif t == "LocalAssign":
            add_names(getattr(n, "targets", None))
        elif t == "Assign":
            for tg in getattr(n, "targets", []) or []:
                if type(tg).__name__ == "Name":
                    store.add(tg.id)
        elif t == "LocalFunction":
            nm = getattr(n, "name", None)
            if nm is not None and type(nm).__name__ == "Name":
                locals_.add(nm.id)
            add_names(getattr(n, "args", None))
            add_names(getattr(n, "parameters", None))
        elif t in ("Function", "AnonymousFunction", "Method"):
            add_names(getattr(n, "args", None))
            add_names(getattr(n, "parameters", None))
        elif t == "Forin":
            add_names(getattr(n, "targets", None))
        elif t == "Fornum":
            nm = getattr(n, "target", None)
            if nm is not None and type(nm).__name__ == "Name":
                locals_.add(nm.id)

    out = {}
    for n in nodes:
        if type(n).__name__ != "Name":
            continue
        i = n.id
        if i in locals_ or i in field_or_method or i in store:
            continue
        out.setdefault(i, 1)
    return out

# ---- 自检：识别器正例必抓、反例不误报 ----
SELF = ('local a = 1\n'
        'local function g(p, q)\n'
        '    local site = SpawnPrefab("x")\n'
        '    local gg = GLOBAL or _G\n'
        '    return p, q, a, gg\n'
        'end\n'
        'local t = TheWorld.ismastersim\n'
        'local obj = {}\nobj.field = 2\nobj:Method()\n'
        'for kk, vv in ipairs(GLOBAL.L) do end\n')
hits = collect_globals(SELF)
must_hit = {"SpawnPrefab", "GLOBAL", "_G", "TheWorld", "ipairs"}
must_not = {"a", "p", "q", "site", "t", "obj", "field", "Method", "kk", "vv", "gg"}
missed = sorted(must_hit - set(hits))
wrong = sorted(must_not & set(hits))
selftest_ok = not missed and not wrong
print("\n[自检1] 全局识别器: %s%s%s" % ("通过" if selftest_ok else "!!! 失败 !!!",
                                      (" 漏抓=%s" % missed) if missed else "",
                                      (" 误报=%s" % wrong) if wrong else ""))
problems = [] if selftest_ok else ["自检失败：全局识别器不可靠"]

# 自检2：SANDBOX_ONLY 的名字必须被判成 BAD（直接测判定分支，不看语料）
_probe = collect_globals('local x = GLOBAL\n')
_probe_bad = sorted(n for n in _probe if n in SANDBOX_ONLY)
_selftest2_ok = (_probe_bad == sorted(SANDBOX_ONLY))
print("[自检2] SANDBOX_ONLY 判定分支: %s（样本 'local x = GLOBAL' 里被判 BAD 的 = %s）"
      % ("通过" if _selftest2_ok else "!!! 失败 !!!", _probe_bad))
if not _selftest2_ok:
    problems.append("自检失败：SANDBOX_ONLY 的判定分支不可靠")
print("[参考] 去注释后 GLOBAL 在游戏源码语料里出现 %d 次（(B) 阶段靠 SANDBOX_ONLY 硬规则拦，不依赖此数）"
      % len(re.findall(r'(?<![\w.:])GLOBAL(?![\w])', game_blob)))

# ---------------- 4) (A) 检查 modmain ----------------
main_src = open(os.path.join(MOD, "modmain.lua"), encoding="utf-8").read()
main_globals = collect_globals(strip_comments(main_src))

print("\n=== (A) modmain.lua 真实全局读 %d 个（必须都在沙箱白名单里）===" % len(main_globals))
for name in sorted(main_globals):
    ok = name in sandbox
    print("   %s %-26s" % ("OK " if ok else "BAD", name))
    if not ok:
        problems.append("modmain.lua 裸用白名单外的全局 '%s' → 必须写 GLOBAL.%s" % (name, name))

declared_by_modmain = set(re.findall(r'GLOBAL\.([A-Za-z_][A-Za-z0-9_]*)\s*=', main_src))
print("   modmain 声明给外部用的名字: %s" % (", ".join(sorted(declared_by_modmain)) or "无"))

# ---------------- 5) (B) 检查 prefab 文件 ----------------
print("\n=== (B) prefab 文件的全局读（strict.lua 会拦住未声明的读取）===")
pf_dir = os.path.join(MOD, "scripts", "prefabs")
checked_any = False
if os.path.isdir(pf_dir):
    for rel in sorted(os.listdir(pf_dir)):
        if not rel.endswith(".lua"):
            continue
        checked_any = True
        src = open(os.path.join(pf_dir, rel), encoding="utf-8").read()
        for name in sorted(collect_globals(strip_comments(src))):
            if name in SANDBOX_ONLY:
                print("   BAD  %-22s (%s)  ← 只在 modmain 沙箱里有，prefab 文件里读它会 strict 报错" % (name, rel))
                problems.append("%s 里读了 '%s' —— 它只存在于 modmain 沙箱（mods.lua:328），"
                                "_G 里没有它，strict.lua 会报 \"variable '%s' is not declared\" 并禁用整个 mod"
                                % (rel, name, name))
                continue
            if name in BASE_LUA:
                continue
            if name in declared_by_modmain:
                print("   OK   %-22s (%s)  modmain 有声明 ✓" % (name, rel))
                continue
            bare = len(re.findall(r'(?<![\w.:])' + name + r'(?![\w])', game_blob))
            ok = bare > 0
            print("   %s %-22s (%s)  游戏源码（去注释）里裸用 %d 次" % ("OK " if ok else "BAD", name, rel, bare))
            if not ok:
                problems.append("%s 里读了未声明的全局 '%s'，strict.lua 会直接报错" % (rel, name))
if not checked_any:
    print("   （没有 prefab 文件）")

# ---------------- 6) (C) modmain 里的 GLOBAL.xxx ----------------
# 沙箱里通往真全局表的唯一入口是 GLOBAL（= _G），而 _G 挂着 strict.lua 的 metatable：
#  · __index   —— 读一个"从未声明过"的名字会 error（不是返回 nil），例：GLOBAL.Tunngs 拼错
#  · __newindex —— 只允许**主 chunk 顶层**赋值新全局；缩进处赋值会报
#                  "assign to undeclared variable"
print("\n=== (C) modmain 里 GLOBAL.xxx 用到的名字 ===")
main_reads = sorted(set(re.findall(r'GLOBAL\.([A-Za-z_][A-Za-z0-9_]*)', strip_comments(main_src))))
top_own = set(re.findall(r'^GLOBAL\.([A-Za-z_][A-Za-z0-9_]*)\s*=', main_src, re.M))
indented_own = set(re.findall(r'^[ \t]+GLOBAL\.([A-Za-z_][A-Za-z0-9_]*)\s*=', main_src, re.M)) - top_own
for name in main_reads:
    if name in BASE_LUA:
        print("   OK  GLOBAL.%-24s Lua 标准库" % name)
    elif len(re.findall(r'(?<![\w.:])' + name + r'(?![\w])', game_blob)) > 0:
        print("   OK  GLOBAL.%-24s 游戏全局（源码里出现过）" % name)
    elif name in top_own:
        print("   OK  GLOBAL.%-24s 本 mod 自己顶层声明 ✓" % name)
    else:
        print("   BAD GLOBAL.%-24s 找不到这个全局 → 读它会被 strict.lua 拦住" % name)
        problems.append("modmain 里读了 GLOBAL.%s，但游戏源码里找不到这个名字（拼错了？）"
                        "—— strict.lua 会报 \"variable '%s' is not declared\"" % (name, name))
for name in sorted(indented_own):
    if len(re.findall(r'(?<![\w.:])' + name + r'(?![\w])', game_blob)) == 0:
        print("   BAD GLOBAL.%-24s 是【缩进处】的赋值，且它不是游戏全局" % name)
        problems.append("modmain 里在缩进处（非主 chunk 顶层）给 GLOBAL.%s 赋值 —— "
                        "strict.lua 的 __newindex 会报 'assign to undeclared variable'" % name)

print("\n" + "=" * 66)
if problems:
    print("发现 %d 个问题：" % len(problems))
    for p_ in problems:
        print("   ✗", p_)
    sys.exit(1)
print("✓ 环境合规检查通过（modmain 沙箱合规 + prefab 文件全局读都已声明）")
