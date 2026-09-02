#!/usr/bin/env python3
"""make_h2h_card_vision.py <art.png> -> results/card_h2h_vision.png
The head-to-head as an eye chart: every row is a measured number, DeepSeek big, GLM beside it, shrinking toward the
20/20 line, which carries the honest negative. Data-bound from results/. Real prompts are the top rows; the counting
prompt appears only on the bottom line, labeled as the ceiling."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ART = sys.argv[1] if len(sys.argv) > 1 else "results/card_vision_art.png"
OUT = "results/card_h2h_vision.png"
FONT = "/System/Library/Fonts/Avenir Next Condensed.ttc"
def F(size, face="heavy"): return ImageFont.truetype(FONT, max(8, int(size)), index={"heavy": 8, "bold": 0, "demi": 2, "medium": 5}[face])
def J(p): return json.load(open(p))
d, g = "ds4tp4", "glmtp4"
C1 = {l: J(f"results/categories_{l}_off_c1.json") for l in (d, g)}; C16 = {l: J(f"results/categories_{l}_off_c16.json") for l in (d, g)}
T = {l: J(f"results/ttft_fresh_{l}.json") for l in (d, g)}; S = {l: J(f"results/sweep_{l}.json") for l in (d, g)}
PW = {l: J(f"results/power_load_{l}.json") for l in (d, g)}; H = J("results/h2h_tp4.json")
PL = {l: J(f"results/prefill_len_{l}.json")["rows"] for l in (d, g)}
cat = lambda l, c, cc=1: (C1 if cc == 1 else C16)[l]["summary"][c]["decode_med_tok_s"]
ov = lambda l, k, cc=1: (C1 if cc == 1 else C16)[l]["overall"][k]
ttft = lambda l, c: next(r["ttft_med_s"] for r in T[l]["rows"] if r["c"] == c)
sweep = lambda l, c: next(r["agg_tok_s"] for r in S[l]["rows"] if r["c"] == c)
tj = (PW[d]["tok_s"] / H["watts"][d], PW[g]["tok_s"] / H["watts"][g])
ROWS = [  # (DeepSeek value, GLM value, label, acuity)
    (f"{cat(d,'coding'):.1f}", f"{cat(g,'coding'):.1f}", "CODE tok/s · single stream", "20/200"),
    (f"{cat(d,'prose'):.1f}", f"{cat(g,'prose'):.1f}", "PROSE tok/s · single stream", "20/100"),
    (f"{ov(d,'agg_tok_s_med',16):.0f}", f"{ov(g,'agg_tok_s_med',16):.0f}", "tok/s · 16 AGENTS IN FLIGHT · MIXED REAL PROMPTS", "20/70"),
    (f"{ov(d,'ttft_med_s',16):.2f}s", f"{ov(g,'ttft_med_s',16):.2f}s", "FIRST TOKEN AT 16 IN FLIGHT", "20/50"),
    ("8.33M", "3.83M", "KV POOL TOKENS · 1M CONTEXT", "20/40"),
    (f"{PL[d][-1]['cold_tok_s']:,}", f"{PL[g][-1]['cold_tok_s']:,}", "COLD PREFILL tok/s · FRESH 182K PROMPT", "20/30"),
    (f"{tj[0]:.2f}", f"{tj[1]:.2f}", "TOKENS PER JOULE · 16 STREAMS · 4 GPUs", "20/25"),
]
BOTTOM = f"IF YOU CAN READ THIS: GLM WINS SINGLE-STREAM COUNTING {sweep(g,1):.0f} vs {sweep(d,1):.0f} · COUNTING IS THE DRAFT CEILING, NOT DECODE · AA INTELLIGENCE INDEX GLM 57 vs 52 · QUALITY {ov(d,'auto_score')*100:.0f}% vs {ov(g,'auto_score')*100:.0f}% INSIDE THE NOISE"

BOARD = (246, 242, 232); INKB = (12, 12, 14); RED = (214, 40, 40); BLUE = (40, 88, 235); MAG = (255, 60, 190); ORG = (255, 122, 24); WHITE = (245, 245, 245); GREY = (120, 120, 128)
art = Image.open(ART).convert("RGBA"); W, Hh = art.size
dr = ImageDraw.Draw(art)
def width(s, f): return dr.textlength(s, font=f)
def fit(s, size, maxw, face="heavy", minsize=10):
    while size > minsize and width(s, F(size, face)) > maxw: size -= 1
    return F(size, face)
def glow(text_xy, s, f, color, anchor="la", spread=10):
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    ld.text(text_xy, s, font=f, fill=color + (255,), anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(spread)); art.alpha_composite(layer); art.alpha_composite(layer)
    dr.text(text_xy, s, font=f, fill=WHITE, anchor=anchor)

# board: right half, a rounded off-white eye-chart card with a thin red frame
BX0, BY0, BX1, BY1 = int(W * 0.515), int(Hh * 0.05), int(W * 0.975), int(Hh * 0.93)
dr.rounded_rectangle([BX0, BY0, BX1, BY1], radius=18, fill=BOARD, outline=RED, width=5)
cx = (BX0 + BX1) // 2; bw = BX1 - BX0
# header on the board
y = BY0 + 22
f = fit("VISION TEST", 62, bw - 60); dr.text((cx, y), "VISION TEST", font=f, fill=INKB, anchor="ma"); y += f.size + 4
sub = "DEEPSEEK V4 FLASH VISION-EXP  vs  GLM-5.3-FLASH NVFP4"; fs = fit(sub, 26, bw - 50); dr.text((cx, y), sub, font=fs, fill=RED, anchor="ma"); y += fs.size + 2
sub2 = "TP4 · 4× DGX SPARK · vLLM · SEQS 64 · CUDA GRAPHS · 1M CONTEXT · SAME 40 PROMPTS · TEMP 0"; fs2 = fit(sub2, 17, bw - 50); dr.text((cx, y), sub2, font=fs2, fill=GREY, anchor="ma"); y += fs2.size + 10
dr.line([BX0 + 30, y, BX1 - 30, y], fill=INKB, width=2); y += 10
# legend
lg = "LEFT = DEEPSEEK   ·   RIGHT = GLM   ·   READ DOWN"; fl = fit(lg, 18, bw - 60); dr.text((cx, y), lg, font=fl, fill=GREY, anchor="ma"); y += fl.size + 8
# rows: sizes shrink like an eye chart, scaled to fill the board
avail = (BY1 - 110) - y
base = [176, 122, 94, 74, 60, 50, 42]
def row_h(sz): return int(sz * 1.02) + max(12, int(sz * 0.24)) + int(sz * 0.18) + 4
k = avail / sum(row_h(b) for b in base)
for (a, b, label, acu), sz in zip(ROWS, base):
    sz = int(sz * k); fa = F(sz); fb = F(int(sz * 0.62)); flab = F(max(12, int(sz * 0.24))); facu = F(max(11, int(sz * 0.2)), "demi")
    ha = fa.getbbox(a)[3]
    wa = width(a, fa); wb = width(b, fb); gap = int(sz * 0.32)
    x = cx - (wa + gap + wb) / 2
    dr.text((x, y), a, font=fa, fill=INKB); dr.text((x + wa + gap, y + (ha - fb.getbbox(b)[3])), b, font=fb, fill=RED)
    dr.text((BX0 + 26, y + ha // 2), acu, font=facu, fill=GREY, anchor="lm")
    yy = y + ha + 4
    dr.text((cx, yy), label, font=flab, fill=GREY, anchor="ma")
    y = yy + flab.size + int(sz * 0.18)
# 20/20 line: the honest negative, tiny, wrapped
dr.line([BX0 + 30, y + 2, BX1 - 30, y + 2], fill=RED, width=2); y += 10
dr.text((cx, y), "20/20", font=F(12, "demi"), fill=RED, anchor="ma"); y += 16
fbt = F(15, "demi"); words = BOTTOM.split(" "); lines = []; cur = ""
for w_ in words:
    t = (cur + " " + w_).strip()
    if width(t, fbt) > bw - 70 and cur: lines.append(cur); cur = w_
    else: cur = t
if cur: lines.append(cur)
for ln in lines[:3]:
    dr.text((cx, y), ln, font=fbt, fill=INKB, anchor="ma"); y += fbt.size + 3
# neon title over the art, top left
tf = F(int(Hh * 0.082)); glow((int(W * 0.03), int(Hh * 0.045)), "CAN YOU READ", tf, MAG, spread=14)
glow((int(W * 0.03), int(Hh * 0.045) + tf.size + 2), "THE BOTTOM LINE?", tf, ORG, spread=14)
# footer strip on the art
FY = Hh - int(Hh * 0.062); dr.rectangle([0, FY, W, Hh], fill=(0, 0, 0, 255))
repo = "github.com/tonyd2wild/GLM-5.3-Flash-EXL3-on-2x-NVIDIA-DGX-Spark  ·  results/h2h_tp4.md"
ff = fit(repo, int(Hh * 0.03), int(W * 0.6)); dr.text((int(W * 0.018), FY + int(Hh * 0.031)), repo, font=ff, fill=WHITE, anchor="lm")
cr = "@tonyd2wild  ·  CREDIT: DeepSeek · Z.ai · vLLM · KEYS (DSpark) · incoai (DFlash2)"; fc = fit(cr, int(Hh * 0.024), int(W * 0.36), "demi"); dr.text((W - int(W * 0.018), FY + int(Hh * 0.031)), cr, font=fc, fill=(190, 190, 200), anchor="rm")
art.convert("RGB").save(OUT, quality=95); print("->", OUT, art.size)
