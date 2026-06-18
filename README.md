# blip MVP (M0–M2)

FastAPI single server: REST API + static SPA shell. SQLite (`walk.db`),
guest-token auth, polling, app-level Haversine for nearby search.
Implements `docs/mvp_spec/00–03`: Auth · Pets · Walks · Nearby · Matches.

## Run

```bash
conda activate alpha-blip            # python 3.11 + requirements.txt installed
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
# → http://localhost:8000  (SPA + API same origin)
```

Phone demo over HTTPS: `scripts/tunnel.sh` (`ngrok http 8000`).

## Smoke test

With the server running:

```bash
bash scripts/smoke.sh
```

`scripts/smoke.sh` (M0–M2), in one pass:
1. `GET /` returns the SPA shell HTML (200).
2. Guest signup → pet create / get / update (2xx).
3. Users A & B start walks → A's `nearby` shows B at an approximate
   (fuzzed) location.
4. A → B match-request → B accept → match-session → end → match-log created.

`scripts/smoke_m34.sh` (M3–M4), in one pass:
1. Quest candidates (3) → select + lock (re-select same day → 409).
2. Dummy WebM clip upload (201) → record save (links clip, auto-links the
   day's quest) → `GET /api/records` shows it.
3. A creates room (6-digit `join_code`) → lookup by code → B joins →
   B shares a `visibility=room` record → A toggles a 🔥 reaction →
   `GET /api/rooms/{id}` timeline shows the record + reaction (and toggle-off).

`scripts/smoke_m5.sh` (M5 Privacy F-09), in one pass:
1. `POST /api/privacy/block` (201) — and the blocked user disappears from
   `nearby` (two-way exclusion).
2. `POST /api/privacy/report` (201).
3. `DELETE /api/privacy/block/{user_id}` (200) — blocked user reappears in
   `nearby`.

## Android WebView wrapper (M5, `android/`)

A Gradle/Kotlin WebView wrapper that loads the SPA over an ngrok HTTPS URL.
See `docs/mvp_spec/05_android_and_demo.md`.

- `MainActivity.kt` — WebView host: `javaScriptEnabled`, `domStorageEnabled`
  (localStorage), `mediaPlaybackRequiresUserGesture=false`; camera/mic via
  `onPermissionRequest().grant()`, geolocation via
  `onGeolocationPermissionsShowPrompt`, file chooser via `onShowFileChooser`;
  deep link `app://join/{room_code}` → loads `/?join={code}`; reload / settings menu.
- `SettingsActivity.kt` — paste the ngrok URL (stored in `SharedPreferences`).
- `AndroidManifest.xml` — `INTERNET`, `ACCESS_FINE_LOCATION`, `CAMERA`,
  `RECORD_AUDIO`; `usesCleartextTraffic=true`; `app://join` intent-filter.

Demo flow (manual, real device): start server → `scripts/tunnel.sh`
(`ngrok http 8000`) → open the HTTPS URL in the phone browser, or install the
APK and enter the URL in SettingsActivity.

## Layout

```
server/
  main.py        app, routers, static mount, startup (create_all + seed)
  database.py    SQLite engine/session
  models.py      all ORM tables (02_data_model.md)
  schemas.py     Pydantic DTOs (M0–M2)
  deps.py        get_db, get_current_user (bearer guest token)
  seed.py        quest templates/missions (idempotent)
  utils/         geo (Haversine + approx offset), codes, events
  api/           auth, pets, walks, nearby, matches,
                 records, clips, quests, rooms, reactions
  services/      matching, quest (candidate/select/lock), room (code/join/dedup)
  static/        index.html + css + js (SPA shell)
scripts/         start.sh, tunnel.sh, smoke.sh, smoke_m34.sh
```

Implemented: M0–M2 (Auth · Pets · Walks · Nearby · Matches) and
M3–M4 (Records · Clips · Quests · Rooms · Reactions, with quest seed).
M5 (privacy settings, Android WebView, ngrok demo) lands in subsequent work;
its tables (`blocks`/`reports`) are already modeled.
