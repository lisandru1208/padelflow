from fastapi import FastAPI
from app.routers import health, auth, clubs, courts, tournaments

app = FastAPI(title="PadelFlow API")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(clubs.router)
app.include_router(courts.router)
app.include_router(tournaments.router)