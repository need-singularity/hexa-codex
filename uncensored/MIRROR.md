# SuperGemma4 — 비공개 아카이브 미러 기록

원작자 `Jiunsong`의 SuperGemma4 패밀리를 `dancinlab` org에 **private** repo +
**private collection**으로 미러링한 기록. 원본 소실 대비 사내 백업 — 공개 배포
트랙(`README.md` · `GROWTH.md`)과는 별개.

- 미러일: 2026-05-16
- 베이스: `google/gemma-4-26B-A4B-it` (26B total · 4B active MoE)
- `uncensored` ≡ `abliterated` (둘 다 refusal-direction 제거), `-v2` = 2차 개정
- 원본 model card는 각 미러에 **변경 없이 보존**, `_MIRROR_NOTE.md`로 출처 표기
- 비공개 컬렉션: `https://huggingface.co/collections/dancinlab/supergemma4-private-mirror-6a07ce94ec41fe67b545a1c8`

> **공개 GGUF는 이 미러에 포함 안 됨.** `dancinlab/supergemma4-e4b-abliterated-Q4_K_M-GGUF`
> 는 ubu‑2에서 자체 변환한 별도 public 아티팩트 → 공개 컬렉션 `dancinlab/uncensored`.

## 변형을 만드는 4개 축

| 축 | 종류 | 의미 |
|---|---|---|
| 크기 | `e4b` / `26b` / `31b` | e4b=엣지 소형 / 26b=Gemma‑4‑26B‑A4B(메인) / 31b=확장판 |
| 포맷 | GGUF / MLX / safetensors | GGUF=llama.cpp·Ollama / MLX=Apple Silicon / safetensors=PyTorch·파인튜닝 |
| 양자화 | bf16 / 8bit / 4bit / Q4_K_M | 정밀도↕ vs 메모리↕ |
| 기능 | text-only / multimodal | uncensored=텍스트 / multimodal=비전(이미지 입력) |

## 미러 상태 (3/4 완료)

| # | repo (→ `dancinlab/<원본명>`, private) | 포맷 | 용량 | 상태 |
|---|---|---|---|---|
| 1 | `supergemma4-e4b-abliterated-mlx` | MLX 4bit | 4.3 GB | ✅ 완료 |
| 2 | `supergemma4-26b-uncensored-mlx-4bit-v2` | MLX 4bit | 14.2 GB | ✅ 완료 |
| 3 | `supergemma4-26b-uncensored-gguf-v2` | GGUF Q4_K_M | 16.8 GB | ✅ 완료 |
| 4 | `supergemma4-26b-abliterated-multimodal` | safetensors bf16 | 51.6 GB | ❌ 미완 |

> #4 미완: 미러 스크립트가 다운로드 4.4 GB / 51.6 GB 시점에 종료됨.
> 재개하려면 `python3 ~/scratch/sg4-mirror/sg4_mirror.py` (resumable·idempotent).

## 하드웨어 적합성 (통합메모리 기준)

| 모델 | 16GB | 24GB | 32GB+ |
|---|---|---|---|
| e4b (4.3G) | ✅ 권장 | ✅ | ✅ |
| 26b-mlx-4bit (14.2G) | ❌ swap | ⚠️ 빠듯 | ✅ |
| 26b-gguf Q4_K_M (16.8G) | ❌ | ⚠️ 빠듯 | ✅ |
| multimodal bf16 (51.6G) | ❌ | ❌ | 64G급 |

> MoE 주의: 총 26B·활성 4B여도 **전체 weight가 메모리 상주** → 요구량은 디스크 용량 전체 기준.

## 미러 대상에서 제외한 동일 패밀리 (참고)

- `Jiunsong/SuperGemma4-31b-abliterated-GGUF` (31B 확장판, 18.7 GB)
- `Jiunsong/supergemma4-26b-abliterated-multimodal-mlx-{4bit,8bit}`
- `Jiunsong/supergemma4-e4b-abliterated` (safetensors, 15.1 GB) / `SuperGemma4-31b-abliterated-mlx-4bit`
- 그 외 수십 개는 타 유저의 재업로드 미러

## 재현 / 운영

- 스크립트: `~/scratch/sg4-mirror/sg4_mirror.py` (resumable·idempotent)
- 로그: `~/scratch/sg4-mirror/mirror.log`
- 확인: `huggingface_hub` `list_models(author="dancinlab", search="supergemma4")`
- 각 repo `_MIRROR_NOTE.md`: 출처 + 미러일 + 비교표
