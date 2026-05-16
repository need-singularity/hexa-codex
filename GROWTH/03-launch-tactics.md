# 03 — 오픈소스 출시·성장 전술

개발자 도구·라이브러리·파일 포맷·리포의 출시·채택 전술. 적용 자산: wilson,
n6/hxc/n12/tape, hexa-codex. 리서치 2026-05-16. `[사실]`=출처/실측 / `[추측]`=사례 기반.

## 1. 출시는 버스트가 아니라 웨이브

- `[사실]` 0→10K 스타 리포 50개 분석 — **87%가 HN 먼저** 출시 후 Reddit·X 교차.
- **3-웨이브 모델:**
  - **웨이브 0 (사전)** — 공개 전 네트워크에서 스타 100~200 확보. `[추측]` 스타 0
    README는 방문자 전환 ~5%에 그침.
  - **웨이브 1 (출시)** — HN Show HN + Reddit. **푸시당 메인 1 + 보조 1**만, 동시 살포 금지.
  - **웨이브 2 (후속)** — 포스트모템·비교글·튜토리얼로 스파이크를 검색 트래픽으로 전환.
- `[추측]` 성장 곡선 비선형 — 1~2개월 ~50스타(지인), 5~6개월 ~1,000(HN 진입 시),
  9~10개월 ~10,000.

## 2. Hacker News "Show HN" 플레이북

- **타이밍** `[사실+추측]` — 무난: 화~목 08~10시 EST. 니치: 일요일 밤 PST(경쟁 ~40%↓).
  금요일 오후·월요일 새벽 회피.
- **알고리즘** `[사실]` — 프론트페이지 30슬롯, 하루 300~400 신규. 점수 감쇠 ~45분 주기
  → **초기 속도가 결정적**. "90분 룰"은 첫 30~90분 모멘텀 확보가 핵심이라는 통념.
- `[추측]` 프론트 진입 임계 — 첫 30분 내 진짜 업보트 8~10 + 사려깊은 댓글 2~3.
- **제목** `[사실]` — 45~65자(모바일 풀 표시). 숫자·결과 앞세움. 클릭베이트 회피.
  **제목 다중 수정 금지**(타임스탬프 리셋).
- **Show HN 요건** `[사실]` — 실제로 시도 가능한 것(라이브 데모·리포)일 때만.
  페이월·이메일 게이트 = 즉시 매장. 공개 업보트 요청·투표 서클·유료 업보트 = 도메인 영구밴.

## 3. 채널 ROI — HN vs Product Hunt vs Reddit

`[실측]` 한 개발자 도구 출시 사례:

| 채널 | 순위 | 방문 | 설치 | 스타 |
|---|---|---|---|---|
| Hacker News | #2 (107점) | 61 | 100+ | 50+ |
| Product Hunt | #14 (193표) | 243 | 30 | 10 |

- PH가 트래픽 4배지만 HN이 **설치·스타 등 고품질 전환**에서 압도.
- **자산 매칭** — HN=기술 깊이·CLI·라이브러리·포맷 / PH=시각적·소비자형 / Reddit=진성
  개발자(가차없음) / dev.to=`[추측]` CLI 마케팅 최고 ROI.

## 4. Product Hunt 2026 위상

- `[추측]` PH는 VC·PR-backed 스타트업 위주로 알고리즘이 기울어 그래스루츠 디스커버리
  위상 약화. 인디 도구는 PH 단독 의존 금물. 대안 — **DevHunt.org**(개발자 도구 전용),
  BetaList, Indie Hackers, Microlaunch. PH 사용 시 12:01 PST 게시 + 즉시 인게이지.

## 5. GitHub 스타 — README 7초 룰

- README가 7초 안에 리포를 판다. 권장 구조: ① 한 줄 포지셔닝(문제 서술, 기술용어 아님)
  → ② GIF/스크린샷 → ③ 한 줄 설치 → ④ 유스케이스 3불릿 → ⑤ 소셜 프루프.
- **복합 레버** — 어바브더폴드 5초 내 "무엇·누구·왜 다른가·다음 클릭" 답 / **이슈
  24시간 응대**(인지 확인만으로도) / 활성 신호(최근 커밋·changelog·로드맵) / "X but
  without Y" 포지셔닝 / 스타 속도(주당)가 트렌딩 알고리즘 주 지표.

## 6. awesome-* 리스트 등재

- `[사실]` awesome 리스트는 GitHub 검색·Google 양쪽 상위 노출, 도메인 권위 높음.
  `[추측]` 등재 효과 **월 50~200 스타 유입** — 작지만 영구·복리.
- 절차 — 카테고리 매칭 리스트 탐색 → CONTRIBUTING 기준 충족 → PR → 1~3주 리뷰.

## 7. 채택 마찰 줄이기 — 한 줄 설치

- `[추측]` 성공 리포 95%가 단일 명령 설치, 5분 내 시도 가능. 브라우저 데모
  (StackBlitz/CodeSandbox)는 전환 2배.
- **레지스트리 매칭** — npm+Homebrew 동시 제공 시 개발자는 brew 선호 → CLI는
  Homebrew formula 우선(bottle로 빠른 설치). Cargo=Rust CLI / npm=JS / PyPI=AI 유틸.
- **HF 모델 특수** — "한 줄 설치"는 카드 상단 복붙 `transformers`/`pipeline` 스니펫 +
  명확한 라이선스·태그 + 토이 노트북.

## 8. 스파이크 → 에버그린 전환

- 출시 1~2주에 **30~50개 디렉토리 제출**(DevHunt·AlternativeTo 등) — 백링크 복리.
- 반응을 **위닝 앵글당 SEO 글 1편**으로(how-to·비교·티어다운·포스트모템).
- `[사실]` 2026 변화 — LLM·AI 검색이 디스커버리를 바꿔, 백링크보다 **다양한
  플랫폼의 긍정적 브랜드 멘션**이 중요. 개발자 도구 디스커버리의 52%가 비추적 채널.

## 9. Discord

- `[사실]` Discord 활성 사용자 30%+가 1개 이상 기술 서버 소속. Discord는 출시 채널이
  아니라 **출시 후 잔존·피드백 루프** 자산 — 사전 개설, docs에 초대 링크, 채널 단순화
  (#help #showcase #announcements), 메인테이너 빠른 응답.

## 실행 체크리스트

- [ ] 공개 전 네트워크에서 스타 100~200 확보
- [ ] README: 1줄 포지셔닝 → GIF → 한 줄 설치 → 유스케이스 3 → 소셜 프루프
- [ ] 한 줄 설치 + Homebrew formula(CLI면) / 적절한 레지스트리 게시
- [ ] Show HN: 화~목 08~10 EST, 45~65자 제목, 라이브 데모, 페이월·제목수정 금지
- [ ] 첫 12시간 모든 댓글·이슈 응대
- [ ] 출시 후 awesome-* PR + 30~50 디렉토리 제출
- [ ] 위닝 앵글마다 SEO 글 1편 + 1분 영상
- [ ] dev.to·Reddit 크로스포스트(메인 1 + 보조 1)
- [ ] Discord 사전 개설, docs에 링크

> **주의** — 임계치 수치(8~10 업보트, 월 50~200 스타, 5%/95% 전환)·성장 곡선은
> 블로그·사례 기반 `[추측]`. 알고리즘 메커니즘(45분 감쇠, 30슬롯, 페이월 매장)과
> 채널 비교 실측치는 `[사실/실측]`.

## 출처

- [How to Get on the Front Page of Hacker News in 2025 — Flowjam](https://www.flowjam.com/blog/how-to-get-on-the-front-page-of-hacker-news-in-2025-the-complete-up-to-date-playbook)
- [The best time to post on Hacker News — alcazarsec](https://blog.alcazarsec.com/tech/posts/best-time-to-post-on-hacker-news)
- [I Analyzed 50 GitHub Repos: 0 to 10K Stars — 7 Patterns](https://dev.to/0012303/i-analyzed-50-github-repos-that-went-from-0-to-10k-stars-here-are-the-7-patterns-54o1)
- [GitHub Star Growth: 9 Levers That Compound in 2026](https://dev.to/iris1031/github-star-growth-9-levers-that-compound-in-2026-15d)
- [Top Product Hunt Alternatives 2026 — GrayGrids](https://graygrids.com/blog/product-hunt-alternatives)
- [Building an Awesome List That Actually Gets Stars](https://dev.to/glue_admin_3465093919ac6b/building-an-awesome-list-that-actually-gets-stars-step-by-step-g6f)
- [Lessons launching a dev tool on HN vs Product Hunt — Medium](https://medium.com/@baristaGeek/lessons-launching-a-developer-tool-on-hacker-news-vs-product-hunt-and-other-channels-27be8784338b)
- [How to Promote an Open Source Project — daily.dev](https://business.daily.dev/resources/promote-open-source-project-proven-channels/)
- [Distributing CLI Tools via npm and Homebrew — Medium](https://medium.com/@sohail_saifi/distributing-cli-tools-via-npm-and-homebrew-getting-your-tool-into-users-hands-111a3cea4946)
- [AEO/GEO for Dev Tools: Win AI Search in 2026 — Draft.dev](https://draft.dev/learn/aeo-geo-for-dev-tools)
