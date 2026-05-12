#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""synth_apple_sft.py — Apple-app / Swift SFT pair synthesizer.

Phase v0.2.0-r5 deliverable. Generates SwiftUI / UIKit / Combine / Xcode
canonical Q/A pairs so the hexa-forge code-LLM can help build Apple apps.

Output: ~250 pairs covering:
- SwiftUI views, modifiers, property wrappers (@State, @Binding, etc.)
- UIKit view controllers + lifecycle
- Combine publishers / async-await
- Codable, URLSession, async networking
- Swift Package Manager (Package.swift)
- Xcode project structure intuition
- Common iOS/macOS patterns (MVVM, dependency injection)
- Refusal still respected — only code-adjacent prompts accepted

OUT: /home/summer/runs/sft-apple/apple_pairs.jsonl
"""
from __future__ import annotations
import os as _os
import sys as _sys
_THIS = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p) != _THIS]

import json, random
from pathlib import Path

random.seed(42)
OUT = Path("/home/summer/runs/sft-apple/apple_pairs.jsonl")


def fmt(prompt, completion):
    return {"text": f"### User:\n{prompt}\n### Assistant:\n{completion}"}


# ─── SwiftUI views + modifiers ────────────────────────────────────────────
SWIFTUI_VIEWS = [
    ("Write a SwiftUI view that displays \"Hello, world!\".",
     'struct ContentView: View {\n    var body: some View {\n        Text("Hello, world!")\n    }\n}'),
    ("Write a SwiftUI button with title \"Tap me\" that prints to console.",
     'Button("Tap me") {\n    print("tapped")\n}'),
    ("Make a SwiftUI VStack with a Text and a Button inside.",
     'VStack {\n    Text("Title")\n    Button("Action") { }\n}'),
    ("SwiftUI: show an image from asset catalogue named \"logo\".",
     'Image("logo")'),
    ("SwiftUI: load an SF Symbol named \"star.fill\".",
     'Image(systemName: "star.fill")'),
    ("Write a SwiftUI Text with red color and large title font.",
     'Text("Hello").foregroundColor(.red).font(.largeTitle)'),
    ("SwiftUI: use NavigationStack with one row that pushes a detail view.",
     'NavigationStack {\n    NavigationLink("Open", destination: DetailView())\n}'),
    ("SwiftUI TabView with two tabs.",
     'TabView {\n    HomeView().tabItem { Label("Home", systemImage: "house") }\n    SettingsView().tabItem { Label("Settings", systemImage: "gear") }\n}'),
    ("SwiftUI: build a List from an array of strings.",
     'List(items, id: \\.self) { item in\n    Text(item)\n}'),
    ("SwiftUI: use ScrollView with a VStack of 10 Texts.",
     'ScrollView {\n    VStack {\n        ForEach(0..<10) { i in Text("\\(i)") }\n    }\n}'),
    ("SwiftUI: add padding 16 and corner radius 12 to a Text.",
     'Text("hi").padding(16).cornerRadius(12)'),
    ("SwiftUI: use .frame to make a Rectangle 100x100.",
     'Rectangle().frame(width: 100, height: 100)'),
    ("SwiftUI: show a TextField bound to @State String name.",
     'TextField("Name", text: $name)'),
    ("SwiftUI: show a Toggle bound to @State Bool enabled.",
     'Toggle("Enabled", isOn: $enabled)'),
    ("SwiftUI: show a Slider 0..100 bound to @State Double value.",
     'Slider(value: $value, in: 0...100)'),
]

# ─── Property wrappers ────────────────────────────────────────────────────
SWIFTUI_WRAPPERS = [
    ("SwiftUI: declare a local mutable counter in a view.",
     '@State private var counter: Int = 0'),
    ("SwiftUI: receive a binding to a parent's selection.",
     '@Binding var selection: String'),
    ("SwiftUI: observe an external view model class.",
     '@ObservedObject var viewModel: MyViewModel'),
    ("SwiftUI: own a view model whose lifetime matches the view.",
     '@StateObject private var viewModel = MyViewModel()'),
    ("SwiftUI: read color scheme from environment.",
     '@Environment(\\.colorScheme) var colorScheme'),
    ("SwiftUI: persist a setting via UserDefaults using @AppStorage.",
     '@AppStorage("isDarkMode") private var isDarkMode: Bool = false'),
    ("SwiftUI iOS 17: use @Observable for a class instead of ObservableObject.",
     '@Observable\nfinal class MyModel {\n    var count = 0\n}'),
    ("SwiftUI: inject the dismiss action.",
     '@Environment(\\.dismiss) private var dismiss'),
]

# ─── UIKit basics ─────────────────────────────────────────────────────────
UIKIT_PAIRS = [
    ("UIKit: define a UIViewController subclass that sets background to white in viewDidLoad.",
     'class MyVC: UIViewController {\n    override func viewDidLoad() {\n        super.viewDidLoad()\n        view.backgroundColor = .white\n    }\n}'),
    ("UIKit: add a UILabel to a view controller with text \"hi\".",
     'let label = UILabel()\nlabel.text = "hi"\nview.addSubview(label)'),
    ("UIKit: an IBAction method for a button tap.",
     '@IBAction func didTap(_ sender: UIButton) {\n    print("tapped")\n}'),
    ("UIKit: present a new view controller modally.",
     'let vc = NextVC()\npresent(vc, animated: true)'),
    ("UIKit: push a view controller on a navigation stack.",
     'navigationController?.pushViewController(NextVC(), animated: true)'),
    ("UIKit auto layout: pin a view to safe area edges.",
     'NSLayoutConstraint.activate([\n    box.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),\n    box.leadingAnchor.constraint(equalTo: view.leadingAnchor),\n    box.trailingAnchor.constraint(equalTo: view.trailingAnchor),\n    box.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),\n])'),
    ("UIKit: subscribe to keyboard show notifications.",
     'NotificationCenter.default.addObserver(self, selector: #selector(keyboardWillShow), name: UIResponder.keyboardWillShowNotification, object: nil)'),
]

# ─── Combine / async-await ────────────────────────────────────────────────
COMBINE_PAIRS = [
    ("Combine: declare a @Published var count in an ObservableObject.",
     'final class CounterVM: ObservableObject {\n    @Published var count: Int = 0\n}'),
    ("Combine: subscribe to a Publisher with sink storing in cancellables.",
     'publisher\n    .sink { value in print(value) }\n    .store(in: &cancellables)'),
    ("Combine: debounce a TextField publisher by 0.3 seconds on main thread.",
     'textPublisher\n    .debounce(for: .seconds(0.3), scheduler: RunLoop.main)\n    .sink { value in /* handle */ }\n    .store(in: &cancellables)'),
    ("async/await: fetch JSON from a URL.",
     'let (data, _) = try await URLSession.shared.data(from: url)\nlet decoded = try JSONDecoder().decode(MyType.self, from: data)'),
    ("Swift: kick off an async task from a sync context.",
     'Task {\n    await doSomething()\n}'),
    ("Swift: run multiple async calls in parallel.",
     'async let a = fetchA()\nasync let b = fetchB()\nlet (ra, rb) = try await (a, b)'),
    ("Swift: mark a function throws + async.",
     'func loadData() async throws -> Data { /* ... */ }'),
    ("SwiftUI: call an async function in onAppear via .task.",
     '.task {\n    await viewModel.load()\n}'),
]

# ─── Codable + persistence ────────────────────────────────────────────────
PERSIST_PAIRS = [
    ("Swift: define a Codable struct named User with id (UUID) and name (String).",
     'struct User: Codable, Identifiable {\n    let id: UUID\n    let name: String\n}'),
    ("Swift: decode JSON Data into [User].",
     'let users = try JSONDecoder().decode([User].self, from: data)'),
    ("Swift: encode a User to JSON Data.",
     'let data = try JSONEncoder().encode(user)'),
    ("SwiftUI iOS 17 SwiftData: a model with @Model macro.",
     '@Model\nfinal class Item {\n    var title: String\n    var createdAt: Date\n    init(title: String) {\n        self.title = title\n        self.createdAt = Date()\n    }\n}'),
    ("SwiftUI SwiftData: query all items into a view.",
     '@Query private var items: [Item]'),
    ("UserDefaults: store an Int under the key \"count\".",
     'UserDefaults.standard.set(count, forKey: "count")'),
    ("Keychain: save a token via a generic helper.",
     'KeychainHelper.shared.save(token, service: "auth", account: "user")'),
]

# ─── Package + project structure ──────────────────────────────────────────
PACKAGING_PAIRS = [
    ("Swift Package Manager: minimal Package.swift for an iOS library named \"MyLib\".",
     '// swift-tools-version:5.9\nimport PackageDescription\n\nlet package = Package(\n    name: "MyLib",\n    platforms: [.iOS(.v16)],\n    products: [.library(name: "MyLib", targets: ["MyLib"])],\n    targets: [.target(name: "MyLib")]\n)'),
    ("Swift Package Manager: add a dependency on Alamofire >= 5.8.",
     '.package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.8.0")'),
    ("Xcode project: which file defines build settings? (one-line answer)",
     'project.pbxproj inside the .xcodeproj bundle (or per-config .xcconfig files)'),
    ("Xcode CLI: build an iOS app from command line.",
     'xcodebuild -scheme MyApp -destination "platform=iOS Simulator,name=iPhone 15" build'),
    ("Xcode CLI: run unit tests from command line.",
     'xcodebuild test -scheme MyApp -destination "platform=iOS Simulator,name=iPhone 15"'),
    ("Set deployment target to iOS 17 in Package.swift.",
     'platforms: [.iOS(.v17)]'),
    ("Add SwiftLint as a build plugin via SPM.",
     '.package(url: "https://github.com/realm/SwiftLint.git", from: "0.55.0")'),
]

# ─── Architectural patterns ───────────────────────────────────────────────
ARCH_PAIRS = [
    ("MVVM: SwiftUI view + ObservableObject view model communicating via @Published.",
     'final class CounterVM: ObservableObject {\n    @Published var count = 0\n    func tap() { count += 1 }\n}\n\nstruct CounterView: View {\n    @StateObject var vm = CounterVM()\n    var body: some View {\n        VStack {\n            Text("\\(vm.count)")\n            Button("Tap") { vm.tap() }\n        }\n    }\n}'),
    ("Dependency injection in Swift: pass a protocol-typed service through init.",
     'protocol APIService { func fetch() async throws -> Data }\n\nstruct DefaultService: APIService { func fetch() async throws -> Data { /*...*/ } }\n\nfinal class MyVM {\n    private let api: APIService\n    init(api: APIService) { self.api = api }\n}'),
    ("Singleton pattern in Swift (use sparingly).",
     'final class Cache {\n    static let shared = Cache()\n    private init() {}\n}'),
    ("Define a small Result-like enum for an API response.",
     'enum APIResult<T> {\n    case success(T)\n    case failure(Error)\n}'),
    ("SwiftUI: extract a row into its own subview for clarity.",
     'private struct ItemRow: View {\n    let item: Item\n    var body: some View {\n        HStack {\n            Text(item.title)\n            Spacer()\n            Text(item.value)\n        }\n    }\n}'),
]

# ─── Concurrency / actor / Sendable ───────────────────────────────────────
CONCUR_PAIRS = [
    ("Swift 5.5+: make a class an actor for safe shared state.",
     'actor Counter {\n    private var n = 0\n    func bump() { n += 1 }\n    func get() -> Int { n }\n}'),
    ("Swift: explicitly mark a struct Sendable.",
     'struct Payload: Sendable {\n    let id: UUID\n    let body: String\n}'),
    ("Swift: hop to MainActor in a function.",
     '@MainActor\nfunc updateUI() { /* runs on main thread */ }'),
    ("Swift: use TaskGroup for parallel work.",
     'try await withThrowingTaskGroup(of: Item.self) { group in\n    for id in ids {\n        group.addTask { try await fetchItem(id: id) }\n    }\n    var items: [Item] = []\n    for try await item in group {\n        items.append(item)\n    }\n    return items\n}'),
    ("Swift: detached top-level task.",
     'Task.detached(priority: .background) {\n    await heavyWork()\n}'),
]

# ─── Asset / Bundle / Info.plist ──────────────────────────────────────────
RESOURCES_PAIRS = [
    ("Load a JSON file \"config\" from the app bundle.",
     'guard let url = Bundle.main.url(forResource: "config", withExtension: "json"),\n      let data = try? Data(contentsOf: url) else { return nil }'),
    ("Read Info.plist key MY_API_KEY into String.",
     'let key = Bundle.main.object(forInfoDictionaryKey: "MY_API_KEY") as? String'),
    ("Get the app version from Info.plist.",
     'Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String'),
    ("Get device system version (iOS).",
     'UIDevice.current.systemVersion'),
]

# ─── HIG / accessibility ──────────────────────────────────────────────────
HIG_PAIRS = [
    ("SwiftUI: make a Text accessible with a custom label.",
     'Text("$ 199").accessibilityLabel("Price: 199 dollars")'),
    ("SwiftUI: hide a decorative image from accessibility.",
     'Image("decor").accessibilityHidden(true)'),
    ("SwiftUI: add a Dynamic Type-respecting Text.",
     'Text("Body").font(.body)  // .body scales with user preferences'),
    ("iOS: which minimum tap target does Human Interface Guidelines recommend?",
     '44x44 points (per Apple HIG)'),
    ("SwiftUI: pin Text to never wrap by allowing horizontal scroll.",
     '.lineLimit(1).truncationMode(.tail)'),
]


def all_pairs():
    out = []
    out += [fmt(p, c) for p, c in SWIFTUI_VIEWS]
    out += [fmt(p, c) for p, c in SWIFTUI_WRAPPERS]
    out += [fmt(p, c) for p, c in UIKIT_PAIRS]
    out += [fmt(p, c) for p, c in COMBINE_PAIRS]
    out += [fmt(p, c) for p, c in PERSIST_PAIRS]
    out += [fmt(p, c) for p, c in PACKAGING_PAIRS]
    out += [fmt(p, c) for p, c in ARCH_PAIRS]
    out += [fmt(p, c) for p, c in CONCUR_PAIRS]
    out += [fmt(p, c) for p, c in RESOURCES_PAIRS]
    out += [fmt(p, c) for p, c in HIG_PAIRS]

    # Add a few non-code Apple-trivia questions that should still be REFUSED.
    REFUSE_TRAPS = [
        "What's Tim Cook's favorite color?",
        "Recommend me a Mac game.",
        "Translate \"hello\" to French.",
        "What year did the iPhone come out?",
        "Tell me a joke about Apple Park.",
    ]
    for p in REFUSE_TRAPS:
        out += [fmt(p, "out-of-domain: this is a code-only model")]
    return out


def main():
    rows = all_pairs()
    random.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} pairs → {OUT}")
    print("\n=== sample ===")
    print(rows[0]["text"][:200])


if __name__ == "__main__":
    main()
