# 📍 MJCET Campus Event System — HANDOVER FILE
> Paste this entire file at the start of every new Antigravity chat to restore full context.
> **Last Updated:** 2026-02-24

---

## 🗂️ Project Overview
A full-stack **Campus Event System** for MJCET college.
- Scrapes Instagram posts from 14 campus clubs
- Extracts event details (title, date, venue, registration link) using **Gemini AI**
- Scans **QR codes** on event posters to extract registration links
- Displays events on a web dashboard with filtering, rating, reminders, and admin panel
- Users can **login/register**, **follow clubs**, **rate events**, and **set reminders**

---

## 🛠️ Tech Stack
| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | PostgreSQL (password: `xyz`, db: `campus_events`) |
| ORM | SQLAlchemy |
| AI | Google Gemini (`gemini-2.5-flash` — confirmed working) |
| Scraper | Selenium + Chrome (persistent session) |
| QR Scanning | pyzbar + OpenCV |
| Frontend | Vanilla HTML/CSS/JS (`frontend/app.html`) |
| Auth | JWT tokens |

---

## 📁 Key File Map
```
campus_event_system/
├── backend/
│   ├── main.py          ← All API routes (FastAPI)
│   ├── models.py        ← DB models: Event, User, Feedback, Reminder, ClubSubscription
│   ├── database.py      ← DB connection (reads DATABASE_URL from .env)
│   ├── auth.py          ← JWT auth helpers
│   └── .env             ← GEMINI keys, DATABASE_URL (PostgreSQL), SECRET_KEY
├── scraper/
│   └── instagram_scraper.py  ← Main Selenium scraper (scrapes + QR + Gemini + saves to DB)
├── ml/
│   └── gemini_refiner.py     ← Gemini AI with dual-key fallback
├── frontend/
│   └── app.html              ← Main dashboard UI
├── data/
│   ├── images/               ← Downloaded event poster images
│   └── scraped_data.json     ← Raw JSON backup of scraped posts
├── campus_events.db          ← SQLite DB root (legacy backup — Postgres is source of truth now)
├── migrate_sqlite_to_pg.py   ← One-click migration from SQLite → PostgreSQL (already run)
└── HANDOVER.md               ← THIS FILE
```

---



## 🤖 Gemini API — Confirmed Working Models (tested 2026-02-24)
| Model | Status |
|---|---|
| `gemini-2.5-flash` | ✅ Working |
| `gemini-flash-latest` | ✅ Working |
| `gemini-2.5-flash-lite` | ✅ Working |
| `gemini-flash-lite-latest` | ✅ Working |
| `gemini-2.0-flash` / `gemini-2.0-flash-lite` | ❌ Free tier quota = 0 |
| `gemini-1.5-flash` / `gemini-1.5-flash-8b` | ❌ 404 Not Found |

`gemini_refiner.py` now uses dual-key fallback:
- `GEMINI_API_KEY` = primary
- `GEMINI_API_KEY_BACKUP` = backup (auto-switches if primary hits quota)

---

## ✅ What Is Fully Working
- [x] PostgreSQL connected and populated (50 events migrated from SQLite)
- [x] FastAPI backend with full CRUD, auth, feedback, reminders, club follow
- [x] Frontend dashboard at `http://localhost:8000` shows events
- [x] Gemini refiner updated with correct working models + dual-key fallback
- [x] QR code scanning (pyzbar + OpenCV, with grayscale fallback)
- [x] Migration complete — scraper now writes DIRECTLY to Postgres

---

## 🔴 Current Data Quality Problem
The 50 events currently in Postgres are **mostly garbage** from old failed scrape:
| Metric | Count |
|---|---|
| Events with real titles | 1/50 |
| Events with registration links | 0/50 |
| Events with venue | 3/50 |
| Events with null date | 31/50 |

**Root cause:** Old API key had quota=0, so Gemini silently failed on every event.
**Fix:** Re-run the scraper now that Gemini is working — it will UPDATE existing events (upsert logic, no wipe needed).

---

## 🔴 Pending Tasks (in order)

| # | Task | Status |
|---|---|---|
| 1 | ✅ Fix Gemini API keys + models | DONE |
| 2 | ✅ Migrate SQLite → PostgreSQL | DONE |
| 3 | **Re-run scraper** to get clean event data | 🔴 TODO NEXT |
| 4 | Verify events show correctly on dashboard (titles, dates, reg links) | 🔴 TODO |
| 5 | Fix card UI: Date TBA / Event Concluded / Remind Me logic | 🔴 TODO |
| 6 | Fix duplicate reminder notification (localStorage dedup) | 🔴 TODO |
| 7 | Fix timezone bug in reminders (`utcnow` everywhere) | 🔴 TODO |

---

## 📋 Agreed Design Decisions
1. **Date display:** Only show `event_date` (actual event date from poster). NEVER show `scraped_at` / Instagram post date.
2. **No date found:** If Gemini can't find a date → `event_date` = null → show **"📅 Date TBA"**
3. **Past events:** If `event_date` < today → show **"✅ Event Concluded"** badge, NO reminder button
4. **Future events:** `event_date` > today → show date + **🔔 Remind Me** button
5. **Re-scraping:** Scraper uses upsert (no wipe needed) — re-running will UPDATE bad events with fresh Gemini data
6. **QR registration links:** pyzbar scans image, found URL passed to Gemini as `qr_hint`

---

## 🚀 How to Run the Project
```bash
# From project root:
cd "c:\Users\sanat\OneDrive\Desktop\campus_event_system"
python -m uvicorn backend.main:app --reload --port 8000
# Open: http://localhost:8000
```

## 🕷️ How to Re-run Scraper
```bash
cd "c:\Users\sanat\OneDrive\Desktop\campus_event_system"
python scraper/instagram_scraper.py
# Log in to Instagram in the Chrome window that opens
# Press Enter in terminal when logged in
# Scraper runs and writes directly to Postgres
```
