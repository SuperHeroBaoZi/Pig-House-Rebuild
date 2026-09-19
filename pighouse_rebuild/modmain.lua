--[[--------------------------------------------------------------------
    猪人房重建 / Pig House Rebuild  v0.1.2
    --------------------------------------------------------------------
    ⚠️⚠️ 改这个文件之前必读：DST 的 modmain 跑在"白名单沙箱"里 ⚠️⚠️

      证据（游戏源码 scripts/mods.lua:297-359 的 CreateEnvironment）：
      mod 的环境 env 是一张**硬编码白名单表**，只包含：
        · Lua 基础库   pairs / ipairs / print / math / table / string / type /
                       tostring / require / Class
        · TUNING       （显式写进白名单）
        · 地图世界生成  GROUND / WORLD_TILES / LOCKS / KEYS / LEVELTYPE ...
        · GLOBAL       （= _G，通往真全局表的唯一入口）
        · 一百多个 mod API（AddPrefabPostInit / GetModConfigData / Recipe ...）
      然后 mods.lua:351 用 setfenv(chunk, env) 把这个环境套在 modmain 上。

      所以下面这些**游戏引擎函数在 modmain 里全是 nil**，必须加 GLOBAL. 前缀：
        SpawnPrefab / CreateEntity / TheWorld / TheSim / TheNet / GetPrefab ...

      ⚠️ 而 scripts/prefabs/*.lua 里的 prefab 文件是**完整环境**，裸名可用
         （本机 workshop-2078243581 的 prefab 文件就用裸名 CreateEntity / TheWorld）。
      ⚠️ 但 GLOBAL 自身只是个沙箱字段，不是真全局 —— prefab 文件里读它前要
         先做 `local G = GLOBAL or _G` 兜底，否则会 "index nil value"。

      👉 教训：v0.1.0/0.1.1 在 modmain 里直接写 SpawnPrefab(...) 导致
         敲猪人房瞬间崩服：modmain.lua:295 attempt to call global 'SpawnPrefab'
         (a nil value)。现在全部改成 GLOBAL.xxx，并且在调用点解析（不是文件加载
         时捕获 local，因为 mod 加载时游戏全局可能还没建好）。
    --------------------------------------------------------------------

    玩法
      【被拆】玩家拆掉猪人房 → 房子和原版一样直接消失（放猪 / 掉落 / 木屑
              特效全部保持原版）→ 原地留下一点几乎看不见的地面痕迹 →
              N 个游戏日后痕迹的位置重新"长"出一间猪人房，并住进一只猪。
      【被烧】猪人房被烧成焦黑的废墟 → 焦黑废墟照原版留在原地 → N 个游戏日
              后它自己变回一间完好的新房子（不需要玩家再锤一下）。
              如果玩家提前把焦黑废墟锤掉，也一样会留痕迹、一样会重建。

    实现思路（针对 DST build 747465 的源码设计，全部有出处）
      1. AddPrefabPostInit("pighouse") 把 components.workable.onfinish 包一层
         （原版 pighouse.lua:411 注册、workable.lua:162 调用）。
      2. 包的那层先原样调用原版 onfinish（放猪 / DropLoot / collapse_big
         / Remove 全部照旧），所以拆掉那一瞬间和原版 100% 一样。
      3. 拆除前记住坐标，回调返回后生成 pighouse_rebuildsite（只有"记性"）。
      4. 烧毁走另一条路：监听 "burntup"（standardcomponents.lua:58 推的），
         在焦黑房子自己身上挂倒计时。
      5. 倒计时结束 → SpawnPrefab("pighouse") + PushEvent("onbuilt")
         播放房子自带的 "place" 生长动画。

    关于掉落
      原版结构掉落 = 配方材料 × TUNING.HAMMER_LOOT_PERCENT(0.5)
      （lootdropper.lua:242 / GetRecipeLoot），猪人房配方见 recipes.lua:583
      {boards 4, cutstone 3, pigskin 4} → 2 木板 + 2 石砖 + 2 猪皮。
      所以"重建出来的房子"关掉 lootdropper.droprecipeloot 就能堵住无限刷材料。
----------------------------------------------------------------------]]

PrefabFiles = {
    "pighouse_rebuildsite",
}

Assets = {
    -- 复用游戏自带的"地面痕迹"贴花素材，不需要新美术
    -- （Asset 在白名单里，可以用裸名；这里照样写清楚来源）
    Asset("ANIM", "anim/scorched_ground.zip"),
}

--==============================================================
--  配置
--==============================================================

local DAY = (GLOBAL.TUNING ~= nil and GLOBAL.TUNING.TOTAL_DAY_TIME) or 480

local CFG =
{
    days          = GetModConfigData("PHR_DAYS") or 4,   -- 兜底值和 modinfo 的 default 保持一致（4 天）
    mode          = GetModConfigData("PHR_MODE") or "timer",
    drop          = GetModConfigData("PHR_DROP") or "reduced",
    burnt_rebuild = GetModConfigData("PHR_BURNT"),
    mark          = GetModConfigData("PHR_MARK"),
    playerbuilt   = GetModConfigData("PHR_PLAYERBUILT"),
}

if CFG.burnt_rebuild == nil then CFG.burnt_rebuild = true end
if CFG.mark == nil then CFG.mark = true end
-- 默认：玩家自己盖的猪人房拆了/烧了不重建（用户定的默认值）
-- 注意写法：这里不能用 `or false`，那样用户选"是"也会被当成 nil 分支处理
if CFG.playerbuilt == nil then CFG.playerbuilt = false end

CFG.seconds       = math.max(30, math.floor(CFG.days * DAY))  -- 重建倒计时（秒）
CFG.retry_seconds = math.max(20, math.floor(DAY * 0.25))      -- 位置被占时的重试间隔
CFG.wait_seconds  = math.max(30, math.floor(DAY * 0.5))       -- 等猪时每次多等多久
CFG.pig_radius    = 30                                        -- 多远内算"附近有猪"
CFG.pig_wait_max  = math.floor(DAY * 4)                       -- 等猪上限，超过就自己长回来

-- 给 pighouse_rebuildsite.lua 读。
-- GLOBAL = _G，所以这行是真写进全局表，prefab 文件那边能读到。
GLOBAL.PIGHOUSE_REBUILD_CFG = CFG

--==============================================================
--  玩家建造 vs 地图原生
--==============================================================
--  判据：玩家用配方盖建筑时，游戏自己会给刚建好的结构推一个 onbuilt 事件
--        （components/builder.lua:825 `prod:PushEvent("onbuilt", { builder = self.inst, pos = pt })`；
--          部署"套装类物品"走 prefabutil.lua:71，也会推同一个事件）
--        所以"这辈子收到过 onbuilt" = 玩家自己盖的。
--        （地图生成的原生猪人房、被本 mod 重建出来的房子，都不会走这条路）
--
--  例外：本 mod 重建房子时也会推 onbuilt（为了让房子播自带的 "place" 生长动画，
--        pighouse.lua:444 在监听它），所以打标记前要先排除带 _pighouse_rebuild_worn 的房子。

local function IsPlayerBuilt(inst)
    return inst ~= nil and inst._phr_playerbuilt == true
end

-- 这间房子被拆/烧掉之后，该不该留重建记号？
-- 注意：必须在实体被删除之前调用（删除后字段就不可靠了）
local function ShouldLeaveSite(inst, was_burnt)
    if was_burnt and not CFG.burnt_rebuild then
        return false                                    -- 整个"烧毁重建"被关掉了
    end
    if IsPlayerBuilt(inst) and not CFG.playerbuilt then
        return false                                    -- 玩家自己盖的房子不重建
    end
    return true
end

--==============================================================
--  重建出来的房子：削弱掉落
--==============================================================

local function ApplyRebuiltHouseLoot(inst)
    local ld = inst.components.lootdropper
    if ld == nil or inst._pighouse_rebuild_worn ~= true then
        return
    end
    if CFG.drop == "vanilla" then
        return -- 原版掉落，啥都不动
    end

    -- 关键：关掉"按配方材料掉落"，否则重建后再拆又掉 2 木板 + 2 石砖 + 2 猪皮
    ld.droprecipeloot = false
    ld:SetLoot(CFG.drop == "reduced" and { "boards" } or {})
end

--==============================================================
--  烧毁的房子：N 天后自己变回完好的新房子
--==============================================================

local StartBurntRegrow

-- 附近有没有活着的猪（给"等猪"模式用；和遗址里那个判断逻辑一致）
local function HasLivingPigNear(x, z, radius)
    -- 注意：TheSim 不在沙箱白名单里 → 必须 GLOBAL.TheSim
    for _, e in ipairs(GLOBAL.TheSim:FindEntities(x, 0, z, radius, { "pig" })) do
        if e:IsValid()
            and e.components.health ~= nil
            and not e.components.health:IsDead()
            and not e:HasTag("playerghost")
        then
            return true
        end
    end
    return false
end

local function RegrowBurntHouse(inst)
    if not inst:IsValid() then
        return
    end

    local x, y, z = inst.Transform:GetWorldPosition()

    local fx = GLOBAL.SpawnPrefab("collapse_big")
    if fx ~= nil then
        fx.Transform:SetPosition(x, y, z)
        fx:SetMaterial("wood")
    end

    -- 焦黑废墟的位置本身就是"记号"，所以不需要额外留地面痕迹
    local house = GLOBAL.SpawnPrefab("pighouse")
    if house ~= nil then
        house.Transform:SetPosition(x, 0, z)
        house._pighouse_rebuild_worn  = true
        house._pighouse_rebuild_count = (inst._pighouse_rebuild_count or 0) + 1
        house:PushEvent("onbuilt")     -- 播房子自带的 "place" 生长动画
    end

    -- 焦黑废墟退场
    inst:Remove()
end

local function OnBurntRegrowTick(inst)
    -- 房子已经被人锤掉/被删了，或者已经不是焦黑状态了，就别管了
    if not inst:IsValid() or not inst:HasTag("burnt") then
        return
    end

    inst._phr_regrow = (inst._phr_regrow or 0) - 1
    if inst._phr_regrow > 0 then
        return
    end

    -- "等猪"模式：附近一只活猪都没有就先不盖
    if CFG.mode == "pig" then
        local x, _, z = inst.Transform:GetWorldPosition()
        if not HasLivingPigNear(x, z, CFG.pig_radius) then
            inst._phr_pigwait = (inst._phr_pigwait or 0) + CFG.wait_seconds
            if inst._phr_pigwait < CFG.pig_wait_max then
                StartBurntRegrow(inst, CFG.wait_seconds)
                return
            end
            -- 等了太久也没猪来，就自己长回来
        end
    end

    if inst._phr_regrow_timer ~= nil then
        inst._phr_regrow_timer:Cancel()
        inst._phr_regrow_timer = nil
    end
    RegrowBurntHouse(inst)
end

StartBurntRegrow = function(inst, seconds)
    if not inst:IsValid() then
        return
    end
    if inst._phr_regrow_timer ~= nil then
        inst._phr_regrow_timer:Cancel()
        inst._phr_regrow_timer = nil
    end
    inst._phr_regrow = math.max(1, math.floor(seconds or 1))
    inst._phr_regrow_timer = inst:DoPeriodicTask(1, OnBurntRegrowTick)
end

--==============================================================
--  接管猪人房的拆除 / 烧毁
--==============================================================

AddPrefabPostInit("pighouse", function(inst)
    -- (1) 服务端的 pighouse 才有 workable 组件：客户端的 pighouse 在加组件之前
    --     就 return 了（pighouse.lua:403）。所以这一条就足以区分服务端/客户端。
    --     另外：世界生成时 TheWorld.ismastersim 已经是 true（world.lua:422-426
    --     在初始化地图之前就设好了），所以地图上原生的猪人房也一样会被接管。
    local workable = inst.components.workable
    if workable == nil or workable.onfinish == nil then
        return
    end

    -- TheWorld 不在沙箱白名单里 → 必须走 GLOBAL。
    -- 但还要用 GLOBAL.rawget 绕过 strict.lua：TheWorld 从来没有被"提前声明"过
    -- （world.lua:422 才第一次 `TheWorld = inst`），所以在世界还没建好的时刻
    -- 直接读 GLOBAL.TheWorld 会触发 "variable 'TheWorld' is not declared" 而崩服。
    -- rawget 走原始访问、不碰 metatable，读不到就老老实实给 nil。
    -- （rawget 本身也不在沙箱白名单里，所以要用 GLOBAL.rawget）
    local world = GLOBAL.rawget(GLOBAL, "TheWorld")
    if world ~= nil and not world.ismastersim then
        return
    end

    if inst._pighouse_rebuild_hooked then
        return
    end
    inst._pighouse_rebuild_hooked = true

    ------------------------------------------------------------
    -- (A) 让"这间房子是重建出来的"和"烧毁后的重建倒计时"能存档
    ------------------------------------------------------------
    local vanilla_onsave, vanilla_onload = inst.OnSave, inst.OnLoad

    inst.OnSave = function(i, data)
        if vanilla_onsave ~= nil then
            vanilla_onsave(i, data)
        end
        if data ~= nil then
            data.phr_worn    = i._pighouse_rebuild_worn
            data.phr_count   = i._pighouse_rebuild_count
            data.phr_plt     = i._phr_playerbuilt     -- 玩家建造标记
            data.phr_regrow  = i._phr_regrow       -- 烧毁后的重建倒计时（秒）
            data.phr_pigwait = i._phr_pigwait      -- 等猪累计时长（秒）
        end
    end

    inst.OnLoad = function(i, data)
        local regrow  = data ~= nil and data.phr_regrow or nil
        local pigwait = data ~= nil and data.phr_pigwait or nil

        if data ~= nil then
            i._pighouse_rebuild_worn  = data.phr_worn
            i._pighouse_rebuild_count = data.phr_count
            i._phr_playerbuilt        = data.phr_plt
        end

        -- 原版 onload：data.burnt 时会把焦黑状态重新恢复出来
        -- （必须在它之后才能判断"这间房现在是不是焦黑的"）
        if vanilla_onload ~= nil then
            vanilla_onload(i, data)
        end

        -- 读档回来的重建房：立刻恢复削弱后的掉落
        ApplyRebuiltHouseLoot(i)

        -- 读档时这间房还是焦黑的：把重建倒计时接上
        if regrow ~= nil and CFG.burnt_rebuild and i:HasTag("burnt") then
            i._phr_pigwait = pigwait or 0
            StartBurntRegrow(i, regrow)
        end
    end

    ------------------------------------------------------------
    -- (B) 刚被重建出来的房子：等生成它的那一边把标记打完再应用掉落规则
    -- （SpawnPrefab 返回之后对方才会设置标记，所以要延后一帧）
    ------------------------------------------------------------
    inst:DoTaskInTime(0, function(i)
        if i:IsValid() then
            ApplyRebuiltHouseLoot(i)
        end
    end)

    ------------------------------------------------------------
    -- (C) 烧成焦黑废墟的那一刻：起一个"自己变回新房子"的倒计时
    --     "burntup" 由 standardcomponents.lua:58 的 DefaultBurntStructureFn
    --     推出，pighouse.lua:436 监听了同一个事件
    ------------------------------------------------------------
    if CFG.burnt_rebuild then
        inst:ListenForEvent("burntup", function(i)
            -- 玩家盖的、且开关没打开 → 就和原版一样，焦黑废墟留在原地不再变回来
            if ShouldLeaveSite(i, true) then
                StartBurntRegrow(i, CFG.seconds)
            end
        end)
    end

    ------------------------------------------------------------
    -- (E) 玩家建造标记：收到过 onbuilt 就说明这间房是玩家自己盖的
    --     （见文件上方"玩家建造 vs 地图原生"的说明和出处）
    ------------------------------------------------------------
    inst:ListenForEvent("onbuilt", function(i)
        if i._pighouse_rebuild_worn == true then
            return          -- 这是本 mod 重建出来的房子，不算玩家建造
        end
        i._phr_playerbuilt = true
    end)

    ------------------------------------------------------------
    -- (D) 包一层原版 onhammered
    ------------------------------------------------------------
    local vanilla_onfinish = workable.onfinish

    workable:SetOnFinishCallback(function(i, worker)
        if not i:IsValid() then
            return
        end

        -- 房子马上就会没了，先把坐标等信息记下来
        local x, y, z = i.Transform:GetWorldPosition()
        local was_burnt = i:HasTag("burnt")
        local count = i._pighouse_rebuild_count or 0
        local regrow_left = i._phr_regrow   -- 焦黑状态下已经等了一阵子的话，还剩多少秒
        -- 拆除后实体就没了，所以"要不要留记号"必须在原版回调之前定下来
        local leave_site = ShouldLeaveSite(i, was_burnt)

        -- 原版行为：释放里面的猪 → 掉落 → collapse_big 木屑特效 → Remove()
        vanilla_onfinish(i, worker)

        -- 原版跑完了，房子已经消失，来留个"记性"
        if not leave_site then
            return
        end

        -- 注意：SpawnPrefab 不在沙箱白名单里 → 必须 GLOBAL.SpawnPrefab
        local site = GLOBAL.SpawnPrefab("pighouse_rebuildsite")
        if site ~= nil then
            site.Transform:SetPosition(x, y, z)
            site.rebuild_count = count + 1
            if regrow_left ~= nil then
                -- 焦黑废墟被提前锤掉：把"已经等过的时间"继承给新记号，别让玩家白等
                site.remaining = regrow_left
            end
        end
    end)
end)
