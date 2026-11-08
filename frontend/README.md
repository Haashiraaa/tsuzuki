# Tsuzuki web app (frontend)

React 19 + TypeScript + Vite. It follows the mockup screen for screen: Library, a series page,
Queue, Sites and Settings.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run typecheck
npm run build
```

## Sample mode

There is no server yet. With `VITE_USE_SAMPLE=true` (the default in `.env.example`) the app runs
on built-in sample data, held in memory, so every screen works. Set it to `false` to talk to a
real server; `/api` is proxied to `127.0.0.1:8000` in development.

## Layout

```
src/
  api/          the contract (types.ts, contract.ts), the HTTP client, the sample data
  components/   ui/ (buttons, panels, titles) and layout/ (sidebar, shell)
  features/     one folder per screen: library, series, queue, sites, settings
  styles/       tokens.css (the palette from the mockup) and base.css
```

Each screen keeps its own components, CSS module and `queries.ts`. Screens only talk to the
`Api` interface, so the sample and HTTP versions are interchangeable.

## API the server needs to provide

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/series` | Library |
| POST | `/api/series` | Add a series by URL |
| GET | `/api/series/:id?order&all` | One series with its episodes |
| POST | `/api/downloads` | Queue episodes |
| GET | `/api/queue` | Downloading, waiting, failed, finished |
| POST | `/api/episodes/:id/retry` | Retry a failed episode |
| POST | `/api/episodes/:id/pause` | Pause (no backend state for this yet) |
| POST | `/api/episodes/:id/cancel` | Cancel |
| GET | `/api/episodes/:id/file` | Save to this device; the server deletes its copy once delivered |
| GET | `/api/episodes/:id/stream` | Play in the browser |
| GET | `/api/me` | The private restore path for this browser's library (`null` before first use) |
| GET | `/api/restore/:token` | Open in another browser to bring a library back (sets the cookie, redirects to `/`) |
| GET | `/api/sites` | Known sites |
| POST | `/api/sites/test` | Try a new site |
| POST | `/api/sites/profiles` | Save a site profile |

The shapes are in `src/api/types.ts`.
