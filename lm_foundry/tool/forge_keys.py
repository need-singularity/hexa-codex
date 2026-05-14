#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""forge_keys.py — vendor API key management CLI for forge runtime (r65).

Wraps the `~/core/secret/bin/secret` CLI (dancinlab credential store)
for the 3 vendor keys that `ForgeRuntimeConfig._load_key()` looks up.
No more remembering `security add-generic-password -s anthropic.api_key
-a $USER -w sk-ant-...` — just `forge_keys add anthropic` and paste.

Wraps stdin-only key entry so the key NEVER appears in shell history
or `ps` output.

USAGE
    # Show which keys are currently registered (env + secret store)
    python3 tool/forge_keys.py status

    # Add or update a key (reads from stdin; key never visible in argv)
    python3 tool/forge_keys.py add anthropic
    # then paste the key + Enter

    # Add via shell pipe (safer than argv)
    cat /path/to/key.txt | python3 tool/forge_keys.py add anthropic

    # Test that a configured key actually works (makes a real API call)
    python3 tool/forge_keys.py test anthropic
    python3 tool/forge_keys.py test openai
    python3 tool/forge_keys.py test gemini
    python3 tool/forge_keys.py test all       # all 3

    # Test costs:
    #   anthropic: ~$0.00006 (claude-haiku-4-5; 1-3 tokens)
    #   openai:    ~$0.00001 (gpt-5-nano; ~10 tokens)
    #   gemini:    ~$0.00001 (gemini-2.5-flash-lite; tiny)

    # Remove a key from the store
    python3 tool/forge_keys.py remove openai

VENDOR ↔ SECRET-KEY MAPPING

    vendor=anthropic → secret-key: anthropic.api_key
    vendor=openai    → secret-key: openai.api_key
    vendor=gemini    → secret-key: gemini.api_key
"""
from __future__ import annotations

# Scrub tool/ from sys.path BEFORE stdlib imports
import os as _os  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

_THIS_DIR = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if Path(p).resolve() != _THIS_DIR]

import argparse  # noqa: E402
import subprocess  # noqa: E402

sys.path.insert(0, str(_THIS_DIR))


# Map vendor short-name → (secret-store-key, env-var, friendly-name).
VENDORS = {
    "anthropic": ("anthropic.api_key", "ANTHROPIC_API_KEY", "Anthropic Claude"),
    "openai":    ("openai.api_key",    "OPENAI_API_KEY",    "OpenAI"),
    "gemini":    ("gemini.api_key",    "GEMINI_API_KEY",    "Google Gemini"),
}

_SECRET_CLI = _os.path.expanduser("~/core/secret/bin/secret")


def _secret_get(key: str) -> str | None:
    """Read a key from the dancinlab secret store. Returns None if missing."""
    if not _os.path.exists(_SECRET_CLI):
        return None
    try:
        r = subprocess.run([_SECRET_CLI, "get", key],
                            capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _secret_set(key: str, value: str) -> bool:
    """Write a key to the dancinlab secret store via stdin (NOT argv).
    Returns True on success."""
    if not _os.path.exists(_SECRET_CLI):
        print(f"ERROR: secret CLI not found at {_SECRET_CLI}", file=sys.stderr)
        return False
    try:
        # `secret set <key>` reads from stdin when no value on argv
        r = subprocess.run([_SECRET_CLI, "set", key],
                            input=value, capture_output=True, text=True,
                            timeout=10)
        if r.returncode == 0:
            return True
        print(f"ERROR: secret set failed: {r.stderr.strip()}", file=sys.stderr)
        return False
    except (OSError, subprocess.SubprocessError) as e:
        print(f"ERROR: secret set failed: {e!r}", file=sys.stderr)
        return False


def _secret_rm(key: str) -> bool:
    """Remove a key from the dancinlab secret store."""
    if not _os.path.exists(_SECRET_CLI):
        return False
    try:
        r = subprocess.run([_SECRET_CLI, "rm", key],
                            capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def cmd_status(args) -> int:
    """Print current state of all 3 vendor keys (env + secret store + runtime resolution)."""
    print("=" * 70)
    print("forge_keys — vendor key status")
    print("=" * 70)
    if not _os.path.exists(_SECRET_CLI):
        print(f"WARN: secret CLI not found at {_SECRET_CLI}", file=sys.stderr)
        print(f"      install via dancinlab/secret repo, or fall back to env vars\n")

    print(f"{'vendor':<12} {'env var':<22} {'secret store':<25} {'runtime resolves':<10}")
    print("-" * 70)

    from forge_runtime import ForgeRuntimeConfig  # type: ignore  # noqa: E402
    cfg = ForgeRuntimeConfig.from_env()
    resolved_map = {
        "anthropic": bool(cfg.anthropic_api_key),
        "openai":    bool(cfg.openai_api_key),
        "gemini":    bool(cfg.gemini_api_key),
    }

    for vendor, (secret_key, env_var, _friendly) in VENDORS.items():
        env_set = "✓ set" if _os.environ.get(env_var) else "—"
        secret_set = "✓ set" if _secret_get(secret_key) else "—"
        resolved = "✓ YES" if resolved_map[vendor] else "✗ MISSING"
        print(f"{vendor:<12} {env_var + (' (' + env_set + ')'):<22} "
              f"{secret_key + ' (' + secret_set + ')':<25} {resolved:<10}")

    print()
    n_resolved = sum(resolved_map.values())
    if n_resolved == 3:
        print("All 3 vendor keys resolved. Runtime is ready for any tier route.")
    elif n_resolved == 0:
        print("No vendor keys resolved. Use `forge_keys add <vendor>` to register.")
    else:
        missing = [v for v, ok in resolved_map.items() if not ok]
        print(f"Resolved: {n_resolved}/3. Missing: {', '.join(missing)}")
        print(f"Add missing key(s) via: forge_keys add <vendor>")
    return 0


def cmd_add(args) -> int:
    """Add or update a vendor key. Reads from stdin (key never visible in argv)."""
    vendor = args.vendor
    if vendor not in VENDORS:
        print(f"ERROR: unknown vendor '{vendor}'. Choose: {', '.join(VENDORS)}",
              file=sys.stderr)
        return 1
    secret_key, env_var, friendly = VENDORS[vendor]

    if not _os.path.exists(_SECRET_CLI):
        print(f"ERROR: secret CLI not found at {_SECRET_CLI}", file=sys.stderr)
        print(f"       install dancinlab/secret first, or set env var {env_var}",
              file=sys.stderr)
        return 1

    # Read the key from stdin. If interactive, prompt; if piped, read directly.
    if sys.stdin.isatty():
        print(f"→ Adding {friendly} API key to secret store as `{secret_key}`")
        print(f"  Paste the key now (input hidden), then Enter:")
        try:
            import getpass
            key_value = getpass.getpass(prompt="  key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nABORTED.", file=sys.stderr)
            return 1
    else:
        key_value = sys.stdin.read().strip()

    if not key_value:
        print("ERROR: empty key value", file=sys.stderr)
        return 1
    # Sanity check the shape
    expect_prefixes = {
        "anthropic": ["sk-ant-", "sk-"],
        "openai":    ["sk-", "sk-proj-"],
        "gemini":    ["AIza"],
    }
    prefixes = expect_prefixes.get(vendor, [])
    if prefixes and not any(key_value.startswith(p) for p in prefixes):
        print(f"WARN: key does not start with expected prefix(es) {prefixes}",
              file=sys.stderr)
        print(f"      proceeding anyway; verify with `forge_keys test {vendor}`",
              file=sys.stderr)

    if not _secret_set(secret_key, key_value):
        return 1
    print(f"✓ stored {secret_key} (key length {len(key_value)} chars)")
    print(f"  Test with: python3 tool/forge_keys.py test {vendor}")
    return 0


def cmd_remove(args) -> int:
    """Remove a vendor key from the secret store."""
    vendor = args.vendor
    if vendor not in VENDORS:
        print(f"ERROR: unknown vendor '{vendor}'. Choose: {', '.join(VENDORS)}",
              file=sys.stderr)
        return 1
    secret_key, _, friendly = VENDORS[vendor]
    if _secret_get(secret_key) is None:
        print(f"  {secret_key} not in store — nothing to remove.")
        return 0
    if _secret_rm(secret_key):
        print(f"✓ removed {secret_key}")
        return 0
    print(f"ERROR: failed to remove {secret_key}", file=sys.stderr)
    return 1


def _test_anthropic(cfg, model: str = "claude-haiku-4-5-20251001") -> tuple[bool, str]:
    """Make a 1-token call to the given anthropic model. Defaults to haiku (cheap)."""
    try:
        import anthropic
    except ImportError:
        return False, "anthropic SDK not installed (pip install anthropic)"
    try:
        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key, timeout=15.0)
        resp = client.messages.create(
            model=model,
            max_tokens=5,
            messages=[{"role": "user", "content": "Say OK only."}],
        )
        text = resp.content[0].text if resp.content else ""
        usage = resp.usage
        return True, (f"OK ({model}) — returned {text!r}, "
                       f"in={usage.input_tokens} out={usage.output_tokens}")
    except anthropic.AuthenticationError as e:
        return False, f"AUTH FAILED ({model}): {e}"
    except Exception as e:
        return False, f"FAILED ({model}): {e!r}"


def _test_openai(cfg, model: str = "gpt-5-nano") -> tuple[bool, str]:
    """Make a tiny call to the given OpenAI model. Defaults to gpt-5-nano (cheap)."""
    try:
        import openai
    except ImportError:
        return False, "openai SDK not installed (pip install openai)"
    try:
        client = openai.OpenAI(api_key=cfg.openai_api_key, timeout=15.0)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=5,
            messages=[{"role": "user", "content": "Say OK only."}],
        )
        text = (resp.choices[0].message.content or "").strip()
        usage = resp.usage
        return True, (f"OK ({model}) — returned {text!r}, "
                       f"in={usage.prompt_tokens} out={usage.completion_tokens}")
    except openai.AuthenticationError as e:
        return False, f"AUTH FAILED ({model}): {e}"
    except Exception as e:
        # If requested model not available, try gpt-4o-mini fallback (only for default)
        if model == "gpt-5-nano":
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Say OK only."}],
                )
                text = (resp.choices[0].message.content or "").strip()
                return True, f"OK (via gpt-4o-mini fallback) — returned {text!r}"
            except Exception:
                return False, f"FAILED ({model}): {e!r}"
        return False, f"FAILED ({model}): {e!r}"


def _test_gemini(cfg, model: str = "gemini-2.5-flash-lite") -> tuple[bool, str]:
    """Make a tiny call to the given gemini model. Defaults to flash-lite (cheap)."""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        return False, "google-genai SDK not installed (pip install google-genai)"
    try:
        client = genai.Client(api_key=cfg.gemini_api_key)
        resp = client.models.generate_content(
            model=model,
            contents="Say OK only.",
            config=genai_types.GenerateContentConfig(max_output_tokens=5),
        )
        text = getattr(resp, "text", None) or ""
        u = getattr(resp, "usage_metadata", None)
        in_tok = getattr(u, "prompt_token_count", 0) if u else 0
        out_tok = getattr(u, "candidates_token_count", 0) if u else 0
        return True, (f"OK ({model}) — returned {text!r}, "
                       f"in={in_tok} out={out_tok}")
    except Exception as e:
        msg = str(e).lower()
        if "auth" in msg or "api key" in msg or "401" in msg or "permission" in msg:
            return False, f"AUTH FAILED ({model}): {e}"
        if "quota" in msg or "rate" in msg or "429" in msg or "resource_exhausted" in msg:
            return False, f"QUOTA ({model}): {e}"
        return False, f"FAILED ({model}): {e!r}"


VENDOR_URLS = {
    "anthropic": "https://console.anthropic.com/settings/keys",
    "openai":    "https://platform.openai.com/api-keys",
    "gemini":    "https://aistudio.google.com/app/apikey",
}


def cmd_setup(args) -> int:
    """Interactive walkthrough — register all missing vendor keys via CLI.

    For each vendor not yet in the secret store:
      1. Print the vendor's API-key web URL.
      2. Optionally open the URL in default browser (`open URL` on macOS).
      3. Prompt for the key via getpass (input hidden).
      4. Store via `secret set vendor.api_key`.
      5. Test via real API call.

    If a vendor is already registered AND tests OK, skip it. If registered
    but test fails, prompt for replacement.
    """
    from forge_runtime import ForgeRuntimeConfig  # type: ignore  # noqa: E402

    print("=" * 70)
    print("forge_keys setup — interactive vendor key registration")
    print("=" * 70)
    print()
    if not _os.path.exists(_SECRET_CLI):
        print(f"ERROR: secret CLI not found at {_SECRET_CLI}", file=sys.stderr)
        return 1

    # Decide which vendors need setup
    vendors_to_setup: list[str] = []
    for vendor in VENDORS:
        secret_key, _, _ = VENDORS[vendor]
        if _secret_get(secret_key) is None:
            vendors_to_setup.append(vendor)
            print(f"  • {vendor:<10} → NOT registered, will set up")
        else:
            # Already set. Decide whether to re-test or skip.
            cfg = ForgeRuntimeConfig.from_env()
            test_fn = {"anthropic": _test_anthropic, "openai": _test_openai,
                        "gemini": _test_gemini}[vendor]
            key_attr = {"anthropic": cfg.anthropic_api_key,
                         "openai":    cfg.openai_api_key,
                         "gemini":    cfg.gemini_api_key}[vendor]
            if not key_attr:
                vendors_to_setup.append(vendor)
                print(f"  • {vendor:<10} → registered but runtime can't read it; will replace")
                continue
            ok, msg = test_fn(cfg)
            if ok:
                print(f"  • {vendor:<10} → ✓ already working ({msg[:50]})")
            else:
                vendors_to_setup.append(vendor)
                print(f"  • {vendor:<10} → registered but test FAILED: {msg[:60]}")
                print(f"               will offer replacement")

    if not vendors_to_setup:
        print()
        print("All 3 vendor keys already registered and working. Nothing to do.")
        return 0

    print()
    print(f"Setting up {len(vendors_to_setup)} vendor(s):"
          f" {', '.join(vendors_to_setup)}")
    print()

    n_ok = 0
    n_skip = 0
    for vendor in vendors_to_setup:
        secret_key, env_var, friendly = VENDORS[vendor]
        url = VENDOR_URLS.get(vendor, "(no URL)")
        print("─" * 70)
        print(f"VENDOR: {friendly}  ({vendor})")
        print(f"  Web URL: {url}")
        print(f"  Secret key: {secret_key}")
        print()

        if args.open_url:
            # macOS: `open URL` launches default browser
            print(f"  → Opening {url} in browser...")
            try:
                subprocess.run(["open", url], check=False, timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass

        print(f"  1. Create or copy a {friendly} API key from the URL above")
        print(f"  2. Paste it below (input hidden) — or skip with Ctrl-C")
        try:
            import getpass
            key_value = getpass.getpass(prompt=f"  {vendor} key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  → skipped {vendor}")
            n_skip += 1
            continue

        if not key_value:
            print(f"  → empty input, skipped {vendor}")
            n_skip += 1
            continue

        # Validate prefix lightly
        expect = {
            "anthropic": ["sk-ant-", "sk-"],
            "openai":    ["sk-", "sk-proj-"],
            "gemini":    ["AIza"],
        }.get(vendor, [])
        if expect and not any(key_value.startswith(p) for p in expect):
            print(f"  WARN: key prefix doesn't match expected {expect}; "
                  f"proceeding anyway")

        if not _secret_set(secret_key, key_value):
            print(f"  ✗ failed to store {secret_key}")
            continue
        print(f"  ✓ stored {secret_key} ({len(key_value)} chars)")

        # Re-read fresh cfg and test
        cfg = ForgeRuntimeConfig.from_env()
        test_fn = {"anthropic": _test_anthropic, "openai": _test_openai,
                    "gemini": _test_gemini}[vendor]
        ok, msg = test_fn(cfg)
        flag = "✓" if ok else "✗"
        print(f"  {flag} test: {msg}")
        if ok:
            n_ok += 1
        else:
            print(f"      key stored but doesn't work — check vendor console for the right key")

    print()
    print("=" * 70)
    print(f"Setup complete: {n_ok} registered and tested OK, {n_skip} skipped")
    print("=" * 70)
    print()
    print("Run `python3 tool/forge_keys.py status` to see current state.")
    return 0 if n_ok > 0 else 1


def cmd_test(args) -> int:
    """Verify a vendor key works by making a real (tiny) API call.

    r68: `--model M` overrides the default cheap-tier test model. Useful for
    verifying paid-tier access (e.g. `--model gemini-2.5-pro` to confirm the
    registered Gemini key is from a paid project, not free-tier).
    `--paid` is a shortcut that tests each vendor's flagship model.
    """
    vendor = args.vendor
    valid = list(VENDORS.keys()) + ["all"]
    if vendor not in valid:
        print(f"ERROR: unknown vendor '{vendor}'. Choose: {', '.join(valid)}",
              file=sys.stderr)
        return 1

    from forge_runtime import ForgeRuntimeConfig  # type: ignore  # noqa: E402
    cfg = ForgeRuntimeConfig.from_env()

    tests = {
        "anthropic": (_test_anthropic, cfg.anthropic_api_key),
        "openai":    (_test_openai,    cfg.openai_api_key),
        "gemini":    (_test_gemini,    cfg.gemini_api_key),
    }
    # r68: paid-tier model overrides for --paid shortcut.
    paid_models = {
        "anthropic": "claude-opus-4-7",
        "openai":    "gpt-5",
        "gemini":    "gemini-2.5-pro",
    }
    targets = list(VENDORS.keys()) if vendor == "all" else [vendor]

    print("=" * 70)
    print(f"forge_keys test — making real API call(s)")
    if args.paid:
        print("  --paid: testing flagship/paid-tier models (opus / gpt-5 / gemini-pro)")
    elif args.model:
        print(f"  --model: overriding default with '{args.model}'")
    print("=" * 70)
    n_pass = 0
    for v in targets:
        fn, key = tests[v]
        if not key:
            print(f"  ✗ {v:<10} SKIP — key not in secret store; add via `forge_keys add {v}`")
            continue
        # Pick model: explicit --model wins, else --paid, else default.
        if args.model and vendor != "all":
            model = args.model
        elif args.paid:
            model = paid_models[v]
        else:
            model = None  # let the test fn pick its default
        print(f"  → {v:<10} testing{' on ' + model if model else ''}...", flush=True)
        ok, msg = fn(cfg, model=model) if model else fn(cfg)
        flag = "✓" if ok else "✗"
        print(f"  {flag} {v:<10} {msg[:120]}")
        if ok:
            n_pass += 1

    print()
    n_targets = sum(1 for v in targets if tests[v][1])  # only count those with keys
    print(f"Result: {n_pass}/{n_targets} vendor(s) verified" +
          (f" (paid-tier)" if args.paid else "") + ".")
    return 0 if n_pass == n_targets and n_targets > 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("status", help="show which keys are configured")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("add", help="add or update a vendor key")
    sp.add_argument("vendor", choices=list(VENDORS.keys()))
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("remove", help="remove a vendor key")
    sp.add_argument("vendor", choices=list(VENDORS.keys()))
    sp.set_defaults(func=cmd_remove)

    sp = sub.add_parser("test", help="verify a key works via real API call")
    sp.add_argument("vendor", choices=list(VENDORS.keys()) + ["all"])
    sp.add_argument("--model", default=None,
                    help="Override default cheap-tier test model (e.g. claude-opus-4-7 / gpt-5 / gemini-2.5-pro)")
    sp.add_argument("--paid", action="store_true",
                    help="Test flagship/paid-tier models (opus / gpt-5 / gemini-pro). "
                         "Useful for verifying paid-tier project key.")
    sp.set_defaults(func=cmd_test)

    sp = sub.add_parser("setup",
                         help="interactive walkthrough — register all missing keys")
    sp.add_argument("--no-open-url", dest="open_url", action="store_false",
                    default=True,
                    help="Don't auto-open vendor URL in browser")
    sp.set_defaults(func=cmd_setup)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
