# 02 — GGUF 양자화 래더 + 로컬 LLM 배포

GGUF 모델을 로컬 LLM 사용자층에 최대로 퍼뜨리는 법. 적용 자산:
`dancinlab/supergemma4-e4b-abliterated-Q4_K_M-GGUF` 및 후속 GGUF.
리서치 2026-05-16. `[사실]`=출처 확인 / `[추측]`=추론.

## 1. Q4_K_M 1종은 최소치다

- `[사실]` bartowski 표준 GGUF 레포는 **단일 레포에 2~32bit 25종 변형**을 출하.
- 채널·하드웨어·취향마다 사용자가 갈리므로 단일 양자화는 다운로드 깔때기 최상단을 막는 셈.
- `[사실]` HF는 `.gguf` 파일별로 다운로드를 따로 집계(`01` §3) → 변형 수 = 노출 표면적.

## 2. K-quant 구조와 BPW

- `[사실]` K-quant는 **super-block 구조** — 블록 내 텐서 중요도별 비트폭 차등 할당.
  이름의 숫자보다 실제 BPW(bits-per-weight)가 높다:

| 양자화 | BPW | 메모 |
|---|---|---|
| Q2_K | ≈2.6 | 일관성 붕괴 위험, 비상용 |
| Q3_K_M | ≈3.3 | |
| **Q4_K_M** | ≈4.8 | 주류 기본값, 다운로드 1위 변형 |
| Q5_K_M | ≈5.7 | |
| Q6_K | ≈6.6 | 품질 권장 상한 |
| Q8_0 | ≈8.5 | 사실상 무손실 |

- `[사실]` `_S`/`_M`/`_L` 접미사 = 같은 비트대에서 임베딩·출력 텐서를 더 높은 정밀도로.
  일반 가이드: **4-bit가 프로덕션 품질의 바닥선**.

## 3. imatrix와 IQ 양자화

- `[사실]` **imatrix(importance matrix)** — 캘리브레이션 코퍼스로 "어느 가중치가
  출력에 중요한가"를 기록. 양자화기가 손실 큰 곳에 정밀도 배분. **llama.cpp 공식 권고:
  Q6 미만에는 imatrix 강력 권장.**
- `[사실]` **IQ 양자화**(IQ2_XXS~IQ4_XS) — 룩업 테이블 + imatrix 재구성으로 저비트
  품질 보존. IQ2_XXS는 2.06 BPW까지. IQ4_XS는 Q4_K_M보다 공격적 압축.
- `[사실]` mradermacher 입장 — "확신 없으면 항상 weighted/imatrix 양자화를 써라 —
  같은 크기에서 더 높은 품질".

## 4. 배포자 사례

- **bartowski** — 단일 레포 25종(static+IQ 혼합), 카드에 파일별 링크·크기·품질 표 +
  RAM/VRAM 결정 트리.
- **mradermacher** — 두 레포 분리: `[model]-GGUF`(static)와 `[model]-i1-GGUF`(imatrix).
- `[추측·강근거]` 풀 래더는 다운로드를 키운다 — 8GB는 IQ3_M, 24GB는 Q6_K, ARM은
  Q4_0류를 받는다. 각 변형이 별도 검색·필터·드롭다운에 노출.

## 5. Ollama — HF 직접 풀 + 라이브러리 등재

- `[사실]` HF GGUF 직접 실행:
  ```
  ollama run hf.co/{user}/{repo}
  ollama run hf.co/{user}/{repo}:Q6_K      # 변형 지정 (대소문자 무관)
  ```
  기본값 — 레포에 있으면 Q4_K_M. 채팅 템플릿은 GGUF 메타데이터에서 자동. 깨졌으면
  레포 루트에 `template`(Go 템플릿, Jinja 아님)·`system`·`params`(JSON) 파일로 보정.
- `[사실]` ollama.com 등재 — 계정·공개키 → `ollama cp` → `ollama push myuser/model`.
  큐레이션 메인 라이브러리(`ollama.com/library`)는 별개, 사용자 푸시는 `myuser/` 네임스페이스.

## 6. LM Studio

- `[사실]` 앱 내 검색이 HF 인덱싱, **HF URL 직접 붙여넣기** 가능. 모델 카드 "Use this
  model" 드롭다운에서 LM Studio 선택 시 즉시 다운로드. 변형 드롭다운에서 **하드웨어
  맞춤 변형 하이라이트**. `lms` CLI 제공. 0.4.2부터 mlx-engine 연속 배칭, MLX↔GGUF 자동전환.

## 7. llama.cpp 채팅 템플릿 함정 — 검증 필수

- `[사실]` `llama-server`는 `--jinja`로 GGUF 메타데이터의 Jinja 템플릿 활성화.
  **`--jinja` 없으면 다수 모델 출력이 깨진다.** 흔한 실패: 변환 시 템플릿 미임베드 →
  `tokenizer.chat_template` 누락(실제 Gemma-4 GGUF 사례 존재). 워크어라운드
  `--chat-template-file template.jinja --jinja`.
- **★ 실행** — Gemma-4 abliterated GGUF는 변환 후 `tokenizer.chat_template`가
  메타데이터에 실제로 들어갔는지 **검증 필수**. 깨진 템플릿은 Ollama·LM Studio·
  llama-server 전 채널에서 잘못된 출력 → 첫 리뷰가 악평(GROWTH 래더 0단계).

## 8. MLX (Apple Silicon)

- `[사실]` WWDC 2025에서 Apple이 MLX를 Apple Silicon LLM 추론 선호 프레임워크로 공식화.
  메모리 효율 강점(Qwen3-Coder-30B: GGUF 40GB 대 MLX 34.7GB, 13%↓). Ollama v0.19.0+
  는 safetensors→MLX, GGUF→llama.cpp 자동 라우팅. `mlx-community`가 수천 변환 호스팅.
- 참고 — SuperGemma4 커뮤니티 MLX판은 미공개 transformers로 변환돼 로드 실패
  ("Missing 963 params"). **작동하는 MLX 빌드 = 빈틈**(`04` 차별화 항목).

## 9. EXL2 / AWQ / GPTQ — 서버용 사용자층

- `[사실]` GGUF = CPU+GPU 추론 1위(Ollama/LM Studio/Apple Silicon 전부). EXL2 =
  NVIDIA 단일 사용자 최고속(신모델 수 주 지연). GPTQ-Marlin = vLLM 다중 서빙.
  AWQ = A100/H100 클라우드 표준.
- **실행** — 로컬 LLM 타겟이면 **GGUF 압도적 1순위**. 2순위 ROI는 MLX. EXL2/AWQ는
  별개 사용자층이라 도달 확대 우선순위 낮음.

## 10. 모델 카드 quickstart

- `[사실]` HF 체크리스트 — 양자화는 별도 레포 + `base_model` 링크. bartowski 카드가
  채택률 높은 이유 — 복붙 `huggingface-cli download` 명령, 파이썬 스니펫, 변형별 표,
  하드웨어 결정 트리.

## 실행 전술 (우선순위)

1. **풀 래더 출하** — Q2_K·Q3_K_M/L·IQ3_M·Q4_K_S/M·IQ4_XS·Q5_K_M·Q6_K·Q8_0(8~10종).
   imatrix로 생성, calibration 데이터 명시.
2. **채팅 템플릿 검증** — Gemma-4 템플릿이 GGUF 메타데이터에 임베드됐는지 확인.
   안 됐으면 재변환 + Ollama용 `template`/`params` 파일 추가.
3. **카드에 복붙 quickstart** — `ollama run hf.co/{repo}`, LM Studio 안내, 변형 표,
   RAM/VRAM 결정 트리.
4. **ollama.com 푸시** + `base_model` 메타데이터.
5. **MLX 변형 추가** (Apple Silicon 도달 — 2순위 ROI).
6. **태그·라이선스 정리** — `gguf`·`text-generation`으로 HF/Ollama/LM Studio 인덱싱 노출.

## 출처

- [GGUF Quantization Guide — Will It Run AI](https://willitrunai.com/blog/quantization-guide-gguf-explained)
- [Choosing a GGUF Model: K-Quants, I-Quants — Kaitchup](https://kaitchup.substack.com/p/choosing-a-gguf-model-k-quants-i)
- [llama.cpp quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)
- [llama.cpp imatrix README](https://github.com/ggml-org/llama.cpp/blob/master/tools/imatrix/README.md)
- [Use Ollama with any GGUF Model on HF Hub](https://huggingface.co/docs/hub/ollama)
- [Importing a Model — Ollama Docs](https://docs.ollama.com/import)
- [GGUF usage with LM Studio — HF Docs](https://huggingface.co/docs/hub/lmstudio)
- [bartowski/Meta-Llama-3.1-8B-Instruct-GGUF](https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF)
- [mradermacher: Imatrix vs regular quants](https://huggingface.co/mradermacher/model_requests/discussions/1436)
- [llama.cpp jinja 템플릿 issue #11866](https://github.com/ggml-org/llama.cpp/issues/11866)
- [Model Formats Explained: GGUF vs GPTQ vs AWQ vs EXL2](https://insiderllm.com/guides/model-formats-explained-gguf-gptq-awq-exl2/)
- [Model Release Checklist — HF Docs](https://huggingface.co/docs/hub/model-release-checklist)
