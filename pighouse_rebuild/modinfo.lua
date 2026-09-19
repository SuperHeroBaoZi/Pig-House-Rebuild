--[[
    猪人房重建 / Pig House Rebuild
    ------------------------------------------------------------
    被拆掉的猪人房会在几天之后自己重新建起来。
    Don't Starve Together 专用 | 服务端 mod（客户端不装也能进）

    作者: 20404
    版本: 0.1.0
]]

name = "猪人房重建 (Pig House Rebuild)"
description = [[
玩家把猪人房拆掉后，房子会像原版一样直接消失（材料照掉、里面的猪照跑出来），
但原地会留下一块几乎看不见的地面痕迹。

过 N 个游戏日之后，那块痕迹的位置会重新"长"出一间猪人房，并自动住进一只猪。

原版掉落是「配方材料 × 50%」= 2 木板 + 2 石砖 + 2 猪皮。房子能无限重建的话，
这就能无限刷材料了，所以本 mod 默认把「重建出来的房子」再拆时的掉落改成 1 块木板。

可在 mod 设置里调整：
  · 重建等待时间（0.5 / 1 / 2 / 4 游戏天）
  · 重建条件（纯计时 / 附近必须有活着的猪人）
  · 重建后再拆的掉落（原版 / 只掉 1 木板 / 什么都不掉）
  · 烧毁的房子是否也能重建
  · 是否留下地面痕迹

------------------------------------------------------------
When a player hammers down a Pig House, it vanishes exactly like
vanilla (loot drops, the pig is released). A barely visible ground
mark stays behind. After N game days, a new Pig House grows back
on that spot, with a pig living inside.

Server-side mod: clients do not need to install it.
]]

author = "20404"
version = "0.1.5"

forumthread = ""

api_version = 10

dst_compatible = true
dont_starve_compatible = false
reign_of_giants_compatible = false

-- 服务端 mod：客户端不装也能进服（客户端看不到地面痕迹，其他一切正常）
all_clients_require_mod = false
client_only_mod = false

-- 图标暂时没做（需要把 png 转成 .tex/.xml），先用游戏默认图标
-- icon_atlas = "modicon.xml"
-- icon = "modicon.tex"

priority = -1

configuration_options =
{
    {
        name = "PHR_DAYS",
        label = "重建等待时间",
        hover = "猪人房被拆掉/烧掉后，过多久自动重建。1 游戏日 = 8 分钟（480 秒）→ 4 天 = 32 分钟、8 天 = 64 分钟、10 天 = 80 分钟。『最快 30 秒』是给你测试 mod 用的，正式玩请改回来 —— 30 秒的话就变成半分钟刷 1 块木板了",
        options =
        {
            { description = "最快 30 秒（测试用）", data = 0.02 },
            { description = "1 天",               data = 1 },
            { description = "2 天",               data = 2 },
            { description = "4 天（默认）",        data = 4 },
            { description = "8 天",               data = 8 },
            { description = "10 天",              data = 10 },
        },
        default = 4,
    },

    {
        name = "PHR_MODE",
        label = "重建条件",
        hover = "『附近要有活着的猪人』：只有拆房时跑出去的那只猪还活着（或附近还有别的猪）时才会重建，代入感更强；如果一直没猪，最多等 4 天后还是会自己长回来",
        options =
        {
            { description = "纯计时（房子自己长回来）", data = "timer" },
            { description = "附近要有活着的猪人",       data = "pig" },
        },
        default = "timer",
    },

    {
        name = "PHR_DROP",
        label = "重建后再拆的掉落",
        hover = "原版拆猪人房掉 2 木板 + 2 石砖 + 2 猪皮。房子能重建的话就能无限刷材料，所以这里默认只掉 1 块木板",
        options =
        {
            { description = "原版（可无限刷材料）", data = "vanilla" },
            { description = "只掉 1 块木板",        data = "reduced" },
            { description = "什么都不掉",           data = "none" },
        },
        default = "reduced",
    },

    {
        name = "PHR_BURNT",
        label = "烧毁的房子自动重建",
        hover = "猪人房被烧成焦黑废墟后，过同样长的时间它自己会变回一间完好的新房子（不用玩家再锤一下）。如果玩家提前把焦黑废墟锤掉，也照样会留痕迹、照样会重建。选『否』= 原版行为：焦黑废墟烂在原地，不会变回来",
        options =
        {
            { description = "是", data = true },
            { description = "否（原版行为）", data = false },
        },
        default = true,
    },

    {
        name = "PHR_MARK",
        label = "留下地面痕迹",
        hover = "拆掉的地方留一块很淡的地面印子（用游戏自带素材），表示『这里曾经飞过一间房』。关掉就完全看不见，玩家根本不知道那地方还会再长房子",
        options =
        {
            { description = "是", data = true },
            { description = "否", data = false },
        },
        default = true,
    },

    {
        name = "PHR_PLAYERBUILT",
        label = "玩家自己盖的房子也重建",
        hover = "玩家用配方亲手盖出来的猪人房，拆掉/烧掉后要不要也自动重建？默认『否』—— 玩家自己盖的拆了就没了（材料照掉，和原版一样）。地图上原生的猪人房（猪人村的房子）永远会重建，不受这个选项影响",
        options =
        {
            { description = "否（默认，只重建地图原生的）", data = false },
            { description = "是（玩家盖的也重建）",        data = true },
        },
        default = false,
    },
}
