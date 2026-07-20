# Warehouse Frontend (React + Vite + TypeScript + Mantine)

## Prerequisites
- Node.js LTS installed
- The FastAPI backend running (uvicorn), with CORS enabled for http://localhost:5173

## Run
1. npm install
2. npm run dev
3. Open http://localhost:5173

## Config
The API URL lives in `.env` as VITE_API_URL.
Vite reads it at startup — restart `npm run dev` after changing it.

## Structure
src/api/client.ts    one generic fetch wrapper (knows the API base URL)
src/api/items.ts     FA_KALA-specific calls
src/types/item.ts    the Item interface (typed row shape)
src/pages/ItemsPage  the FA_KALA table screen
src/components/       reusable components (e.g. DataTable) — next step
