# 14 · W4 — 카메라 촬영 (가로) — *이미지 2*

> 가로 전체화면 촬영. 퀘스트 진입 시 상단에 퀘스트 한 줄. 촬영→클립 업로드→출처로 복귀.
> 먼저 읽기: [`00_orchestration.md`](00_orchestration.md), [`01_overview.md §3.4`](01_overview.md).

브랜치: `feat/v2-W4-camera` ← (W0 머지 후) `feat/v2-redesign`
담당 파일: **`server/static/js/screens/camera.js`** (+ `media.js` 재사용, 필요시 소폭 보강).

---

## 1. 목표 (손그림 요구 → 구현)

| # | 요구 | 구현 |
|---|---|---|
| 1 | 가로(landscape) 촬영 | 전체화면 가로 레이아웃(`.camera-screen.landscape`), 세로기기에서도 가로 프레임 |
| 2 | 퀘스트 진입 시 상단 퀘스트 텍스트 | `?quest=` 있으면 상단 한 줄(이미지의 "얼렁뚱땅…" 위치), 없으면 미표기 |
| — | 촬영 후 출처 복귀 | 클립 업로드 → `store.addWalkClip` → `#/walk`(미종료) 복귀 |

## 2. 진입 / 파라미터
- 라우트 `#/camera`, `setTab(null)`.
- 쿼리: `?mission=<id>&quest=<제목>`(퀘스트 박스에서) 또는 없음(일반 촬영 버튼).
- 진입 출처는 항상 **산책 중**(W2). 복귀도 산책 중(미종료). (종료는 W2 통화종료 버튼이 담당하므로
  카메라에서 종료 분기는 없음 — 단순히 `#/walk`로 복귀.)

## 3. 레이아웃 (이미지 2 기준)
- 전체 검정 배경, **가로 카메라 프리뷰**(`getUserMedia` video, object-fit cover).
- 상단(가로 기준 한쪽 가장자리): `?quest`가 있으면 **퀘스트 한 줄 텍스트**. 없으면 빈 영역.
- 우상단: 닫기(X) → `#/walk` 복귀(촬영 취소).
- 하단 중앙: **촬영 버튼**(둥근 큰 버튼). 하단 보조: 타이머/전환 등은 선택(이미지의 .5/1, 플래시/전환 아이콘은 장식 수준, MVP 생략 가능).
- 디자인 시스템 입체 버튼 사용, 인라인 스타일 금지(가로 회전 등 동적 변환만 예외).

## 4. 촬영 / 업로드 (media.js 재사용)
- `openCamera()`로 스트림 확보(권한 거부 시 안내). `record(stream)` 2초 클립(기존 `CLIP_MS`).
- 업로드:
  ```
  const form = new FormData();
  form.append("file", blob, "clip.webm");
  form.append("duration_ms", String(CLIP_MS));
  form.append("order", String(store.walkClips.length));
  if (mission) form.append("mission_id", mission);
  const { clip_id } = await api.upload("/clips/upload", form);
  store.addWalkClip({ clip_id, mission_id: mission || null, order: store.walkClips.length });
  ```
- 업로드 성공 → 토스트 + `#/walk` 복귀(W2가 퀘스트 완료 갱신).
- `onLeave`에서 `stopStream` 정리(기존 패턴).

## 5. 의존성 / 주의
- 선행: **W0**(라우트, `store.walkClips`/`addWalkClip`). **W2**(클립 계약: mission_id 태깅·복귀 라우트).
- `media.js`는 공용이지만 변경 최소(가능하면 무변경, 보강 시 `/* W4 */` 주석). 다른 워커가 안 쓰는 함수만 추가.
- app.css는 `/* === W4: camera === */` 배너로 append(가로 레이아웃, 촬영 버튼, 퀘스트 한 줄).

## 6. 완료 조건 (DoD)
1. (헤드리스 fake 카메라) `#/camera?quest=테스트` 진입 → 가로 레이아웃 + 상단 퀘스트 텍스트 표시 단언, 콘솔 0.
2. `#/camera`(쿼리 없음) → 퀘스트 텍스트 **미표시** 단언.
3. 촬영 버튼 → `POST /clips/upload` 201 → `store.walkClips` 길이 증가 → `#/walk` 복귀 단언.
4. 퀘스트 진입 촬영 시 업로드 폼에 `mission_id` 포함되는지 단언.
5. before/after 스크린샷 + 로그. `scripts/fe_smoke_record.py` 촬영 부분 수정. 또는 50턴 후 중단.
