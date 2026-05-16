# 01 — HuggingFace Hub 트렌딩/디스커버리 메커니즘

HF에서 모델/컬렉션이 발견되고 트렌딩하는 원리. 적용 자산: `dancinlab/uncensored`
및 모든 HF 모델·데이터. 리서치 2026-05-16. `[사실]`=출처 확인 / `[추측]`=추론.

## 1. 트렌딩 알고리즘이 보는 것

- `[사실]` HF 트렌딩 정렬은 **비공개·독점**. 공식 포럼도 "publicized 안 됨"만 확인.
  공식 문서는 입력 신호만 명시 — "방문수·좋아요가 많을수록 트렌딩 상위 → 더 많은 노출".
- `[사실]` 핵심 입력 3종 — 다운로드, 좋아요, 최근성(recency). 좋아요는 최근 ~7일 윈도우.
- `[추측]` 트렌딩은 누적값이 아니라 **변화율(velocity) + 시간 감쇠**에 가깝다. 누적
  1위가 트렌딩 1위가 아니고, 무명 신규가 상위에 오르는 패턴이 근거. → **출시 후
  첫 3~7일의 좋아요 가속도**가 트렌딩 진입을 좌우.

## 2. 다운로드 집중도 — 극단적 롱테일

- `[사실]` 2026년 봄 기준 공개 모델 약 200만, 사용자 13M.
- `[사실]` **상위 200개(0.01%)가 전체 다운로드의 49.6%**. 상위 50개 엔티티가 80%+.
  **전체 모델의 약 50%는 누적 다운로드 200건 미만**.
- `[사실]` 다운로드의 92.5%가 1B 미만, 69.8%가 200M 미만 모델.
- **시사점** — 디스커버리(트렌딩·검색·Model Tree) 없이는 200건 롱테일에 묻힌다.
  작고 빠른 모델에 다운로드가 쏠림 — e4b GGUF(5GB)는 이 구간 정중앙.

## 3. GGUF 다운로드 집계 — 전술적으로 중요

- `[사실]` HF는 중복 방지로 라이브러리별 "쿼리 파일"만 카운트(기본 `config.json`).
  **GGUF는 자체완결이라 모든 `.gguf` 파일이 각각 집계** → 한 레포에 양자화 여러 종을
  올리면 파일별 다운로드가 따로 쌓인다. HTTP GET·HEAD 모두 다운로드로 집계.
- **시사점** — 풀 양자화 래더 출하는 디스커버리뿐 아니라 다운로드 카운트 자체를 키운다(`02`).

## 4. 모델 카드 SEO — 메타데이터가 검색 노출을 결정

- `[사실]` README.md 상단 YAML이 검색·필터·위젯·API를 결정. 권장 필드:
  ```yaml
  pipeline_tag: text-generation     # 작업 검색·위젯 — 틀리면 검색 누락
  library_name: gguf                # 2024-08 이후 레포는 명시 필수, 다운로드 추적 활성화
  language: [en, ko]                # /languages 페이지 노출
  license: gemma                    # 라이선스 필터
  base_model: <원본>                # ★ 최대 레버 — §5
  base_model_relation: quantized    # quantized/finetune/adapter/merge
  tags: [uncensored, abliterated, gguf, gemma, ...]   # 추가 검색 표면
  ```
- `[사실]` `arxiv:` 링크를 카드에 넣으면 자동 태그화 → "같은 논문 인용 모델" 필터 노출.
- 복붙·실행 가능한 코드 스니펫 + `notebook.ipynb`(Colab/Kaggle 버튼 자동 생성).

## 5. base_model 링크 = 트래픽 최대 단일 레버

- `[사실]` `base_model` 필드는 모델 페이지에 **Model Tree 패널**(Adapters/Finetunes/
  Quantizations/Merges)을 만든다.
- `[사실]` Model Atlas 논문(arXiv 2503.10633): **non-leaf 모델의 50%는 자손 노드
  총 다운로드가 자기 자신을 초과**. 인기 base의 Quantizations 탭에 들어가면 그 트래픽이 흘러온다.
- `[사실]` HF 공식 체크리스트 — 양자화는 **별도 레포**로 올리고 `base_model` +
  `base_model_relation`으로 링크해야 Model Tree에 표시. Space 데모는 **Hub 레포에서
  가중치를 다운로드**해야 cross-link 생성(외부 소스 금지).
- **실행** — `base_model`을 원본 Gemma-4(및 abliterated 중간 모델)에 정확히 지정 →
  2단계 트리로 양쪽 트래픽 흡수. 각 양자화는 별도 레포 + 한 Collection으로 묶기.

## 6. derivative 모델 = 바이럴 지표 겸 증폭기

- `[사실]` State of OS 2026 — Qwen 패밀리 derivative 11.3만+(태그 포함 20만+),
  구글+메타 합산 초과. 2026-04 트렌딩 1위는 커뮤니티 증류 파인튠(Jackrong).
- `[추측·근거 있음]` 누가 내 모델을 finetune/quant/merge하면 (1) 그들의 `base_model`이
  내 Model Tree를 채우고 (2) 다운로드 일부가 내게 어트리뷰션 (3) 그들 출시가 트렌딩에서
  나를 가리킨다. → **"재배포되기 쉬운 모델"(명확한 라이선스·깨끗한 카드·safetensors
  원본)을 만드는 것 자체가 바이럴 전략.**

## 7. Collections · Spaces · ZeroGPU

- `[사실]` **Collections** — 모델/데이터/Space/논문을 한 페이지로. 공개 컬렉션은
  프로필 상단 노출, 미리보기에 첫 3개. 항목별 노트 가능. 다중 변형 출시 시 공식 권장.
- `[사실]` **Spaces 데모** — 코드 없이 체험. 모델에 링크하면 모델 페이지에 데모 표시.
  **ZeroGPU** = H200 동적 할당 무료 GPU(PRO/Enterprise; PRO는 5배 쿼터). uncensored
  모델은 "한 번 돌려보려는" 호기심 트래픽이 커 ZeroGPU Space ROI가 특히 높다.

## 8. 관여 반감기 — 약 6주

- `[사실]` State of OS 2026 — 모델 평균 관여 지속 **출시 후 약 6주**. 정체 시
  점유율 이탈. DeepSeek은 V3→R1→V3.2 연속 출시로 경쟁력 유지.
- **실행** — 출시 후 첫 3~7일에 좋아요 가속 집중 → 6주 안에 v2(개선 양자화·imatrix
  추가·새 base 추적). 구버전 카드에 `new_version` 필드 → 배너로 신버전 링크.

## 9. 네이티브 소셜 채널

- `[사실]` HF 체크리스트 — "대부분의 사용자는 소셜·채팅(Slack/Discord)·뉴스레터로
  모델을 발견." 채널: **HF Posts**(플랫폼 내 피드), **HF Blog**(Enterprise 조직),
  **Community 탭**(질문 응답 — 빠른 응답이 좋아요·재방문 유도).

## 10. 실행 체크리스트

1. `base_model` + `base_model_relation: quantized`로 원본에 정확히 링크 (최대 레버).
2. 각 양자화 = 별도 레포, 전부를 한 Collection으로 묶기.
3. 메타데이터 완비 — `pipeline_tag`·`library_name: gguf`·`tags`·`language`·`license`.
4. ZeroGPU Space 데모 + 모델 페이지 링크(Hub에서 가중치 다운로드해 cross-link).
5. 출시 후 3~7일 윈도우에 HF Post + Discord/Reddit 홍보 집중 → 좋아요 가속.
6. 6주 반감기 전 v2 출시, 구버전에 `new_version`.
7. Community 탭 빠른 응답.

## 출처

- [Models Download Stats — HF Docs](https://huggingface.co/docs/hub/en/models-download-stats)
- [Model Cards — HF Docs](https://huggingface.co/docs/hub/en/model-cards)
- [Model(s) Release Checklist — HF Docs](https://huggingface.co/docs/hub/en/model-release-checklist)
- [State of Open Source on Hugging Face: Spring 2026](https://huggingface.co/blog/huggingface/state-of-os-hf-spring-2026)
- [What Factors Determine the "Trending" Sort? — HF Forums](https://discuss.huggingface.co/t/what-factors-determine-the-trending-sort-on-hugging-face-models/126813)
- [HF 2026: 2M+ Models, 80% of Downloads From Top 50](https://www.programming-helper.com/tech/hugging-face-2026-2-million-models-80-percent-downloads-python)
- [Charting Hugging Face's Model Atlas — arXiv 2503.10633](https://arxiv.org/html/2503.10633v1)
- [Anatomy of an ML Ecosystem: 2M Models — arXiv 2508.06811](https://arxiv.org/html/2508.06811v1)
- [Spaces ZeroGPU — HF Docs](https://huggingface.co/docs/hub/spaces-zerogpu)
- [Collections — HF Docs](https://huggingface.co/docs/hub/collections)
