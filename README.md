# 猪人房重建 (Pig House Rebuild) v0.1.5

Don't Starve Together 服务端 mod ｜ 作者 20404

![预览图](preview.png)

> 预览图由 `tools/make_preview.py` 用 Pillow 直接绘制（2× 超采样抗锯齿），改了文字/配色重跑一次即可。

---

## 效果

有两条路，都能"自己再建起来"：

### ① 被拆掉

1. **和原版一模一样**：掉材料、里面的猪跑出来（变敌对）、木屑特效、房子直接消失
2. 原地留下一块**很淡的地面印子**（用游戏自带素材，几乎看不出来）
3. 过 **4 个游戏日**（默认，可调）之后，那块印子的位置**重新长出一间猪人房**，木屑特效 + 房子自带的生长动画，并自动住进一只猪

### ② 被烧掉

1. 房子烧完 → 变成**焦黑的废墟**（这是原版行为，废墟照旧留在原地，还能被锤 1 下清掉）
2. 焦黑废墟在原地待 **4 个游戏日**（同一个设置）
3. 时间到 → 焦黑废墟冒木屑，**原地变回一间完好的新房子**，猪也回来了
4. **不需要玩家再锤那一下**；当然玩家也可以提前锤掉它，那就会走 ① 的路子（留痕迹 + 正常重建）

> 1 游戏日 = 480 秒 = 8 分钟真实时间（`tuning.lua:19-20`：`seg_time=30` × 16）

---

## 安装

mod 已经放在：

```
E:\Steam\steamapps\common\Don't Starve Together\mods\pighouse_rebuild\
```

启动游戏 → 主菜单 **模组** → **服务器模组** → 找到「猪人房重建 (Pig House Rebuild)」→ 打勾启用 → 进世界。

> 这是服务端 mod（`all_clients_require_mod = false`）。别人不加也能进你的服，
> 只是他们看不到那块地面痕迹而已，房子本身照样看得见。

---

## 测试步骤

**最简单的测法 —— 完全不用控制台：**

> 模组设置里把「重建等待时间」改成 **「最快 30 秒（测试用）」** → 进世界 → 随便找间猪人房，用锤子砸掉 → 半分钟后它就自己长回来了。看完记得改回「4 天」。

**想看细节就用控制台：**

进世界后按 `~` 键（键盘左上角、数字 1 左边那个）打开控制台。
如果命令提示作弊被禁用，就在「世界设置」里把「作弊」改成启用（新建世界时设定）；
或者干脆用上面那个 30 秒测试选项，效果完全一样。

### A. 测"拆掉后重建"

| 步骤 | 命令 / 操作 | 应该看到 |
|---|---|---|
| 1 | `c_spawn("pighouse")` | 面前出现一间猪人房，一会儿亮灯、住进一只猪 |
| 2 | 用锤子砸 4 下 | 掉 **2 木板 + 2 石砖 + 2 猪皮**、猪跑出来变敌对、木屑特效、房子消失 |
| 3 | 调高视角看看地面 | 原地有一块**很淡的印子**（偏暗的地面贴花） |
| 4 | `c_findnext("pighouse_rebuildsite").remaining = 3` | 倒计时改成 3 秒 → **3 秒后原地长出新房子**（木屑 + 生长动画） |
| 5 | 再砸掉这间新房子 | 只掉 **1 块木板**（掉落削弱生效） |

### B. 测"烧掉后重建"

| 步骤 | 命令 / 操作 | 应该看到 |
|---|---|---|
| 1 | `c_spawn("pighouse")` | 出现一间猪人房 |
| 2 | `c_findnext("pighouse").components.burnable:SetBurnTime(3)` | 把燃烧时间改成 3 秒，省得等 |
| 3 | `c_findnext("pighouse").components.burnable:StartWildfire()` | 房子冒烟 → 烧起来 → 烧成**焦黑的废墟**（猪会跑出来） |
| 4 | `c_findnext("pighouse")._phr_regrow = 3` | 把"自己变回新房子"的倒计时改成 3 秒 |
| 5 | 等 3 秒 | 焦黑废墟冒木屑 → **变回一间完好的新房子**，住进一只猪 |

### C. 测存档

拆掉（或烧掉）后，趁倒计时没走完就存档退出 → 重进世界 → 痕迹／焦黑废墟还在，倒计时接着走，到点照样长回来。

**排查用命令：**
```lua
c_findnext("pighouse_rebuildsite")             -- 找到痕迹实体，打印 GUID
= c_findnext("pighouse_rebuildsite")           -- 打印实体（能看 remaining / mode）
= c_findnext("pighouse")                       -- 打印猪人房（能看 _phr_regrow）
c_countprefabs("pighouse")                     -- 数一下世界上有几间猪人房
```

---

## 配置项（游戏内「模组」界面可改）

| 选项 | 默认 | 说明 |
|---|---|---|
| 重建等待时间 | **4 天** | 最快 30 秒（测试用）/ 1 天 / 2 天 / 4 天 / 8 天 / 10 天（拆掉和烧掉共用；1 天 = 8 分钟） |
| 重建条件 | **纯计时** | 「附近要有活着的猪人」：附近有活猪才重建，最多等 4 天 |
| 重建后再拆的掉落 | **只掉 1 块木板** | 原版 / 只掉 1 木板 / 什么都不掉 |
| 烧毁的房子自动重建 | **是** | 焦黑废墟过 N 天自己变回新房子；选「否」= 原版行为，废墟不会变回来 |
| 留下地面痕迹 | **是** | 关掉就完全隐形，玩家根本不知道那地方还会再长房子（只影响"被拆"那条路） |
| 玩家自己盖的房子也重建 | **否** | 玩家用配方亲手盖出来的猪人房，被拆/烧后要不要也自动重建。默认「否」= 玩家自己盖的拆了就没了（材料照掉，同原版）；**地图原生的猪人房永远会重建，不受这一项影响**（判据：游戏在玩家建造/部署时推的 `onbuilt` 事件，`components/builder.lua:825`） |

---

## 实现原理（每一处都对应游戏源码）

这个 mod 一共 **3 个 Lua 文件、约 400 行**，全靠"借"游戏自带的机制：

**① 接管「拆房」动作** —— `modmain.lua`

原版 `scripts/prefabs/pighouse.lua:411`：

```lua
inst.components.workable:SetOnFinishCallback(onhammered)
```

而 `scripts/components/workable.lua:162` 是直接调用这个函数引用。所以我们用
`AddPrefabPostInit("pighouse")` 把这个引用**包一层**，先原样调用原版逻辑
（放猪 / `DropLoot` / `collapse_big` 特效 / `inst:Remove()`），等房子消失之后再
在原地生成一个"记性"实体。**"拆掉"那一瞬间和原版零差异。**

**② 接管「烧成焦黑」这个瞬间** —— `modmain.lua`

房子烧完时，`standardcomponents.lua:58` 的 `DefaultBurntStructureFn` 会推一个事件：

```lua
inst:AddTag("burnt")
inst:AnimState:PlayAnimation("burnt", true)
inst:PushEvent("burntup")
```

（`pighouse.lua:436` 自己也监听了这个 `burntup` 做收尾。）我们挂一个自己的监听，
在这个**焦黑房子自己身上**起倒计时；到点就 `SpawnPrefab("pighouse")` 换掉它。
因为倒计时挂在房子身上，玩家提前锤掉它 → 倒计时自然消失 → 改走"拆掉"那条路。

**③ 用游戏自带的"地面痕迹"当记号** —— `scripts/prefabs/pighouse_rebuildsite.lua`

`scripts/prefabs/scorchedground.lua` 是游戏自带的地面贴花 prefab
（`OnGround` + `LAYER_BACKGROUND` + 10 种随机形状 + 可存档）。
我们直接复用它的 build `scorched_ground`，**零美术成本**、贴地、点不到、不挡建造。

**④ 掉落为什么能精确控制** —— `lootdropper.lua:242`

原版结构掉落**不是硬编码**的，是这么算出来的：

```
配方材料 × TUNING.HAMMER_LOOT_PERCENT(0.5)     -- 烧过的按 BURNT_..._PERCENT(0.25)
```

猪人房配方见 `recipes.lua:583`：

```lua
Recipe2("pighouse", {Ingredient("boards",4), Ingredient("cutstone",3), Ingredient("pigskin",4)}, ...)
```

→ `ceil(4×0.5)=2` 木板、`ceil(3×0.5)=2` 石砖、`ceil(4×0.5)=2` 猪皮。

所以只要给"重建出来的房子"设 `lootdropper.droprecipeloot = false` 再给一张自己的
掉落表，就能精确控制掉落、堵住无限刷材料。这个状态用 `OnSave/OnLoad` 存下来。

**⑤ 重建瞬间的动画**

`pighouse.lua:444` 有 `inst:ListenForEvent("onbuilt", onbuilt)`，而 `onbuilt`
就是播 `place`（生长）+ `idle`。所以我们 `SpawnPrefab("pighouse")` 之后推一个
`PushEvent("onbuilt")` 就复用了玩家自己造房时的那段动画。房子自带的
`pig_house` build 里确实有 `place` / `idle` / `lit` / `hit` / `burnt` 这些动画
（已解析 `data/anim/pig_house.zip` 的 `anim.bin` 确认）。

**⑥ 存档 / 联机为什么不用额外处理**

痕迹是个普通实体，`OnSave/OnLoad` 存 `remaining`（剩余秒数）、随机形状、旋转。
焦黑房子的倒计时存进猪人房自己的存档（包装原版 `OnSave/OnLoad`）。
标签和动画在 DST 里会自动同步给客户端，所以联机不用写任何同步代码。

---

## ⚠️ 踩过的坑：modmain 跑在"白名单沙箱"里（v0.1.2 修的致命 bug）

**症状**：敲猪人房 → 服务器崩溃，日志 `modmain.lua:295: attempt to call global 'SpawnPrefab' (a nil value)`。

**原因**：DST 给 mod 的运行环境是一张硬编码白名单表（`scripts/mods.lua:297-359` 的
`CreateEnvironment`），只有这些能用：

```
pairs / ipairs / print / math / table / string / type / tostring / require / Class
TUNING
GROUND / WORLD_TILES / LOCKS / KEYS / LEVELTYPE / LEVELCATEGORY
GLOBAL（= _G，通往真全局表的唯一入口）
+ 一百多个 mod API（AddPrefabPostInit / GetModConfigData / Recipe ...）
+ 只有三个引擎函数：Prefab / Asset / Ingredient（modutil.lua:830/832/834）
```

**所以 `SpawnPrefab` / `CreateEntity` / `TheWorld` / `TheSim` / `TheNet` 在 modmain 里全是 nil**，
必须写 `GLOBAL.SpawnPrefab(...)`。而且要在**调用点**解析，不能 `local SpawnPrefab = GLOBAL.SpawnPrefab`
捕获——mod 加载时游戏全局可能还没建好。

**而 `scripts/prefabs/*.lua` 是完整环境，裸名才对**（本机 `workshop-2078243581` 的 prefab 文件
就用裸的 `CreateEntity` / `TheWorld`，能正常跑）。

**坑 2（v0.1.3 修的）—— DST 开着 `strict.lua`：读"未声明"的全局会直接报错，不是返回 nil**

`scripts/strict.lua` 给 `_G` 挂了 metatable：

```lua
mt.__index = function (t, n)
  if not mt.__declared[n] and debug.getinfo(2, "S").what ~= "C" then
    error("variable '"..n.."' is not declared", 2)   -- ← 报错，不是返回 nil！
  end
  return rawget(t, n)
end
```

所以：

- **prefab 文件里读一个 `_G` 里不存在的名字 = 直接崩**。我为了"兼容两种环境"写的
  `local G = GLOBAL or _G` 正好踩中：`GLOBAL` 只存在于 modmain 的沙箱里
  （`mods.lua:328`，而且是**沙箱表的字段**，不是 `_G` 的字段），而 prefab 文件的环境是
  `_G` → 读它就报 `variable 'GLOBAL' is not declared` → **整个 mod 被禁用、服务器启动失败**。
- ✅ **正确写法：prefab 文件里直接用裸名。** 引擎全局（`CreateEntity` / `SpawnPrefab` /
  `TheWorld` / `TheSim` / `ANIM_ORIENTATION` / `LAYER_BACKGROUND`）在 DST 启动时都已经被
  顶层赋值"声明"过了，strict 不会拦。
- 要读 modmain 传过来的东西，用 `rawget(_G, "名字")` 绕过 metatable，最安全：
  `rawget(_G, "PIGHOUSE_REBUILD_CFG")`
- modmain 顶层写 `GLOBAL.X = v` 时，strict 的 `__newindex` 会自动把它标记为已声明
  （`mt.__declared[n] = true`），所以跨文件传配置是可行的 ✓

**防复发**：审计脚本里有第 9、10 项专门查这个，并且**自检**（确认它能抓到坏代码，不是永远返回绿）。

---

## 已知限制

- **倒计时按服务器运行时间计**：服务器关着的时候不走（不是"日历天"）。重启后从存档里的剩余秒数接着走。
- 「位置被占」时（玩家在痕迹那儿放了箱子/墙/建筑）会**跳过本次重建**，每 6 小时重试一次，直到位置空出来。
  （"烧掉"那条路不需要这个检查：焦黑废墟本身有碰撞体，玩家没法在它原地盖东西。）
- 地表和洞穴是两个独立分片，各自计时，互不影响。
- 只作用于**普通猪人房**。猪人守卫塔、猪王、猪人商店等不受影响。
- 客户端不装这个 mod 时看不到地面痕迹（但重建出的房子是原版 prefab，所有人都看得见）。
- 关掉 mod 前建议先让痕迹/焦黑废墟长回来，否则世界里的痕迹实体会变成未知 prefab。

---

## 文件结构

```
pighouse_rebuild/
├── modinfo.lua                          # mod 元信息 + 5 个配置项
├── modmain.lua                          # 接管拆毁/烧毁回调、掉落控制、存档包装
├── README.md                            # 本文件
└── scripts/
    └── prefabs/
        └── pighouse_rebuildsite.lua     # 痕迹实体：倒计时 + 位置检查 + 重建
```

---

## 待办 / 可以继续加的东西

- [ ] mod 图标（需要把 png 转成 `.tex` + `.xml`，得用 Klei 的 Mod Tools）
- [ ] 重建前加一点"预警"（比如前一天地上冒一点烟），给玩家反应时间
- [ ] 玩家可以用材料"催熟"重建（提前长出来，但要花木板/猪皮）
- [ ] 让拆房跑出去的猪参与重建（猪活着才重建 + 猪自己走进新房子）
- [ ] 支持猪人守卫塔 / 其他"房子"类结构（兔子窝、鱼人房、猴屋，实现方式完全一样）

---

## 自检工具（改代码后请务必跑一遍）

`tools/` 里放了三脚本，都是我开发这个 mod 时用来"静态抓错"的。DST 的很多错误
在游戏里只表现为**崩溃日志一行**或者**静默失效**，这些脚本能在不进游戏的情况下先抓出来：

| 脚本 | 干什么 | 怎么跑 |
|---|---|---|
| `lua_check.py` | 用 luaparser 解析全部 .lua，检查语法 | `python lua_check.py` |
| `audit_mod.py` | 10 项交叉审计：prefab 名 / tag / 事件 / 动画名 / API / 配置键一致性 / **沙箱合规（第9项）** / prefab 环境（第10项） | `python audit_mod.py` |
| `sandbox_diff.py` | **完整白名单对表**：从游戏源码自动生成 modmain 沙箱白名单（mods.lua 20 项 + modutil.lua 108 项注入），用 AST 取出 modmain 里每个"全局读"逐个对表；同时校验 prefab 文件里的 `G.xxx` 都是真全局 | `python sandbox_diff.py` |

**关键：这三个脚本都带"自检"**——它们会先验证自己**能抓到已知的坏代码**，否则就是
一个永远返回绿的废检查（我踩过这个坑：第一版 `sandbox_diff.py` 因为 luaparser 的
`Name` 节点没有 `ctx` 属性，把所有名字都跳过了，报"0 个全局"的假绿）。

想验证 `sandbox_diff.py` 真的会红，可以拿一个故意写坏的 mod 目录试：

```bash
python sandbox_diff.py "<任意含有裸用 SpawnPrefab 的 modmain.lua 的目录>"
# 应该 exit=1，并精确报出哪一行裸用了哪个全局
```

---

## 更新记录

- **v0.1.5** — 重建等待时间**默认从 2 天改为 4 天**，可选值扩为
  「30 秒（测试用）/ 1 天 / 2 天 / 4 天（默认）/ 8 天 / 10 天」（去掉了原来的「半天」）；
  同时把 `modmain` 的兜底值（`or 2` → `or 4`）和 prefab 文件里的兜底秒数（`960` → `FALLBACK_CFG.seconds` = 1920）
  一起同步，避免"设置读不到时回落到旧默认"。
- **v0.1.4** — 新增「玩家自己盖的房子也重建」开关（**默认：否**）
  起因：原实现对所有服务端猪人房一视同仁 —— 玩家从配方亲手盖的房子被拆掉后也会自动重建。
  现在用 **DST 自带的 `onbuilt` 事件**打"玩家建造"标记
  （`components/builder.lua:825` 玩家用配方建造时推、`prefabutil.lua:71` 部署套装类物品时推；
  **地图生成的原生建筑不会收到** —— 全源码只有 10 个地方推这个事件，除这两个通用入口外都是
  桅杆/船/温泉/擂台等特定 prefab，不会误判到猪人房上）。
  拆除（`onfinish`）和烧毁（`burntup`）两条路都按开关决定留不留重建记号；
  标记随存档走（`data.phr_plt`）。**默认否** = 玩家自己盖的拆了就没了（材料照掉，同原版），
  地图原生的猪人房照常重建。
- **v0.1.3** — 🔴 修**第二个致命 bug**（现象：服务器启动失败、mod 被自动禁用）
  `pighouse_rebuildsite.lua` 里我为了"兼容两种环境"写了 `local G = GLOBAL or _G` ——
  但 `GLOBAL` 只存在于 modmain 沙箱，prefab 文件的环境是 `_G`，而 DST 开着 `strict.lua`：
  **读未声明的全局会直接 `error` 而不是返回 nil** → `variable 'GLOBAL' is not declared`
  → DST 禁用整个 mod 并把它从 cluster 的 `modoverrides.lua` 里删掉。
  修法：prefab 文件全部改回**裸名**，配置用 `rawget(_G, "PIGHOUSE_REBUILD_CFG")` 读；
  modmain 里 `GLOBAL.TheWorld` 改成 `GLOBAL.rawget(GLOBAL, "TheWorld")`（`TheWorld` 从未被
  提前声明，world.lua:422 才第一次赋值）。
  检查器新增两项：**(B) prefab 文件的全局读必须都已声明**（`GLOBAL` 硬规则拦）、
  **(C) modmain 里 `GLOBAL.xxx` 的 xxx 必须是已声明全局 / 顶层赋值**。
- **v0.1.2** — 🔴 修致命 bug：`modmain.lua` 里裸用 `SpawnPrefab` 导致**敲猪人房必崩服**
  （modmain 跑在白名单沙箱里，游戏全局必须写 `GLOBAL.xxx`，详见上面"踩过的坑"）。
  同时修掉 `scripts/prefabs/` 里误用 `GLOBAL.xxx` 的隐患（改成 `local G = GLOBAL or _G`）。
  审计脚本新增第 9/10 项沙箱合规检查 + 自检，防止复发。
- **v0.1.1** — 新增「烧毁的房子 N 天后自动变回完好的新房子」；焦黑废墟被提前锤掉时
  继承已等待的时间，不白等。
- **v0.1.0** — 首版：拆掉的猪人房 N 天后原地重建（隐形地面痕迹 → 木屑 + `place` 生长动画
  → 猪回来住），掉落削弱防止无限刷材料，5 个配置项，中文 README。
