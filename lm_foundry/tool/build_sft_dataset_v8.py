#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""build_sft_dataset_v8.py — broaden the code-LLM's domain surface (learning-surface audit 2026-05-12).

`papers/learning-surface-2026-05-12.md` surveyed all ~/core/* projects and
flagged seven domains the model currently has no SFT coverage for but that
recur in the owner's own work:

  1. Dart / Flutter        (cake-wallet — wraith-wallet's Stage-1 backend)
  2. PyTorch training loop (anima — the owner's own ML stack: pytorch 2.5 + cu12.4)
  3. BIP39 / PSBT / HD-wallet primitives (wraith-wallet + orpheus crypto stack)
  4. Zig deep              (void — build.zig / build.zig.zon / comptime)
  5. Discord bot + Anthropic SDK (pixie — slash commands + worker queue)
  6. Playwright E2E        (browser-harness — locator / storage-state)
  7. TOML schema design    (hexa-meta — 601 .toml, hexa-toml-spec v1.0)

ORM was explicitly excluded by the owner — the stack is raw SQL (DuckDB /
BigQuery) + hexa.toml config, no SQLAlchemy/Prisma/Diesel anywhere.

v8 = v7 base (1,985 rows) + ~360 hand-crafted domain Q/A pairs.

The Q/A all use the unified `### User:\n<prompt>\n### Assistant:\n<completion>`
template (the format-balance lesson from r1→r3). Pairs are short and
recipe-shaped — not file continuations (the v5 over-continuation regression).

OUTPUT
    /home/summer/runs/sft-train-v8/train.jsonl
    /home/summer/runs/sft-train-v8/MANIFEST.json
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

V7_BASE = Path("/home/summer/runs/sft-train-v8/.._v7_base") if False else Path("/home/summer/runs/sft-train-v7/train.jsonl")
OUT_DIR = Path("/home/summer/runs/sft-train-v8")
OUT = OUT_DIR / "train.jsonl"
MANIFEST = OUT_DIR / "MANIFEST.json"


def fmt(p: str, c: str) -> dict:
    return {"text": f"### User:\n{p}\n### Assistant:\n{c}"}


# ---------------------------------------------------------------------------
# 1. Dart / Flutter
# ---------------------------------------------------------------------------
def gen_dart() -> list[dict]:
    pairs = [
        ("Write a Flutter StatelessWidget `Greeting` that shows a centered Text 'Hello'.",
         "class Greeting extends StatelessWidget {\n  const Greeting({super.key});\n  @override\n  Widget build(BuildContext context) {\n    return const Center(child: Text('Hello'));\n  }\n}"),
        ("Write a Flutter StatefulWidget `Counter` with an int that increments on a FloatingActionButton press.",
         "class Counter extends StatefulWidget {\n  const Counter({super.key});\n  @override\n  State<Counter> createState() => _CounterState();\n}\n\nclass _CounterState extends State<Counter> {\n  int _count = 0;\n  @override\n  Widget build(BuildContext context) {\n    return Scaffold(\n      body: Center(child: Text('$_count')),\n      floatingActionButton: FloatingActionButton(\n        onPressed: () => setState(() => _count++),\n        child: const Icon(Icons.add),\n      ),\n    );\n  }\n}"),
        ("In Dart, define an immutable data class `User` with name and age using a const constructor.",
         "class User {\n  final String name;\n  final int age;\n  const User({required this.name, required this.age});\n}"),
        ("How do I make an async HTTP GET in Dart with the http package and decode JSON?",
         "import 'dart:convert';\nimport 'package:http/http.dart' as http;\n\nFuture<Map<String, dynamic>> fetchJson(Uri url) async {\n  final res = await http.get(url);\n  if (res.statusCode != 200) throw Exception('HTTP \${res.statusCode}');\n  return jsonDecode(res.body) as Map<String, dynamic>;\n}"),
        ("Show a Flutter FutureBuilder that renders a CircularProgressIndicator while loading and Text on done.",
         "FutureBuilder<String>(\n  future: loadName(),\n  builder: (context, snap) {\n    if (snap.connectionState != ConnectionState.done) {\n      return const CircularProgressIndicator();\n    }\n    if (snap.hasError) return Text('Error: \${snap.error}');\n    return Text(snap.data ?? '');\n  },\n)"),
        ("Dart: write a sealed class hierarchy `Shape` with `Circle(double r)` and `Square(double s)` and an area getter.",
         "sealed class Shape {\n  double get area;\n}\n\nclass Circle extends Shape {\n  final double r;\n  Circle(this.r);\n  @override\n  double get area => 3.141592653589793 * r * r;\n}\n\nclass Square extends Shape {\n  final double s;\n  Square(this.s);\n  @override\n  double get area => s * s;\n}"),
        ("How do I declare a Flutter route and navigate to it with Navigator?",
         "// register in MaterialApp:\n// routes: {'/details': (_) => const DetailsPage()},\nNavigator.pushNamed(context, '/details');\n// or, anonymous:\nNavigator.push(context, MaterialPageRoute(builder: (_) => const DetailsPage()));"),
        ("Dart: parse a List<dynamic> of JSON maps into a List<User>.",
         "List<User> parseUsers(List<dynamic> raw) =>\n    raw.map((e) => User(name: e['name'] as String, age: e['age'] as int)).toList();"),
        ("Show a Flutter ListView.builder for a list of strings.",
         "ListView.builder(\n  itemCount: items.length,\n  itemBuilder: (context, i) => ListTile(title: Text(items[i])),\n)"),
        ("Dart: write an extension method `capitalize` on String.",
         "extension Capitalize on String {\n  String capitalize() =>\n      isEmpty ? this : '\${this[0].toUpperCase()}\${substring(1)}';\n}"),
        ("Flutter: use a StreamBuilder to render the latest int from a Stream<int>.",
         "StreamBuilder<int>(\n  stream: ticks,\n  initialData: 0,\n  builder: (context, snap) => Text('${snap.data}'),\n)"),
        ("Dart: define an enum `Status` with a method that returns a label.",
         "enum Status {\n  idle, running, done;\n  String get label => switch (this) {\n    Status.idle => 'Idle',\n    Status.running => 'Running',\n    Status.done => 'Done',\n  };\n}"),
        ("How do I read a value from SharedPreferences in Flutter?",
         "final prefs = await SharedPreferences.getInstance();\nfinal token = prefs.getString('token') ?? '';"),
        ("Dart: write a function returning Future<Result> that retries 3 times with a 200ms backoff.",
         "Future<T> retry<T>(Future<T> Function() op, {int tries = 3}) async {\n  for (var i = 0; ; i++) {\n    try {\n      return await op();\n    } catch (_) {\n      if (i >= tries - 1) rethrow;\n      await Future.delayed(const Duration(milliseconds: 200));\n    }\n  }\n}"),
        ("Flutter: wrap a widget in a Padding of 16 on all sides.",
         "Padding(\n  padding: const EdgeInsets.all(16),\n  child: child,\n)"),
        ("Dart: use a Completer to bridge a callback API to a Future.",
         "Future<String> readFirstLine(Stream<String> lines) {\n  final c = Completer<String>();\n  late StreamSubscription<String> sub;\n  sub = lines.listen((l) {\n    if (!c.isCompleted) { c.complete(l); sub.cancel(); }\n  }, onError: c.completeError);\n  return c.future;\n}"),
        ("Flutter: define a ChangeNotifier `CartModel` exposing items and a notify on add.",
         "class CartModel extends ChangeNotifier {\n  final List<String> _items = [];\n  List<String> get items => List.unmodifiable(_items);\n  void add(String x) {\n    _items.add(x);\n    notifyListeners();\n  }\n}"),
        ("Dart: pattern-match a record (int, String) and destructure it.",
         "final (code, msg) = panic();\nprint('$code: $msg');\n// where: (int, String) panic() => (500, 'oops');"),
        ("Flutter: show a SnackBar with text 'Saved'.",
         "ScaffoldMessenger.of(context).showSnackBar(\n  const SnackBar(content: Text('Saved')),\n);"),
        ("Dart: write a const list of records used as a lookup table.",
         "const table = <(String, int)>[\n  ('low', 1),\n  ('mid', 5),\n  ('high', 9),\n];"),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
# 2. PyTorch training loop
# ---------------------------------------------------------------------------
def gen_pytorch() -> list[dict]:
    pairs = [
        ("Write a minimal PyTorch training loop for one epoch over a DataLoader with CrossEntropyLoss and Adam.",
         "import torch\nfor xb, yb in loader:\n    xb, yb = xb.to(device), yb.to(device)\n    optimizer.zero_grad()\n    logits = model(xb)\n    loss = torch.nn.functional.cross_entropy(logits, yb)\n    loss.backward()\n    optimizer.step()"),
        ("How do I move a PyTorch model and use bfloat16 autocast on CUDA?",
         "model = model.to('cuda')\nwith torch.autocast('cuda', dtype=torch.bfloat16):\n    out = model(x)\n    loss = criterion(out, y)\nloss.backward()"),
        ("Show gradient accumulation over 4 steps in PyTorch.",
         "ACCUM = 4\nfor i, (xb, yb) in enumerate(loader):\n    loss = criterion(model(xb), yb) / ACCUM\n    loss.backward()\n    if (i + 1) % ACCUM == 0:\n        optimizer.step()\n        optimizer.zero_grad()"),
        ("Define a tiny nn.Module: an MLP with one hidden layer of width 128 and ReLU.",
         "import torch.nn as nn\nclass MLP(nn.Module):\n    def __init__(self, d_in, d_out):\n        super().__init__()\n        self.net = nn.Sequential(nn.Linear(d_in, 128), nn.ReLU(), nn.Linear(128, d_out))\n    def forward(self, x):\n        return self.net(x)"),
        ("How do I save and load a PyTorch checkpoint with model + optimizer state?",
         "torch.save({'model': model.state_dict(), 'opt': optimizer.state_dict()}, 'ckpt.pt')\n# later:\nck = torch.load('ckpt.pt', map_location=device)\nmodel.load_state_dict(ck['model'])\noptimizer.load_state_dict(ck['opt'])"),
        ("Set up a cosine LR schedule with warmup in PyTorch using get_cosine_schedule_with_warmup.",
         "from transformers import get_cosine_schedule_with_warmup\nsched = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=100, num_training_steps=total_steps)\n# call sched.step() after optimizer.step()"),
        ("How do I freeze all but the last layer of a PyTorch model?",
         "for p in model.parameters():\n    p.requires_grad = False\nfor p in model.classifier.parameters():\n    p.requires_grad = True"),
        ("Write a no-grad evaluation loop computing accuracy.",
         "model.eval()\ncorrect = total = 0\nwith torch.no_grad():\n    for xb, yb in val_loader:\n        pred = model(xb.to(device)).argmax(-1)\n        correct += (pred.cpu() == yb).sum().item()\n        total += yb.numel()\nacc = correct / total"),
        ("How do I clip gradients to a max-norm of 1.0 in PyTorch?",
         "torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)"),
        ("Create a DataLoader from a TensorDataset with batch size 32 and shuffle.",
         "from torch.utils.data import TensorDataset, DataLoader\nds = TensorDataset(X, y)\nloader = DataLoader(ds, batch_size=32, shuffle=True, drop_last=True)"),
        ("Show how to load a HF causal LM with device_map='auto' and bf16.",
         "from transformers import AutoModelForCausalLM, AutoTokenizer\nimport torch\ntok = AutoTokenizer.from_pretrained(name)\nmodel = AutoModelForCausalLM.from_pretrained(name, dtype=torch.bfloat16, device_map='auto')"),
        ("How do I attach a LoRA adapter to a HF model with peft?",
         "from peft import LoraConfig, get_peft_model\ncfg = LoraConfig(r=16, lora_alpha=32, target_modules=['q_proj','k_proj','v_proj','o_proj'], task_type='CAUSAL_LM')\nmodel = get_peft_model(model, cfg)\nmodel.print_trainable_parameters()"),
        ("Greedy-decode a HF model for 64 new tokens.",
         "ids = tok(prompt, return_tensors='pt').to(model.device)\nout = model.generate(**ids, max_new_tokens=64, do_sample=False)\ntext = tok.decode(out[0][ids.input_ids.shape[1]:], skip_special_tokens=True)"),
        ("Merge a LoRA adapter into the base weights and save.",
         "from peft import PeftModel\nmerged = PeftModel.from_pretrained(base, adapter_dir).merge_and_unload()\nmerged.save_pretrained('merged-fp16')"),
        ("Write a Dockerfile base line for a CUDA 12.4 PyTorch 2.5 training image.",
         "FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime\nWORKDIR /workspace\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt"),
        ("How do I report peak CUDA memory after a training step?",
         "peak_gb = torch.cuda.max_memory_allocated() / 1e9\nprint(f'peak {peak_gb:.2f} GB')\ntorch.cuda.reset_peak_memory_stats()"),
        ("Enable gradient checkpointing on a HF model to save VRAM.",
         "model.gradient_checkpointing_enable()\nmodel.config.use_cache = False"),
        ("Set a manual seed across torch / numpy / random for reproducibility.",
         "import torch, numpy as np, random\nSEED = 42\ntorch.manual_seed(SEED); np.random.seed(SEED); random.seed(SEED)\ntorch.cuda.manual_seed_all(SEED)"),
        ("Compute per-token loss with ignore_index=-100 for a causal LM.",
         "loss = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1), ignore_index=-100)"),
        ("Use SFTTrainer from trl to fine-tune on a jsonl with a 'text' column.",
         "from trl import SFTTrainer, SFTConfig\ncfg = SFTConfig(output_dir='out', per_device_train_batch_size=1, gradient_accumulation_steps=4, num_train_epochs=2, learning_rate=1e-4, bf16=True, max_length=1024)\ntrainer = SFTTrainer(model=model, args=cfg, train_dataset=ds)\ntrainer.train()"),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
# 3. BIP39 / PSBT / HD-wallet primitives
# ---------------------------------------------------------------------------
def gen_crypto() -> list[dict]:
    pairs = [
        ("Explain what a BIP39 mnemonic is and how many bits of entropy a 12-word phrase carries.",
         "A BIP39 mnemonic encodes wallet entropy as words from a fixed 2048-word list. 12 words = 132 bits transmitted, of which 128 bits are entropy and 4 bits are a checksum (the first 4 bits of SHA-256 of the entropy). 24 words = 256 bits entropy + 8 bits checksum."),
        ("How is a BIP39 seed derived from a mnemonic?",
         "seed = PBKDF2-HMAC-SHA512(password=mnemonic_NFKD, salt='mnemonic' + passphrase_NFKD, iterations=2048, dkLen=64). The optional passphrase ('25th word') changes the seed entirely."),
        ("What is a BIP32 extended key, and what's the difference between xprv and xpub?",
         "A BIP32 extended key bundles a key + 32-byte chain code, enabling deterministic child derivation. xprv (extended private) can derive hardened and non-hardened children; xpub (extended public) can derive only non-hardened children — it never exposes private material."),
        ("Explain the BIP44 derivation path m/44'/0'/0'/0/0 component by component.",
         "m = master. 44' = BIP44 purpose (hardened). 0' = coin type (0 = Bitcoin mainnet, hardened). 0' = account index (hardened). 0 = change (0 = external/receive, 1 = internal/change). 0 = address index. Apostrophe = hardened (index + 0x80000000)."),
        ("What does BIP84 change relative to BIP44?",
         "BIP84 uses purpose 84' and produces native SegWit (P2WPKH, bech32 'bc1q...') addresses, with xpub serialized as 'zpub'. BIP44 = legacy P2PKH ('1...'), BIP49 = wrapped SegWit ('3...', 'ypub')."),
        ("What is a PSBT (BIP174) and why is it useful?",
         "A Partially Signed Bitcoin Transaction is a binary format for passing an unsigned/partial transaction between parties — e.g. a watch-only wallet builds it, an offline/hardware signer signs it, a combiner merges signatures, and a finalizer produces the broadcastable tx. It carries inputs' UTXO data, derivation paths, and partial sigs."),
        ("List the PSBT roles in BIP174.",
         "Creator (makes the empty PSBT), Updater (adds UTXO + script + bip32 derivation info), Signer (adds partial signatures), Combiner (merges PSBTs for the same tx), Input Finalizer (assembles scriptSig/witness), Extractor (produces the network-serializable transaction)."),
        ("How does a Bitcoin transaction compute its txid versus its wtxid?",
         "txid = double-SHA256 of the legacy (non-witness) serialization, byte-reversed for display. wtxid = double-SHA256 of the full serialization including the witness; for non-segwit txs wtxid == txid. The block's witness commitment in the coinbase uses wtxids."),
        ("Explain UTXO selection: what is the 'dust limit' and 'change output'?",
         "A wallet picks UTXOs whose total ≥ amount + fee. The leftover (inputs − amount − fee) becomes a change output back to the wallet. If change < dust limit (~546 sat for P2PKH, ~294 for P2WPKH — outputs cheaper to create than to ever spend at the relay fee rate), it's dropped into the fee instead."),
        ("What is a SegWit witness, and where does the signature live for a P2WPKH input?",
         "For native SegWit the scriptSig is empty; the signature and pubkey live in the transaction's witness field (a per-input stack of byte vectors). P2WPKH witness = [signature, pubkey]. This moves sig data outside the txid preimage (fixing malleability) and gives it a 4x weight discount."),
        ("Describe the structure of a Bitcoin address checksum for bech32.",
         "bech32 (BIP173) = human-readable part ('bc'), separator '1', then data: a 1-char witness version + the witness program in 5-bit groups + a 6-char BCH checksum over (hrp || data). bech32m (BIP350) uses constant 0x2bc830a3 instead of 1, required for witness v1+ (Taproot)."),
        ("What does a hardened child derivation prevent that a non-hardened one allows?",
         "Non-hardened: given the parent xpub + one child xprv, an attacker can recover the parent xprv (and thus all siblings). Hardened derivation requires the parent private key as input, so an exposed child + parent xpub leaks nothing. That's why account-level and above are hardened in BIP44."),
        ("How do you fingerprint a master key in BIP32?",
         "fingerprint = first 4 bytes of HASH160(serP(master_pubkey)) where HASH160 = RIPEMD160(SHA256(x)). PSBT and descriptor outputs carry this 4-byte fingerprint + the derivation path so a signer knows whether an input belongs to it."),
        ("What is a Bitcoin output descriptor, e.g. wpkh([d34db33f/84'/0'/0']xpub.../0/*)?",
         "A descriptor is a compact, checksummed string describing a set of scripts: wpkh = P2WPKH script function; [d34db33f/84'/0'/0'] = key origin (master fingerprint + path); xpub.../0/* = the extended key with a wildcard for address index. Wallets use descriptors to import and rescan deterministically."),
        ("Explain RBF (BIP125) in one paragraph.",
         "Replace-By-Fee lets an unconfirmed transaction be superseded by a higher-fee version. Opt-in RBF signals it by setting at least one input's nSequence < 0xfffffffe. The replacement must pay a higher absolute fee and a higher feerate, include all original inputs, and not add new unconfirmed inputs (BIP125 rules 1–5)."),
        ("What's the difference between a hot wallet and a watch-only wallet?",
         "A hot wallet holds private keys (or seed) online and can sign autonomously — convenient, higher risk. A watch-only wallet imports only xpubs/descriptors: it can derive addresses, see balances, and build PSBTs, but cannot sign — signing is delegated to an offline/hardware signer. Wraith-style architectures keep the backend watch-only and push PSBTs to the signer."),
        ("How is a transaction fee rate expressed and estimated?",
         "Fee rate = fee (sats) / virtual size (vbytes), where vsize = ceil(weight/4) and weight = 4*(non-witness bytes) + 1*(witness bytes). Wallets estimate the sat/vB target from recent block inclusion (e.g. mempool feerate buckets) and let the user pick fast/normal/slow."),
        ("What does signing a PSBT input with SIGHASH_ALL commit to?",
         "SIGHASH_ALL (the default) signs all inputs (their outpoints + sequences) and all outputs, so the signature is invalid if any input or output changes. Other flags: SIGHASH_NONE (no outputs committed), SIGHASH_SINGLE (only the output at the same index), and the |ANYONECANPAY modifier (only this input committed)."),
        ("Walk through producing a spendable tx from a watch-only wallet + offline signer.",
         "1. Watch-only wallet builds a PSBT: selects UTXOs from its descriptor, adds an output to the recipient and a change output, attaches each input's witness UTXO + bip32 derivation. 2. Export PSBT (base64/binary). 3. Offline signer (which has the seed) imports it, verifies amounts/addresses, signs each input → partial sigs. 4. Watch-only wallet finalizes (assembles witnesses) and extracts the raw tx. 5. Broadcast."),
        ("What is BIP340 Schnorr / Taproot in one sentence each?",
         "BIP340 = Schnorr signatures over secp256k1 (64-byte, linear, enabling key/signature aggregation). BIP341 = Taproot output (a single 32-byte x-only pubkey that is either a key-path spend or, via a Merkle tree of scripts, a script-path spend). BIP342 = Tapscript, the script semantics under Taproot."),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
# 4. Zig deep (build.zig / build.zig.zon / comptime)
# ---------------------------------------------------------------------------
def gen_zig() -> list[dict]:
    pairs = [
        ("Write a minimal build.zig that builds an executable named 'app' from src/main.zig.",
         "const std = @import(\"std\");\npub fn build(b: *std.Build) void {\n    const target = b.standardTargetOptions(.{});\n    const optimize = b.standardOptimizeOption(.{});\n    const exe = b.addExecutable(.{\n        .name = \"app\",\n        .root_source_file = b.path(\"src/main.zig\"),\n        .target = target,\n        .optimize = optimize,\n    });\n    b.installArtifact(exe);\n    const run = b.addRunArtifact(exe);\n    const run_step = b.step(\"run\", \"Run the app\");\n    run_step.dependOn(&run.step);\n}"),
        ("Show a build.zig.zon manifest declaring name, version, and one dependency.",
         ".{\n    .name = \"app\",\n    .version = \"0.1.0\",\n    .minimum_zig_version = \"0.13.0\",\n    .dependencies = .{\n        .known_folders = .{\n            .url = \"https://example.com/known-folders.tar.gz\",\n            .hash = \"1220...\",\n        },\n    },\n    .paths = .{ \"build.zig\", \"build.zig.zon\", \"src\" },\n}"),
        ("Zig: write a generic function that returns the max of two values of any ordered type.",
         "fn maxOf(comptime T: type, a: T, b: T) T {\n    return if (a > b) a else b;\n}"),
        ("Zig: define a tagged union `Value` of int / float / bool and a function returning its tag name.",
         "const Value = union(enum) {\n    int: i64,\n    float: f64,\n    boolean: bool,\n};\n\nfn tagName(v: Value) []const u8 {\n    return @tagName(v);\n}"),
        ("Zig: read a file fully into an allocator-owned slice.",
         "fn readAll(allocator: std.mem.Allocator, path: []const u8) ![]u8 {\n    const file = try std.fs.cwd().openFile(path, .{});\n    defer file.close();\n    return try file.readToEndAlloc(allocator, 1 << 20);\n}"),
        ("Zig: use comptime to build a lookup table of squares for 0..8.",
         "const squares = blk: {\n    var t: [8]u32 = undefined;\n    for (&t, 0..) |*x, i| x.* = @intCast(i * i);\n    break :blk t;\n};"),
        ("Zig: write a struct with a method, instantiated and called.",
         "const Counter = struct {\n    n: u32 = 0,\n    fn bump(self: *Counter) void {\n        self.n += 1;\n    }\n};\n// var c = Counter{}; c.bump();"),
        ("Zig: handle an error union with `catch` providing a default.",
         "const value = parseInt(input) catch 0;\n// or propagate:\nconst value = try parseInt(input);"),
        ("Zig: allocate a slice, use `defer` to free it, fill it with a value.",
         "const buf = try allocator.alloc(u8, 64);\ndefer allocator.free(buf);\n@memset(buf, 0);"),
        ("Zig: add a test block that asserts maxOf(i32, 2, 5) == 5.",
         "test \"maxOf picks larger\" {\n    try std.testing.expectEqual(@as(i32, 5), maxOf(i32, 2, 5));\n}"),
        ("Zig: in build.zig, add a unit-test step that runs all tests in src/main.zig.",
         "const tests = b.addTest(.{ .root_source_file = b.path(\"src/main.zig\"), .target = target, .optimize = optimize });\nconst run_tests = b.addRunArtifact(tests);\nconst test_step = b.step(\"test\", \"Run unit tests\");\ntest_step.dependOn(&run_tests.step);"),
        ("Zig: print formatted output to stdout.",
         "const stdout = std.io.getStdOut().writer();\ntry stdout.print(\"x = {d}, name = {s}\\n\", .{ x, name });"),
        ("Zig: iterate a slice with index using the `for ... |item, i|` form.",
         "for (items, 0..) |item, i| {\n    std.debug.print(\"{d}: {s}\\n\", .{ i, item });\n}"),
        ("Zig: define an error set and a function returning it.",
         "const ParseError = error{ Empty, BadDigit };\nfn parseDigit(c: u8) ParseError!u8 {\n    if (c < '0' or c > '9') return ParseError.BadDigit;\n    return c - '0';\n}"),
        ("Zig: use an ArrayList to collect values then convert to an owned slice.",
         "var list = std.ArrayList(u32).init(allocator);\ndefer list.deinit();\ntry list.append(1);\ntry list.append(2);\nconst owned = try list.toOwnedSlice();"),
        ("Zig: link a C library 'm' to an executable in build.zig.",
         "exe.linkLibC();\nexe.linkSystemLibrary(\"m\");"),
        ("Zig: add a build option that becomes a compile-time constant.",
         "const enable_logs = b.option(bool, \"logs\", \"Enable verbose logging\") orelse false;\nconst opts = b.addOptions();\nopts.addOption(bool, \"enable_logs\", enable_logs);\nexe.root_module.addOptions(\"config\", opts);"),
        ("Zig: switch on a tagged union and extract the payload.",
         "switch (v) {\n    .int => |n| std.debug.print(\"int {d}\\n\", .{n}),\n    .float => |f| std.debug.print(\"float {d}\\n\", .{f}),\n    .boolean => |b| std.debug.print(\"bool {}\\n\", .{b}),\n}"),
        ("Zig: write a comptime-generic Stack(T) type.",
         "fn Stack(comptime T: type) type {\n    return struct {\n        items: std.ArrayList(T),\n        const Self = @This();\n        fn init(a: std.mem.Allocator) Self {\n            return .{ .items = std.ArrayList(T).init(a) };\n        }\n        fn push(self: *Self, x: T) !void {\n            try self.items.append(x);\n        }\n        fn pop(self: *Self) ?T {\n            return self.items.popOrNull();\n        }\n    };\n}"),
        ("Zig: declare a packed struct mapping a 16-bit register with named bit fields.",
         "const Reg = packed struct(u16) {\n    enable: bool,\n    mode: u2,\n    _reserved: u5 = 0,\n    channel: u8,\n};"),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
# 5. Discord bot + Anthropic SDK
# ---------------------------------------------------------------------------
def gen_discord() -> list[dict]:
    pairs = [
        ("Write a discord.js v14 bot that replies 'pong' to a /ping slash command.",
         "const { Client, GatewayIntentBits } = require('discord.js');\nconst client = new Client({ intents: [GatewayIntentBits.Guilds] });\nclient.on('interactionCreate', async (i) => {\n  if (i.isChatInputCommand() && i.commandName === 'ping') {\n    await i.reply('pong');\n  }\n});\nclient.login(process.env.DISCORD_TOKEN);"),
        ("How do I register a guild slash command with discord.js REST?",
         "const { REST, Routes, SlashCommandBuilder } = require('discord.js');\nconst cmds = [new SlashCommandBuilder().setName('ping').setDescription('Ping!').toJSON()];\nconst rest = new REST().setToken(process.env.DISCORD_TOKEN);\nawait rest.put(Routes.applicationGuildCommands(APP_ID, GUILD_ID), { body: cmds });"),
        ("Defer a Discord interaction reply and edit it after a slow operation.",
         "await interaction.deferReply();\nconst result = await slowWork();\nawait interaction.editReply(result);"),
        ("Call the Anthropic Messages API from Node with the official SDK.",
         "import Anthropic from '@anthropic-ai/sdk';\nconst client = new Anthropic();\nconst msg = await client.messages.create({\n  model: 'claude-sonnet-4-6',\n  max_tokens: 1024,\n  messages: [{ role: 'user', content: 'Hello' }],\n});\nconsole.log(msg.content[0].text);"),
        ("Stream an Anthropic response token-by-token in Node.",
         "const stream = client.messages.stream({\n  model: 'claude-sonnet-4-6',\n  max_tokens: 1024,\n  messages: [{ role: 'user', content: prompt }],\n});\nstream.on('text', (t) => process.stdout.write(t));\nconst final = await stream.finalMessage();"),
        ("Add prompt caching to an Anthropic call by marking a large system block.",
         "const msg = await client.messages.create({\n  model: 'claude-sonnet-4-6',\n  max_tokens: 1024,\n  system: [{ type: 'text', text: LARGE_CONTEXT, cache_control: { type: 'ephemeral' } }],\n  messages: [{ role: 'user', content: question }],\n});"),
        ("Discord.js: send an embed with a title and one field.",
         "const { EmbedBuilder } = require('discord.js');\nconst embed = new EmbedBuilder().setTitle('Status').addFields({ name: 'Uptime', value: '3h' });\nawait interaction.reply({ embeds: [embed] });"),
        ("Handle a Discord button interaction.",
         "client.on('interactionCreate', async (i) => {\n  if (i.isButton() && i.customId === 'confirm') {\n    await i.update({ content: 'Confirmed!', components: [] });\n  }\n});"),
        ("Push jobs onto a simple in-memory worker queue in Node.",
         "const queue = [];\nlet running = false;\nasync function drain() {\n  if (running) return;\n  running = true;\n  while (queue.length) await queue.shift()();\n  running = false;\n}\nfunction enqueue(job) { queue.push(job); drain(); }"),
        ("Read the Anthropic API key from env and fail fast if missing.",
         "const key = process.env.ANTHROPIC_API_KEY;\nif (!key) throw new Error('ANTHROPIC_API_KEY not set');\nconst client = new Anthropic({ apiKey: key });"),
        ("Discord.js: restrict a slash command to a specific role.",
         "if (!interaction.member.roles.cache.has(ADMIN_ROLE_ID)) {\n  return interaction.reply({ content: 'Not allowed.', ephemeral: true });\n}"),
        ("Use Anthropic tool use: declare one tool and handle a tool_use block.",
         "const tools = [{ name: 'get_time', description: 'Current time', input_schema: { type: 'object', properties: {} } }];\nconst msg = await client.messages.create({ model: 'claude-sonnet-4-6', max_tokens: 512, tools, messages });\nfor (const block of msg.content) {\n  if (block.type === 'tool_use') { /* run block.name with block.input, append tool_result */ }\n}"),
        ("Discord.js: paginate a long reply into chunks under 2000 chars.",
         "function chunk(s, n = 1900) {\n  const out = [];\n  for (let i = 0; i < s.length; i += n) out.push(s.slice(i, i + n));\n  return out;\n}\nfor (const part of chunk(longText)) await channel.send(part);"),
        ("Set up a discord.js client that also reads message content (privileged intent).",
         "const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] });"),
        ("Retry an Anthropic call once on a 429 with a short backoff in Node.",
         "async function call(args) {\n  try { return await client.messages.create(args); }\n  catch (e) {\n    if (e.status === 429) { await new Promise(r => setTimeout(r, 1500)); return client.messages.create(args); }\n    throw e;\n  }\n}"),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
# 6. Playwright E2E
# ---------------------------------------------------------------------------
def gen_playwright() -> list[dict]:
    pairs = [
        ("Write a Playwright test that opens example.com and asserts the page title.",
         "import { test, expect } from '@playwright/test';\ntest('has title', async ({ page }) => {\n  await page.goto('https://example.com');\n  await expect(page).toHaveTitle(/Example/);\n});"),
        ("Playwright: click a button by its accessible role and name.",
         "await page.getByRole('button', { name: 'Sign in' }).click();"),
        ("Playwright: fill a form field by label and submit.",
         "await page.getByLabel('Email').fill('a@b.com');\nawait page.getByLabel('Password').fill('secret');\nawait page.getByRole('button', { name: 'Submit' }).click();"),
        ("How do I wait for navigation after a click in Playwright?",
         "await Promise.all([\n  page.waitForURL('**/dashboard'),\n  page.getByRole('link', { name: 'Open dashboard' }).click(),\n]);"),
        ("Playwright: assert an element is visible and contains text.",
         "await expect(page.getByTestId('toast')).toBeVisible();\nawait expect(page.getByTestId('toast')).toHaveText('Saved');"),
        ("Save and reuse authenticated storage state in Playwright.",
         "// after logging in:\nawait page.context().storageState({ path: 'auth.json' });\n// later, in playwright.config.ts:\n// use: { storageState: 'auth.json' }"),
        ("Playwright: intercept a network request and stub the JSON response.",
         "await page.route('**/api/user', (route) =>\n  route.fulfill({ status: 200, body: JSON.stringify({ name: 'Test' }) })\n);"),
        ("Playwright: take a screenshot of the full page.",
         "await page.screenshot({ path: 'page.png', fullPage: true });"),
        ("Playwright: select an option in a <select> by visible label.",
         "await page.getByLabel('Country').selectOption({ label: 'Korea' });"),
        ("Playwright: handle a new tab opened by a click.",
         "const [popup] = await Promise.all([\n  page.waitForEvent('popup'),\n  page.getByRole('link', { name: 'Open in new tab' }).click(),\n]);\nawait popup.waitForLoadState();"),
        ("Playwright: use a beforeEach to navigate before every test.",
         "test.beforeEach(async ({ page }) => {\n  await page.goto('https://app.example.com');\n});"),
        ("Playwright: assert a request was made with a given payload.",
         "const reqPromise = page.waitForRequest('**/api/save');\nawait page.getByRole('button', { name: 'Save' }).click();\nconst req = await reqPromise;\nexpect(req.postDataJSON()).toMatchObject({ id: 1 });"),
        ("Playwright config: run tests headed in chromium only.",
         "// playwright.config.ts\nexport default defineConfig({\n  use: { headless: false },\n  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],\n});"),
        ("Playwright: locate the nth row of a table and click its edit link.",
         "await page.getByRole('row').nth(2).getByRole('link', { name: 'Edit' }).click();"),
        ("Playwright: expect a download to start and read its filename.",
         "const [download] = await Promise.all([\n  page.waitForEvent('download'),\n  page.getByRole('button', { name: 'Export' }).click(),\n]);\nexpect(download.suggestedFilename()).toBe('report.csv');"),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
# 7. TOML schema design
# ---------------------------------------------------------------------------
def gen_toml() -> list[dict]:
    pairs = [
        ("Write a TOML config with a top-level key, a [server] table, and a port number.",
         "name = \"app\"\n\n[server]\nhost = \"0.0.0.0\"\nport = 8080"),
        ("How do I express an array of tables in TOML, e.g. multiple [[route]] entries?",
         "[[route]]\npath = \"/\"\nhandler = \"index\"\n\n[[route]]\npath = \"/health\"\nhandler = \"health\""),
        ("TOML: write a nested table [database.pool] with two integer keys.",
         "[database]\nurl = \"postgres://localhost/app\"\n\n[database.pool]\nmin = 2\nmax = 16"),
        ("TOML: a key with an inline table value.",
         "owner = { name = \"Ada\", role = \"admin\" }"),
        ("TOML: a multiline string and an array of strings.",
         "description = \"\"\"\nA multi-line\ndescription.\n\"\"\"\ntags = [\"web\", \"api\", \"v2\"]"),
        ("TOML: how do you write a date-time and a local date?",
         "created = 2026-05-12T03:00:00Z\nrelease_day = 2026-06-01"),
        ("Design a minimal schema doc snippet describing a [feature] table with name (string, required) and enabled (bool, default false).",
         "# [feature]\n# name     : string, required — the feature flag key\n# enabled  : bool, default false — whether the flag is on\n#\n[feature]\nname = \"new_ui\"\nenabled = false"),
        ("TOML: represent a list of feature flags as an array of tables, each with key + ramp percentage.",
         "[[flag]]\nkey = \"new_ui\"\nramp = 0.10\n\n[[flag]]\nkey = \"fast_path\"\nramp = 1.0"),
        ("TOML: dotted keys to set deep values without explicit tables.",
         "service.name = \"forge\"\nservice.limits.cpu = 2\nservice.limits.mem_gb = 8"),
        ("TOML: comment style and how to disable a key.",
         "# active config below\nverbose = true\n# debug = true   # disabled — uncomment to enable"),
        ("Write a TOML manifest for a tool: name, version, entrypoint, and a [deps] table.",
         "name = \"packer\"\nversion = \"1.0.0\"\nentrypoint = \"tool/packer.py\"\n\n[deps]\npyarrow = \">=14\"\nzstandard = \"*\""),
        ("TOML: an array of integers and an array of floats.",
         "ports = [8080, 8081, 8082]\nweights = [0.7, 0.2, 0.1]"),
        ("TOML schema: describe an [[endpoint]] array-of-tables with method (enum GET|POST), path (string), auth (bool).",
         "# [[endpoint]]\n# method : \"GET\" | \"POST\" — HTTP verb\n# path   : string       — URL path, must start with /\n# auth   : bool         — require an authenticated caller\n#\n[[endpoint]]\nmethod = \"GET\"\npath = \"/items\"\nauth = false\n\n[[endpoint]]\nmethod = \"POST\"\npath = \"/items\"\nauth = true"),
        ("TOML: how to write a table whose name has a dot or space (quoted key).",
         "[\"server.eu-west\"]\nregion = \"eu-west-1\"\n\n[targets.\"my board\"]\nmcu = \"stm32f4\""),
        ("TOML: top-level boolean, integer with underscores, and hex/oct/bin literals.",
         "enabled = true\nmax_conns = 1_000_000\nmask = 0xDEAD_BEEF\nperms = 0o755\nflags = 0b1010"),
    ]
    return [fmt(p, c) for p, c in pairs]


# ---------------------------------------------------------------------------
def main() -> int:
    if not V7_BASE.exists():
        print(f"ERROR: v7 base not found at {V7_BASE}", file=_sys.stderr)
        return 1
    base = [json.loads(l) for l in V7_BASE.read_text().splitlines() if l.strip()]
    print(f"v7 base: {len(base)}")

    blocks = {
        "dart_flutter": gen_dart(),
        "pytorch": gen_pytorch(),
        "crypto_bip39": gen_crypto(),
        "zig_deep": gen_zig(),
        "discord_anthropic": gen_discord(),
        "playwright": gen_playwright(),
        "toml_schema": gen_toml(),
    }
    added = []
    for name, rows in blocks.items():
        print(f"  + {name:18s} {len(rows):4d}")
        added.extend(rows)
    print(f"domain additions: {len(added)}")

    rows = base + added
    random.shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    manifest = {
        "version": "v0.2.0-r8",
        "base": str(V7_BASE),
        "base_rows": len(base),
        "domain_blocks": {k: len(v) for k, v in blocks.items()},
        "domain_added": len(added),
        "total_rows": len(rows),
        "source_audit": "papers/learning-surface-2026-05-12.md",
        "seed": 42,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"wrote: {OUT}  ({len(rows)} rows)")
    print(f"manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
