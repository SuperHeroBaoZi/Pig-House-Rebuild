import sys, os
from luaparser import ast
from luaparser.astnodes import Node

ROOT = r"E:\Steam\steamapps\common\Don't Starve Together\mods\pighouse_rebuild"

files = []
for dirpath, _, names in os.walk(ROOT):
    for n in names:
        if n.endswith(".lua"):
            files.append(os.path.join(dirpath, n))

print("要检查的 Lua 文件 %d 个\n" % len(files))
fail = 0
for f in sorted(files):
    src = open(f, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
        # 统计一下解析出的顶层节点数，确认不是空壳
        n = len(tree.body.body) if hasattr(tree, "body") else 0
        print("  [OK]   %-58s  %d 行, 顶层节点 %s" % (os.path.relpath(f, ROOT), src.count("\n")+1, n))
    except Exception as e:
        fail += 1
        print("  [FAIL] %-58s" % os.path.relpath(f, ROOT))
        print("         %s: %s" % (type(e).__name__, e))

print("\n失败 %d 个" % fail)
sys.exit(1 if fail else 0)
