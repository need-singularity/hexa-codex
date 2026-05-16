# GROWTH — `dancinlab/uncensored` 채택 전략

공개 컬렉션 `dancinlab/uncensored`를 다운로드·좋아요·재배포가 도는 리포로
키우기 위한 아이디어 뱅크. 합법적·정직한 채택 전술만 — 가짜 다운로드/봇/
과장 벤치는 `안티패턴`에 격리.

## 현재 상태 (2026-05-16 · 시작점)

- 컬렉션: `dancinlab/uncensored` (public) — 항목 **1개**
- `supergemma4-e4b-abliterated-Q4_K_M-GGUF` — public · **다운로드 0 · 좋아요 0**
- 양자화 **1종**(Q4_K_M)만 · 데모 없음 · 외부 노출 0

비교 기준점: 원본 패밀리 `supergemma4-26b-uncensored-gguf-v2`는 280k DL.
즉 수요는 존재 — 노출·완성도·차별화가 레버.

---

## 30일 우선순위 래더

깨지면 안 되는 것 → 빠른 효과 → 큰 베팅 순. 위에서부터.

| 단계 | 작업 | 근거 |
|---|---|---|
| 0 | **Gemma 라이선스·use policy 카드 동봉 검증** | 누락 시 takedown — 바이럴 전에 죽음 (#H1) |
| 0 | **채팅 템플릿/Jinja GGUF 메타데이터 정합성 검증** | 템플릿 깨지면 첫 리뷰가 악평 → 안티바이럴 (#A14) |
| 1 | **양자화 래더 출하** Q2_K·Q3_K_M·Q4_K_M·Q5_K_M·Q6_K·Q8_0 | 파일별 DL 누적 + VRAM 티어별 채택 (#A1) |
| 1 | **모델 카드 상단 복붙 quickstart** (ollama/llama.cpp/LM Studio) | 마찰 = 다운로드 누수 (#B14) |
| 1 | **Ollama 라이브러리 등재** + Modelfile | 자체 디스커버리 + `ollama run` 한 줄 = 최저 마찰 훅 (#C21) |
| 2 | **벤치 수치 카드 등재** (거부율 전/후 · MMLU·IFEval) | 능력 보존 증명 — 스크린샷되는 숫자 (#B12) |
| 2 | **r/LocalLLaMA 릴리스 포스트** (quant 표 + 정직한 트레이드오프) | 로컬 모델 최대 바이럴 채널 (#C23) |
| 2 | **HF Space 채팅 데모** (ZeroGPU/CPU) | 다운로드 전 체험 + Spaces 트렌딩 (#E39) |
| 3 | **작동하는 MLX 빌드** (커뮤니티판은 깨짐 → 빈틈) | "유일하게 로드되는 MLX" 차별화 (#A3/#D34) |
| 3 | **imatrix/IQ 양자화** IQ2_XXS…IQ4_XS | llama.cpp 헤비유저층 흡수 (#A2) |
| 3 | **UGI 리더보드 등재** | 패시브 디스커버리 (#C32) |
| 4 | **블로그/메서드 글 + 한국 채널 노출** | 백링크 + 미개척 한국 커뮤니티 (#F42/#C30) |

---

## 아이디어 뱅크

### A. 아티팩트 — 무엇을 출하하나

1. **양자화 풀 래더** — 현재 Q4_K_M 1종뿐. Q2_K~Q8_0 + f16. 파일별 DL 누적,
   유저는 VRAM 티어로 고름. 원본 26b-gguf 280k DL의 핵심 동인.
2. **imatrix / IQ 양자화** — IQ2_XXS…IQ4_XS. importance-matrix 양자화는
   SOTA로 인식 → llama.cpp 헤비유저층 흡수. 캘리브레이션 셋 공개.
3. **작동하는 MLX 빌드** — 커뮤니티 MLX판은 미공개 transformers로 변환돼
   "Missing 963 parameters". *제대로 로드되는* MLX 4bit/8bit = 빈틈 = 차별화.
4. **Ollama 네이티브** — `ollama.com/dancinlab/...` 등재 + Modelfile(기본 샘플러 튜닝).
5. **multimodal + mmproj** — 비전 프로젝터 동봉해 llama.cpp 비전 동작.
   "uncensored 멀티모달 로컬 모델"은 희귀 조합 = 공유성 높음.
6. **EXL2 / AWQ / GPTQ** — vLLM·exllama·TabbyAPI 서버 유저층.
7. **WebLLM/wllama 빌드** — 브라우저 인-브라우저 실행 → 설치 0, 극강 공유성.
8. **31B 변종** — 제외했던 확장판. "가장 큰 uncensored Gemma‑4" 헤드라인.
9. **GGUF split** — 거대 파일(>48GB)은 분할해 다운로드 가능하게.
10. **샘플러 프리셋 파일** — SillyTavern·Kobold용 `.json` 프리셋 동봉.

### B. 모델 카드 / HF SEO

11. **base_model 링크 유지** — 이미 설정됨. Gemma‑4 베이스 페이지의
    "quantizations" 패널에 노출 = 공짜 트래픽.
12. **벤치 수치** — UGI(Uncensored General Intelligence) 점수, 거부율 전/후,
    MMLU·IFEval로 abliteration이 능력 안 깎았음 증명. 숫자는 스크린샷된다.
13. **비교표** — 베이스 대비·타 abliterated Gemma 대비. "능력 손실 최소" 주장(사실일 때만).
14. **상단 복붙 quickstart** — `ollama run …`, `llama-server -hf … --jinja`,
    LM Studio 검색어. 마찰이 다운로드를 죽인다.
15. **예시 트랜스크립트** — 모델 성격을 보이되 *방어 가능한* 엣지 예시만
    (보안·픽션·의료정보 뉘앙스). 실제 유해 출력 금지(#H3).
16. **언어 태그 확장** — 현재 `en`만. 다국어면 `ko` 등 추가 — 한국 uncensored
    수요는 미개척.
17. **카드 changelog** — 버전드. 유지보수 신호 = 신뢰.
18. **출처·메서드 정직 표기** — Jiunsong·Google 베이스·abliteration 기법 명시.
    신뢰가 좋아요를 만든다.
19. **다운로드/좋아요 배지** + 검색 자석어("Uncensored Gemma 4")를 리포 표시명에.
20. **README H1·태그에 핵심 검색어** — abliterated·no-refusal·local·roleplay.

### C. 배포 채널 (HF 밖)

21. **Ollama 라이브러리** — 자체 디스커버리 + 거대 유저베이스. `ollama run` 한 줄.
22. **LM Studio** — HF GGUF 자동 인덱싱. 리포 구조 맞추고 Discord에 제보.
23. **r/LocalLLaMA** — 로컬 모델 최대 바이럴 채널. 벤치+quant표+정직한 트레이드오프
    릴리스 포스트, 댓글 응대. 타이밍 잡기.
24. **r/SillyTavernAI · 롤플레이 커뮤니티** — uncensored 모델의 실사용 최대층.
    SillyTavern 프리셋·샘플러 설정 제공.
25. **양자화 아카운트 공조** — bartowski·mradermacher 등이 quant하면 정당성 신호.
    선제적으로 동급 품질 quant를 직접 내거나 제보.
26. **X/Twitter** — 로컬-LLM 계정. quant표 + 강렬한 데모 스레드.
27. **Discord** — KoboldAI·SillyTavern·llama.cpp·local-llama 서버.
28. **HF Posts** — HF 네이티브 소셜 피드에 릴리스 포스트.
29. **YouTube/쇼츠** — "1줄로 로컬 무검열 AI" 튜토리얼. 크리에이터가 좋아함.
30. **한국 채널** — GeekNews·클리앙·아카라이브 AI채널·DCInside AI갤. 미개척·고전환.
31. **awesome-list PR** — awesome-uncensored-llms·awesome-local-llm GitHub 리스트.
32. **리더보드** — UGI 리더보드·abliterated 트래커 등재 = 패시브 디스커버리.

### D. 차별화 — "왜 이거냐"

33. **능력 손실 최소 abliteration** — 변환이 성능 더 보존하면 그게 헤드라인.
34. **유일하게 로드되는 MLX** — 커뮤니티판 깨짐 → "actually loads".
35. **어디서든 1커맨드** — ollama·llama.cpp·LM Studio·MLX 전부 문서화.
36. **uncensored 멀티모달** — 희귀.
37. **노트북에서 도는 무검열 AI** — e4b 5GB는 16GB 맥/8GB GPU. 강한 바이럴 프레이밍.
38. **속도 수치** — M-시리즈·3060 등에서 tok/s 공개.

### E. 데모 / 인터랙티브

39. **HF Space 채팅 데모** — ZeroGPU/CPU. 다운로드 전 체험 + Spaces 트렌딩 페이지.
40. **인-브라우저 try** — WebLLM/wllama. 설치 0, 극강 공유성.
41. **무료 호스팅 엔드포인트** — 레이트리밋된 즉시 체험 API.

### F. 콘텐츠 / 내러티브

42. **메서드 블로그** — "Gemma‑4를 abliterate해서 전 포맷으로 출하한 법". 백링크 모음.
43. **정직한 안전 섹션** — abliteration이 하는 일 + 책임있는 사용 노트.
    신뢰 + 백래시/takedown 리스크 완화.
44. **기억되는 모델명** — slug보다 브랜드. `dancinlab/uncensored` 아래 서브브랜드.
45. **릴리스 노트 시리즈** — 버전마다 짧은 글, "활발히 유지보수" 신호.

### G. 컬렉션 · org 정비

46. **컬렉션 설명·썸네일** — 현재 항목 1개. 모든 포맷을 한 컬렉션에 모아 원스톱 허브.
47. **포맷 분산 금지** — 한 컬렉션, 명확한 네이밍.
48. **org 페이지 정비** — `dancinlab` 아바타·설명·컬렉션 핀.
49. **상호 링크** — 각 리포 카드 → 컬렉션, 컬렉션 → quickstart.
50. **베이스 작가 태깅** — Jiunsong 크레딧 = 호의 + 그의 팔로워 노출.
51. **Discussion 탭 빠른 응대** — 응대 활발한 리포가 랭킹 잘 받음.
52. **업데이트 케이던스** — 베이스 갱신 시 재quant, 트렌딩 유지.

---

## 측정 지표

- 1차: 컬렉션 합산 다운로드(파일별), 좋아요, Discussion 활동.
- 2차: 외부 유입 — r/LocalLLaMA 업보트, Space 방문, Ollama pull 수.
- 선행: 양자화 종수, 채널 노출 수, 카드 완성도(벤치·quickstart 유무).
- 리뷰: 주 1회 — 어느 채널·포맷이 DL을 끌었는지 → 다음 주 배분.

## 안티패턴 — 하지 말 것 (바이럴을 죽이는 것)

- **H1. Gemma 라이선스 누락** — 재배포 시 Gemma Terms·use policy 동봉 필수.
  누락 = 가장 빠른 takedown 경로. 바이럴 이전에 생존 조건.
- **H2. 가짜 다운로드/봇** — HF가 탐지 → 랭킹 박탈 + 평판 파탄.
- **H3. 유해 예시 출력 호스팅** — 플랫폼 제재 유발. 데모는 엣지하되 방어 가능선.
- **H4. 벤치 과장** — 스크린샷으로 검증당함, 역효과. 재현 가능한 수치만.
- **H5. 컬렉션 분산** — 포맷별로 흩어놓으면 디스커버리·DL 카운트 희석.
- **H6. lattice-fit 외부 주장** — 외부 엔티티(HF·Google·커뮤니티)에 n=6 격자
  파생 규칙 적용 금지 (`AGENTS.tape` `@F f1`). 그들의 고유 지표만 인용.
