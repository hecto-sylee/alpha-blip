# docs/v2_redesign — blip v2 재설계 계획

blip 핵심 루프 재설계: **지도=홈 → (혼자/매칭) 산책 → 카메라 촬영 → 기록(영상+펫일기)**.
worktree 병렬 작업용 중앙관리 + 전체정리 + 워크패키지 스펙.

## 읽는 순서
1. [`00_orchestration.md`](00_orchestration.md) — **중앙 관리 허브(먼저 읽기)**: 불변 규칙, 라우트/탭 단일출처, 공용파일 소유권, 브랜치·머지 순서, 공통 DoD.
2. [`01_overview.md`](01_overview.md) — **전체 정리**: 상태머신, 화면별 요구(손그림5장), 신규 백엔드, 결정/가정.
3. 워크패키지 스펙 (각 = worktree 1개):

| W | 문서 | 화면/범위 | 담당 파일 |
|---|---|---|---|
| W0 | [`10_W0_foundation.md`](10_W0_foundation.md) | 탭3개·라우트선등록·스텁·공용헬퍼·삭제숨김 | index.html, app.js, ui.js, store.js, my.js |
| W1 | [`11_W1_home_map.md`](11_W1_home_map.md) | 홈 idle 지도 | screens/home_map.js |
| W2 | [`12_W2_walking.md`](12_W2_walking.md) | 산책 중 HUD | screens/walking.js |
| W3 | [`13_W3_matching.md`](13_W3_matching.md) | 산책 매칭중(발자국) | screens/matching.js |
| W4 | [`14_W4_camera.md`](14_W4_camera.md) | 가로 카메라 | screens/camera.js |
| W5 | [`15_W5_record_tab.md`](15_W5_record_tab.md) | 기록 탭 + 상대기록 API | screens/record_tab.js, matches.py, clips.py |
| W6 | [`16_W6_pet_diary.md`](16_W6_pet_diary.md) | 펫일기 BE+FE | screens/pet_diary.js, models.py, api/pet_diary.py |

## 머지 순서
**W0 먼저** → (W1·W2·W3·W4 병렬) → **W6** → **W5**(W6 rebase 후).

## 확정 결정 (2026-06-25)
삭제=프론트만 숨김 · 펫일기=신규 모델 · 상대기록=신규 API · 발자국=프론트 시뮬.

## 디자인
기존 듀오링고풍(neo-tactile) 100% 준수: [`../mvp_refactor/01_design_system.md`](../mvp_refactor/01_design_system.md).
