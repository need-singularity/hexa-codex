"""Score an adapter on a manifest. bf16 base (for H100). Cleans Qwen FIM/role
markers AND v0.4.x delegation-protocol tokens (`<|confidence:*|>`,
`<|delegate|>…<|/delegate|>`, `<|delegate-result|>…<|/delegate-result|>`)
before compile/substring scoring — r40/r41 lost ~2-3pp Mk.I to confidence
prefix leak; v0.4.2 routing-RL gets clean numbers from the start.
"""
import os, sys, json, argparse, re, subprocess, tempfile
from pathlib import Path
sys.path[:] = [p for p in sys.path if os.path.abspath(p) != os.path.dirname(os.path.abspath(__file__))]
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

HEXA_CC = "/workspace/hexa_cc"
ERR_PATS = ("Parse error", "parse error", "CODEGEN ERROR", "Resolve error", "Type error",
            "Lint S", "unhandled binop", "unhandled operator", "unexpected token")
STOPS = ("<|fim_middle|>", "<|fim_prefix|>", "<|fim_suffix|>", "<|fim_pad|>", "<|endoftext|>",
         "<|im_end|>", "<|im_start|>", "<|repo_name|>", "<|file_sep|>", "### User:", "### Assistant")

# v0.4.x delegation-protocol markers. These appear in delegation-trained
# adapter outputs (r40/r41 and beyond). We strip:
#   - <|confidence:high|>, <|confidence:medium|>, <|confidence:low|>      (prefix)
#   - <|delegate|>{...}<|/delegate|>                                      (block)
#   - <|delegate-result|>{...}<|/delegate-result|>                        (block)
# AFTER STOPS truncation, BEFORE scorer dispatch. A delegation-emit answer
# is then scored on its *non-token* content (refusal text, wrap-up, etc.).
_CONFIDENCE_RE = re.compile(r"<\|confidence:(?:high|medium|low)\|>")
_DELEGATE_RE   = re.compile(r"<\|delegate\|>.*?<\|/delegate\|>", re.DOTALL)
_DELRESULT_RE  = re.compile(r"<\|delegate-result\|>.*?<\|/delegate-result\|>", re.DOTALL)


def _clean(c):
    # Truncate at any STOPS marker.
    for s in STOPS:
        i = c.find(s)
        if i != -1:
            c = c[:i]
    # v0.4.x delegation protocol markers — strip in place so the downstream
    # scorer sees the answer text, not the protocol wrapper. Order matters:
    # remove blocks first (they have inner content the regex matches), then
    # the standalone confidence prefix.
    c = _DELRESULT_RE.sub("", c)
    c = _DELEGATE_RE.sub("", c)
    c = _CONFIDENCE_RE.sub("", c)
    return c.strip()


def s_compile(comp, gold):
    comp = _clean(comp)
    if not comp:
        return False
    if not os.path.exists(HEXA_CC):
        return bool(gold) and gold in comp
    with tempfile.TemporaryDirectory() as td:
        ip = Path(td) / "in.hexa"
        op = Path(td) / "out.c"
        ip.write_text(comp + "\n")
        try:
            r = subprocess.run([HEXA_CC, str(ip), str(op)], capture_output=True, text=True, timeout=10)
        except Exception:
            return False
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        if r.returncode != 0:
            return False
        for p in ERR_PATS:
            if p in out:
                return False
        return True


def s_sub(comp, gold):
    return bool(gold) and gold in _clean(comp)


def s_exact(comp, gold):
    c = _clean(comp).lower()
    g = (gold or "").lower()
    return bool(g) and g in c


def s_yesno(comp, gold):
    first = _clean(comp).split("\n")[0].lower()
    return (gold or "").lower() in first


SCORERS = {
    "s0_s1_exit_0": s_compile, "ast_equality": s_compile,
    "annotation_match": s_sub, "byte_exact_subset": s_sub,
    "exact_match": s_exact, "yes_no_match": s_yesno,
    "code_synth_pass": lambda c, g: bool(_clean(c)) and "out-of-domain" not in _clean(c).lower(),
    "refusal_required": lambda c, g: "out-of-domain" in _clean(c).lower(),
    "explanation_match": lambda c, g: len(_clean(c).split()) >= 5,
}

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True)
ap.add_argument("--adapter", required=True)
ap.add_argument("--manifest", required=True)
ap.add_argument("--output", required=True)
args = ap.parse_args()

print("loading", args.base, "(bf16) + adapter", args.adapter, flush=True)
tok = AutoTokenizer.from_pretrained(args.base)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
m = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.bfloat16, device_map="auto")
m = PeftModel.from_pretrained(m, args.adapter)
m.eval()

rows = [json.loads(l) for l in open(args.manifest) if l.strip()]
print("tasks:", len(rows), flush=True)
out_dir = Path(args.output)
out_dir.mkdir(parents=True, exist_ok=True)
results, fp, ft = [], {}, {}
for i, t in enumerate(rows):
    gold = t.get("gold_pattern", "") or ""
    ids = tok("### User:\n" + t["prompt"] + "\n### Assistant:\n", return_tensors="pt").to(m.device)
    with torch.no_grad():
        out = m.generate(**ids, max_new_tokens=200, do_sample=False, pad_token_id=tok.eos_token_id)
    comp = tok.decode(out[0][ids.input_ids.shape[1]:], skip_special_tokens=True)
    sc = SCORERS.get(t.get("scorer", ""), lambda c, g: False)
    p = bool(sc(comp, gold))
    fam = t.get("family", "?")
    ft[fam] = ft.get(fam, 0) + 1
    if p:
        fp[fam] = fp.get(fam, 0) + 1
    results.append({"task_id": t.get("task_id"), "family": fam, "scorer": t.get("scorer"),
                    "pass": p, "gold_pattern": gold, "completion": comp[:300]})
    if (i + 1) % 50 == 0:
        s = sum(1 for r in results if r["pass"])
        print("  [{}/{}] pass={}/{} = {:.3f}".format(i + 1, len(rows), s, i + 1, s / (i + 1)), flush=True)

tp = sum(1 for r in results if r["pass"])
out_dir.joinpath("per_task_strict.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results))
summ = {"tasks_total": len(rows), "tasks_passed": tp, "pass_at_1": round(tp / len(rows), 4),
        "per_family": {f: "{}/{} = {:.1f}%".format(fp.get(f, 0), ft[f], fp.get(f, 0) / ft[f] * 100) for f in sorted(ft)}}
out_dir.joinpath("scores_strict.json").write_text(json.dumps(summ, indent=2))
print("\nSTRICT pass@1: {} ({}/{})".format(summ["pass_at_1"], tp, len(rows)))
for f in sorted(ft):
    print("  {}: {}/{} = {:.1f}%".format(f, fp.get(f, 0), ft[f], fp.get(f, 0) / ft[f] * 100))
