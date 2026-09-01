#!/usr/bin/env python3
"""quality_battery.py <base_url> <served_model> <lane> [--thinking off|on] [--max-tokens N]

12-item auto-graded quality / reasoning battery, identical for every lane. Each item asks for a checkable final
answer on its own last line as `ANSWER: <x>`; grading is a normalized exact match (numbers compared numerically,
strings case/whitespace-insensitive). temp 0, non-stream. thinking=on lets the model reason first (GLM reasoning
mode); thinking=off forces a direct answer. Writes results/quality_battery_<lane>_<mode>.json with per-item
correctness, the model's final answer, an answer excerpt, reasoning length, tokens and wall time.
"""
import sys, json, time, re, argparse, urllib.request
ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("model"); ap.add_argument("lane")
ap.add_argument("--thinking", default="off", choices=["off", "on"]); ap.add_argument("--max-tokens", type=int, default=0)
a = ap.parse_args(); URL = a.base.rstrip("/") + "/v1/chat/completions"
MAXTOK = a.max_tokens or (2500 if a.thinking == "on" else 700)
SUFFIX = "\n\nGive your final answer on the last line exactly as: ANSWER: <answer>"

ITEMS = [
 ("math1", "math", "A bakery sells muffins in boxes of 6 and cookies in boxes of 8. Maya buys 7 boxes of muffins and 9 boxes of cookies, then gives away one third of the muffins and one quarter of the cookies. How many items does she have left in total?", "82"),
 ("math2", "math", "A tank fills at 12 liters per minute and drains at 5 liters per minute when both valves are open. It starts with 40 liters and has a 250-liter capacity. After how many whole minutes of both valves open does it first reach or exceed capacity?", "30"),
 ("math3", "math", "Three numbers have a mean of 20. The smallest is 8 and the largest is 35. What is the middle number?", "17"),
 ("logic1", "logic", "Alice, Ben and Cara each have a different pet: a cat, a dog and a fish. Alice is allergic to fur. Ben does not have the cat. Who has the dog?", "Ben"),
 ("logic2", "logic", "If all Bloops are Razzies and no Razzie is a Lazzie, can a Bloop be a Lazzie? Answer yes or no.", "no"),
 ("logic3", "logic", "A clock shows 3:15. What is the smaller angle, in degrees, between the hour and minute hands?", "7.5"),
 ("code1", "code", "What does this Python print?\n\nx = [1, 2, 3, 4, 5]\ny = x[1:-1]\ny.append(x[0] * x[-1])\nprint(sum(y) - len(x))", "9"),
 ("code2", "code", "This function should return the second-largest distinct value in a list, or None if there isn't one. It has one bug. What single line is wrong? Reply with the corrected line only.\n\ndef second_largest(nums):\n    s = sorted(set(nums))\n    if len(s) < 2:\n        return None\n    return s[-1]", "return s[-2]"),
 ("know1", "knowledge", "A year is a leap year if it is divisible by 4, except century years, which must be divisible by 400. Which of these is a leap year: 1900, 2000, 2100, 2023? Give one year.", "2000"),
 ("know2", "reasoning", "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost, in dollars?", "0.05"),
 ("fmt1", "format", "Return a JSON object with exactly two keys, \"city\" and \"population\", for the most populous city in Japan, using 13960000 as the population. Output the JSON as the answer.", "{\"city\":\"Tokyo\",\"population\":13960000}"),
 ("fmt2", "format", "Write the word 'benchmark' backwards, in lowercase.", "kramhcneb"),
]

def norm(s):
    s = s.strip().strip("`'\" .*").replace("$", "")
    s = re.sub(r"\s*(°|degrees?|dollars?|liters?|minutes?)\s*$", "", s, flags=re.I).strip()  # units are not the answer
    try: return str(float(s.replace(",", "")))
    except ValueError: return re.sub(r"\s+", "", s).lower()
def grade(item_id, expected, got):
    if item_id == "fmt1":
        try: j = json.loads(got.strip().strip("`")); return j.get("city", "").lower() == "tokyo" and int(j.get("population", 0)) == 13960000
        except Exception: return norm(got) == norm(expected)
    if item_id == "code2": return norm(got).replace("\n", "") == norm(expected)
    return norm(got) == norm(expected)

def ask(prompt):
    body = json.dumps({"model": a.model, "messages": [{"role": "user", "content": prompt + SUFFIX}], "temperature": 0,
                       "max_tokens": MAXTOK, "stream": False, "chat_template_kwargs": {"enable_thinking": a.thinking == "on"}}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t = time.time(); r = json.load(urllib.request.urlopen(req, timeout=900)); dt = time.time() - t
    m = r["choices"][0]["message"]; txt = m.get("content") or ""
    rc = m.get("reasoning") or m.get("reasoning_content") or ""  # vLLM's glm45 parser returns the trace as `reasoning`
    return txt, rc, r.get("usage", {}).get("completion_tokens", 0), dt, r["choices"][0].get("finish_reason")

results, correct = [], 0
for iid, cat, prompt, expected in ITEMS:
    txt, rc, tok, dt, fin = ask(prompt)
    m = re.findall(r"ANSWER:\s*(.+)", txt); got = m[-1].strip() if m else ""
    no_line = not m
    if no_line:  # no ANSWER: line — grade the last non-empty line of the reply instead, and flag it
        lines = [l for l in txt.strip().splitlines() if l.strip()]; got = lines[-1].strip() if lines else ""
    ok = bool(got) and grade(iid, expected, got); correct += ok
    results.append({"id": iid, "category": cat, "expected": expected, "got": got[:120], "correct": ok, "no_answer_line": no_line,
                    "finish": fin, "completion_tokens": tok, "wall_s": round(dt, 1), "reasoning_chars": len(rc),
                    "reasoning_excerpt": rc[:600], "answer_excerpt": txt[-300:], "content": txt})
    print(f"  [{a.lane}/{a.thinking}] {iid:6} {cat:9} {'OK ' if ok else 'X  '} got={got[:40]!r:44} exp={expected[:30]!r} ({tok} tok, {dt:.1f}s, reasoning {len(rc)} ch, {fin})", flush=True)
by_cat = {}
for r_ in results: by_cat.setdefault(r_["category"], [0, 0]); by_cat[r_["category"]][1] += 1; by_cat[r_["category"]][0] += r_["correct"]
out = {"lane": a.lane, "model": a.model, "thinking": a.thinking, "n": len(ITEMS), "correct": correct,
       "accuracy": round(correct / len(ITEMS), 3), "by_category": by_cat, "items": results, "ts": time.strftime("%Y-%m-%d %H:%M")}
path = f"results/quality_battery_{a.lane}_{a.thinking}.json"; json.dump(out, open(path, "w"), indent=1)
print(f"[{a.lane}/{a.thinking}] {correct}/{len(ITEMS)} correct ({out['accuracy']*100:.0f}%)  by category: {by_cat}  -> {path}")
