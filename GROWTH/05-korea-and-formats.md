# 05 — 한국 커뮤니티 노출 + 직렬화 포맷/CLI 채택

리서치 2026-05-16. 파트 A는 모든 자산의 한국 노출, 파트 B는 dancinlab의 sister
포맷(n6 / hxc / n12 / tape) 채택 전략. `[사실]`=출처 확인 / `[추측]`=추론.

---

## 파트 A — 한국 AI/개발자 커뮤니티 노출

### A1. GeekNews (news.hada.io) — 최우선 진입점

- `[사실]` 한국판 Hacker News. 일 방문 약 20만, 4,000+ 국내 기업이 Slack 봇 수신.
  섹션 3 — News / Ask / **Show**. 업보트 정렬.
- `[사실]` **Show GN**은 국내 서비스·오픈소스 전용 섹션 — 기술 뉴스에 묻히지 않고
  더 오래 노출, 피드백 설계.
- **실행** — 모델·포맷·CLI를 **각각 Show GN에 별도 제출**(묶지 말 것, 1프로젝트=1제출).
  제목 직설·구체(과장 금지). 제출 직후 5분 내 본인 댓글로 동기·아키텍처·라이선스 설명.
  정치·종교·사건사고 배제 — 순수 기술 프레이밍.

### A2. 아카라이브 / 클리앙

- `[사실]` 아카라이브 **AI 언어모델 로컬 채널**(arca.live/b/alpaca) — 한국어 로컬 LLM
  실사용자(파인튜닝·양자화·GGUF 운용) 집결지. 클리앙 **AI 게시판(cm_ai)**도 활발.
- **실행** — 한국어 모델은 알파카 채널에 GGUF/벤치와 함께. "직접 만든 것 공유 +
  질문 받기" 톤(노골적 홍보 민감). DCInside는 도달 넓으나 시그널 낮음 — 우선순위 하위.

### A3. 한국어 평가 인프라

- `[사실]` 한국어 출력 품질 — Qwen 2.5 계열 최상위, Gemma 3·Llama 3.3 추종.
  **Horangi**(W&B 한국어 리더보드, GLP/ALT 2축, 20+ 벤치) 운영 중. **LogicKor**는
  변별력 소실로 read-only 동결.
- `[추측]` LogicKor 동결로 "갱신되는 한국어 리더보드" 자리에 공백 — 새 모델은 Horangi
  제출 + 자체 벤치 공개가 변별력 확보에 유리.
- **실행** — 한국어 모델 출시 시 Horangi 등록 + `NomaDamas/awesome-korean-llm`류 PR.

### A4. 한국어 콘텐츠 채널

- `[사실]` **velog** — 마크다운·코드 친화, 한국 개발 블로그 사실상 표준. **브런치**는
  코드 지원 빈약 → 기술 콘텐츠 부적합. 보조 — DevBench(디스코드 4,000+), OKKY, GDG.
- **실행** — 기술 글은 velog에 쓰고 GeekNews News에 제출. 주 1편 실사용 사례 글(유지 신호).

---

## 파트 B — 직렬화 포맷 / 스펙 / CLI 채택

### B1. 레퍼런스 케이스 — TOON

- `[사실]` TOON = 2025년 가장 빠르게 채택된 LLM-시대 직렬화 포맷. GitHub 21,600+ 스타,
  v2.0 스펙 + 컨포먼스 테스트 스위트. 공식 구현 7언어(TS·Python·Go·Rust·.NET·Java·
  Swift·Dart), **커뮤니티 구현 20+ 언어**(R은 CRAN 등재까지). CLI(`npx`로 즉시 변환,
  stdin/stdout 파이프, `--stats`로 토큰 절감 표시). VS Code 확장 + tree-sitter 그래머.
  공식·커뮤니티 플레이그라운드. 4 LLM × 209문항 벤치(JSON 대비 토큰 ~40%↓).
- **채택 3축** — 기술 우위 입증(공개 벤치) + 개발자 접근성(CLI·IDE) + 생태계 확대(다언어 구현).

### B2. 새 포맷이 채택되는 조건

- `[사실]` **킬러 유스케이스**가 결정적 — TOON은 "LLM 토큰 비용 절감"이라는 측정
  가능한 단일 통증 공략, JSON 전면 대체가 아니라 특정 영역(균일 배열·표)만.
- `[사실]` **레퍼런스 구현** — 포맷은 스펙 문서가 아니라 `pip`/`npm`/`cargo` 설치
  가능한 라이브러리로 존재해야 채택. CBOR이 MessagePack보다 단순하지 않은데도 산
  이유는 RFC 표준화 + 다언어 구현 + 태그 레지스트리 같은 생태계 자산.
- `[사실]` **API 친숙성** — 기존 직렬화 API 미러링(예: `.NET JsonSerializer` 시그니처
  동일)으로 학습비용 0에 근접.

### B3. 스펙 프로젝트 실패/성공

- `[사실]` 실패 — 동작하는 레퍼런스 라이브러리 없이 스펙 문서만 / 단일 워크플로만
  가정 / 컨포먼스 테스트 부재. 성공 — 살아있는(최신) 스펙 + 컨포먼스 스위트 + semver.

### B4. 에디터 끈끈함 — VS Code / tree-sitter / LSP

- `[사실]` VS Code는 **TextMate 그래머**로 토큰화 — 다수 에디터 공통 자산. LSP는 색을
  규정하지 않음 — **하이라이트=TextMate, 검증·자동완성=LSP** 역할 분담.
- **실행 순서** — (1) TextMate 그래머 + VS Code 확장(최소 비용·최대 효과), (2)
  tree-sitter 그래머(Neovim/Helix/Zed/Emacs 한 번에), (3) 여력되면 LSP.
- 끈끈함의 핵심 — 포맷 파일을 "그냥 열면 색이 입혀지고 오류가 보이는" 경험.

### B5. 플레이그라운드 + 통합 PR

- `[사실]` JSON Schema 생태계에서 "공식 플레이그라운드 부재"가 명시적 진입 장벽으로
  지목됨. 설치 없이 붙여넣고 검증·변환 + **공유 가능 URL**(스니펫 인코딩)이 채택에 결정적.
- `[사실]` Parquet은 Pandas·Polars·DuckDB가 모두 직접 읽고 쓰기 때문에 표준이 됨.
  → 사용자가 이미 쓰는 인접 도구에 "이 포맷 읽기/쓰기" **통합 PR**을 넣어 부트스트랩.
  CLI는 stdin/stdout 파이프 우선 지원.

### B6. dancinlab 포맷에의 적용 (n6 / hxc / n12 / tape)

- 각 포맷의 **킬러 유스케이스 한 줄**을 먼저 확정 — JSON 대체로 팔지 말 것.
  tape는 wilson이 실사용 = 살아있는 킬러 앱(이미 확보).
- 레퍼런스 구현 — 최소 Python + Rust 또는 TS, `pip`/`crates`/`npm` 등재.
- `.tape` VS Code 확장 + tree-sitter 그래머 → Neovim/Zed 커버.
- 온라인 인코더/디코더 플레이그라운드 + 공유 URL.
- JSON·MessagePack·Parquet·CBOR 대비 공개 벤치(크기·속도·KV-cache 안정성).
- 인접 도구(LLM 프레임워크·직렬화 허브)에 통합 PR.
- 출시는 `03`의 Show HN 플레이북 — 포맷·도구는 HN 최적.

## 출처

- [GeekNews — About & ToS](https://news.hada.io/about) · [GeekNews Show](https://news.hada.io/show)
- [GeekNews 1주년 회고 — Guru's Blog](https://xguru.net/2215)
- [아카라이브 AI 언어모델 로컬 채널](https://arca.live/b/alpaca)
- [Best Open Source LLM For Korean in 2026 — SiliconFlow](https://www.siliconflow.com/articles/en/best-open-source-llm-for-korean)
- [awesome-korean-llm — GitHub](https://github.com/NomaDamas/awesome-korean-llm)
- [Horangi 한국어 LLM 리더보드 — W&B](https://github.com/wandb/llm-leaderboard-korean/blob/main/README.md)
- [TOON — GitHub (toon-format/toon)](https://github.com/toon-format/toon)
- [TOON: Data Serialization and AI Token Economics — Heavybit](https://www.heavybit.com/library/article/toon-how-data-serialization-improves-ai-token-economics)
- [MessagePack vs CBOR — diziet](https://diziet.dreamwidth.org/6568.html)
- [VS Code — Syntax Highlight Guide](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)
- [GSoC 2026: Official Web-Based JSON Schema Playground](https://github.com/json-schema-org/community/issues/972)
- [Building Your Modern Data Analytics Stack with Parquet and DuckDB — KDnuggets](https://www.kdnuggets.com/building-your-modern-data-analytics-stack-with-python-parquet-and-duckdb)
