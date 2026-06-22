# 05 · 펫 캐릭터 (마스코트)

펫마다 "고정" 캐릭터(강아지 마스코트)를 보여준다. 같은 펫이면 언제 어디서나
같은 캐릭터가 나온다. 사용자(사람) 캐릭터는 추후 작업.

## 현재 구현 (Phase 1 · 정적 SVG, 의존성 0)

- 모듈: `server/static/js/character.js`
- 적용 위치(앱 전체): `/pets` 리스트, 홈 펫 카드, 마이 프로필 헤드, 매칭(미리보기·세션 HUD·수신 배너),
  지도 마커(상대/데모/나), 방 멤버 칩·타임라인 작성자, 방 피드, 매칭 성사 축하 모션
- 데이터 없을 때 폴백: 펫 정보가 없는 자리(예: 방 멤버)는 `user_id`로 시드한 안정적 캐릭터를 보여줌
  (실제 펫 정보가 API에 실리면 자동으로 진짜 펫 캐릭터로 대체)
- 모션: idle(숨쉬기·꼬리·깜빡임)는 `app.css`의 `@keyframes`(`bp-breathe`/`bp-wag`/`bp-blink`).
  리스트에서 가볍고 `prefers-reduced-motion` 자동 대응.

### 결정적 매핑 (`petVisualParams(pet)`)

| 입력 | → | 출력 |
| --- | --- | --- |
| `pet.id` 해시(FNV-1a) | → | **색 팔레트**(8종, UI 토큰 계열) · 무늬 패치 |
| `pet.breed` (키워드 룩업) | → | **귀**(floppy/pointy/round) · **털**(smooth/fluffy/curly), 미입력이면 해시 폴백 |
| `pet.size` | → | **크기 스케일**(소 .86 / 중 1.0 / 대 1.14) |
| `pet.personality_tags` | → | **무드**(idle 속도) · **눈 모양**(round/happy/shy) · **혀** 노출 |

> 색은 견종이 아니라 `id` 해시에서 나온다 → "고정 + 펫마다 고유"가 목적이고
> 실제 모색 재현이 목적이 아니다.

### 공개 API

```js
import { petCharacterEl, mountPetCharacter, petVisualParams } from "./character.js";

petCharacterEl(pet, { size: 60 })        // el() 자식으로 넣을 캐릭터 노드
mountPetCharacter(container, pet, opts)  // 기존 컨테이너를 캐릭터로 채움 (Rive 확장 지점)
```

## Phase 2 · Rive 업그레이드 (라이브 캐릭터)

"살아있는" 인터랙티브 캐릭터(idle⇄walk⇄celebrate, 반응)는 `.riv` 아트 파일이
필요하다. 아트는 Rive 에디터(rive.app)에서 제작한다. 코드 측 연결부는 모두
준비돼 있고, 아래 계약대로 만든 `.riv`만 떨어뜨리면 켜진다.

### 런타임
- `@rive-app/canvas` 를 CDN ESM 로 지연 로드(현재 `motion.js`가 Motion One을
  로드하는 방식과 동일). CDN 실패 / reduced-motion → 정적 SVG 폴백.

### 아트 파일 계약 (`.riv`)
- 경로: `server/static/assets/characters/dog.riv`
- 아트보드: `Dog`
- 스테이트 머신: `Mascot`
- 입력(Inputs):
  - `variant` (Number 0–7) — 팔레트 인덱스(코랄/앰버/민트/버터/라벤더/스카이/로즈/모카)
  - `breed` (Number) — 귀·몸 실루엣 프리셋
  - `size` (Number 0–2) — 소/중/대
  - `mood` (Number) — idle / happy / walk
  - `celebrate` (Trigger) — 매칭 성공 등
  - `tap` (Trigger) — 탭 반응

### 연결부 (`mountPetCharacter`)
이 함수 한 곳만 분기한다:
1. `dog.riv` 존재 & reduced-motion 아님 & 라이브 표시 위치(아래) → `<canvas>` 마운트,
   런타임 로드, `petVisualParams(pet)` → 위 입력으로 구동.
2. 그 외 → 현재 SVG(`petCharacterEl`).

### 성능 가이드 — 라이브 Rive는 "주인공" 자리에만
Rive 인스턴스 1개 = 캔버스 1개. 많이 깔면 무겁다.
- **라이브 Rive**: 프로필/펫 상세 히어로, 방 상단 히어로, 매칭 HUD (동시 ≤2)
- **정적 SVG**: 리스트 행, 멤버 칩, 지도 마커, (추후) 방 놀이터 — 그리고 항상 폴백

## Phase 3 (추후)
- 방 "놀이터": 멤버들의 강아지가 모여 노는 씬(단일 캔버스로 최적화). **AI 불필요** —
  위치 + 가벼운 wander/근접 거동.
- 진척 코스메틱: 리그 티어 → 프레임/왕관, 업적 → 액세서리.
- 사용자(사람) 캐릭터.
