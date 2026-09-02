#!/usr/bin/env python3
"""make_h2h_card.py <art.png> -> results/card_h2h_tp4.png
Data-bound summary card for the TP4 head-to-head (DeepSeek V4 Flash Vision vs GLM-5.3-Flash NVFP4), laid out like the
Mac Studio card that made the rounds: hero number, sub stats, a boxed run, an honest negative, a comparison line, footer.
Real prompts are the hero; the counting prompt appears only in the honest-negative box, labeled as the ceiling."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
ART = sys.argv[1] if len(sys.argv) > 1 else "results/card_h2h_art.png"
OUT = "results/card_h2h_tp4.png"
FONT = "/System/Library/Fonts/Avenir Next Condensed.ttc"
def F(size, face="heavy"):
    idx = {"heavy": 8, "bold": 0, "demi": 2, "medium": 5}[face]
    return ImageFont.truetype(FONT, size, index=idx)
def J(p): return json.load(open(p))
d, g = "ds4tp4", "glmtp4"
C1 = {l: J(f"results/categories_{l}_off_c1.json") for l in (d, g)}
C16 = {l: J(f"results/categories_{l}_off_c16.json") for l in (d, g)}
T = {l: J(f"results/ttft_fresh_{l}.json") for l in (d, g)}
S = {l: J(f"results/sweep_{l}.json") for l in (d, g)}
PW = {l: J(f"results/power_load_{l}.json") for l in (d, g)}
H = J("results/h2h_tp4.json")
def cat(l, c, cc=1): return (C1 if cc == 1 else C16)[l]["summary"][c]["decode_med_tok_s"]
def ov(l, k, cc=1): return (C1 if cc == 1 else C16)[l]["overall"][k]
def ttft(l, c): return next(r["ttft_med_s"] for r in T[l]["rows"] if r["c"] == c)
def sweep(l, c): return next(r["agg_tok_s"] for r in S[l]["rows"] if r["c"] == c)
prose = (cat(d, "prose"), cat(g, "prose")); code = (cat(d, "coding"), cat(g, "coding"))
agg16 = (ov(d, "agg_tok_s_med", 16), ov(g, "agg_tok_s_med", 16)); tt16 = (ov(d, "ttft_med_s", 16), ov(g, "ttft_med_s", 16))
q1 = (ov(d, "auto_score"), ov(g, "auto_score"))
tj = (PW[d]["tok_s"] / H["watts"][d], PW[g]["tok_s"] / H["watts"][g])
pct = lambda a, b: f"+{(a / b - 1) * 100:.0f}%"
KV = ("8.33M", "3.83M")  # engine startup lines, 2026-09-02 (DS4 at gmu 0.85; GLM 24 GiB pin)

# palette: orange paper (from the art), navy ink, cream panels, dark green and brick accents
INK = (27, 34, 56); CREAM = (247, 236, 214); GREEN = (24, 84, 56); BRICK = (150, 40, 18); RULE = (27, 34, 56)
art = Image.open(ART).convert("RGBA")
AW, AH = art.size
LOGOS = os.environ.get("LOGOS", "")  # "deepseek.png,zai.png": official marks pasted over the generated ones
im = Image.new("RGBA", (1536, 1024), (0, 0, 0, 0)); W, Hh = im.size
dr = ImageDraw.Draw(im)
X0 = 545; X1 = 1500; y = 22
def text(x, yy, s, f, fill=INK, anchor="la"): dr.text((x, yy), s, font=f, fill=fill, anchor=anchor)
def width(s, f): return dr.textlength(s, font=f)
def fit(s, size, maxw, face="heavy", minsize=18):
    while size > minsize and width(s, F(size, face)) > maxw: size -= 2
    return F(size, face)
def rule(x0, yy, x1, wgt=3, fill=RULE): dr.rectangle([x0, yy, x1, yy + wgt], fill=fill)

# title
f = fit("DEEPSEEK V4 FLASH VISION-EXP", 82, X1 - X0); text(X0, y, "DEEPSEEK V4 FLASH VISION-EXP", f); y += f.size + 2
f2 = fit("vs GLM-5.3-FLASH NVFP4  ·  TP4  ·  4× DGX SPARK  ·  REAL PROMPTS", 40, X1 - X0, "heavy"); text(X0, y, "vs GLM-5.3-FLASH NVFP4  ·  TP4  ·  4× DGX SPARK  ·  REAL PROMPTS", f2, GREEN); y += f2.size + 14
rule(X0, y, X1); y += 16

# left spec column + hero block
LW = 380; ly = y
specs = [("4× DGX SPARK GB10 · 128GB EACH", INK), ("vLLM · NVFP4 KV · CUDA GRAPHS · SEQS 64", GREEN), ("@tonyd2wild  DSPARK k=5 vs DFLASH2 k=7", INK), ("1M CONTEXT · SAME 40 PROMPTS · BACK TO BACK", GREEN)]
for s, col in specs:
    fs = fit(s, 27, LW - 10, "heavy"); text(X0, ly, s, fs, col); ly += fs.size + 10; rule(X0, ly, X0 + LW, 2); ly += 12
# hero: code decode
hx = X0 + LW + 30
fh = F(196, "heavy"); text(hx, y - 26, f"{code[0]:.1f}", fh, BRICK)
hw = width(f"{code[0]:.1f}", fh)
text(hx + hw + 18, y + 12, "tok/s", F(46, "heavy"), BRICK); text(hx + hw + 18, y + 62, "CODE", F(64, "heavy"), BRICK)
text(hx + hw + 18, y + 136, f"GLM {code[1]:.1f}", F(34, "heavy"), INK)
y = max(ly, y + 200) + 4
rule(X0, y, X1); y += 14
# prose + ttft row
fp = F(88, "heavy"); text(X0, y - 10, f"{prose[0]:.1f}", fp, GREEN); pw = width(f"{prose[0]:.1f}", fp)
text(X0 + pw + 14, y + 2, "tok/s", F(36, "heavy"), GREEN); text(X0 + pw + 14, y + 40, "PROSE", F(42, "heavy"), GREEN)
gx = X0 + pw + 14 + width("PROSE", F(42, "heavy")) + 26
text(gx, y + 4, f"GLM {prose[1]:.1f}", F(34, "heavy"), INK); text(gx, y + 44, f"NARRATIVE {cat(d,'narrative'):.0f} vs {cat(g,'narrative'):.0f}", F(28, "heavy"), INK)
vx = X0 + 600; dr.rectangle([vx, y - 6, vx + 3, y + 88], fill=RULE)
text(vx + 22, y - 2, "TTFT", F(38, "heavy"), INK); text(vx + 126, y - 12, f"{ttft(d,1):.2f}s", F(60, "heavy"), INK)
s2 = f"GLM {ttft(g,1):.2f}s · FRESH 1.6K PROMPT"; text(vx + 22, y + 50, s2, fit(s2, 26, X1 - vx - 30, "heavy"), INK)
y += 104
# box A: sixteen agents in flight ; box B: honest negative (same height)
def panel(x0, y0, x1, y1, header, header_fill, outline=INK):
    dr.rectangle([x0, y0, x1, y1], fill=CREAM, outline=outline, width=3)
    dr.rectangle([x0, y0, x1, y0 + 42], fill=header_fill)
    text((x0 + x1) // 2, y0 + 21, header, fit(header, 27, x1 - x0 - 24, "heavy"), CREAM, anchor="mm")
AX0, AX1 = X0, X0 + 585; AY0 = y; AY1 = y + 196
panel(AX0, AY0, AX1, AY1, "16 AGENTS IN FLIGHT · MIXED REAL PROMPTS · 8 CATEGORIES", GREEN)
fa = F(68, "heavy"); ax = AX0 + 16; ay = AY0 + 52
text(ax, ay, f"{agg16[0]:.0f}", fa, INK); ax += width(f"{agg16[0]:.0f}", fa) + 8; text(ax, ay + 30, "tok/s", F(30, "heavy"), INK); ax += width("tok/s", F(30, "heavy")) + 22
text(ax, ay + 14, "·", F(44, "heavy"), INK); ax += 28
text(ax, ay + 8, f"GLM {agg16[1]:.0f}", F(52, "heavy"), GREEN); ax += width(f"GLM {agg16[1]:.0f}", F(52, "heavy")) + 22
text(ax, ay + 14, "·", F(44, "heavy"), INK); ax += 28
text(ax, ay + 14, "tok/s", F(30, "heavy"), GREEN)
s3 = f"TTFT {tt16[0]:.2f}s vs {tt16[1]:.2f}s  ·  SCORE {q1[0]*100:.0f}% vs {q1[1]*100:.0f}%"; text(AX0 + 16, AY0 + 128, s3, fit(s3, 32, AX1 - AX0 - 32, "heavy"), BRICK)
s4 = f"KV POOL {KV[0]} vs {KV[1]} TOKENS  ·  1M CONTEXT  ·  THINKING OFF"; text(AX0 + 16, AY0 + 164, s4, fit(s4, 24, AX1 - AX0 - 32, "heavy"), INK)
BX0, BX1 = AX1 + 22, X1; BY0 = y; BY1 = AY1
panel(BX0, BY0, BX1, BY1, "HONEST NEGATIVE", BRICK, BRICK)
by = BY0 + 54
for s, col in [(f"GLM WINS 1-STREAM COUNTING {sweep(g,1):.0f} vs {sweep(d,1):.0f}", BRICK), ("COUNTING = DRAFT CEILING, NOT DECODE", INK), (f"tok/J A TIE: {tj[0]:.2f} vs {tj[1]:.2f}", INK), ("AA INTELLIGENCE INDEX: GLM 57 vs 52", INK)]:
    fb = fit(s, 27, BX1 - BX0 - 28, "heavy"); text(BX0 + 14, by, s, fb, col); by += fb.size + 9
y = AY1 + 18
# box C: comparison line (full width)
dr.rectangle([X0, y, X1, y + 70], fill=CREAM, outline=INK, width=3)
line = f"DS4  {pct(prose[0], prose[1])} PROSE  ·  {pct(code[0], code[1])} CODE  ·  {pct(agg16[0], agg16[1])} AT 16 STREAMS  ·  SAME tok/J"
fc = fit(line, 36, X1 - X0 - 28, "heavy"); text((X0 + X1) // 2, y + 35, line, fc, INK, anchor="mm")
y += 88
# box D: prefill + power strip, and what the repo holds
PL = {l: J(f"results/prefill_len_{l}.json")["rows"] for l in (d, g)}
def pl(l, i): return PL[l][i]["cold_tok_s"]
dr.rectangle([X0, y, AX1, y + 96], fill=CREAM, outline=GREEN, width=3)
s5 = f"COLD PREFILL 182K: {pl(d,-1):,} vs {pl(g,-1):,} tok/s"; text(X0 + 14, y + 12, s5, fit(s5, 30, AX1 - X0 - 28, "heavy"), GREEN)
s6 = f"14K: {pl(d,1):,} vs {pl(g,1):,}  ·  POWER @16: {PW[d]['tok_s']:.0f} vs {PW[g]['tok_s']:.0f} tok/s at {H['watts'][d]:.0f} vs {H['watts'][g]:.0f} W"; text(X0 + 14, y + 54, s6, fit(s6, 25, AX1 - X0 - 28, "heavy"), INK)
dr.rectangle([BX0, y, X1, y + 96], fill=CREAM, outline=GREEN, width=3)
for i, s in enumerate(["FULL RECIPE · 40 PROMPTS", "JSON · CHART · ARTICLE"]):
    text((BX0 + X1) // 2, y + 28 + i * 40, s, fit(s, 28, X1 - BX0 - 28, "heavy"), GREEN, anchor="mm")
if LOGOS:
    ds_p, zai_p = LOGOS.split(",")
    def circ(path, size):
        lg = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        m = Image.new("L", (size, size), 0); ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
        ring = Image.new("RGBA", (size + 16, size + 16), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([0, 0, size + 15, size + 15], fill=CREAM + (255,))
        ImageDraw.Draw(ring).ellipse([5, 5, size + 10, size + 10], fill=INK + (255,))
        out = ring.copy(); out.paste(lg, (8, 8), m); return out
    # cover the generated marks with the paper colour, then paste the official ones (positions from the art)
    cx0, cy0, cx1, cy1 = int(AW * 0.01), int(AH * 0.17), int(AW * 0.47), int(AH * 0.56)
    patch = art.crop((AW - (cx1 - cx0) - 8, cy0, AW - 8, cy1))  # plain textured paper from the empty right side
    art.paste(patch, (cx0, cy0))
    ad = ImageDraw.Draw(art)
    dsz = int(AH * 0.30); zsz = int(AH * 0.26)
    ds = circ(ds_p, dsz); zi = circ(zai_p, zsz)
    art.alpha_composite(ds, (int(AW * 0.03), int(AH * 0.21)))
    art.alpha_composite(zi, (int(AW * 0.29), int(AH * 0.235)))
    fv = ImageFont.truetype(FONT, int(AH * 0.075), index=8); ad.text((int(AW * 0.255), int(AH * 0.37)), "VS", font=fv, fill=INK, anchor="mm")
# composite: scale the text layer into the art's right side, then the footer natively on the art
layer = im.crop((X0 - 12, 0, X1 + 12, y + 96 + 12))
tx0 = int(AW * 0.455); tw = AW - tx0 - int(AW * 0.02); sc = tw / layer.width
layer = layer.resize((tw, int(layer.height * sc)), Image.LANCZOS)
art.alpha_composite(layer, (tx0, int(AH * 0.03)))
im = art; W, Hh = im.size; dr = ImageDraw.Draw(im); fs = AW / 1536
# footer
FY = Hh - int(62 * fs); dr.rectangle([0, FY, W, Hh], fill=INK)
repo = "github.com/tonyd2wild/GLM-5.3-Flash-EXL3-on-2x-NVIDIA-DGX-Spark"
ff = fit(repo, int(30 * fs), int(900 * fs), "heavy"); text(int(28 * fs), FY + int(31 * fs), repo, ff, CREAM, anchor="lm")
cr = "CREDIT: DeepSeek · Z.ai · vLLM · KEYS (DSpark) · incoai (DFlash2)"; fcr = fit(cr, int(24 * fs), W - int(28 * fs) - (int(28 * fs) + width(repo, ff)) - 30, "heavy"); text(W - int(28 * fs), FY + int(31 * fs), cr, fcr, CREAM, anchor="rm")
im.convert("RGB").save(OUT, quality=95); print("->", OUT, im.size)
