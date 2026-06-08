# 기술 스택

> 웹 MVP → 앱 MVP → 정식 서비스로 갈수록 위치 수집 안정성, 실시간성, 확장성이 강화되는 구조

---

## Phase별 기술 스택 비교

| 구분 | Phase 1. 웹 MVP | Phase 2. 앱 MVP | Phase 3. 정식 서비스 |
|---|---|---|---|
| **목표** | 핵심 UX 검증 | 실제 산책 상황 검증 | 확장 가능한 위치 기반 P2P 네트워크 구축 |
| **제품 형태** | 모바일 웹 / 반응형 웹 | iOS·Android 앱 | iOS·Android 정식 앱 |
| **프론트엔드** | Next.js / React | React Native / Flutter | React Native / Flutter |
| **지도 API** | MapLibre + OpenStreetMap | Naver Maps API / Kakao Maps API | Naver / Kakao / Google Maps / Mapbox |
| **위치 수집** | Browser Geolocation API | iOS Core Location / Android Fused Location Provider | iOS Core Location / Android Fused Location Provider |
| **위치 업데이트** | `watchPosition()` (웹 실행 중) | 앱 위치 권한 기반 실시간 업데이트 | 실시간 + 백그라운드 위치 처리 |
| **위치 데이터 처리** | Supabase PostGIS / Firebase GeoFire | Supabase PostGIS / Firebase GeoFire | PostgreSQL + PostGIS |
| **백엔드** | Supabase / Firebase | Supabase / Firebase 또는 경량 Node.js | NestJS / Node.js |
| **DB** | Supabase PostgreSQL / Firebase Firestore | Supabase PostgreSQL / Firebase Firestore | PostgreSQL |
| **공간 검색** | PostGIS 반경 검색 또는 GeoFire | PostGIS 반경 검색 또는 GeoFire | PostGIS 기반 반경 검색·거리 계산 |
| **실시간 통신** | Supabase Realtime / Firebase Realtime | Supabase Realtime / Firebase Realtime / Socket.IO | WebSocket / Socket.IO |
| **실시간 상태 관리** | Supabase Realtime 상태값 | Firebase / Supabase 상태값 | Redis |
| **푸시 알림** | 웹 내부 알림 / Web Push | FCM | FCM + APNs |
| **인증** | Supabase Auth / Firebase Auth | Supabase Auth / Firebase Auth | Firebase Auth / 자체 JWT / OAuth |
| **파일 저장** | Supabase Storage / Firebase Storage | Supabase Storage / Firebase Storage | AWS S3 / Cloudflare R2 |
| **배포** | Vercel / Netlify | TestFlight / Google Play Internal Test | AWS / GCP / Azure |
| **분석** | GA4 / 기본 이벤트 로그 | GA4 / Firebase Analytics | Amplitude / Mixpanel / GA4 |
| **모니터링** | Vercel Logs / Supabase Logs | Firebase Crashlytics / Sentry | Sentry / Datadog / Grafana |
| **핵심 구현 기능** | 산책 시작, 위치 권한, 근처 강아지 지도 표시, 산책 요청, 매칭 로그 | 실시간 산책 매칭, 푸시 요청, 매칭 로그, 친구 요청 | 친구 시스템, 친밀도 시스템, 산책 호출, 그룹 산책, 커뮤니티, AI 추천 |
| **장점** | 빠르고 저렴하게 검증 가능 | 실제 산책 환경에서 사용성 검증 가능 | 안정성·확장성·실시간성 확보 |
| **한계** | 웹은 백그라운드 위치 추적이 약함 | 서버 구조가 커지면 리팩토링 필요 | 개발 비용과 운영 비용 증가 |

---

## 단계별 추천 조합 요약

| 단계 | 추천 조합 | 적합한 목적 |
|---|---|---|
| **Phase 1. 웹 MVP** | Next.js + MapLibre/OSM + Browser Geolocation API + Supabase PostGIS/Realtime | 아이디어 검증, 데모, 피치덱용 프로토타입 |
| **Phase 2. 앱 MVP** | React Native/Flutter + Naver/Kakao Maps + Core Location/Fused Location + Firebase/Supabase | 실제 산책 상황에서 매칭 UX 검증 |
| **Phase 3. 정식 서비스** | React Native/Flutter + Naver/Kakao Maps + NestJS + PostgreSQL/PostGIS + Redis + WebSocket + FCM/APNs + AWS/GCP | 확장 가능한 실시간 P2P 산책 네트워크 구축 |

---

## 개발 로드맵

| 순서 | 구현 범위 | 주요 기능 | 사용 기술 |
|---|---|---|---|
| 1 | 웹 MVP | 지도 표시, 현재 위치 수집, 근처 사용자 표시 | Next.js, MapLibre, Browser Geolocation API |
| 2 | 위치 기반 매칭 | 반경 내 산책 중 사용자 조회, 같이 산책 요청 | Supabase, PostGIS, Realtime |
| 3 | 매칭 로그 | 산책 성공 기록, 만남 횟수, 산책 시간 저장 | Supabase DB, Storage |
| 4 | 앱 MVP | 앱 기반 위치 수집, 푸시 알림 | React Native/Flutter, FCM |
| 5 | 친구 시스템 | 친구 요청, 친구 목록, 반복 만남 기록 | PostgreSQL, Auth, Push |
| 6 | 친밀도 시스템 | 반복 산책·친구 수락·긍정 피드백 기반 점수화 | PostgreSQL, Batch/Server Logic |
| 7 | 산책 호출 | 친밀도 기반 "같이 산책할래요?" 알림 | FCM, APNs, WebSocket |
| 8 | 정식 확장 | 그룹 산책, 커뮤니티, AI 추천 | NestJS, Redis, PostGIS, AI API |
