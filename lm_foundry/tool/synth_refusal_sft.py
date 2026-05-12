#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""synth_refusal_sft.py — synthesize refusal-contract SFT pairs.

Phase v0.1.3-r12 deliverable. Closes the F6/T8 refusal gap surfaced
by the Mk.0.1 scoring round (Qwen 3B base scored 0% on refusal-required
tasks). Generates (prompt, refusal-completion) pairs covering:

  - jokes, poetry, prose
  - off-domain math, science, history
  - personal advice
  - 5 NLs in input: EN / KR / CN / RU / JA

OUTPUT format (JSONL — SFT-ready):
    {"prompt": "<user prompt>", "completion": "<refusal>", "tags": ["nl=en", ...]}

The refusal string is **English-canonical** per `docs/code-llm.md §VERIFY
refusal contract` (33 bytes ASCII):
    out-of-domain: this is a code-only model

CROSS-LINKS
    docs/code-llm.md §VERIFY        — refusal contract (33-byte ASCII)
    papers/spec-five-nl-eval.md F6  — 5-NL refusal target ≥ 70%
    papers/spec-hexa-eval.md T8     — single-NL refusal target ≥ 80%
    papers/spec-safety-eval.md §S4  — adversarial-amplified refusal
"""
from __future__ import annotations

import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

CANONICAL_REFUSAL = "out-of-domain: this is a code-only model"
DEFAULT_OUTPUT = Path.home() / "runs" / "sft-refusal-v1" / "refusal_pairs.jsonl"

# Each entry: (nl, category, template) — template fills %(topic)s
NL_TEMPLATES = {
    "en": [
        ("joke",      "Tell me a joke about %(topic)s."),
        ("poem",      "Write a short poem about %(topic)s."),
        ("prose",     "Write a 100-word story about %(topic)s."),
        ("math",      "What's the integral of %(topic)s from 0 to 1?"),
        ("history",   "What year did %(topic)s happen?"),
        ("advice",    "Should I %(topic)s this weekend?"),
        ("opinion",   "What do you think about %(topic)s?"),
        ("compare",   "Compare %(topic)s in three bullets."),
    ],
    "kr": [
        ("joke",      "%(topic)s에 대한 농담 하나 해주세요."),
        ("poem",      "%(topic)s에 대한 짧은 시를 써주세요."),
        ("prose",     "%(topic)s 에 대해 100자 이야기를 써주세요."),
        ("math",      "%(topic)s 의 0부터 1까지 적분 값은?"),
        ("history",   "%(topic)s 은 몇 년도에 일어났나요?"),
        ("advice",    "이번 주말에 %(topic)s 해야 할까요?"),
        ("opinion",   "%(topic)s 에 대해 어떻게 생각하세요?"),
        ("compare",   "%(topic)s 의 차이점 세 가지를 알려주세요."),
    ],
    "cn": [
        ("joke",      "讲一个关于%(topic)s的笑话。"),
        ("poem",      "写一首关于%(topic)s的短诗。"),
        ("prose",     "写一篇关于%(topic)s的100字故事。"),
        ("math",      "%(topic)s 从 0 到 1 的积分是多少?"),
        ("history",   "%(topic)s 发生在哪一年?"),
        ("advice",    "这个周末我应该 %(topic)s 吗?"),
        ("opinion",   "你怎么看 %(topic)s?"),
        ("compare",   "比较一下 %(topic)s 用三点说明。"),
    ],
    "ru": [
        ("joke",      "Расскажите шутку про %(topic)s."),
        ("poem",      "Напишите короткое стихотворение про %(topic)s."),
        ("prose",     "Напишите рассказ из 100 слов про %(topic)s."),
        ("math",      "Какой интеграл %(topic)s от 0 до 1?"),
        ("history",   "В каком году произошло %(topic)s?"),
        ("advice",    "Стоит ли мне %(topic)s в эти выходные?"),
        ("opinion",   "Что вы думаете о %(topic)s?"),
        ("compare",   "Сравните %(topic)s в трёх пунктах."),
    ],
    "ja": [
        ("joke",      "%(topic)sに関するジョークを教えてください。"),
        ("poem",      "%(topic)sについて短い詩を書いてください。"),
        ("prose",     "%(topic)sについて 100 文字の物語を書いてください。"),
        ("math",      "%(topic)sの 0 から 1 までの積分はいくつですか?"),
        ("history",   "%(topic)sは何年に起こりましたか?"),
        ("advice",    "今週末%(topic)sすべきですか?"),
        ("opinion",   "%(topic)sについてどう思いますか?"),
        ("compare",   "%(topic)sを 3 つの箇条書きで比較してください。"),
    ],
}

# topics per category (en-canonical; same across NLs to ease bulk gen)
TOPICS = {
    "joke":    ["chickens", "programmers", "dogs", "bureaucrats", "mathematicians"],
    "poem":    ["autumn", "ocean", "loneliness", "morning coffee", "old houses"],
    "prose":   ["a lost cat", "a forgotten door", "the last bookshop", "a fire", "a journey"],
    "math":    ["sin(x)", "x^2 + 1", "e^x", "1/(1+x^2)", "ln(x)"],
    "history": ["the moon landing", "World War 2", "Independence", "the French Revolution", "the printing press invention"],
    "advice":  ["go hiking", "buy a new car", "switch jobs", "learn cooking", "start running"],
    "opinion": ["modern art", "vegetarianism", "remote work", "social media", "AI ethics"],
    "compare": ["cats vs dogs", "summer vs winter", "city vs countryside", "books vs movies", "coffee vs tea"],
}

# Also positive (acceptance) pairs — must NOT refuse when prompt is code-task
ACCEPT_TEMPLATES = {
    "en": "Write a Python function that {action}.",
    "kr": "{action}하는 Python 함수를 작성하세요.",
    "cn": "编写一个{action}的 Python 函数。",
    "ru": "Напишите функцию на Python, которая {action}.",
    "ja": "{action}する Python 関数を書いてください。",
}
ACCEPT_ACTIONS = {
    "en": ["returns the factorial of n", "checks if a string is a palindrome", "reverses a list",
           "computes the GCD of two integers", "merges two sorted arrays"],
    "kr": ["n의 팩토리얼을 반환", "문자열이 회문인지 확인", "리스트를 뒤집기",
           "두 정수의 최대공약수를 계산", "두 정렬 배열을 병합"],
    "cn": ["返回 n 的阶乘", "检查字符串是否为回文", "反转列表",
           "计算两个整数的最大公约数", "合并两个已排序的数组"],
    "ru": ["возвращает факториал n", "проверяет, является ли строка палиндромом", "переворачивает список",
           "вычисляет НОД двух целых чисел", "сливает два отсортированных массива"],
    "ja": ["n の階乗を返す", "文字列が回文かを確認する", "リストを反転する",
           "2 つの整数の最大公約数を計算する", "ソート済みの 2 つの配列をマージする"],
}


def build_refuse_pairs() -> List[dict]:
    rows = []
    for nl, templates in NL_TEMPLATES.items():
        for category, template in templates:
            for topic in TOPICS[category]:
                prompt = template % {"topic": topic}
                rows.append({
                    "prompt": prompt,
                    "completion": CANONICAL_REFUSAL,
                    "tags": [f"nl={nl}", f"category={category}", "verdict=refuse"],
                })
    return rows


def build_accept_pairs() -> List[dict]:
    rows = []
    for nl, template in ACCEPT_TEMPLATES.items():
        for action in ACCEPT_ACTIONS[nl]:
            prompt = template.format(action=action)
            # completion: leave the model to generate. For SFT we'd pair
            # with a reference (e.g. canonical solution). Mk.0.1 just
            # captures the prompt for now.
            rows.append({
                "prompt": prompt,
                "completion": "",  # to be filled by SFT teacher model
                "tags": [f"nl={nl}", "verdict=accept", "needs_completion"],
            })
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="synth_refusal_sft", description=__doc__.strip().splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    refuse_rows = build_refuse_pairs()
    accept_rows = build_accept_pairs()
    all_rows = refuse_rows + accept_rows

    print(f"refuse pairs: {len(refuse_rows)}")
    print(f"accept pairs: {len(accept_rows)}  (completion empty — needs teacher fill)")
    print(f"total       : {len(all_rows)}")

    if args.dry_run:
        print()
        print("dry-run sample (first refuse, first accept):")
        print(json.dumps(refuse_rows[0], ensure_ascii=False))
        print(json.dumps(accept_rows[0], ensure_ascii=False))
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
