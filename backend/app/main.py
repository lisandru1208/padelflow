from fastapi import FastAPI
from app.routers import health, auth

app = FastAPI(title="PadelFlow API")

app.include_router(health.router)
app.include_router(auth.router)