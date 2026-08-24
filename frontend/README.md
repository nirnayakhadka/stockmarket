# NEPSE Watchlist — Frontend Scaffold (TypeScript + Tailwind, mock data only)

Same sections as before, now in TypeScript with Tailwind CSS v4 for styling.
All data comes from `src/data/mockData.ts` — no real API calls yet.

## Run it

```
npm install
npm run dev
```

## Stack

- Vite + React + TypeScript
- Tailwind CSS v4 (via `@tailwindcss/vite` — no separate config file needed,
  custom colors defined in `src/index.css` under `@theme`)
- react-router-dom, recharts

## What's here

- `src/types/index.ts` — shared TypeScript interfaces (Company, NewsArticle,
  PricePoint, etc.) — extend these as your real API shapes solidify.
- `src/data/mockData.ts` — mock companies, 30-day OHLCV series, news, brokers,
  behavior summaries, crawl runs, users. Swap this file for real API calls later.
- `src/AuthContext.tsx` — simple mock login (pick a role: admin/analyst/viewer),
  no real JWT yet.
- `src/components/Layout.tsx` — sidebar nav, role-based link visibility (UI only —
  remember real role checks must also be enforced server-side).
- Pages (`src/pages/`):
  - `Login.tsx` — pick a role
  - `Dashboard.tsx` — cross-company overview (stat cards + watchlist table + latest news)
  - `CompanyDetail.tsx` — price/volume chart, VWAP, behavior analysis, top brokers, news feed
  - `NewsReview.tsx` — correct mis-tagged news (Admin/Analyst)
  - `Admin.tsx` — manage watchlist, trigger/view crawl runs, manage users

## Not done on purpose

- No real API integration (axios/fetch calls) — wire these up as you build the backend.
- No real auth/JWT — `AuthContext` just sets a mock user object.
- No form validation, loading/error states, or tests.
- Tailwind classes are inlined in JSX; extract to components if they get repetitive.
