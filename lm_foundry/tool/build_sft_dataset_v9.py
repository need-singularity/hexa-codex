#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v9.py — r8 follow-up: hammer the stuck families + the two ⚠️ domains.

r8 smoke test left two domains shaky and hexa-eval stuck at 60.7%:
- BIP39 / PSBT — gist right, exact constants drift (12 words = 128-bit entropy, not 256)
- Zig build.zig — model mixed pre-0.11 build API with the modern `b.addExecutable(.{...})` form
- hexa-eval T2 atlas / T4 enum / T5 HX-codes — pinned at 33% (only ~5 exemplars each in the SFT set)

v9 = v8 base (2,110) + ~230 targeted boost pairs:
- +60 BIP39/PSBT constants drilled (entropy bits, checksum bits, PBKDF2 iters, paths, dust limits)
- +50 Zig modern build API only (b.path, b.addExecutable(.{...}), b.installArtifact, b.step)
- +40 atlas L[N] (proves/explores × annotations, wider N range)
- +40 enum variants (more shapes, generic params, payload fields)
- +40 HX codes (8 families, diverse phrasings, @grace combos)

Total v9: ~2,340 rows.

OUTPUT
    /home/summer/runs/sft-train-v9/train.jsonl
    /home/summer/runs/sft-train-v9/MANIFEST.json
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS_DIR = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS_DIR]

import json
import random
from pathlib import Path

random.seed(42)

V8_BASE = Path("/home/summer/runs/sft-train-v8/train.jsonl")
OUT_DIR = Path("/home/summer/runs/sft-train-v9")
OUT = OUT_DIR / "train.jsonl"
MANIFEST = OUT_DIR / "MANIFEST.json"


def fmt(p: str, c: str) -> dict:
    return {"text": f"### User:\n{p}\n### Assistant:\n{c}"}


# ---------------------------------------------------------------------------
# 1. BIP39 / PSBT constants — drilled hard, exact numbers
# ---------------------------------------------------------------------------
def gen_bip39_facts() -> list[dict]:
    base = [
        ("How many bits of entropy does a 12-word BIP39 mnemonic carry, and how much is checksum?",
         "128 bits of entropy + 4 bits of checksum = 132 bits, encoded as 12 words (each word = 11 bits, 12 x 11 = 132)."),
        ("How many bits of entropy does a 24-word BIP39 mnemonic carry?",
         "256 bits of entropy + 8 bits of checksum = 264 bits, encoded as 24 words (24 x 11 = 264)."),
        ("BIP39: word count for 128 / 160 / 192 / 224 / 256 bits of entropy?",
         "128 -> 12 words, 160 -> 15 words, 192 -> 18 words, 224 -> 21 words, 256 -> 24 words. Checksum bits = entropy_bits / 32 (so 4/5/6/7/8 respectively)."),
        ("How is the BIP39 checksum computed?",
         "Take SHA-256 of the entropy bytes; the first (entropy_bits / 32) bits of that hash are appended to the entropy before splitting into 11-bit groups."),
        ("How big is the BIP39 wordlist?",
         "2048 words (2^11), so each word encodes exactly 11 bits."),
        ("BIP39: how is the seed derived from a mnemonic? Give the exact PBKDF2 parameters.",
         "seed = PBKDF2-HMAC-SHA512(password = NFKD(mnemonic), salt = NFKD('mnemonic' + passphrase), iterations = 2048, dkLen = 64 bytes). The output is a 512-bit seed."),
        ("What does the BIP39 optional passphrase do?",
         "It is concatenated onto the salt string 'mnemonic' before PBKDF2. Any change to it produces a completely different 64-byte seed — there is no checksum, so a wrong passphrase silently gives a valid-but-empty wallet ('plausible deniability')."),
        ("BIP44 path: spell out m/44'/0'/0'/0/0.",
         "m = master node; 44' = purpose (hardened, BIP44); 0' = coin type (hardened, 0 = Bitcoin mainnet); 0' = account #0 (hardened); 0 = change chain (0 = external/receive, 1 = internal/change); 0 = address index #0. Apostrophe = hardened = index + 0x80000000."),
        ("Purpose values: BIP44 vs BIP49 vs BIP84 vs BIP86?",
         "BIP44 = 44' -> legacy P2PKH ('1...', xpub). BIP49 = 49' -> nested SegWit P2SH-P2WPKH ('3...', ypub). BIP84 = 84' -> native SegWit P2WPKH ('bc1q...', zpub). BIP86 = 86' -> Taproot P2TR ('bc1p...')."),
        ("What coin_type does Bitcoin testnet use in BIP44?",
         "1' (one, hardened). Mainnet Bitcoin = 0'."),
        ("BIP32: what is the size of a chain code, and what does an extended key contain?",
         "Chain code = 32 bytes. An extended key = key (33-byte compressed pubkey or 32-byte privkey padded to 33) + 32-byte chain code = 64 bytes of working material, plus 1-byte depth, 4-byte parent fingerprint, 4-byte child number when serialized."),
        ("BIP32: how is a key's fingerprint computed?",
         "fingerprint = first 4 bytes of HASH160(compressed_pubkey), where HASH160(x) = RIPEMD-160(SHA-256(x))."),
        ("BIP32: hardened child index range?",
         "Indices 0 .. 2^31 - 1 are non-hardened; 2^31 .. 2^32 - 1 are hardened. A hardened index i' is written as i + 0x80000000."),
        ("Why can an xpub only derive non-hardened children?",
         "Hardened derivation hashes the parent PRIVATE key (HMAC-SHA512 over 0x00 || ser256(k_par) || ser32(i)); an xpub has no private key, so only non-hardened (HMAC over serP(K_par) || ser32(i)) is possible."),
        ("What HMAC and hash does BIP32 child key derivation use?",
         "HMAC-SHA512 with the chain code as the key; output is split into IL (left 32 bytes -> tweak added to parent key mod n) and IR (right 32 bytes -> child chain code)."),
        ("Bitcoin: what is the P2WPKH dust limit (roughly), and why does dust exist?",
         "~294 satoshis for P2WPKH (~546 for P2PKH) at the default 1 sat/vB relay rate — an output is 'dust' when it costs more in fees to ever spend than it is worth. Wallets drop sub-dust change into the fee instead of creating it."),
        ("How is a transaction's virtual size (vbytes) computed?",
         "weight = 4 x (non-witness bytes) + 1 x (witness bytes); vsize = ceil(weight / 4). Fee rate = fee_sats / vsize."),
        ("BIP125 RBF: what nSequence value signals opt-in replaceability?",
         "Any input with nSequence < 0xFFFFFFFE (i.e. <= 0xFFFFFFFD) signals BIP125 opt-in RBF. 0xFFFFFFFF and 0xFFFFFFFE both disable it."),
        ("PSBT (BIP174): how many roles, and name them.",
         "Six roles: Creator, Updater, Signer, Combiner, Input Finalizer, and (Transaction) Extractor."),
        ("What is the magic prefix of a binary PSBT?",
         "0x70 0x73 0x62 0x74 0xFF — ASCII 'psbt' followed by 0xFF."),
        ("Taproot: BIP340/341/342 — one line each.",
         "BIP340 = Schnorr signatures over secp256k1 (64-byte sigs, key/sig aggregation). BIP341 = Taproot output: a 32-byte x-only key that is a key-path spend or, via a Merkle tree of scripts, a script-path spend. BIP342 = Tapscript: the script semantics used under Taproot."),
        ("bech32 vs bech32m: which witness versions, which constant?",
         "bech32 (BIP173) -> witness v0 (P2WPKH/P2WSH), checksum constant 1. bech32m (BIP350) -> witness v1+ (P2TR), checksum constant 0x2bc830a3."),
        ("SIGHASH_ALL — what does the signature commit to?",
         "All inputs (outpoints + sequences) and all outputs. Any change to inputs or outputs invalidates it. SIGHASH_SINGLE commits only to the output at the same index; SIGHASH_NONE to no outputs; |ANYONECANPAY restricts the input commitment to just the signing input."),
        ("How many satoshis in a bitcoin, and how is the Bitcoin supply cap stated?",
         "1 BTC = 100,000,000 satoshis (10^8). Total supply cap ~ 21,000,000 BTC = 2,100,000,000,000,000 (2.1e15) satoshis."),
        ("Bitcoin: block subsidy halving interval?",
         "Every 210,000 blocks (~4 years). The subsidy started at 50 BTC and halves each interval; it reaches 0 after 33 halvings."),
        ("What does deriving m/0/* vs m/1/* mean for a BIP44 account?",
         "Within an account, chain 0 is the external (receive) chain — addresses you hand out; chain 1 is the internal (change) chain — addresses your own change goes to. Wallets scan both with a gap limit (default 20)."),
        ("BIP44 gap limit — what is it and what's the default?",
         "After this many consecutive unused addresses on a chain, a wallet stops scanning further. Default = 20. If you skip past the gap, funds at higher indices won't be discovered on restore."),
        ("What's the difference between a watch-only wallet and a hot wallet, in terms of keys?",
         "A hot wallet holds private keys (or the seed) and can sign autonomously. A watch-only wallet imports only xpubs / output descriptors: it derives addresses, sees balances, builds PSBTs, but cannot sign — signing is delegated to an offline / hardware signer."),
        ("Output descriptor wpkh([fp/84'/0'/0']xpub.../0/*) — decode each part.",
         "wpkh = produce P2WPKH scripts. [fp/84'/0'/0'] = key origin: 4-byte master fingerprint 'fp' and derivation path to the account xpub. xpub... = the account extended key. /0/* = chain 0 (external), wildcard over address index."),
        ("What is a transaction's txid vs wtxid?",
         "txid = double-SHA256 of the legacy (no-witness) serialization, displayed byte-reversed. wtxid = double-SHA256 of the full serialization including the witness; equals txid for non-SegWit txs. The coinbase carries a witness commitment over the block's wtxids."),
    ]
    out = [fmt(p, c) for p, c in base]
    # add a batch of "exactly N words = M bits" drills with varied phrasing
    table = {12: (128, 4), 15: (160, 5), 18: (192, 6), 21: (224, 7), 24: (256, 8)}
    phrasings = [
        "A BIP39 phrase with {w} words encodes how many bits of entropy?",
        "How much entropy is in a {w}-word seed phrase?",
        "{w} BIP39 words -> ? bits of entropy and ? bits of checksum.",
    ]
    for w, (ent, cs) in table.items():
        for ph in phrasings:
            out.append(fmt(ph.format(w=w),
                           f"{ent} bits of entropy plus {cs} bits of checksum ({ent}+{cs} = {w*11} bits = {w} x 11-bit words)."))
    return out


# ---------------------------------------------------------------------------
# 2. Zig modern build API only
# ---------------------------------------------------------------------------
def gen_zig_build() -> list[dict]:
    pairs = [
        ("Write a modern (Zig 0.13) build.zig that builds an executable 'app' from src/main.zig with a run step.",
         "const std = @import(\"std\");\npub fn build(b: *std.Build) void {\n    const target = b.standardTargetOptions(.{});\n    const optimize = b.standardOptimizeOption(.{});\n    const exe = b.addExecutable(.{\n        .name = \"app\",\n        .root_source_file = b.path(\"src/main.zig\"),\n        .target = target,\n        .optimize = optimize,\n    });\n    b.installArtifact(exe);\n    const run_cmd = b.addRunArtifact(exe);\n    run_cmd.step.dependOn(b.getInstallStep());\n    if (b.args) |args| run_cmd.addArgs(args);\n    const run_step = b.step(\"run\", \"Run the app\");\n    run_step.dependOn(&run_cmd.step);\n}"),
        ("Modern Zig build.zig: add a static library target.",
         "const lib = b.addStaticLibrary(.{\n    .name = \"mylib\",\n    .root_source_file = b.path(\"src/root.zig\"),\n    .target = target,\n    .optimize = optimize,\n});\nb.installArtifact(lib);"),
        ("Modern Zig build.zig: add a unit-test step for src/main.zig.",
         "const unit_tests = b.addTest(.{\n    .root_source_file = b.path(\"src/main.zig\"),\n    .target = target,\n    .optimize = optimize,\n});\nconst run_unit_tests = b.addRunArtifact(unit_tests);\nconst test_step = b.step(\"test\", \"Run unit tests\");\ntest_step.dependOn(&run_unit_tests.step);"),
        ("Modern Zig: how do you reference a source file path in build.zig?",
         "Use `b.path(\"src/main.zig\")` — it returns a LazyPath rooted at the build root. The old `.{ .path = \"src/main.zig\" }` literal form is removed; never use a bare string."),
        ("Modern Zig build.zig: add a module dependency from build.zig.zon.",
         "const dep = b.dependency(\"known_folders\", .{ .target = target, .optimize = optimize });\nexe.root_module.addImport(\"known_folders\", dep.module(\"known-folders\"));"),
        ("Modern Zig build.zig: link libC and a system library.",
         "exe.linkLibC();\nexe.linkSystemLibrary(\"sqlite3\");"),
        ("Modern Zig build.zig: expose a public module so other packages can import it.",
         "_ = b.addModule(\"mylib\", .{\n    .root_source_file = b.path(\"src/root.zig\"),\n    .target = target,\n    .optimize = optimize,\n});"),
        ("Modern Zig build.zig: add a build option that becomes compile-time config.",
         "const verbose = b.option(bool, \"verbose\", \"Enable verbose logs\") orelse false;\nconst options = b.addOptions();\noptions.addOption(bool, \"verbose\", verbose);\nexe.root_module.addOptions(\"build_config\", options);"),
        ("What does b.installArtifact(exe) do in a modern build.zig?",
         "It registers the artifact to be copied into the install prefix (zig-out/bin for executables) when `zig build install` (the default step) runs. Returns nothing; chain it after addExecutable."),
        ("Modern Zig build.zig: make `zig build run` pass through CLI args.",
         "const run_cmd = b.addRunArtifact(exe);\nif (b.args) |args| run_cmd.addArgs(args);\nconst run_step = b.step(\"run\", \"Run\");\nrun_step.dependOn(&run_cmd.step);\n// then: zig build run -- arg1 arg2"),
        ("Modern Zig build.zig.zon: minimal manifest with one URL dependency.",
         ".{\n    .name = \"app\",\n    .version = \"0.1.0\",\n    .minimum_zig_version = \"0.13.0\",\n    .dependencies = .{\n        .known_folders = .{\n            .url = \"https://github.com/ziglibs/known-folders/archive/<rev>.tar.gz\",\n            .hash = \"1220<64-hex>\",\n        },\n    },\n    .paths = .{ \"build.zig\", \"build.zig.zon\", \"src\" },\n}"),
        ("Modern Zig: how do you add a C source file to an executable in build.zig?",
         "exe.addCSourceFile(.{ .file = b.path(\"src/glue.c\"), .flags = &.{\"-std=c11\"} });\nexe.addIncludePath(b.path(\"include\"));\nexe.linkLibC();"),
        ("Modern Zig build.zig: build for a specific cross target (wasm32-freestanding).",
         "const wasm_target = b.resolveTargetQuery(.{ .cpu_arch = .wasm32, .os_tag = .freestanding });\nconst exe = b.addExecutable(.{ .name = \"app\", .root_source_file = b.path(\"src/main.zig\"), .target = wasm_target, .optimize = .ReleaseSmall });"),
        ("Modern Zig build.zig: set optimize to ReleaseFast unconditionally.",
         "const exe = b.addExecutable(.{\n    .name = \"app\",\n    .root_source_file = b.path(\"src/main.zig\"),\n    .target = b.standardTargetOptions(.{}),\n    .optimize = .ReleaseFast,\n});"),
        ("Modern Zig build.zig: add an additional named step that runs the tests AND a fmt check.",
         "const fmt_step = b.addFmt(.{ .paths = &.{ \"src\", \"build.zig\" }, .check = true });\nconst check = b.step(\"check\", \"fmt + tests\");\ncheck.dependOn(&fmt_step.step);\ncheck.dependOn(&run_unit_tests.step);"),
        ("Modern Zig: signature of the build function?",
         "pub fn build(b: *std.Build) void { ... } — takes a *std.Build, returns void. (The old `*std.build.Builder` name is gone.)"),
        ("Modern Zig build.zig: install an extra file (a config) alongside the binary.",
         "b.installFile(\"config/default.toml\", \"share/app/default.toml\");"),
        ("Modern Zig: how do you get the target and optimize the user passed on the CLI?",
         "const target = b.standardTargetOptions(.{});       // honors -Dtarget=...\nconst optimize = b.standardOptimizeOption(.{});   // honors -Doptimize=Debug|ReleaseFast|ReleaseSafe|ReleaseSmall"),
        ("Modern Zig build.zig: add a dependency's artifact (a C library it builds) and link it.",
         "const dep = b.dependency(\"zlib\", .{ .target = target, .optimize = optimize });\nexe.linkLibrary(dep.artifact(\"z\"));"),
        ("Modern Zig build.zig: chain two executables where building one depends on the other.",
         "const tool = b.addExecutable(.{ .name = \"gen\", .root_source_file = b.path(\"tool/gen.zig\"), .target = target, .optimize = optimize });\nconst run_gen = b.addRunArtifact(tool);\nconst out_file = run_gen.addOutputFileArg(\"generated.zig\");\nconst app = b.addExecutable(.{ .name = \"app\", .root_source_file = b.path(\"src/main.zig\"), .target = target, .optimize = optimize });\napp.root_module.addAnonymousImport(\"generated\", .{ .root_source_file = out_file });\nb.installArtifact(app);"),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
# 3. hexa atlas L[N]
# ---------------------------------------------------------------------------
def gen_atlas(n=40) -> list[dict]:
    out = []
    for _ in range(n // 2):
        nL = random.randint(1, 600)
        verb = random.choice(["proves", "PROVES", "establishes", "demonstrates", "shows", "confirms"])
        prompt = f"Annotate a hexa function `prove_{nL}` that {verb} law `L[{nL}]`."
        out.append(fmt(prompt, f"@implements(L[{nL}])"))
    for _ in range(n // 2):
        nL = random.randint(1, 600)
        verb = random.choice(["EXPLORES", "discovers", "searches for", "hunts", "probes", "looks for"])
        prompt = f"Annotate `explore_{nL}` that {verb} new instances of law `L[{nL}]`."
        out.append(fmt(prompt, '@discover(kind="L")'))
    return out


# ---------------------------------------------------------------------------
# 4. hexa enums
# ---------------------------------------------------------------------------
def gen_enum() -> list[dict]:
    defs = [
        ("Color with Red, Green, Blue", "enum Color {\n    Red,\n    Green,\n    Blue,\n}"),
        ("Direction with North, South, East, West", "enum Direction {\n    North,\n    South,\n    East,\n    West,\n}"),
        ("Status with Idle, Running, Done, Error", "enum Status {\n    Idle,\n    Running,\n    Done,\n    Error,\n}"),
        ("Priority with Low, Normal, High, Critical", "enum Priority {\n    Low,\n    Normal,\n    High,\n    Critical,\n}"),
        ("LogLevel with Trace, Debug, Info, Warn, Error", "enum LogLevel {\n    Trace,\n    Debug,\n    Info,\n    Warn,\n    Error,\n}"),
        ("a generic Maybe<T> with None and Some(T)", "enum Maybe<T> {\n    None,\n    Some(T),\n}"),
        ("a generic Option<T> with None and Some(T)", "enum Option<T> {\n    None,\n    Some(T),\n}"),
        ("a generic Result<T> with Ok(T) and Err(String)", "enum Result<T> {\n    Ok(T),\n    Err(String),\n}"),
        ("a generic Either<E, T> with Err(E) and Ok(T)", "enum Either<E, T> {\n    Err(E),\n    Ok(T),\n}"),
        ("a generic Pair<A, B> with Two(A, B)", "enum Pair<A, B> {\n    Two(A, B),\n}"),
        ("Shape with Circle(f64), Square(f64), Rect(f64, f64)", "enum Shape {\n    Circle(f64),\n    Square(f64),\n    Rect(f64, f64),\n}"),
        ("Token with Ident(String), Int(i64), Punct(char), Eof", "enum Token {\n    Ident(String),\n    Int(i64),\n    Punct(char),\n    Eof,\n}"),
        ("HttpMethod with Get, Post, Put, Delete, Patch", "enum HttpMethod {\n    Get,\n    Post,\n    Put,\n    Delete,\n    Patch,\n}"),
        ("Json with Null, Bool(bool), Num(f64), Str(String), Arr(Vec<Json>), Obj(Map<String, Json>)",
         "enum Json {\n    Null,\n    Bool(bool),\n    Num(f64),\n    Str(String),\n    Arr(Vec<Json>),\n    Obj(Map<String, Json>),\n}"),
        ("Tree<T> with Leaf(T) and Node(Box<Tree<T>>, Box<Tree<T>>)",
         "enum Tree<T> {\n    Leaf(T),\n    Node(Box<Tree<T>>, Box<Tree<T>>),\n}"),
        ("Command with Move { x: i32, y: i32 }, Quit, Say(String)",
         "enum Command {\n    Move { x: i32, y: i32 },\n    Quit,\n    Say(String),\n}"),
        ("State with Connecting, Connected { since: u64 }, Closed",
         "enum State {\n    Connecting,\n    Connected { since: u64 },\n    Closed,\n}"),
        ("Op with Add, Sub, Mul, Div", "enum Op {\n    Add,\n    Sub,\n    Mul,\n    Div,\n}"),
        ("Visibility with Public, Private, Internal", "enum Visibility {\n    Public,\n    Private,\n    Internal,\n}"),
        ("a generic Validated<T> with Valid(T) and Invalid(Vec<String>)",
         "enum Validated<T> {\n    Valid(T),\n    Invalid(Vec<String>),\n}"),
    ]
    templates = [
        "Define a hexa enum {d}.",
        "Write the hexa declaration for an enum {d}.",
    ]
    out = []
    for d, body in defs:
        for t in templates:
            out.append(fmt(t.format(d=d), body))
    return out


# ---------------------------------------------------------------------------
# 5. hexa HX codes
# ---------------------------------------------------------------------------
def gen_hx() -> list[dict]:
    families = {
        "HX0": "lexical / parse errors (HX0001..HX0999)",
        "HX1": "name resolution / scoping errors (HX1001..HX1999)",
        "HX2": "type errors (HX2001..HX2999)",
        "HX3": "ownership / borrow errors (HX3001..HX3999)",
        "HX4": "trait / generic resolution errors (HX4001..HX4999)",
        "HX5": "linker / target errors (HX5001..HX5999)",
        "HX6": "lint diagnostics S0..S8 (HX6001..HX6999)",
        "HX7": "codegen errors (HX7001..HX7999)",
        "HX8": "FFI / ABI errors (HX8001..HX8999)",
        "HX9": "deprecation / @grace notices (HX9001..HX9999)",
    }
    out = []
    for code, desc in families.items():
        out.append(fmt(f"What does the hexa diagnostic family {code}xxxx cover?",
                       f"The {code}xxxx family is {desc}."))
        out.append(fmt(f"A hexa diagnostic numbered {code}001 — which category is it?",
                       f"{code}001 is in the {desc.split(' (')[0]} family."))
        out.append(fmt(f"Classify a hexa error with code {code}042.",
                       f"{code}042 belongs to the {desc.split(' (')[0]} family."))
        out.append(fmt(f"List the hexa diagnostic family for: {desc.split(' (')[0]}.",
                       f"That is the {code}xxxx family ({desc})."))
    # @grace combos
    for _ in range(8):
        code = f"HX9{random.randint(1,999):03d}"
        d = random.choice([("2026-06-30", "replaced by the new builder"),
                           ("2026-09-01", "deprecated in RFC-021"),
                           ("2027-01-01", "removed; use the v2 API"),
                           ("2026-12-31", "superseded by atlas L-anchoring")])
        out.append(fmt(f"Annotate a hexa item that triggers {code}; it should be removed by {d[0]} because it was {d[1]}.",
                       f'@grace({code}, until={d[0]}, reason="{d[1]}")'))
    return out


# ---------------------------------------------------------------------------
def main() -> int:
    if not V8_BASE.exists():
        print(f"ERROR: v8 base not found at {V8_BASE}", file=_sys.stderr)
        return 1
    base = [json.loads(l) for l in V8_BASE.read_text().splitlines() if l.strip()]
    print(f"v8 base: {len(base)}")
    blocks = {
        "bip39_facts": gen_bip39_facts(),
        "zig_build_modern": gen_zig_build(),
        "atlas_LN": gen_atlas(40),
        "hexa_enums": gen_enum(),
        "hexa_hx_codes": gen_hx(),
    }
    added = []
    for name, rows in blocks.items():
        print(f"  + {name:18s} {len(rows):4d}")
        added.extend(rows)
    print(f"boost additions: {len(added)}")
    rows = base + added
    random.shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    MANIFEST.write_text(json.dumps({
        "version": "v0.2.0-r9",
        "base": str(V8_BASE),
        "base_rows": len(base),
        "boost_blocks": {k: len(v) for k, v in blocks.items()},
        "boost_added": len(added),
        "total_rows": len(rows),
        "seed": 42,
        "purpose": "r8 follow-up: BIP39 constants + modern Zig build API + atlas/enum/HX boost",
    }, indent=2))
    print(f"wrote: {OUT}  ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
