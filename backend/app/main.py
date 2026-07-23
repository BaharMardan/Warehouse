from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth.router import router as auth_router
from app.routers import health
from app.routers.tally import router as tally_router
from app.routers.tally_header import router as tally_header_router
from app.routers.ghabz import router as ghabz_router
from app.routers.invoice import router as invoice_router
from app.routers.commodity import router as commodity_router

from app.crud.registry import crud_routers

app = FastAPI(title="APEX Migration API")

app.add_middleware(
    CORSMiddleware,
    # Accept the Vite dev server on any local host form: localhost, 127.0.0.1, or a
    # LAN IP (e.g. opening the app from another machine). A single hard-coded origin
    # made every other host fail preflight -> browser reports "Failed to fetch".
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|\d+\.\d+\.\d+\.\d+):5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth_router)
app.include_router(tally_router)
app.include_router(tally_header_router)
app.include_router(ghabz_router)
app.include_router(invoice_router)
app.include_router(commodity_router)

# app.include_router(items.router)
# app.include_router(anbar.router)
for router in crud_routers:
    app.include_router(router)

@app.get("/")
def root():
    return {"message": "API is running. Open /docs"}
