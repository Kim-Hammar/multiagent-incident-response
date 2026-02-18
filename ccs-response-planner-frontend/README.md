# CCS Response Planner Frontend

React frontend for the CCS Incident Response Planner built with Vite.

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3005](http://localhost:3005) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm run dev`

Alias for the Vite dev server (same as `npm start`).

### `npm test`

Runs tests once (single run).

### `npm run test:watch`

Launches the test runner in watch mode.

### `npm run build`

Builds the app for production to the `build` folder.

### `npx eslint . --quiet`

Runs the linter.

### `npm run lint:fix`

Runs the linter with auto-fix.

### `npm run format`

Formats all source files with Prettier.

## Architecture

The frontend source lives under `src/`:

- `components/ResponsePlanner/` — Main incident response planning interface
- `components/Agents/` — Agent management and visualization (15 shared utility modules)
- `components/DigitalTwin/` — Digital twin deployment and interaction
- `components/Tools/` — External security tool interfaces (Tavily, NVD, MITRE, VirusTotal, AbuseIPDB, OTX)
- `components/LLM/` — LLM configuration and interaction
- `components/Login/` — Login page and authentication UI
- `components/Common/` — Shared constants and utilities
- `contexts/AuthContext.jsx` — Authentication context (token/user in localStorage + React state)
- `hooks/useTabWithHash.js` — URL hash-based tab navigation hook

## Dependencies

| Package | Purpose |
|---------|---------|
| React 18 | UI framework |
| React Router v6 | Client-side routing |
| react-markdown | Markdown rendering for LLM output |
| xterm.js | Terminal emulator for penetration testing |
| Vite | Build tool and dev server |
| Vitest | Unit testing framework |
| ESLint | Linting |
| Prettier | Code formatting |

## Docker

From the project root:

```bash
docker compose up --build
docker compose exec app bash -c "cd ccs-response-planner-frontend && npm start"
docker compose exec app bash -c "cd ccs-response-planner-frontend && npm test"
docker compose exec app bash -c "cd ccs-response-planner-frontend && npx eslint . --quiet"
docker compose exec app bash -c "cd ccs-response-planner-frontend && npm run build"
```

## Author & Maintainer

Kim Hammar <kimham@kth.se>

## Copyright and license

[LICENSE](../LICENSE.md)

Creative Commons

(C) 2026, Kim Hammar, Tansu Alpcan, Emil Lupu
