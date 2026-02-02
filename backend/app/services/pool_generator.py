import math
import random
import time
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models.pool import Pool, PoolTeam, PoolMatch
from app.models.team import Team
from app.models.round import Round
from app.models.match import Match


def calculate_pool_configuration(num_teams: int) -> dict:
    """
    Calcule la configuration optimale des poules.
    
    Règles:
    - < 20 équipes : Quarts de finale (8 qualifiés)
    - >= 20 équipes : Huitièmes de finale (16 qualifiés)
    - Poules de 3 ou 4 équipes idéalement
    
    Returns:
        {
            "num_pools": int,
            "teams_per_pool": List[int],  # ex: [3, 3, 3, 3] ou [4, 4, 3, 3]
            "qualifiers_per_pool": int,   # 1 ou 2
            "total_qualifiers": int,
            "final_phase": str,           # "quarts" ou "huitiemes"
            "recommended": bool,          # True si config recommandée
            "message": str
        }
    """
    if num_teams < 4:
        return {
            "num_pools": 1,
            "teams_per_pool": [num_teams],
            "qualifiers_per_pool": 2,
            "total_qualifiers": min(2, num_teams),
            "final_phase": "finale",
            "recommended": False,
            "message": f"Pas assez d'équipes pour des poules ({num_teams})"
        }
    
    # Déterminer la phase finale
    if num_teams >= 20:
        # Huitièmes de finale = 16 qualifiés
        target_qualifiers = 16
        final_phase = "huitiemes"
    else:
        # Quarts de finale = 8 qualifiés
        target_qualifiers = 8
        final_phase = "quarts"
    
    # Calculer le nombre de poules
    # On veut 2 qualifiés par poule généralement
    num_pools = target_qualifiers // 2
    
    # Ajuster si pas assez d'équipes
    if num_teams < num_pools * 2:
        num_pools = num_teams // 2
        target_qualifiers = num_pools * 2
    
    # Distribuer les équipes dans les poules
    base_teams = num_teams // num_pools
    extra_teams = num_teams % num_pools
    
    teams_per_pool = []
    for i in range(num_pools):
        if i < extra_teams:
            teams_per_pool.append(base_teams + 1)
        else:
            teams_per_pool.append(base_teams)
    
    # Vérifier si la config est bonne (poules de 3-4 équipes)
    min_per_pool = min(teams_per_pool)
    max_per_pool = max(teams_per_pool)
    recommended = 3 <= min_per_pool <= 5 and max_per_pool <= 5
    
    if min_per_pool < 3:
        message = f"Poules trop petites ({min_per_pool} équipes). Format bracket recommandé."
    elif max_per_pool > 5:
        message = f"Poules trop grandes ({max_per_pool} équipes). Ajouter des poules."
    else:
        message = f"{num_pools} poules de {min_per_pool}-{max_per_pool} équipes → {final_phase}"
    
    return {
        "num_pools": num_pools,
        "teams_per_pool": teams_per_pool,
        "qualifiers_per_pool": 2,
        "total_qualifiers": target_qualifiers,
        "final_phase": final_phase,
        "recommended": recommended,
        "message": message
    }


def generate_pools(db: Session, tournament_id: str, court_ids: List[str] = None) -> dict:
    """
    Génère les poules pour un tournoi.
    
    1. Récupère les équipes
    2. Calcule la configuration
    3. Crée les poules
    4. Distribue les équipes (têtes de série séparées)
    5. Génère les matchs de poule
    """
    random.seed(time.time() * 1000)
    
    teams = db.query(Team).filter(
        Team.tournament_id == tournament_id
    ).all()
    
    num_teams = len(teams)
    
    if num_teams < 4:
        raise ValueError("Minimum 4 équipes pour le format poules")
    
    # Nettoyer les anciennes poules
    existing_pools = db.query(Pool).filter(
        Pool.tournament_id == tournament_id
    ).all()
    
    for pool in existing_pools:
        db.query(PoolMatch).filter(PoolMatch.pool_id == pool.id).delete()
        db.query(PoolTeam).filter(PoolTeam.pool_id == pool.id).delete()
    
    db.query(Pool).filter(Pool.tournament_id == tournament_id).delete()
    
    # Nettoyer les rounds de phase finale existants
    existing_rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).all()
    
    for r in existing_rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    
    db.query(Round).filter(Round.tournament_id == tournament_id).delete()
    
    db.commit()
    
    # Calculer la configuration
    config = calculate_pool_configuration(num_teams)
    
    print(f"=== GÉNÉRATION POULES ===")
    print(f"Équipes: {num_teams}")
    print(f"Config: {config}")
    
    # Séparer têtes de série et autres
    seeded_teams = sorted(
        [t for t in teams if t.is_seeded],
        key=lambda t: t.seed_position or 999
    )
    unseeded_teams = [t for t in teams if not t.is_seeded]
    random.shuffle(unseeded_teams)
    
    # Créer les poules
    pools = []
    pool_names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    
    for i in range(config["num_pools"]):
        pool = Pool(
            tournament_id=tournament_id,
            name=f"Poule {pool_names[i]}",
            pool_order=i + 1
        )
        db.add(pool)
        db.commit()
        db.refresh(pool)
        pools.append(pool)
        print(f"Poule créée: {pool.name}")
    
    # Distribuer les équipes
    # 1. D'abord les têtes de série (une par poule si possible)
    # 2. Puis les autres équipes
    
    pool_teams = [[] for _ in range(config["num_pools"])]
    
    # Distribuer les têtes de série en serpentin
    for i, team in enumerate(seeded_teams):
        pool_idx = i % config["num_pools"]
        pool_teams[pool_idx].append(team)
    
    # Distribuer les autres équipes
    unseeded_idx = 0
    for pool_idx in range(config["num_pools"]):
        while len(pool_teams[pool_idx]) < config["teams_per_pool"][pool_idx]:
            if unseeded_idx < len(unseeded_teams):
                pool_teams[pool_idx].append(unseeded_teams[unseeded_idx])
                unseeded_idx += 1
            else:
                break
    
    # Créer les associations PoolTeam
    for pool_idx, pool in enumerate(pools):
        for team in pool_teams[pool_idx]:
            pool_team = PoolTeam(
                pool_id=pool.id,
                team_id=team.id
            )
            db.add(pool_team)
        print(f"  {pool.name}: {len(pool_teams[pool_idx])} équipes")
    
    db.commit()
    
    # Générer les matchs de poule (round-robin)
    court_idx = 0
    total_matches = 0
    
    for pool_idx, pool in enumerate(pools):
        teams_in_pool = pool_teams[pool_idx]
        match_order = 1
        
        # Round-robin: chaque équipe contre chaque autre
        for i in range(len(teams_in_pool)):
            for j in range(i + 1, len(teams_in_pool)):
                team1 = teams_in_pool[i]
                team2 = teams_in_pool[j]
                
                # Assigner un court si disponible
                court_id = None
                if court_ids and len(court_ids) > 0:
                    court_id = court_ids[court_idx % len(court_ids)]
                    court_idx += 1
                
                pool_match = PoolMatch(
                    pool_id=pool.id,
                    team1_id=team1.id,
                    team2_id=team2.id,
                    match_order=match_order,
                    court_id=court_id
                )
                db.add(pool_match)
                match_order += 1
                total_matches += 1
        
        print(f"  {pool.name}: {match_order - 1} matchs générés")
    
    db.commit()
    
    return {
        "success": True,
        "num_teams": num_teams,
        "num_pools": config["num_pools"],
        "teams_per_pool": config["teams_per_pool"],
        "total_matches": total_matches,
        "final_phase": config["final_phase"],
        "message": config["message"]
    }


def calculate_pool_standings(db: Session, pool_id: str) -> List[dict]:
    """
    Calcule le classement d'une poule.
    
    Critères de classement:
    1. Points (2 pts victoire, 1 pt défaite, 0 forfait)
    2. Différence de sets
    3. Différence de jeux
    4. Confrontation directe
    """
    pool_teams = db.query(PoolTeam).filter(PoolTeam.pool_id == pool_id).all()
    
    standings = []
    for pt in pool_teams:
        team = db.query(Team).filter(Team.id == pt.team_id).first()
        
        standings.append({
            "pool_team_id": str(pt.id),
            "team_id": str(pt.team_id),
            "team": team,
            "matches_played": pt.matches_played,
            "matches_won": pt.matches_won,
            "matches_lost": pt.matches_lost,
            "sets_won": pt.sets_won,
            "sets_lost": pt.sets_lost,
            "sets_diff": pt.sets_won - pt.sets_lost,
            "games_won": pt.games_won,
            "games_lost": pt.games_lost,
            "games_diff": pt.games_won - pt.games_lost,
            "points": pt.points
        })
    
    # Trier par points, puis diff sets, puis diff jeux
    standings.sort(key=lambda x: (x["points"], x["sets_diff"], x["games_diff"]), reverse=True)
    
    # Assigner les rangs
    for i, standing in enumerate(standings):
        standing["rank"] = i + 1
    
    return standings


def generate_final_phase_from_pools(db: Session, tournament_id: str, court_ids: List[str] = None) -> dict:
    """
    Génère la phase finale (bracket) à partir des qualifiés des poules.
    
    Les 1ers et 2èmes de chaque poule sont qualifiés.
    Croisement: 1er Poule A vs 2ème Poule B, etc.
    """
    from app.services.bracket_generator import generate_bracket, get_round_name
    
    pools = db.query(Pool).filter(
        Pool.tournament_id == tournament_id
    ).order_by(Pool.pool_order).all()
    
    if not pools:
        raise ValueError("Aucune poule trouvée")
    
    # Vérifier que toutes les poules sont terminées
    for pool in pools:
        matches = db.query(PoolMatch).filter(
            PoolMatch.pool_id == pool.id,
            PoolMatch.is_finished == False
        ).count()
        
        if matches > 0:
            raise ValueError(f"{pool.name} n'est pas terminée ({matches} matchs restants)")
    
    # Récupérer les qualifiés de chaque poule
    qualifiers = []  # [(team, pool_rank, pool_order), ...]
    
    for pool in pools:
        standings = calculate_pool_standings(db, str(pool.id))
        
        # Prendre les 2 premiers
        for standing in standings[:2]:
            team = standing["team"]
            qualifiers.append({
                "team": team,
                "pool_rank": standing["rank"],
                "pool_order": pool.pool_order,
                "pool_name": pool.name
            })
    
    num_qualifiers = len(qualifiers)
    print(f"Qualifiés: {num_qualifiers}")
    
    # Calculer la taille du bracket
    bracket_size = 2 ** math.ceil(math.log2(num_qualifiers))
    round_count = int(math.log2(bracket_size))
    
    # Nettoyer les anciens rounds de phase finale
    existing_rounds = db.query(Round).filter(
        Round.tournament_id == tournament_id
    ).all()
    
    for r in existing_rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    
    db.query(Round).filter(Round.tournament_id == tournament_id).delete()
    db.commit()
    
    # Créer les rounds
    rounds = []
    for i in range(round_count):
        round_name = get_round_name(i + 1, round_count)
        r = Round(
            tournament_id=tournament_id,
            name=round_name,
            order=i + 1
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        rounds.append(r)
    
    # Organiser le croisement des qualifiés
    # 1er Poule A vs 2ème Poule B, 1er Poule B vs 2ème Poule A, etc.
    first_round = rounds[0]
    first_round_matches = bracket_size // 2
    
    # Séparer 1ers et 2èmes
    firsts = [q for q in qualifiers if q["pool_rank"] == 1]
    seconds = [q for q in qualifiers if q["pool_rank"] == 2]
    
    # Créer les paires (croisement)
    pairs = []
    num_pools = len(pools)
    
    for i in range(num_pools // 2):
        # 1er poule i vs 2ème poule (num_pools - 1 - i)
        first_idx = i
        second_idx = num_pools - 1 - i
        
        if first_idx < len(firsts) and second_idx < len(seconds):
            pairs.append((firsts[first_idx]["team"], seconds[second_idx]["team"]))
        
        # 1er poule (num_pools - 1 - i) vs 2ème poule i
        if second_idx < len(firsts) and first_idx < len(seconds):
            pairs.append((firsts[second_idx]["team"], seconds[first_idx]["team"]))
    
    # Créer les matchs
    court_idx = 0
    for match_num in range(1, first_round_matches + 1):
        pair_idx = match_num - 1
        
        team1 = pairs[pair_idx][0] if pair_idx < len(pairs) else None
        team2 = pairs[pair_idx][1] if pair_idx < len(pairs) else None
        
        court_id = None
        if court_ids and len(court_ids) > 0:
            court_id = court_ids[court_idx % len(court_ids)]
            court_idx += 1
        
        match = Match(
            round_id=first_round.id,
            match_order=match_num,
            team1_id=team1.id if team1 else None,
            team2_id=team2.id if team2 else None,
            court_id=court_id,
            bracket_type='winner'
        )
        db.add(match)
    
    # Créer les matchs vides pour les rounds suivants
    for round_idx in range(1, round_count):
        current_round = rounds[round_idx]
        matches_in_round = bracket_size // (2 ** (round_idx + 1))
        
        for match_num in range(1, matches_in_round + 1):
            match = Match(
                round_id=current_round.id,
                match_order=match_num,
                team1_id=None,
                team2_id=None,
                bracket_type='winner'
            )
            db.add(match)
    
    db.commit()
    
    # Créer les matchs de classement
    from app.services.bracket_generator import create_classification_matches
    create_classification_matches(db, tournament_id, round_count, bracket_size)
    
    return {
        "success": True,
        "qualifiers": num_qualifiers,
        "bracket_size": bracket_size,
        "rounds": round_count,
        "message": f"Phase finale générée avec {num_qualifiers} qualifiés"
    }