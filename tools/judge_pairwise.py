#!/usr/bin/env python3
"""judge_pairwise.py <judge_base_url> <judge_model> <lane_a_json> <lane_b_json> [--categories prose,narrative,summary,format,coding,html]

Blind pairwise judging of two lanes' outputs from bench_categories.py. For every prompt in the chosen categories the
judge sees the prompt and two anonymous responses (A/B) and returns JSON {"winner": "A"|"B"|"tie", "reason": ...}.
Each pair is judged TWICE with the positions swapped; a lane only gets the win if it wins in both orders, otherwise
the pair is a tie (this cancels position bias). Judge runs at temperature 0. Writes results/judge_<thinking>.json.
"""
import sys, json, argparse, urllib.request, re, time
ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("model"); ap.add_argument("a"); ap.add_argument("b")
ap.add_argument("--categories", default="prose,narrative,summary,format,coding,html")
x = ap.parse_args(); URL = x.base.rstrip("/") + "/v1/chat/completions"
A = json.load(open(x.a)); B = json.load(open(x.b)); cats = x.categories.split(",")
IA = {i["id"]: i for i in A["items"]}; IB = {i["id"]: i for i in B["items"]}
RUBRIC = {"prose": "clarity, accuracy, meeting the brief and its length/word constraints, natural writing",
          "narrative": "meeting every stated constraint, story quality, voice, coherence, satisfying ending",
          "summary": "faithfulness to the source, coverage of the key points, meeting the exact format asked for",
          "format": "following the instruction exactly, nothing extra",
          "coding": "correctness, handling edge cases, clean readable code, doing exactly what was asked",
          "html": "valid well-structured markup, meeting every requirement, accessibility, nothing extra"}
def ask(prompt):
    body = json.dumps({"model": x.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 400, "stream": False,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600)); return r["choices"][0]["message"].get("content") or ""
def judge(cat, prompt, ra, rb):
    q = (f"You are grading two responses to the same task. Criteria: {RUBRIC.get(cat, 'quality and following the task')}.\n"
         f"Judge only on the criteria. Ignore length unless the task set a length. Do not favor a position.\n\n"
         f"### TASK\n{prompt[:6000]}\n\n### RESPONSE A\n{ra[:6000]}\n\n### RESPONSE B\n{rb[:6000]}\n\n"
         f"Reply with JSON only: {{\"winner\": \"A\" or \"B\" or \"tie\", \"reason\": \"one sentence\"}}")
    out = ask(q); m = re.search(r"\{.*?\}", out, re.S)
    try: j = json.loads(m.group(0)); w = str(j.get("winner", "tie")).strip().upper(); return (w if w in ("A", "B") else "tie"), j.get("reason", "")[:200]
    except Exception: return "tie", "unparsable: " + out[:80]
res = []; tally = {}
for pid, ia in IA.items():
    if ia["category"] not in cats or pid not in IB: continue
    ib = IB[pid]; prompt = ia.get("prompt") or f"(prompt id {pid})"
    w1, r1 = judge(ia["category"], prompt, ia["output"], ib["output"])   # A = lane a
    w2, r2 = judge(ia["category"], prompt, ib["output"], ia["output"])   # A = lane b
    a_wins = (w1 == "A" and w2 == "B"); b_wins = (w1 == "B" and w2 == "A")
    verdict = A["lane"] if a_wins else B["lane"] if b_wins else "tie"
    t = tally.setdefault(ia["category"], {A["lane"]: 0, B["lane"]: 0, "tie": 0}); t[verdict] += 1
    res.append({"id": pid, "category": ia["category"], "order1": w1, "order2": w2, "verdict": verdict, "reason1": r1, "reason2": r2})
    print(f"  {pid:8} {ia['category']:10} order1={w1:3} order2={w2:3} -> {verdict}", flush=True)
out = {"judge": x.model, "lanes": [A["lane"], B["lane"]], "thinking": A["thinking"], "tally": tally, "items": res, "ts": time.strftime("%Y-%m-%d %H:%M")}
path = f"results/judge_{A['thinking']}.json"; json.dump(out, open(path, "w"), indent=1)
print("tally:", json.dumps(tally), "->", path)
