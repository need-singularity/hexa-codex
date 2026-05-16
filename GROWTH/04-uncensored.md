# 04 — uncensored / abliterated 모델 전략 (앵커 케이스)

`dancinlab/uncensored` 컬렉션의 채택 전략. 리서치 2026-05-16. 디스커버리 메커니즘은
`01`, GGUF 배포는 `02`, 출시 전술은 `03`과 함께 읽을 것.

## 0. 현 위치 — 정직한 진단

- 공개 컬렉션 `dancinlab/uncensored` — 항목 1개(`supergemma4-e4b-abliterated-Q4_K_M-GGUF`),
  다운로드 0. 이 모델은 `Jiunsong/supergemma4-e4b-abliterated`를 자체 GGUF 변환한 것.
- **★ 시장은 이미 포화** — `[사실]` Gemma-4 uncensored 생태계에 TrevorJS, HauhauCS,
  prithivMLmods, huihui-ai, dealignai 등 다수가 경쟁 중. huihui-ai는 신모델 출시 후
  수 시간 내 abliterated 버전을 낸다. 단순 미러/재양자화로는 묻힌다.
- **차별화 축은 둘** — (A) **배포 완성도**(풀 양자화 래더·작동 MLX·Ollama 등재로 채널
  커버리지), (B) **정량 품질**(Heretic 재abliteration으로 측정 가능한 낮은 KL).
  둘 다 없으면 출시 의미 없음.

## 1. abliteration 기법 — Heretic이 SOTA

- `[사실]` abliteration(directional ablation, Arditi 2024) — harmful/harmless 프롬프트
  활성화 차이로 **거부 방향**을 계산해 가중치 직교화. 재학습 아님 → 거의 무손실.
- `[사실]` **Heretic**(p-e-w) — Optuna TPE 최적화기로 두 목표(harmful 거부 수,
  harmless KL divergence)를 동시 최소화. 거부 방향 인덱스를 실수로 다뤄 difference-
  of-means보다 훨씬 넓은 탐색. 그 외 OBLITERATUS·abliterix(MoE expert 단위)·
  ErisForge·DECCP·FailSpy/abliterator.
- `[사실]` **Gemma 계열은 abliteration에 비교적 강건** — Qwen 2.5보다 덜 손상(mlabonne 평).

## 2. 능력 손실 — KL divergence로 증명

- `[사실]` 능력 손실은 실재. arXiv 2512.13655(4도구·16모델): 수학 추론이 가장 민감,
  Yi-1.5-9B+Heretic은 GSM8K **-26.5%**. 거부율은 표준 abliteration으로 70~80%p 하락.
- `[사실]` Gemma-3-12B-IT 비교 — 같은 3/100 거부율에서 KL이 갈린다:

| 변형 | 거부 | KL div |
|---|---|---|
| 원본 | 97/100 | 0 (기준) |
| Heretic | 3/100 | **0.16** |
| huihui-ai | 3/100 | 0.45 |
| mlabonne v2 | 3/100 | 1.04 |

- → Heretic의 능력 손상이 수동 abliteration 대비 2.8~6.5배 적다. **이게 dancinlab의
  가장 정직하고 검증 가능한 차별화 레버.**
- **실행** — 모델 카드에 **거부율 + KL + 표준 벤치(MMLU/IFEval/GSM8K) 원본 vs
  abliterated 비교표**를 직접 싣기. KL만으로 능력 보존을 대리하지 말 것.

## 3. UGI Leaderboard

- `[사실]` UGI(Uncensored General Intelligence) Leaderboard — HF Space
  `DontPlanToEnd/UGI-Leaderboard`(좋아요 ~1.76k), **1,000+ 모델** 추적.
- 측정 — **UGI**(민감 주제 지식+의향, 0~100), **W/10**(응답 의향), **NatInt**(일반
  지능), **Writing**(SFW~NSFW 문체).
- `[사실]` 디스커버리 효과 실질적 — 각 모델 옆 다운로드 아이콘이 HF 리포 직결.
  등재 = 신뢰의 증표. `[추측]` 등재 경로는 HF Space Community 탭 제출(정확 절차는
  Space 토론 확인 필요).

## 4. r/LocalLLaMA 출시 포스트

- `[사실]` 자기홍보는 전체 활동 10% 이하, 선정적 제목 금지, 직접 링크. 포스트는
  LLM 관련 필수. 가장 업보트 높은 시간대 **미국 시간 오전 3시**. Link 포스트가 인기.
  역대 DeepSeek 스레드 2,316 업보트.
- **전술** — 홍보가 아니라 **그 자체로 가치 있는 콘텐츠**(벤치 표·KL/거부율 수치·
  비교·GGUF 링크)를 본문에 담고 홍보는 부수적·명시적으로.

## 5. r/SillyTavernAI + 롤플레이 — 최대 실사용층

- `[사실]` 롤플레이 사용자가 uncensored 모델 **최대 실사용층**. r/SillyTavernAI는
  주간 메가스레드로 모델 추천 수집. 2026-04 선호 모델에 Huihui Gemma 4 31B
  Abliterated(멀티모달)가 이미 포함.
- `[사실]` 샘플러 — SillyTavern 프리셋이 temp·top-p·min-p·rep penalty·DRY를 묶음.
  표준 리소스 Virt-io·sphiratrioth666(HF 배포). "단일 마법 프리셋 없음".
- **실행** — 모델 카드에 **권장 generation parameter 명시**(mlabonne의 Gemma 3
  abliterated가 이를 함). 메가스레드 + Locally Uncensored Discord에 공유.

## 6. Gemma 라이선스 · 플랫폼 리스크

- `[사실]` Gemma Terms는 derivative에도 적용, Google에 **사용 원격 제한권** 부여.
  Gemma Prohibited Use Policy가 위험·불법·악의적 활동 조장 금지. abliterated 파생물도 구속.
- `[사실]` 2025~2026 현재 Google의 공격적 약관 집행 사례는 **확인되지 않음** — 단
  "집행 위협" 자체가 채택 억제 요인. Gemma 4는 HF에서 게이트 모델.
- **실행** — 카드에 `license: gemma` 명시, Prohibited Use Policy 링크, base model
  출처 명기.

## 7. 책임있는 배포

- 모델 카드에 **Intended Use / Limitations / Ethical Considerations** 섹션.
- **명시적 안전 섹션** — "안전 정렬이 의도적으로 약화됨 — 로컬 사적 실험용, 프로덕션
  배포 비권장"을 솔직히 기술. abliteration 도구·파라미터·KL 수치 공개로 재현성 확보.
- 신뢰가 좋아요·재배포를 만든다(`01` §6). 정직한 안전 섹션은 백래시·takedown 완화이자
  바이럴 자산.

## 8. 30일 우선순위 래더

깨지면 안 되는 것 → 빠른 효과 → 큰 베팅:

| 단계 | 작업 | 근거 |
|---|---|---|
| 0 | Gemma 라이선스·use policy 카드 동봉 검증 | 누락=takedown (§6, 안티 H1) |
| 0 | 채팅 템플릿/Jinja GGUF 메타데이터 정합성 검증 | 깨지면 전 채널 악평 (`02` §7) |
| 1 | 양자화 풀 래더 출하 Q2_K~Q8_0 + IQ (imatrix) | 파일별 DL 누적 (`02` §1·3) |
| 1 | 카드 상단 복붙 quickstart 3종 | 마찰 = 다운로드 누수 (`02` §10) |
| 1 | Ollama 라이브러리 등재 + Modelfile | 자체 디스커버리 + 최저 마찰 (`02` §5) |
| 1 | `base_model` Model Tree 링크 정합 | Gemma-4 페이지 트래픽 흡수 (`01` §5) |
| 2 | KL + 거부율 + MMLU/IFEval 비교표 카드 등재 | 정량 차별화 (§2) |
| 2 | r/LocalLLaMA 릴리스 포스트 (미국 오전 3시) | 최대 채널 (§4) |
| 2 | ZeroGPU Space 데모 | 체험 + Spaces 트렌딩 (`01` §7) |
| 2 | UGI 리더보드 등재 시도 | 패시브 디스커버리 + 신뢰 증표 (§3) |
| 3 | Heretic 재abliteration으로 낮은 KL 빌드 | 측정 가능한 품질 차별화 (§1·2) |
| 3 | 작동하는 MLX 빌드 (커뮤니티판 깨짐=빈틈) | Apple Silicon 도달 (`02` §8) |
| 4 | r/SillyTavernAI + 권장 샘플러 + 메서드 블로그 | 실사용층 + 백링크 (§5) |

## 출처

- [Heretic vs Abliterated LLMs: Refusal Rates & Benchmarks (2026)](https://aithinkerlab.com/heretic-ai-abliteration-benchmarks-2026/)
- [Comparative Analysis of LLM Abliteration Methods — arXiv 2512.13655](https://arxiv.org/html/2512.13655v1)
- [Uncensor any LLM with abliteration — mlabonne, HF blog](https://huggingface.co/blog/mlabonne/abliteration)
- [Heretic — GitHub p-e-w/heretic](https://github.com/p-e-w/heretic)
- [UGI Leaderboard — HF Space DontPlanToEnd](https://huggingface.co/spaces/DontPlanToEnd/UGI-Leaderboard)
- [UGI Leaderboard 메트릭 설명 — LLMIndex](https://llmindex.net/benchmarks/ugi-leaderboard)
- [Exploiting Leaderboards for Malicious Model Distribution — arXiv 2507.08983](https://arxiv.org/html/2507.08983v1)
- [Reddit self-promotion rules in 2026 — Redship](https://redship.io/blog/reddit-self-promotion-rules-2026)
- [r/localLlama + r/sillytavernAI preferred models — GitHub gist](https://gist.github.com/swyxio/324fc884061bf20e97a2ecbe59bae34a)
- [SillyTavern-Presets-Sphiratrioth — HuggingFace](https://huggingface.co/sphiratrioth666/SillyTavern-Presets-Sphiratrioth)
- [mlabonne/gemma-3-27b-it-abliterated — HuggingFace](https://huggingface.co/mlabonne/gemma-3-27b-it-abliterated)
- [Gemma 4 Uncensored — TrevorJS Collection](https://huggingface.co/collections/TrevorJS/gemma-4-uncensored)
- ['Open' AI model licenses carry concerning restrictions — TechCrunch](https://techcrunch.com/2025/03/14/open-ai-model-licenses-often-carry-concerning-restrictions/)
- [Gated models — HuggingFace docs](https://huggingface.co/docs/hub/en/models-gated)
