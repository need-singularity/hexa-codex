# uncensored/ — `dancinlab/uncensored` 공개 배포 허브

거부-제거(abliterated / uncensored) Gemma‑4 파생 **SuperGemma4** 모델을
HuggingFace에서 **공개 배포**하는 운영 폴더. 목표는 공개 컬렉션
`dancinlab/uncensored`의 채택(다운로드·좋아요·재배포)을 키우는 것.

> 운영 폴더 — 연구 도메인 문서 아님. `wilson --uncensored` 에이전트 연동은
> hexa 쪽이 SSOT(`~/core/wilson/uncensored/README.md`).

## 두 갈래 — 헷갈리지 말 것

| | 공개 배포 (이 폴더의 주제) | 비공개 아카이브 미러 |
|---|---|---|
| HF 컬렉션 | **`dancinlab/uncensored`** (public) | `supergemma4-private-mirror-…` (private) |
| 들어있는 것 | 자체 변환 public GGUF | Jiunsong 원본 리포 백업 미러 3개 |
| 목적 | **바이럴 · 다운로드 · 채택** | 원본 소실 대비 사내 백업 |
| 문서 | 이 `README.md` · `../GROWTH/` | `MIRROR.md` |

## 공개 컬렉션 — `dancinlab/uncensored`

- 컬렉션: `https://huggingface.co/collections/dancinlab/uncensored-6a080743e6774450ba77a427`
- 현재 항목 1개 · 다운로드 0 — **성장 시작점** (전략은 `../GROWTH/README.md` §3.1)

| 리포 | 포맷 | 용량 | 상태 |
|---|---|---|---|
| `dancinlab/supergemma4-e4b-abliterated-Q4_K_M-GGUF` | GGUF Q4_K_M | 5.34 GB | ✅ public |

- 베이스: `Jiunsong/supergemma4-e4b-abliterated` → `google/gemma-4` 계열 (e4b = 엣지 소형)
- 라이선스: `gemma` (Gemma Terms of Use — 재배포 시 동봉 필수, `GROWTH.md` 안티패턴 참조)
- 변환: ubu‑2에서 `convert_hf_to_gguf.py` → f16 → `llama-quantize` Q4_K_M
  (5.07 GiB · 5.66 BPW · gemma‑4 42L). abliteration은 가중치에 베이크 → 포맷 불변.

## 빠른 실행 (공개 GGUF)

```bash
# llama.cpp — 서버 (OpenAI 호환). 채팅 템플릿 위해 --jinja 필수
llama-server -hf dancinlab/supergemma4-e4b-abliterated-Q4_K_M-GGUF --jinja -c 8192

# llama.cpp — 단발 CLI
llama-cli   -hf dancinlab/supergemma4-e4b-abliterated-Q4_K_M-GGUF --jinja -p "안녕"

# Ollama / LM Studio — HF GGUF 리포를 직접 검색해 가져옴
ollama run hf.co/dancinlab/supergemma4-e4b-abliterated-Q4_K_M-GGUF
```

e4b는 4bit 양자화(5.3GB)라 ~6GB 메모리로 동작 — 16GB 맥 / 8GB GPU에서 OK.

## wilson 에이전트로 쓰려면

`wilson --uncensored`(약자 `-U`) 한 번이면 메인+서브 에이전트가 이 모델로 뜸.
구현·셋업은 wilson 쪽이 SSOT — bash 스크립트 없이 hexa-native:

```bash
wilson --uncensored          # = wilson -U
```

상세: `~/core/wilson/uncensored/README.md` (`wilson uncensored serve` 가
로컬 GGUF 우선 · HF fallback으로 `llama-server` 기동).

## 파일

| 파일 | 내용 |
|---|---|
| `README.md` | 이 인덱스 |
| `MIRROR.md` | 비공개 아카이브 미러 기록 (별개 트랙) |
| `../GROWTH/README.md` | 채택·성장 브레인스토밍 허브 — uncensored 전략은 §3.1 |

## 정리 이력 (2026-05-16)

- 죽은 MLX 경로 폐기 — `RUN-e4b-mlx.md` · `run_e4b.sh` · `serve_e4b.sh` 삭제.
  커뮤니티 MLX 리포는 미공개 transformers로 변환돼 어떤 런타임도 키 불일치
  ("Missing 963 parameters"). 실제 경로는 llama.cpp + GGUF.
- `WILSON.md` 폐기 — wilson 연동은 `~/core/wilson/uncensored/`가 SSOT.
- 초점 전환: 비공개 미러 런북 → **공개 컬렉션 배포 허브**.
