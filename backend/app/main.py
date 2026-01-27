from fastapi import FastAPI
from app.routers import health, auth, clubs, courts, tournaments, teams, brackets, matches, scores

app = FastAPI(title="PadelFlow API")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(clubs.router)
app.include_router(courts.router)
app.include_router(tournaments.router)
app.include_router(teams.router)
app.include_router(brackets.router)
app.include_router(matches.router)
app.include_router(scores.router)