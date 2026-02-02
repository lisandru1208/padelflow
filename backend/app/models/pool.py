import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Pool(Base):
    """Une poule dans un tournoi"""
    __tablename__ = "pools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False)
    name = Column(String, nullable=False)  # "Poule A", "Poule B", etc.
    pool_order = Column(Integer, nullable=False)  # 1, 2, 3, 4...


class PoolTeam(Base):
    """Association équipe-poule avec classement"""
    __tablename__ = "pool_teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("pools.id"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    
    # Statistiques (mises à jour après chaque match)
    matches_played = Column(Integer, default=0)
    matches_won = Column(Integer, default=0)
    matches_lost = Column(Integer, default=0)
    sets_won = Column(Integer, default=0)
    sets_lost = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    games_lost = Column(Integer, default=0)
    points = Column(Integer, default=0)  # 2 pts victoire, 1 pt défaite, 0 forfait
    
    # Classement final dans la poule (calculé)
    final_rank = Column(Integer, nullable=True)


class PoolMatch(Base):
    """Un match dans une poule"""
    __tablename__ = "pool_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("pools.id"), nullable=False)
    
    team1_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    team2_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    
    # Score détaillé
    score = Column(String, nullable=True)  # "6-4 6-3"
    team1_sets = Column(Integer, default=0)
    team2_sets = Column(Integer, default=0)
    team1_games = Column(Integer, default=0)
    team2_games = Column(Integer, default=0)
    
    winner_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    is_finished = Column(Boolean, default=False)
    
    # Court assigné
    court_id = Column(UUID(as_uuid=True), ForeignKey("courts.id"), nullable=True)
    
    # Ordre du match dans la poule (pour l'affichage)
    match_order = Column(Integer, nullable=False)