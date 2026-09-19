--[[--------------------------------------------------------------------
    pighouse_rebuildsite —— 猪人房的"重建遗址"

    ⚠️⚠️ 关于运行环境（连续踩了两个坑，务必看完再改）⚠️⚠️

    【坑 1】这个文件是 **prefab 文件**（列在 PrefabFiles 里），加载路径是
        scripts/mods.lua:696 → scripts/mainfunctions.lua:145 LoadPrefabFile()
        → 里面用 `loadfile()` 而**没有任何 setfenv**
        ⇒ 所以它的环境就是**完整全局表 _G**，裸名 CreateEntity / SpawnPrefab /
          TheWorld / ANIM_ORIENTATION / LAYER_BACKGROUND 全部可以直接用。
        （对比：modmain.lua 是白名单沙箱，那些名字在那边才是 nil，必须写 GLOBAL.xxx）

    【坑 2】DST 开着 scripts/strict.lua 的全局变量严格检查：
        mt.__index = function(t, n)
            if not mt.__declared[n] and debug.getinfo(2,"S").what ~= "C" then
                error("variable '"..n.."' is not declared", 2)   -- ← 报错，不是返回 nil
            end
            return rawget(t, n)
        end
        ⇒ **读一个"未声明"的全局会直接 error 崩溃**，不是得到 nil。
        ⇒ 而 `GLOBAL` 这个名字**只存在于 modmain 的沙箱里**（全游戏只有
           mods.lua:328 的 `GLOBAL = _G`），_G 里根本没有它。

        v0.1.2 我为了"兼容两种环境"写了 `local G = GLOBAL or _G`，
        结果在 prefab 文件里读 GLOBAL → "variable 'GLOBAL' is not declared"
        → 整个 mod 在服务器启动阶段被禁用。**所以这里绝对不能提 GLOBAL。**

    【正确写法】直接用裸名。引擎全局在 DST 启动时都是有声明的，strict 不会拦。
        需要读 modmain 注入的东西时，用 rawget 绕过 metatable，最安全：
            rawget(_G, "PIGHOUSE_REBUILD_CFG")

    --------------------------------------------------------------------

    这个实体不是废墟，玩家拆掉房子时它不会出现；它是房子**已经消失之后**留在
    原地的一个"记性"：一块几乎看不见的地面痕迹 + 一个倒计时。

    视觉直接复用游戏自带的 scorched_ground 贴花（prefabs/scorchedground.lua）：
      · 不需要任何新美术
      · 贴地、不可点选、无碰撞、不挡建造
      · 自带 10 种形状和随机旋转，看着像地面上一块淡淡的印子

    倒计时结束（或"等猪"模式等到了猪）→ 原地 SpawnPrefab("pighouse")，
    并推 onbuilt 事件让房子播自带的 "place" 生长动画。
----------------------------------------------------------------------]]

local assets = {
    Asset("ANIM", "anim/scorched_ground.zip"),
}

local prefabs = {
    "pighouse",
    "collapse_big",
    "boards",
}

-- 跟 prefabs/scorchedground.lua 一样：idle, idle2 ... idle10
local ANIM_NAMES = { "idle" }
for i = 2, 10 do
    table.insert(ANIM_NAMES, "idle" .. tostring(i))
end

-- modmain 还没跑起来时的兜底（正常不会用到）
local FALLBACK_CFG = {
    seconds       = 1920,   -- 4 游戏日（和 modinfo 的默认一致）
    retry_seconds = 120,
    wait_seconds  = 240,
    pig_radius    = 30,
    pig_wait_max  = 1920,
    mode          = "timer",
    mark          = true,
}

local function GetCfg()
    -- modmain 顶层写了 `GLOBAL.PIGHOUSE_REBUILD_CFG = CFG`（= 写进真 _G，
    -- 而且 strict.lua 会把它标记为 __declared），所以这里能取到。
    -- 用 rawget 兜底：万一还没写进来，也不会触发 strict 报错，只会拿到 nil。
    return rawget(_G, "PIGHOUSE_REBUILD_CFG") or FALLBACK_CFG
end

--==============================================================
--  位置检查：那块地还能不能盖房子
--==============================================================

-- 只把"玩家"和"建筑"当成占位。猪/物品/地上的东西不算 ——
-- 否则猪人村旁边总有猪溜达，房子会被无限推迟。
local BLOCK_TAGS = { "player", "structure" }

local function SiteIsClear(site)
    local x, _, z = site.Transform:GetWorldPosition()

    -- 地形被改成海/洞了，或者那儿是个不可通行的静态物
    if TheWorld.Map:IsPassableAtPoint(x, 0, z) == false then
        return false
    end

    for _, e in ipairs(TheSim:FindEntities(x, 0, z, 2, BLOCK_TAGS)) do
        if e ~= site and e:IsValid() then
            return false
        end
    end

    return true
end

--==============================================================
--  "等猪"模式：附近还有活着的猪吗
--==============================================================

local function FindLivingPig(x, z, radius)
    for _, e in ipairs(TheSim:FindEntities(x, 0, z, radius, { "pig" })) do
        if e:IsValid()
            and e.components.health ~= nil
            and not e.components.health:IsDead()
            and not e:HasTag("playerghost")
        then
            return e
        end
    end
    return nil
end

--==============================================================
--  倒计时
--==============================================================

local StartCountdown

local function TryRebuild(site)
    if not site:IsValid() then
        return
    end

    local cfg = GetCfg()

    -- 1) 那块地被占了？过一会儿再试
    if not SiteIsClear(site) then
        StartCountdown(site, cfg.retry_seconds or 120)
        return
    end

    -- 2) "等猪"模式：附近没活着的猪就先不建，等它回来
    if cfg.mode == "pig" then
        local x, _, z = site.Transform:GetWorldPosition()
        if FindLivingPig(x, z, cfg.pig_radius or 30) == nil then
            site.pig_wait = (site.pig_wait or 0) + (cfg.wait_seconds or 240)
            if site.pig_wait < (cfg.pig_wait_max or 1920) then
                StartCountdown(site, cfg.wait_seconds or 240)
                return
            end
            -- 等了太久也没猪来，就自己长回来
        end
    end

    -- 3) 建！
    local x, y, z = site.Transform:GetWorldPosition()

    local fx = SpawnPrefab("collapse_big")
    if fx ~= nil then
        fx.Transform:SetPosition(x, y, z)
        fx:SetMaterial("wood")
    end

    local house = SpawnPrefab("pighouse")
    if house == nil then
        -- 理论上不会发生，真发生了就留着记号下次再试
        StartCountdown(site, cfg.retry_seconds or 120)
        return
    end

    house.Transform:SetPosition(x, 0, z)
    house._pighouse_rebuild_worn  = true          -- 标记：这是重建出来的房子
    house._pighouse_rebuild_count = site.rebuild_count or 1
    house:PushEvent("onbuilt")                    -- 播房子自带的 "place" 生长动画
    -- 里面的猪不用手动生成：pighouse.lua 的 oninit 会自动补一只并让它回家

    site:Remove()
end

local function OnTick(site)
    if not site:IsValid() then
        return
    end
    site.remaining = (site.remaining or 0) - 1
    if site.remaining > 0 then
        return
    end
    if site._pighouse_timer ~= nil then
        site._pighouse_timer:Cancel()
        site._pighouse_timer = nil
    end
    TryRebuild(site)
end

StartCountdown = function(site, seconds)
    if not site:IsValid() then
        return
    end
    if site._pighouse_timer ~= nil then
        site._pighouse_timer:Cancel()
        site._pighouse_timer = nil
    end
    site.remaining = math.max(1, math.floor(seconds or 1))
    site._pighouse_timer = site:DoPeriodicTask(1, OnTick)
end

--==============================================================
--  存档
--==============================================================

local function OnSave(inst, data)
    data.remaining    = inst.remaining
    data.pig_wait     = inst.pig_wait
    data.rebuild_count = inst.rebuild_count
    data.anim         = inst.anim
    data.rotation     = inst.Transform:GetRotation()
end

local function OnLoad(inst, data)
    if data ~= nil then
        inst.pig_wait      = data.pig_wait or 0
        inst.rebuild_count = data.rebuild_count or inst.rebuild_count
        if data.anim ~= nil then
            inst.anim = data.anim
            inst.AnimState:PlayAnimation(inst.anim)
        end
        if data.rotation ~= nil then
            inst.Transform:SetRotation(data.rotation)
        end
    end

    local remaining = (data ~= nil and data.remaining) or GetCfg().seconds or FALLBACK_CFG.seconds
    inst:DoTaskInTime(math.random() * 3, function(i)
        if i:IsValid() then
            StartCountdown(i, remaining)
        end
    end)
end

--==============================================================
--  prefab
--==============================================================

local function fn()
    local inst = CreateEntity()

    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddNetwork()

    -- 和 prefabs/scorchedground.lua 完全一样的表现方式：贴在地面的图层
    inst.AnimState:SetBank("scorched_ground")
    inst.AnimState:SetBuild("scorched_ground")
    inst.AnimState:SetOrientation(ANIM_ORIENTATION.OnGround)
    inst.AnimState:SetLayer(LAYER_BACKGROUND)
    inst.AnimState:SetSortOrder(3)

    inst:AddTag("NOCLICK")   -- 点不到
    inst:AddTag("FX")        -- 只是装饰，不是建筑/实体

    inst.entity:SetPristine()

    if not TheWorld.ismastersim then
        return inst
    end

    local cfg = GetCfg()

    inst.persists      = true
    inst.remaining     = cfg.seconds or FALLBACK_CFG.seconds
    inst.pig_wait      = 0
    inst.rebuild_count = 1

    if cfg.mark ~= false then
        inst.anim = ANIM_NAMES[math.random(#ANIM_NAMES)]
        inst.AnimState:PlayAnimation(inst.anim)
        inst.Transform:SetRotation(math.random() * 360)
    end
    -- cfg.mark == false 时不播动画 —— 什么都没画出来，玩家完全看不见

    inst:DoTaskInTime(0, function(i)
        if i:IsValid() then
            StartCountdown(i, i.remaining or FALLBACK_CFG.seconds)
        end
    end)

    inst.OnSave = OnSave
    inst.OnLoad = OnLoad

    return inst
end

return Prefab("pighouse_rebuildsite", fn, assets, prefabs)
