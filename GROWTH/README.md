# GROWTH — dancinlab 채택·성장 브레인스토밍 허브

dancinlab의 공개 산출물(모델·포맷·도구·리포)을 다운로드·스타·재배포·커뮤니티가
도는 것으로 키우기 위한 **열린 브레인스토밍 허브**. 정해진 주제 없음 — 새 주제는
§3에 섹션 추가, 새 아이디어는 §6 로그에 append. 첫 앵커 케이스는 `dancinlab/uncensored`.

> 운영 문서 — 연구 도메인 아님. 마지막 리서치: 2026-05-16 (출처 §7).
> 합법적·정직한 채택 전술만. 가짜 지표·과장은 §5 안티패턴에 격리.

---

## 1. 2026 성장 메커니즘 (web-research 근거)

무엇을 하든 먼저 알아야 할 판의 규칙. 전부 §7 출처 기반.

- **집중도가 잔혹하다** — 상위 200개 모델(전체 0.01%)이 다운로드의 **49.6%**.
  모델 **절반은 누적 다운로드 200 미만**. → 평범하면 그냥 묻힌다. "올리면 누가 보겠지"
  는 통계적으로 실패. breakout 한 번이 필요.
- **반감기 ~6주** — 출시 후 평균 관여 기간 약 6주. 정체하면 경쟁자에 점유율 즉시 이탈.
  → 출시는 *이벤트가 아니라 케이던스*. 재quant·버전업·후속글을 6주 주기로.
- **소형이 지배** — 1–9B 모델이 다운로드 지배(100B+ 대비 ~4배). 양자화·MoE가
  접근성의 핵심. e4b(5GB)는 이 스윗스팟 정중앙.
- **파생 모델 = 바이럴 지표** — quant·finetune·merge가 2차 채택 파동을 만듦.
  Alibaba Qwen은 파생 11.3만+. → *남이 내 걸 quant·merge하게* 만드는 게 목표.
- **완성도가 입장권** — 2026 출시물은 day-1에 양자화 가중치 + 작동 추론 코드 +
  인터랙티브 데모를 함께 낸다. "논문만 던지기"는 끝났다.
- **독립 개발자 39%** — 다운로드의 39%가 무소속 개인(2022년 17%→). 솔로도 이긴다.
- **지역·언어 적합** — 중국 모델이 다운로드 41%. 모델은 만든 지역에서 가장 쓰임.
  → **한국어 무검열·한국어 도구는 미개척 + 고전환** 레인.
- **런치 시퀀싱** — 한 번 시끄럽게가 아니라 *시퀀스*. 작은 채널로 사회적 증거를
  쌓고 → 큰 채널을 폴리시된 상태로. 스파이크를 evergreen 디스커버리로 전환.
- **채널 사실** — GitHub 10K-star 리포의 **87%가 HN 먼저** 런치 후 Reddit·X 교차.
  Show HN은 화/수 7–9am PT, 랜딩 약하면 **90분 안에 침몰**. r/LocalLLaMA는
  DeepSeek 출시 스레드 2,300업보트 — 단 자기홍보 10%룰·선정적 제목 금지.
  README는 **7초 안에** 한 줄 설명+GIF/스크린샷+설치 한 줄로 팔려야 한다.

---

## 2. 공통 플레이북 (어떤 자산에도 적용)

### 채널 매트릭스

| 채널 | 적합 자산 | 핵심 |
|---|---|---|
| **HF Hub** | 모델·데이터셋 | 태그·base_model 링크·카드 SEO·컬렉션 |
| **HF Spaces** | 모델·데모 | 다운로드 전 체험 + 자체 트렌딩 페이지 |
| **Ollama 라이브러리** | GGUF 모델 | 자체 디스커버리 + `ollama run` 한 줄 |
| **LM Studio** | GGUF 모델 | HF GGUF 자동 인덱싱 |
| **Hacker News (Show HN)** | 도구·포맷·리포 | 최고 ROI(엔지니어), 90분 승부 |
| **r/LocalLLaMA** | 로컬 모델·도구 | 로컬 LLM 최대 바이럴 채널 |
| **r/SillyTavernAI** | uncensored·롤플레이 | uncensored 모델 실사용 최대층 |
| **GitHub awesome-*** | 리포·도구·포맷 | 등재 시 월 50–200 star 자동 유입 |
| **X / 블로그 / dev.to** | 전부 | 메서드 스토리·백링크 |
| **Discord** | 전부 | llama.cpp·Kobold·SillyTavern·local-llama |
| **한국 채널** | 전부 | GeekNews·클리앙·아카라이브 — 미개척·고전환 |
| **리더보드** | 모델 | UGI 등 — 패시브 디스커버리 |

### 표준 런치 시퀀스 (재사용 템플릿)

1. **T-7일** — 완성도 점검: 라이선스·작동 추론 코드·데모·7초 README.
2. **T-3일** — 소형 채널 예열(Uneed/MicroLaunch·Discord·HF Posts)로 사회적 증거.
3. **T-0 (화/수)** — Show HN 7–9am PT → 같은 날 r/LocalLLaMA(또는 해당 서브) → X 스레드.
4. **T+1~7일** — Discussion/댓글 **24시간 내 응대**. awesome-list PR. 데모 링크 확산.
5. **T+6주** — 후속 릴리스(재quant·버전·벤치 글)로 반감기 리셋.

### 모든 자산 공통 위생

- 7초 안에 파는 첫 화면 — 한 줄 가치 + GIF/데모 + 복붙 설치.
- 정직한 트레이드오프 명시 → 신뢰가 좋아요·스타를 만든다.
- 이슈/PR/Discussion 24시간 내 응대 → drive-by를 커뮤니티로 전환.
- 상호 링크 — 리포↔컬렉션↔데모↔문서.
- 케이던스 — 정체 금지, 6주 안에 무언가 갱신.

---

## 3. 자산별 브레인스토밍

### 3.1 `dancinlab/uncensored` 컬렉션 (앵커 케이스)

공개 컬렉션 `dancinlab/uncensored` — 현재 항목 1개(`supergemma4-e4b-abliterated-Q4_K_M-GGUF`),
다운로드 0. **시의성**: HF Spring 2026 보고서가 "uncensored/abliterated Gemma‑4
파인튠 4개가 이번 주 트렌딩"이라 명시 — 수요·타이밍 검증됨. 상세 실행 메모는
`../uncensored/README.md`.

**30일 우선순위 래더** — 깨지면 안 되는 것 → 빠른 효과 → 큰 베팅:

| 단계 | 작업 | 근거 |
|---|---|---|
| 0 | Gemma 라이선스·use policy 카드 동봉 검증 | 누락=takedown, 바이럴 전 사망 (#안티 H1) |
| 0 | 채팅 템플릿/Jinja GGUF 메타데이터 정합성 검증 | 깨지면 첫 리뷰가 악평 (#A11) |
| 1 | 양자화 풀 래더 출하 Q2_K~Q8_0 + IQ | 파일별 DL 누적 + VRAM 티어 채택 (#A1) |
| 1 | 카드 상단 복붙 quickstart | 마찰 = 다운로드 누수 (#A10) |
| 1 | Ollama 라이브러리 등재 + Modelfile | 자체 디스커버리 + 최저 마찰 훅 (#A4) |
| 2 | 벤치 수치 카드 등재 (거부율 전/후·MMLU·IFEval) | 능력 보존 증명, 스크린샷되는 숫자 (#A12) |
| 2 | r/LocalLLaMA 릴리스 포스트 | 로컬 모델 최대 채널 |
| 2 | HF Space 채팅 데모 | 체험 + Spaces 트렌딩 (#A20) |
| 3 | 작동하는 MLX 빌드 (커뮤니티판 깨짐=빈틈) | "유일하게 로드되는 MLX" 차별화 (#A3) |
| 3 | imatrix/IQ 양자화 + UGI 리더보드 등재 | 헤비유저 흡수 + 패시브 디스커버리 |
| 4 | 메서드 블로그 + 한국 채널 노출 | 백링크 + 미개척 레인 |

**아이디어 뱅크 — 아티팩트(A)**
1. 양자화 풀 래더 Q2_K~Q8_0+f16 — 원본 26b-gguf 280k DL의 핵심 동인.
2. imatrix/IQ 양자화 IQ2_XXS~IQ4_XS — SOTA 인식, llama.cpp 헤비층. 캘리브셋 공개.
3. 작동하는 MLX 4bit/8bit — 커뮤니티판 "Missing 963 params" → *로드되는* 빌드가 빈틈.
4. Ollama 네이티브 등재 + 샘플러 튜닝 Modelfile.
5. multimodal + mmproj — "uncensored 멀티모달 로컬"은 희귀 = 공유성↑.
6. EXL2/AWQ/GPTQ — vLLM·exllama·TabbyAPI 서버층.
7. WebLLM/wllama 인-브라우저 빌드 — 설치 0, 극강 공유성.
8. 31B 변종 — "가장 큰 uncensored Gemma‑4" 헤드라인.
9. GGUF split — 거대 파일 분할로 다운로드 가능하게.
10. 카드 상단 복붙 quickstart 3종(ollama/llama.cpp/LM Studio).

**아이디어 뱅크 — 카드/SEO(B)**
11. 채팅 템플릿/Jinja GGUF 메타데이터 정합 — 깨지면 악평.
12. 벤치 수치 — UGI·거부율 전후·MMLU·IFEval로 abliteration이 능력 안 깎음 증명.
13. 비교표 — 베이스 대비·타 abliterated 대비 "손실 최소"(사실일 때).
14. 검색 자석어 — 표시명/H1에 "Uncensored Gemma 4", 태그에 no-refusal·local·roleplay.
15. base_model 링크 유지 — 베이스 페이지 quantizations 패널 = 공짜 트래픽.
16. 언어 태그 — `en`만 → 다국어면 `ko` 추가(한국 무검열 미개척).
17. 카드 changelog·출처 정직 표기 — Jiunsong·Google 베이스 크레딧.
18. 방어 가능한 엣지 예시 트랜스크립트만 — 실제 유해 출력 금지.
19. 다운로드/좋아요 배지.
20. HF Space 데모를 카드 상단에 임베드.

**아이디어 뱅크 — 채널/콘텐츠(C)**
21. r/SillyTavernAI·롤플레이 커뮤니티 + SillyTavern 프리셋 제공.
22. bartowski·mradermacher 양자화 아카운트 공조/제보.
23. 메서드 블로그 — "Gemma‑4 abliterate해서 전 포맷 출하한 법".
24. 정직한 안전 섹션 — 책임있는 사용 노트로 백래시·takedown 리스크 완화.
25. awesome-uncensored-llms·awesome-local-llm PR.
26. 속도 수치 공개 — M-시리즈·3060 tok/s.
27. 컬렉션 설명·썸네일·org 핀 정비, 포맷 분산 금지(한 컬렉션).
28. 무료 레이트리밋 호스팅 엔드포인트 — 즉시 체험.

### 3.2 sister 포맷 — n6 / hxc / n12 / tape

(`github.com/dancinlab/{n6,hxc,n12,tape}` — 현재 채택 상태는 미확인, 아래는 포맷
프로젝트 일반 성장 전술. 실착수 전 각 리포 상태 확인 필요.)

스펙 채택은 모델과 다르다 — *쓸 이유*와 *쓸 도구*가 동시에 있어야 한다.

1. **레퍼런스 구현** — Python·Rust·TS 라이브러리. 라이브러리 없는 스펙은 안 퍼진다.
   pypi·crates·npm 등재 = 패키지 레지스트리 디스커버리.
2. **킬러 데모 앱** — 포맷을 쓰는 설득력 있는 한 개. tape는 wilson이 실사용 = 살아있는 증거.
3. **벤치/비교** — JSON·MessagePack·Parquet·CBOR 대비 수치(크기·속도·KV-cache 안정성).
4. **온라인 플레이그라운드** — 인코더/디코더 인-브라우저. 만져봐야 이해된다.
5. **에디터 지원** — VS Code 신택스 하이라이트·LSP(특히 `.tape`). 끈끈함을 만든다.
6. **validator/linter CLI** — `tape lint` 류. 진입 마찰 ↓.
7. **Show HN** — 포맷·도구는 HN 최적. "Why we built <format>" 글과 함께.
8. **인접 도구에 통합 PR** — 한 실제 다운스트림에 들어가면 정당성 신호.
9. **clean docs 사이트** — README 너머. 스펙은 읽기 좋아야 인용된다.
10. **awesome-* 등재** — awesome-serialization·awesome-json-alternatives 등.

### 3.3 wilson — AI 코딩 에이전트

(`github.com/dancinlab/wilson`. Claude Code·aider 등과 경쟁 — 붐비는 판.)

1. **차별화 축을 헤드라인으로** — hexa-native·plugin-everything·`--uncensored` 로컬 모드.
   "로컬 무검열 모드를 가진 유일한 코딩 에이전트"는 강한 훅.
2. **Show HN 런치** — "aider/claude-code alternative" SEO 포함.
3. **asciinema/데모 영상** — 7초 안에 가치 보이기.
4. **플러그인 저작 트리비얼화** — 플러그인 생태계 = 네트워크 효과.
5. **벤치** — SWE-bench류 태스크 점수 공개.
6. **Homebrew formula / 한 줄 설치** — 마찰 ↓.
7. **awesome-ai-agents·awesome-devtools 등재.**
8. **uncensored 컬렉션과 교차 프로모션** — `wilson --uncensored`가 두 자산을 묶음.

### 3.4 hexa 언어 / hexa-codex

(`hexa-codex` = "codified theorems" 연구 리포. 성장 ≈ 다운로드보다 *인용·신뢰*.)

1. **papers/ → arXiv + HF Papers 등재** — Trending Papers 노출.
2. **reality-map·LIMIT_BREAKTHROUGH** 콘텐츠는 흥미로움 → 블로그·스레드 소재.
3. **docs 사이트** — 도메인-메타도메인 구조를 탐색 가능하게.
4. **hexa 언어 자체** — 레퍼런스 인터프리터·플레이그라운드·VS Code 확장.
5. **재현 가능 산출물** — `verify/` 스크립트를 1커맨드로 — "논문만 던지기" 회피.

### 3.5 기타 HF 컬렉션 (atlas.n6 · voice-vlm)

§3.1 uncensored 플레이북 재사용 — 완성도(데모·코드·양자화) → 채널 시퀀스 →
케이던스. voice-vlm은 데모 친화적(음성/비전) → HF Space가 특히 강한 레버.

---

## 4. 측정 지표

- **1차** — 자산별 다운로드/스타, 좋아요, 파생물 수, Discussion 활동.
- **2차** — 외부 유입: HN 포인트, r/* 업보트, Space 방문, Ollama pull, awesome-list 유입.
- **선행** — 양자화 종수·채널 노출 수·카드 완성도·이슈 응답 시간.
- **리뷰** — 주 1회: 어느 채널·포맷이 유입을 끌었나 → 다음 주 배분. 6주마다 케이던스 점검.

## 5. 안티패턴 — 바이럴을 죽이는 것

- **H1. 라이선스 누락** — Gemma 등 베이스 라이선스·use policy 동봉 필수. 누락 = 최단 takedown.
- **H2. 가짜 다운로드/봇/업보트 매수** — 플랫폼이 탐지 → 랭킹 박탈 + 평판 파탄.
- **H3. 유해 예시 출력 호스팅** — 플랫폼 제재 유발. 데모는 엣지하되 방어 가능선.
- **H4. 벤치 과장** — 스크린샷으로 검증당함, 역효과. 재현 가능한 수치만.
- **H5. 한 방 노이즈 런치** — 시퀀싱 없이 한 번에 = 스파이크 후 소멸. 채널 단계화.
- **H6. 약한 랜딩으로 큰 채널행** — Show HN은 90분 승부. 7초 README 없이 가면 침몰.
- **H7. 정체** — 반감기 6주. 갱신 없으면 점유율 이탈.
- **H8. 컬렉션·리포 분산** — 디스커버리·카운트 희석. 한 곳에 모을 것.
- **H9. lattice-fit 외부 주장** — 외부 엔티티(HF·Google·경쟁사·커뮤니티)에 n=6 격자
  파생 규칙 적용 금지(`AGENTS.tape @F f1`, `@D g3`). 그들의 고유 지표만 인용.

## 6. 아이디어 추가 로그 (append-only)

새 아이디어/주제는 날짜와 함께 여기 아래에 append. 정리되면 §3로 승격.

- 2026-05-16 — 문서 신설. §3.1(uncensored)을 `uncensored/GROWTH.md`에서 승격·이관.

## 7. 출처 (2026-05-16 web-research)

- [State of Open Source on Hugging Face: Spring 2026](https://huggingface.co/blog/huggingface/state-of-os-hf-spring-2026)
- [r/LocalLLaMA — a year in review](https://gist.github.com/av/5e4820a48210600a458deee0f3385d4f) · [Local LLM Reddit 가이드](https://www.aitooldiscovery.com/guides/local-llm-reddit)
- [Show HN vs Product Hunt 런치 교훈](https://medium.com/@baristaGeek/lessons-launching-a-developer-tool-on-hacker-news-vs-product-hunt-and-other-channels-27be8784338b) · [Product Hunt Launch Playbook 2026](https://dev.to/iris1031/product-hunt-launch-playbook-the-definitive-guide-30x-1-winner-48g5)
- [GitHub Star Growth: 9 Levers (2026)](https://dev.to/iris1031/github-star-growth-9-levers-that-compound-in-2026-15d) · [0→10K star 7가지 패턴](https://dev.to/0012303/i-analyzed-50-github-repos-that-went-from-0-to-10k-stars-here-are-the-7-patterns-54o1)
- [Use Ollama with any GGUF Model on HF Hub](https://huggingface.co/docs/hub/en/ollama)
