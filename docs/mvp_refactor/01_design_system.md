# 01 · 디자인 시스템 — 듀오링고풍 (neo-tactile)

> `server/static/css/app.css`를 이 스펙대로 교체한다. 핵심: **외곽 볼드 선 제거**,
> **눌리는 3D 입체 버튼/카드**, **챙키한 라운드/컬러블록**, **글래스 클래스 제거/흡수**.
> 기존 `04_ui_ux_style.md`의 "지도=글래스 / 기록=M3" 2-레이어를 **단일 통일 무드**로 대체한다.

---

## 1. 디자인 언어 한 줄

> "둥글고 통통하고 **눌러지는** UI." 모든 인터랙티브 요소는 솔리드 컬러 면 + **아래쪽 솔리드 그림자**로
> 물리적 두께(입체)를 가지며, 누르면 그림자가 줄며 내려간다(`translateY`). 얇은 테두리 선은 쓰지 않는다.

## 2. 컬러 (`:root`)

blip 코랄 아이덴티티 **유지**, 채도/명도를 듀오링고처럼 더 화사하게. 핵심은 **각 컬러롤의 `*-shadow`(어두운 변형)** 추가 — 입체 버튼의 하단 그림자 색으로 쓴다.

```
/* 브랜드 */
--primary:        #FF6B5E;   /* 코랄 (유지) */
--primary-shadow: #D94A3D;   /* 입체 하단 그림자색 (신규) */
--on-primary:     #ffffff;
--primary-soft:   #FFE2DD;   /* 연한 컨테이너 */

--secondary:        #2BC9A8;  /* 그린(채도↑) */
--secondary-shadow: #14A083;
--secondary-soft:   #C9F4EA;

--tertiary:        #FFB454;   /* 노랑 */
--tertiary-shadow: #E0921F;
--tertiary-soft:   #FFE9C7;

--success: #58CC02; --success-shadow:#46A302;   /* 듀오링고 그린 — 성공/완료 */
--danger:  #FF4B4B; --danger-shadow: #D63333;

/* 중립 — 따뜻한 화이트 베이스 */
--bg:           #FBF7F4;
--surface:      #FFFFFF;
--surface-2:    #F1ECE8;   /* 비활성/세컨더리 버튼 면 */
--surface-shadow:#E2D8D0;  /* 중립 면의 입체 하단색 */
--on-surface:   #2B2420;
--on-surface-var:#7A6F68;
/* --outline 은 폐기. 분리는 그림자/면색 대비로만. */
```

> 다크 모드는 이번 범위 밖(라이트 우선).

## 3. 입체 깊이 토큰 (신규 — 듀오링고 핵심)

```
--depth:        4px;    /* 버튼/탭/세그 기본 두께 */
--depth-cta:    6px;    /* 큰 CTA 두께 */
--press:        2px;    /* 누를 때 내려가는 양 */

/* 입체 그림자 헬퍼 (color 인자만 바꿔 사용) */
/* box-shadow: 0 var(--depth) 0 <shadow-color>, <soft ambient>; */
--ambient:      0 4px 10px rgba(43,36,32,.10);
--ambient-lg:   0 10px 24px rgba(43,36,32,.14);
```

## 4. 셰이프 / 모션 토큰 (대체로 유지, 소폭 강화)

```
--r-sm:12px; --r-md:16px; --r-lg:20px; --r-xl:28px; --r-pill:999px;

--spring:    cubic-bezier(0.34, 1.56, 0.64, 1);  /* 오버슈트(유지) */
--spring-lo: cubic-bezier(0.5, 1.25, 0.55, 1);   /* 약한 바운스 */
--ease:      cubic-bezier(0.22, 0.61, 0.36, 1);
--dur-fast:140ms; --dur:240ms; --dur-slow:420ms;
```

## 5. 컴포넌트 스펙

### 5-1. 버튼 `.btn` / 단일 CTA `.cta` — 눌리는 3D
- 솔리드 면 + `box-shadow: 0 var(--depth) 0 <role-shadow>, var(--ambient)`.
- `:active` → `transform: translateY(var(--press))` + 그림자 깊이를 `--press`만큼 축소(눌림감).
- **테두리 없음.** 라운드는 `.btn`=`--r-lg`, `.cta`=`--r-lg`(크게), pill 변형은 `--r-pill`.
- 변형: `.btn.secondary`(green soft), `.btn.ghost`(면·그림자 없음), `.btn.danger`.
- CTA는 화면당 1개, `min-height:56px`, 굵은 타이포.

```
.cta{ background:var(--primary); color:var(--on-primary);
  box-shadow:0 var(--depth-cta) 0 var(--primary-shadow), var(--ambient-lg);
  border:none; border-radius:var(--r-lg); transition:transform var(--dur-fast) var(--spring), box-shadow var(--dur-fast); }
.cta:active{ transform:translateY(calc(var(--depth-cta) - var(--press)));
  box-shadow:0 var(--press) 0 var(--primary-shadow), var(--ambient); }
```

### 5-2. 카드 `.card` — 테두리 제거 + 소프트 입체
- `background:var(--surface)`; **테두리 삭제**; `box-shadow: 0 2px 0 var(--surface-shadow), var(--ambient)`; `border-radius:var(--r-lg)`.
- `.card.tappable:active{ transform:translateY(2px) scale(.995); }` (살짝 눌림).

### 5-3. 입력 `.input`/`.select`/`textarea` — 채움+입체
- 얇은 테두리 → `background:var(--surface)`; `box-shadow: inset 0 0 0 2px var(--surface-2)`(면 대비로 경계);
  `:focus` → `box-shadow: inset 0 0 0 2px var(--primary)`. **outline 선 금지.**

### 5-4. 세그먼트 `.seg .opt` / 태그 `.tags .tag` — 칩형 3D
- 미선택: `--surface-2` 면 + 얕은 입체. 선택: 컬러 soft 면 + 해당 role 그림자색 입체 + 텍스트 진하게.
- 테두리 없음. 선택 시 `transform`으로 살짝 팝.

### 5-5. 칩/배지 `.chip`/`.badge` — pill 챙키
- `--r-pill`, 솔리드 soft 면, 작은 입체 또는 평면. on 상태는 컬러 soft.

### 5-6. ~~글래스~~ → 챙키 카드 (통일)
- 신규 마크업에서는 `.glass`/`.glass-edge`를 쓰지 않고 `.card`, `.sheet`, 화면 전용 클래스에 흡수한다.
  기존 잔재가 생기면 **불투명 화이트 면 + 입체 그림자**로 대체하고 블러/반투명은 제거한다.
- `.sheet`(바텀시트): 화이트 면 + 상단 큰 라운드(`--r-xl`) + `var(--ambient-lg)`, 스프링 업(모션 스펙 참조).
  스크림은 유지(`rgba(20,16,30,.34)`).
- **지도 마커 `.dog-marker`**: 글래스 칩 → **화이트 입체 핀**(둥근 흰 카드 + role 그림자색 하단 입체 + 사진/이모지).
  내 위치 마커도 입체 도트 유지.

### 5-7. 탭바 `.tabbar` — 4탭 + 챙키 active
- `border-top` 선 **제거**, `background:var(--surface)` + 상단 `var(--ambient)`(떠 있는 느낌).
- 4개 항목 균등(`flex:1`). active: 아이콘 뒤 **챙키 펄(컬러 soft pill)** + `color:var(--primary)` + 아이콘 통통 모션.
- IA/탭 목록은 `02_information_architecture.md` 참조.

### 5-8. 토스트/스피너/빈 상태
- 토스트: 유지(스프링 인/아웃, err 셰이크). `--r-md`.
- 빈 상태 `.empty`: 큰 이모지 + 다음 행동 CTA + 가벼운 모션(모션 스펙).

## 6. 타이포 / 접근성
- 폰트: **Pretendard 헤비 웨이트**로 챙키하게(의존성 0 유지). 헤딩 `800~900`, 본문 `500~600`.
  (둥근 헤딩 폰트 Nunito CDN은 선택지로 열어두되 기본은 미도입.)
- 터치 타깃 ≥ 44px, 모바일 세로 우선, 대비 WCAG AA.
- 모든 입체/모션은 `prefers-reduced-motion`에서 그림자만 남기고 transform 모션 축소(모션 스펙).

## 7. DoD 체크 (R0)
- [ ] `app.css`에 `grep "1px solid var(--outline)"`/`1.5px solid` 결과 0 (테두리 선 제거).
- [ ] 버튼/CTA `:active`에서 눌림(translateY) 동작.
- [ ] 글래스 잔재(`.glass`, `.glass-edge`, `backdrop-filter` 의존 패널) 제거/흡수.
- [ ] 헤드리스 스모크 콘솔 에러 0 + before/after 스크린샷.
