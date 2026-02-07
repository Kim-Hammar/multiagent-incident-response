# CCS Response Planner Frontend

React frontend for the CCS Incident Response Planner built with Vite.

## Available Scripts

In the project directory, you can run:

### `npx eslint . --quiet`

Runs the linter

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3005](http://localhost:3005) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.

## Docker

From the project root:

```bash
docker compose up --build
docker compose exec app bash -c "cd ccs-response-planner-frontend && npm start"
docker compose exec app bash -c "cd ccs-response-planner-frontend && npm test"
docker compose exec app bash -c "cd ccs-response-planner-frontend && npx eslint . --quiet"
docker compose exec app bash -c "cd ccs-response-planner-frontend && npm run build"
```
