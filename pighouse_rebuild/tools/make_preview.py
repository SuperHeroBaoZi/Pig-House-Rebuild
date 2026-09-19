# -*- coding: utf-8 -*-
"""
生成「猪人房重建」mod 的预览图（纯 PIL 手绘，2x 超采样抗锯齿）。
输出：preview.png (1024) + modicon.png (256, 无文字，留给 .tex 图标用)
"""
import math, os
from PIL import Image, ImageDraw, ImageFont

SS   = 2                       # 超采样
W = H = 1024
CW, CH = W * SS, H * SS
OUT  = r"E:\Steam\steamapps\common\Don't Starve Together\mods\pighouse_rebuild"

# ---------- 配色（DST 那种偏暗、低饱和的调子）----------
BG1, BG2   = (30, 45, 49), (12, 18, 20)
PANEL      = (36, 51, 55)
PANEL_BD   = (60, 82, 86)
GROUND     = (45, 59, 52)
BODY, BD   = (233, 218, 182), (198, 176, 134)
ROOF, RD   = (126, 91, 68), (92, 63, 47)
DOOR, DD   = (74, 51, 39), (40, 26, 18)
WIN_GLOW   = (238, 190, 104)
PINK, PINK2= (241, 170, 162), (223, 136, 130)
NOSE       = (128, 62, 60)
HANDLE     = (166, 119, 75)
METAL, METL= (150, 159, 164), (205, 214, 218)
ACCENT     = (233, 184, 92)
DUST       = (203, 170, 108)
TEXT, TOL  = (243, 234, 217), (16, 22, 24)
GHOST      = (104, 148, 132)
BURNT, BRD = (56, 53, 49), (26, 24, 22)

def sc(v):                     # 1x 坐标 -> 超采样坐标（PIL 12 要求整数）
    return int(round(v * SS))

def font(bold, size):
    p = r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"
    return ImageFont.truetype(p, sc(size))

def rr(d, xy, r, fill=None, outline=None, width=0):
    d.rounded_rectangle([sc(xy[0]), sc(xy[1]), sc(xy[2]), sc(xy[3])],
                        radius=sc(r), fill=fill, outline=outline, width=sc(width))

def house(d, cx, cy, w, h, mode="solid"):
    """画一间猪人房。mode: solid / ghost / burnt"""
    solid = mode != "ghost"
    bodyf  = BODY if mode == "solid" else (BURNT if mode == "burnt" else None)
    bodyo  = BD   if mode == "solid" else (BRD   if mode == "burnt" else GHOST)
    rooff  = ROOF if mode == "solid" else ((42, 40, 37) if mode == "burnt" else None)
    roofo  = RD   if mode == "solid" else ((20, 18, 16) if mode == "burnt" else GHOST)
    detail = BD   if mode == "solid" else ((38, 36, 33) if mode == "burnt" else GHOST)
    lw  = max(2.0, w * 0.014)
    bw  = w * 0.84
    roof_h = h * 0.44
    body_t = cy - h / 2 + roof_h * 0.70
    body_b = cy + h / 2

    if solid:                                   # 屋身（圆角桶形）
        rr(d, (cx - bw / 2, body_t, cx + bw / 2, body_b), h * 0.07, bodyf, bodyo, lw)
    else:                                       # 幽灵：只画轮廓
        rr(d, (cx - bw / 2, body_t, cx + bw / 2, body_b), h * 0.07, None, bodyo, lw * 1.3)

    # 穹顶
    rbox = [sc(cx - w / 2), sc(cy - h / 2), sc(cx + w / 2), sc(cy - h / 2 + roof_h * 2)]
    if solid:
        d.pieslice(rbox, 180, 360, fill=rooff, outline=roofo, width=sc(lw))
        d.ellipse([sc(cx - w * 0.045), sc(cy - h / 2 + roof_h * 0.10),
                   sc(cx + w * 0.045), sc(cy - h / 2 + roof_h * 0.24)], fill=roofo)
    else:
        d.arc(rbox, 180, 360, fill=roofo, width=sc(lw * 1.6))

    # 木纹 / 烧焦裂纹
    if solid:
        for i in (1, 2, 3):
            yy = body_t + (body_b - body_t) * i / 4.0
            d.line([sc(cx - bw / 2 + w * 0.05), sc(yy), sc(cx + bw / 2 - w * 0.05), sc(yy)],
                   fill=detail, width=sc(lw))
    if mode == "burnt":
        for a, b in ((-0.15, 0.1), (0.1, -0.2), (0.25, 0.3)):
            d.line([sc(cx + bw * a), sc(body_t + (body_b - body_t) * (0.3 + abs(a))),
                    sc(cx + bw * b), sc(body_b - (body_b - body_t) * 0.2)],
                   fill=(96, 62, 40), width=sc(lw * 0.9))

    # 门（拱形）：solid/burnt 有门，ghost 只画框
    dw, dh = w * 0.33, h * 0.40
    dx0, dy0 = cx - dw / 2, cy + h / 2 - dh
    arch = [sc(dx0), sc(dy0 - dw * 0.5), sc(dx0 + dw), sc(dy0 + dw * 0.5)]
    if solid:
        d.pieslice(arch, 180, 360, fill=DOOR, outline=DD, width=sc(lw))
        d.rectangle([sc(dx0), sc(dy0), sc(dx0 + dw), sc(body_b - lw)],
                    fill=DOOR, outline=DD, width=sc(lw))
    else:
        d.arc(arch, 180, 360, fill=GHOST, width=sc(lw * 1.3))
        d.line([sc(dx0), sc(dy0), sc(dx0), sc(body_b)], fill=GHOST, width=sc(lw * 1.3))
        d.line([sc(dx0 + dw), sc(dy0), sc(dx0 + dw), sc(body_b)], fill=GHOST, width=sc(lw * 1.3))

    # 门里探出头的猪（只在 solid 模式）
    if mode == "solid":
        pcx, pcy, pr = cx, cy + h / 2 - dh * 0.44, dw * 0.30
        d.ellipse([sc(pcx - pr * 1.15), sc(pcy - pr * 1.15), sc(pcx + pr * 1.15), sc(pcy + pr * 1.15)],
                  fill=PINK, outline=NOSE, width=sc(lw * 0.7))
        for s in (-1, 1):     # 耳朵
            d.polygon([(sc(pcx + s * pr * 0.75), sc(pcy - pr * 0.95)),
                       (sc(pcx + s * pr * 1.35), sc(pcy - pr * 1.75)),
                       (sc(pcx + s * pr * 1.35), sc(pcy - pr * 0.75))],
                      fill=PINK2, outline=NOSE)
        d.ellipse([sc(pcx - pr * 0.62), sc(pcy - pr * 0.05), sc(pcx + pr * 0.62), sc(pcy + pr * 0.85)],
                  fill=PINK2, outline=NOSE, width=sc(lw * 0.6))
        for s in (-1, 1):     # 鼻孔
            d.ellipse([sc(pcx + s * pr * 0.30 - pr * 0.13), sc(pcy + pr * 0.28),
                       sc(pcx + s * pr * 0.30 + pr * 0.13), sc(pcy + pr * 0.54)], fill=NOSE)
        for s in (-1, 1):     # 眼睛
            d.ellipse([sc(pcx + s * pr * 0.52 - pr * 0.11), sc(pcy - pr * 0.62),
                       sc(pcx + s * pr * 0.52 + pr * 0.11), sc(pcy - pr * 0.40)], fill=(48, 32, 30))

    # 圆窗
    if mode != "ghost":
        for s in (-1, 1):
            wx, wy, wr = cx + s * bw * 0.29, body_t + (body_b - body_t) * 0.30, w * 0.062
            d.ellipse([sc(wx - wr), sc(wy - wr), sc(wx + wr), sc(wy + wr)],
                      fill=WIN_GLOW if mode == "solid" else (30, 28, 26), outline=bodyo, width=sc(lw * 0.8))
            d.line([sc(wx - wr), sc(wy), sc(wx + wr), sc(wy)], fill=bodyo, width=sc(lw * 0.5))
    else:
        for s in (-1, 1):
            wx, wy, wr = cx + s * bw * 0.29, body_t + (body_b - body_t) * 0.30, w * 0.062
            d.ellipse([sc(wx - wr), sc(wy - wr), sc(wx + wr), sc(wy + wr)], outline=GHOST, width=sc(lw * 1.2))

def hammer(d, x, y, ang, ln, lw):
    a = math.radians(ang)
    hx, hy = x + math.cos(a) * ln, y + math.sin(a) * ln
    d.line([sc(x), sc(y), sc(hx), sc(hy)], fill=HANDLE, width=sc(lw))
    px, py = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
    d.line([sc(hx - px * lw * 1.5), sc(hy - py * lw * 1.5),
            sc(hx + px * lw * 1.5), sc(hy + py * lw * 1.5)], fill=METAL, width=sc(lw * 1.15))
    d.line([sc(hx - px * lw * 1.5 - math.cos(a) * lw * 0.25), sc(hy - py * lw * 1.5 - math.sin(a) * lw * 0.25),
            sc(hx + px * lw * 1.5 - math.cos(a) * lw * 0.25), sc(hy + py * lw * 1.5 - math.sin(a) * lw * 0.25)],
           fill=METL, width=sc(lw * 0.45))

def spark(d, cx, cy, r, col):
    pts = []
    for i in range(8):
        ang = math.radians(i * 45)
        rad = r if i % 2 == 0 else r * 0.34
        pts.append((sc(cx + math.cos(ang) * rad), sc(cy + math.sin(ang) * rad)))
    d.polygon(pts, fill=col)

def ring(d, cx, cy, r, frac, lw):
    d.ellipse([sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r)], outline=(62, 78, 80), width=sc(lw))
    d.arc([sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r)], -90, -90 + 360 * frac,
          fill=ACCENT, width=sc(lw))

def blob(d, cx, cy, rw, rh, col, n=14, seed=7):
    """不规则椭圆（地面痕迹）"""
    import random
    rnd = random.Random(seed)
    pts = []
    for i in range(n):
        ang = 2 * math.pi * i / n
        k = 0.78 + rnd.random() * 0.42
        pts.append((sc(cx + math.cos(ang) * rw * k), sc(cy + math.sin(ang) * rh * k)))
    d.polygon(pts, fill=col)

# ---------- 画布 ----------
img = Image.new("RGB", (CW, CH), BG2)
d = ImageDraw.Draw(img)
for i in range(CH):                      # 竖向渐变背景
    t = i / CH
    d.line([(0, i), (CW, i)], fill=tuple(int(BG1[k] + (BG2[k] - BG1[k]) * t) for k in range(3)))

# 标题
d.text((sc(W / 2), sc(96)), "猪人房重建", font=font(True, 88), fill=TEXT, anchor="mm",
       stroke_width=sc(5), stroke_fill=TOL)
d.text((sc(W / 2), sc(166)), "Pig House Rebuild  ·  Don't Starve Together 服务端 mod",
       font=font(False, 24), fill=(168, 186, 180), anchor="mm")

# 三分格
GAP, CWID = 26, 296
x0 = (W - (CWID * 3 + GAP * 2)) / 2
PY0, PY1 = 224, 736
cells = []
for i in range(3):
    cx = x0 + i * (CWID + GAP)
    rr(d, (cx, PY0, cx + CWID, PY1), 16, PANEL, PANEL_BD, 3)
    cells.append((cx, cx + CWID))
    if i < 2:                            # 小箭头
        ax = cx + CWID + GAP / 2
        d.line([sc(ax - 7), sc(520), sc(ax + 5), sc(546)], fill=ACCENT, width=sc(5))
        d.line([sc(ax - 7), sc(572), sc(ax + 5), sc(546)], fill=ACCENT, width=sc(5))
    # 地面
    d.line([sc(cx + 26), sc(640), sc(cx + CWID - 26), sc(640)], fill=GROUND, width=sc(4))

LBL = font(True, 26)
SUB = font(False, 20)

# ① 被拆
c1 = cells[0][0]
house(d, c1 + CWID / 2, 505, 168, 200, "solid")
hammer(d, c1 + 88, 372, 34, 84, 10)
d.arc([sc(c1 + 60), sc(344), sc(c1 + 168), sc(452)], 200, 330, fill=(150, 150, 150), width=sc(4))
for (dx, dy) in ((c1 + 62, 400), (c1 + 44, 470), (c1 + 66, 540)):
    d.ellipse([sc(dx - 5), sc(dy - 5), sc(dx + 5), sc(dy + 5)], fill=DUST)
d.text((c1 + CWID / 2, PY0 + 48), "① 被锤掉", font=LBL, fill=TEXT, anchor="mm")
d.text((c1 + CWID / 2, PY0 + 80), "和原版一模一样", font=SUB, fill=(152, 170, 164), anchor="mm")

# ② 留痕迹 + 倒计时
c2 = cells[1][0]
house(d, c2 + CWID / 2, 505, 168, 200, "ghost")
blob(d, c2 + CWID / 2, 646, 96, 20, (58, 70, 62))
ring(d, c2 + CWID / 2, 505, 44, 0.68, 9)
d.text((c2 + CWID / 2, 505), "4天", font=font(True, 30), fill=ACCENT, anchor="mm")
d.text((c2 + CWID / 2, PY0 + 48), "② 留个淡淡的印子", font=LBL, fill=TEXT, anchor="mm")
d.text((c2 + CWID / 2, PY0 + 80), "开始倒计时（可调 30 秒~10 天）", font=SUB, fill=(152, 170, 164), anchor="mm")

# ③ 长回来
c3 = cells[2][0]
house(d, c3 + CWID / 2, 505, 168, 200, "solid")
for (dx, dy, r) in ((c3 + 58, 400, 15), (c3 + 236, 372, 12), (c3 + 248, 512, 9), (c3 + 52, 528, 8)):
    spark(d, dx, dy, r, ACCENT)
d.text((c3 + CWID / 2, PY0 + 48), "③ 自己长回来", font=LBL, fill=TEXT, anchor="mm")
d.text((c3 + CWID / 2, PY0 + 80), "猪也自动住回去", font=SUB, fill=(152, 170, 164), anchor="mm")

# 底注
d.text((sc(W / 2), sc(806)), "拆掉或烧掉的猪人房，过设定时间后原地重新长出一间（并住进一只猪）",
       font=font(False, 27), fill=(206, 216, 208), anchor="mm")
d.text((sc(W / 2), sc(852)), "地图原生的房子一定重建  ·  玩家自己盖的默认不重建  ·  重建后再拆只掉 1 块木板",
       font=font(False, 21), fill=(140, 158, 152), anchor="mm")
d.text((sc(W / 2), sc(910)), "v0.1.5", font=font(False, 22), fill=(104, 122, 118), anchor="mm")

preview = img.resize((W, H), Image.LANCZOS)
preview.save(os.path.join(OUT, "preview.png"))

# ---------- 无文字的方图标（给 modicon.tex 用）----------
ic = Image.new("RGB", (256 * SS, 256 * SS), (24, 36, 40))
di = ImageDraw.Draw(ic)
for i in range(256 * SS):
    t = i / (256 * SS)
    di.line([(0, i), (256 * SS, i)],
            fill=(int(24 + (10 - 24) * t), int(36 + (16 - 36) * t), int(40 + (18 - 40) * t)))
di.line([sc(28), sc(212), sc(228), sc(212)], fill=GROUND, width=sc(5))
house(di, 128, 132, 150, 178, "solid")
spark(di, 46, 74, 13, ACCENT)
spark(di, 210, 92, 10, ACCENT)
ic.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "modicon.png"))

# ---------- 自检 ----------
print("=== 自检 ===")
for name in ("preview.png", "modicon.png"):
    p = os.path.join(OUT, name)
    im = Image.open(p)
    print("  %-14s %s  %d KB" % (name, im.size, os.path.getsize(p) // 1024))

im = Image.open(os.path.join(OUT, "preview.png")).convert("RGB")
px = im.load()
def region_colors(x0, y0, x1, y1, step=3):
    seen = {}
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            c = px[x, y]
            seen[(c[0] // 24 * 24, c[1] // 24 * 24, c[2] // 24 * 24)] = seen.get((c[0] // 24 * 24, c[1] // 24 * 24, c[2] // 24 * 24), 0) + 1
    return seen

def has(seen, target, tol=40):
    for c in seen:
        if all(abs(c[i] - target[i]) <= tol for i in range(3)):
            return True
    return False

checks = []
# ① 格子里必须有屋身的米色（说明房子画出来了）
s1 = region_colors(int(cells[0][0]), PY0, int(cells[0][0] + CWID), PY1)
checks.append(("① 格子里有屋身米色", has(s1, BODY)))
checks.append(("① 格子里有锤子木柄色", has(s1, HANDLE, 50)))
# ② 格子里必须有幽灵绿（虚影）和痕迹深色
s2 = region_colors(int(cells[1][0]), PY0, int(cells[1][0] + CWID), PY1)
checks.append(("② 格子里有虚影绿轮廓", has(s2, GHOST, 45)))
checks.append(("② 格子里有倒计时金色", has(s2, ACCENT, 40)))
# ③ 格子里必须有星星金
s3 = region_colors(int(cells[2][0]), PY0, int(cells[2][0] + CWID), PY1)
checks.append(("③ 格子里有闪光星星", has(s3, ACCENT, 40)))
checks.append(("③ 格子里有猪脸粉色", has(s3, PINK, 35)))
# 文字没超出画布
fonts = {"title": font(True, 88), "sub": font(False, 24), "caption": font(False, 27)}
for k, txt, y in (("title", "猪人房重建", 96), ("sub", "Pig House Rebuild  ·  Don't Starve Together 服务端 mod", 166),
                  ("caption", "拆掉或烧掉的猪人房，过设定时间后原地重新长出一间（并住进一只猪）", 806)):
    # 度量必须在 2x 坐标系里做：锚点用 CW/2，字号本来就是 2x 的
    # （这里连续写错过两次：先是拿 W 比 2x 宽度，后是把 2x 字号锚在 1x 位置上）
    bb = ImageDraw.Draw(im).textbbox((CW / 2, sc(y)), txt, font=fonts[k], anchor="mm")
    w1 = (bb[2] - bb[0]) / SS                 # 换算回成品像素
    ok = w1 <= W - 40 and bb[1] > 8 and bb[3] < CH - 8
    checks.append(("文字「%s」在画布内" % txt[:10], ok))
    print("    文字「%s…」 成品宽度 %.0f px / %d（左右各留 %.0f px）"
          % (txt[:10], w1, W, (W - w1) / 2))

# 兜底：画面不能是空白的（"鲜艳"像素占比过低 = 根本没画出来）
def vivid_frac(image, step=4):
    p = image.load()
    w, h = image.size
    n = v = 0
    for yy in range(0, h, step):
        for xx in range(0, w, step):
            c = p[xx, yy]
            n += 1
            if max(c) - min(c) > 25:
                v += 1
    return v / float(n)

for name, im2 in (("preview.png", im), ("modicon.png", Image.open(os.path.join(OUT, "modicon.png")).convert("RGB"))):
    fr = vivid_frac(im2)
    checks.append(("%s 不是空白（鲜艳像素 %.1f%%）" % (name, fr * 100), fr > 0.06))

for name, ok in checks:
    print("  [%s] %s" % ("OK " if ok else "BAD", name))
bad = [n for n, ok in checks if not ok]
print("\n%s" % ("✅ 全部自检通过" if not bad else "❌ 失败: %s" % bad))
