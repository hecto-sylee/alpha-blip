# 03 · 모션 스펙 — CSS + Motion One

> 듀오링고풍의 "통통 튀는" 감각은 **(1) CSS 입체 버튼/마이크로인터랙션**(가볍고 항상)과
> **(2) Motion One 기반 스프링 전환/스태거/축하**(JS, 의도된 순간)로 구현한다.
> Lottie 마스코트는 이번 범위 밖(추후 옵션). **`prefers-reduced-motion` 전면 존중.**

---

## 1. 라이브러리 선택 근거
- 프로젝트는 **빌드 없는 ESM** SPA. 따라서 **Motion One**을 ESM import로만 추가(빌드 체인 0).
  - React/Tailwind용 Magic UI·Animata는 도입하지 않음(빌드 필요, 철학 충돌).
  - GSAP/Lottie는 보류(현 범위는 Motion One + CSS로 충분).

## 2. 도입 방식 (`js/motion.js` 신설)

`app.js`가 `type="module"`이므로 ESM으로 직접 import.

```js
// motion.js — Motion One 래퍼 (+ reduced-motion 가드)
import { animate, stagger, inView } from "https://cdn.jsdelivr.net/npm/motion@11/+esm";
import { reducedMotion } from "./ui.js";

const SPRING = { type: "spring", stiffness: 520, damping: 30 }; // 쫄깃한 기본 스프링
const SOFT   = { type: "spring", stiffness: 380, damping: 34 };

export function springIn(el, { y = 12, scale = 0.98, delay = 0 } = {}) {
  if (reducedMotion()) { el.style.opacity = 1; return; }
  el.style.opacity = 1;
  return animate(el,
    { transform: [`translateY(${y}px) scale(${scale})`, "translateY(0px) scale(1)"] },
    { ...SPRING, delay });
}

export function staggerIn(els, { y = 14, each = 0.05 } = {}) {
  if (reducedMotion()) { els.forEach(e => (e.style.opacity = 1)); return; }
  els.forEach(e => (e.style.opacity = 1));
  return animate(els,
    { transform: [`translateY(${y}px)`, "translateY(0px)"] },
    { ...SOFT, delay: stagger(each) });
}

export function sheetUp(el) {
  if (reducedMotion()) { el.style.transform = "none"; return; }
  return animate(el, { transform: ["translateY(110%)", "translateY(0px)"] }, SPRING);
}

export { animate, inView, SPRING, SOFT };
```

> 핀 버전(`motion@11`)으로 고정. 오프라인/CDN 차단 시를 대비해 import 실패해도 화면은
> 동작하도록 방어한다. 화면/카드는 **처음부터 `opacity:1`로 표시**하고 transform만 스프링 처리한다.
> Motion 완료 후에는 `opacity:1`, `transform:none`으로 정리해 브라우저가 `"none"` keyframe을 `scale(0)`으로
> 보간하거나 첫 진입 순간 본문이 사라져 보이는 회귀를 막는다.

## 3. `ui.js` 훅인 지점

| 헬퍼 | 현재 | 변경 |
|---|---|---|
| `mount(node)` | CSS `screen-in` 애니메이션(`.screen`) | Motion `springIn`으로 전환 + 화면 내 카드 리스트 `staggerIn`(선택) |
| `bottomSheet()` | CSS `translateY(110%)→0` | `sheetUp()` 스프링(또는 CSS 유지 + 토큰만 강화) |
| `celebrate()` | 이모지 컨페티(Web Animations) | **마스코트 팝(스케일 버스트) + 컨페티 스프링** 업그레이드 |
| `toast()` | CSS 스프링/셰이크 | 유지 |
| `setTab()` | CSS 아이콘 통통 | 유지(+ active 펄 등장) |

> `ui.js`가 `motion.js`를 import해도 되고, 각 screen이 직접 import해도 됨. **순환 import 주의**
> (`motion.js`는 `ui.js`의 `reducedMotion`만 가져옴 — 단방향 유지).

## 4. CSS 마이크로인터랙션 (항상, 라이브러리 불필요)
- 버튼/CTA `:active` 눌림(01 디자인 시스템 5-1).
- `.card.tappable:active` 살짝 눌림.
- 탭 아이콘 active 통통(`transform: translateY(-2px) scale(1.12)`), active 펄 페이드.
- 스피너/토스트/셰이크 키프레임 유지.

## 5. 순간별 모션 표 (목적형)

| 순간 | 모션 | 구현 | 햅틱 |
|---|---|---|---|
| 화면 진입 | springIn(+자식 stagger) | `mount`/`staggerIn` | — |
| 산책 시작 | 버튼 눌림 → 지도 전환 | CSS + 라우팅 | 가벼움 |
| 마커 탭 | 바텀시트 스프링 업 | `sheetUp` | 가벼움 |
| 같이 산책 요청 | 버튼 눌림 + 전송 펄스 | CSS | 미디엄 |
| **매칭 성사** | 풀스크린 축하(마스코트 팝+컨페티) | `celebrate` | 성공 |
| 요청 거절/만료 | 부드러운 페이드 다운 | CSS | — |
| 기록 저장 | 카드가 캘린더로 안착(스프링) | Motion `animate` | 성공 |
| 스탯 증가 | 숫자 카운트업 + 셰이프 채워짐 | JS 카운트업 | 가벼움 |
| **방 새 로그** | 피드 상단 슬라이드 인 / 리스트 stagger | `staggerIn` | 가벼움 |
| 퀘스트 후보 노출 | 카드 stagger 등장 | `staggerIn` | — |

## 6. 접근성 (`prefers-reduced-motion`)
- `motion.js`의 모든 함수가 `reducedMotion()` 가드로 transform 모션 제거(즉시 표시).
- CSS도 `@media (prefers-reduced-motion: reduce)`로 입체 그림자는 남기되 transform/keyframe 축소.
- 축하 모션(`celebrate`)은 reduced 시 **실행 안 함**(기존 동작 유지).

## 7. DoD 체크 (R2)
- [ ] `motion.js` ESM import 성공, 콘솔 에러 0.
- [ ] 화면 전환·바텀시트·방 피드 stagger·매칭 축하 동작 확인(스크린샷/영상 프레임).
- [ ] `prefers-reduced-motion: reduce` 컨텍스트에서 모션 축소되고 기능 정상(스모크 1회 reduced 모드 통과).
- [ ] CDN 차단 시에도 화면 깨지지 않음(fallback).
