import math
import random
import time
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models.pool_tournament import Pool, PoolTeam, PoolMatch
from app.models.team import Team
from app.models.round import Round
from app.models.match import Match



# Configuration des poules selon le nombre d'équipes (User defined)
# Key: Nb équipes
# Value: (Nb qualifiés tableau final, Nb Bye (TS), Nb équipes en poules, Nb poules, Qualifiés/poule)
POOL_CONFIG = {
    4:  {"final": 4,  "bye_ts": 0,  "pool_teams": 0,  "nb_pools": 0, "qualify_per_pool": 0},
    5:  {"final": 8,  "bye_ts": 3,  "pool_teams": 2,  "nb_pools": 1, "qualify_per_pool": 1},
    6:  {"final": 8,  "bye_ts": 2,  "pool_teams": 4,  "nb_pools": 1, "qualify_per_pool": 2},
    7:  {"final": 8,  "bye_ts": 1,  "pool_teams": 6,  "nb_pools": 2, "qualify_per_pool": 1},
    8:  {"final": 8,  "bye_ts": 0,  "pool_teams": 0,  "nb_pools": 0, "qualify_per_pool": 0},
    9:  {"final": 16, "bye_ts": 7,  "pool_teams": 2,  "nb_pools": 1, "qualify_per_pool": 1},
    10: {"final": 16, "bye_ts": 6,  "pool_teams": 4,  "nb_pools": 1, "qualify_per_pool": 2},
    11: {"final": 16, "bye_ts": 5,  "pool_teams": 6,  "nb_pools": 2, "qualify_per_pool": 1},
    12: {"final": 16, "bye_ts": 4,  "pool_teams": 8,  "nb_pools": 2, "qualify_per_pool": 2},
    13: {"final": 16, "bye_ts": 3,  "pool_teams": 10, "nb_pools": 3, "qualify_per_pool": 1},
    14: {"final": 16, "bye_ts": 2,  "pool_teams": 12, "nb_pools": 3, "qualify_per_pool": 2},
    15: {"final": 16, "bye_ts": 1,  "pool_teams": 14, "nb_pools": 4, "qualify_per_pool": 1},
    16: {"final": 16, "bye_ts": 0,  "pool_teams": 0,  "nb_pools": 0, "qualify_per_pool": 0},
    17: {"final": 32, "bye_ts": 15, "pool_teams": 2,  "nb_pools": 1, "qualify_per_pool": 1},
    18: {"final": 32, "bye_ts": 14, "pool_teams": 4,  "nb_pools": 1, "qualify_per_pool": 2},
    19: {"final": 32, "bye_ts": 13, "pool_teams": 6,  "nb_pools": 2, "qualify_per_pool": 1},
    20: {"final": 32, "bye_ts": 12, "pool_teams": 8,  "nb_pools": 2, "qualify_per_pool": 2},
    21: {"final": 32, "bye_ts": 11, "pool_teams": 10, "nb_pools": 3, "qualify_per_pool": 1},
    22: {"final": 32, "bye_ts": 10, "pool_teams": 12, "nb_pools": 3, "qualify_per_pool": 2},
    23: {"final": 32, "bye_ts": 9,  "pool_teams": 14, "nb_pools": 4, "qualify_per_pool": 1},
    24: {"final": 32, "bye_ts": 8,  "pool_teams": 16, "nb_pools": 4, "qualify_per_pool": 2},
    25: {"final": 32, "bye_ts": 7,  "pool_teams": 18, "nb_pools": 5, "qualify_per_pool": 1},
    26: {"final": 32, "bye_ts": 6,  "pool_teams": 20, "nb_pools": 5, "qualify_per_pool": 2},
    27: {"final": 32, "bye_ts": 5,  "pool_teams": 22, "nb_pools": 6, "qualify_per_pool": 1},
    28: {"final": 32, "bye_ts": 4,  "pool_teams": 24, "nb_pools": 6, "qualify_per_pool": 2},
    29: {"final": 32, "bye_ts": 3,  "pool_teams": 26, "nb_pools": 7, "qualify_per_pool": 1},
    30: {"final": 32, "bye_ts": 2,  "pool_teams": 28, "nb_pools": 7, "qualify_per_pool": 2},
    31: {"final": 32, "bye_ts": 1,  "pool_teams": 30, "nb_pools": 8, "qualify_per_pool": 1},
    32: {"final": 32, "bye_ts": 0,  "pool_teams": 0,  "nb_pools": 0, "qualify_per_pool": 0},
}

def calculate_pool_configuration(num_teams: int) -> dict:
    """
    Calcule la configuration optimale des poules basée sur la table POOL_CONFIG.
    """
    config = POOL_CONFIG.get(num_teams)
    
    if not config:
        # Fallback pour > 32 ou cas non gérés
        return {
            "num_pools": 0,
            "teams_per_pool": [],
            "qualifiers_per_pool": 0,
            "total_qualifiers": 0,
            "final_phase": "unknown",
            "bye_ts": 0,
            "recommended": False,
            "message": f"Pas de configuration de poule pour {num_teams} équipes."
        }
    
    nb_pools = config["nb_pools"]
    
    if nb_pools == 0:
        return {
            "num_pools": 0,
            "teams_per_pool": [],
            "qualifiers_per_pool": 0,
            "total_qualifiers": config["final"],
            "final_phase": "finale" if config["final"] == 2 else ("demies" if config["final"] == 4 else ("quarts" if config["final"] == 8 else ("huitiemes" if config["final"] == 16 else "seiziemes"))),
            "bye_ts": 0,
            "recommended": False,
            "message": "Format Tableau recommandé (4, 8, 16, 32 équipes)."
        }

    teams_in_pools_count = config["pool_teams"]
    qualify_per_pool = config["qualify_per_pool"]
    
    # Calculer la répartition exacte des équipes dans les poules
    base_teams = teams_in_pools_count // nb_pools
    extra_teams = teams_in_pools_count % nb_pools
    
    teams_per_pool = []
    for i in range(nb_pools):
        if i < extra_teams:
            teams_per_pool.append(base_teams + 1)
        else:
            teams_per_pool.append(base_teams)
            
    final_phase_map = {4: "demies", 8: "quarts", 16: "huitiemes", 32: "seiziemes"}
    final_phase = final_phase_map.get(config["final"], "unknown")
    
    return {
        "num_pools": nb_pools,
        "teams_per_pool": teams_per_pool,
        "qualifiers_per_pool": qualify_per_pool,
        "total_qualifiers": config["final"], # Taille du tableau final visé
        "final_phase": final_phase,
        "bye_ts": config["bye_ts"], # Nombre de têtes de série exemptées
        "recommended": True,
        "message": f"{nb_pools} poules de {min(teams_per_pool)}-{max(teams_per_pool)} équipes + {config['bye_ts']} TS qualifiés d'office"
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
    
    if config["num_pools"] == 0:
        return {
            "success": False,
            "num_teams": num_teams,
            "num_pools": 0,
            "teams_per_pool": [],
            "total_matches": 0,
            "final_phase": config["final_phase"],
            "message": config["message"]
        }

    # Séparer les équipes :
    # 1. Les Têtes de Série exemptées (Direct Qualifiers)
    # 2. Les équipes pour les poules (qu'on sépare en seeded/unseeded pour l'équilibre)
    
    # D'abord, on trie tout le monde par seed
    all_teams_sorted = sorted(teams, key=lambda t: t.seed_position or 9999)
    
    num_bye_ts = config.get("bye_ts", 0)
    direct_qualifiers = all_teams_sorted[:num_bye_ts] # Les X premiers
    teams_for_pools = all_teams_sorted[num_bye_ts:]   # Le reste
    
    print(f"Direct Qualifiers ({num_bye_ts}): {[t.name for t in direct_qualifiers]}")
    print(f"Teams in Pools ({len(teams_for_pools)}): Expecting {sum(config['teams_per_pool'])}")
    
    # Parmi les équipes de poules, on sépare Seeded / Unseeded pour bien répartir
    pool_seeded = [t for t in teams_for_pools if t.is_seeded]
    pool_unseeded = [t for t in teams_for_pools if not t.is_seeded]
    
    # Mélanger les non-têtes de série pour l'aléatoire
    random.shuffle(pool_unseeded)
    
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
    pool_teams_dist = [[] for _ in range(config["num_pools"])]
    
    # 1. Distribuer les têtes de série (restantes) en serpentin
    for i, team in enumerate(pool_seeded):
        pool_idx = i % config["num_pools"]
        pool_teams_dist[pool_idx].append(team)
    
    # 2. Distribuer les autres équipes pour remplir
    unseeded_idx = 0
    # On itère sur les poules pour remplir jusqu'au quota
    # Attention : pool_seeded a déjà rempli certaines places
    
    # Stratégie de remplissage équilibré: on continue le "serpentin" avec les unseeded
    current_pool_idx = len(pool_seeded) % config["num_pools"] # Continuer là où on s'est arrêté?
    # Ou plus simple: Remplir chaque poule jusqu'à son quota spécifique
    
    # Approche naïve par quota :
    for pool_idx in range(config["num_pools"]):
        target_size = config["teams_per_pool"][pool_idx]
        while len(pool_teams_dist[pool_idx]) < target_size:
            if unseeded_idx < len(pool_unseeded):
                pool_teams_dist[pool_idx].append(pool_unseeded[unseeded_idx])
                unseeded_idx += 1
            else:
                break
    
    # Refaire une passe si des unseeded restent (cas d'erreur config ?)
    # Normalement config["teams_per_pool"] somme == len(teams_for_pools)
    
    # Créer les associations PoolTeam
    for pool_idx, pool in enumerate(pools):
        for team in pool_teams_dist[pool_idx]:
            pool_team = PoolTeam(
                pool_id=pool.id,
                team_id=team.id
            )
            db.add(pool_team)
        print(f"  {pool.name}: {len(pool_teams_dist[pool_idx])} équipes")
    
    db.commit()
    
    # Générer les matchs de poule (round-robin)
    court_idx = 0
    total_matches = 0
    
    for pool_idx, pool in enumerate(pools):
        teams_in_pool = pool_teams_dist[pool_idx]
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
        "direct_qualifiers": num_bye_ts,
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
    Génère la phase finale (bracket) à partir des qualifiés des poules ET des Têtes de série exemptées.
    """
    from app.services.bracket_generator import create_classification_matches, assign_courts_globally, place_teams_in_bracket, get_round_name
    from app.models.team import Team

    # 1. Récupérer toutes les équipes et la config
    all_teams = db.query(Team).filter(Team.tournament_id == tournament_id).all()
    num_total_teams = len(all_teams)
    config = calculate_pool_configuration(num_total_teams)
    
    if not config["recommended"] and config["num_pools"] == 0:
        # Cas fallback si pas de poules configurées
        bracket_size = config["total_qualifiers"] 
    else:
        bracket_size = config["total_qualifiers"]

    # 2. Identifier les équipes qui ÉTAIENT en poule
    pool_teams_entries = db.query(PoolTeam).join(Pool).filter(Pool.tournament_id == tournament_id).all()
    pool_team_ids = {pt.team_id for pt in pool_teams_entries}
    
    # 3. Direct Qualifiers (ceux qui n'étaient pas en poule)
    # On suppose que ce sont les meilleures têtes de série
    direct_qualifiers = [t for t in all_teams if t.id not in pool_team_ids]
    # Tri par seed
    direct_qualifiers.sort(key=lambda t: t.seed_position or 9999)
    
    print(f"Direct Qualifiers ({len(direct_qualifiers)}): {[t.name for t in direct_qualifiers]}")
    
    # 4. Pool Qualifiers
    pools = db.query(Pool).filter(Pool.tournament_id == tournament_id).order_by(Pool.pool_order).all()
    
    pool_qualifiers_winners = []
    pool_qualifiers_runners = []
    
    qualify_count = config.get("qualifiers_per_pool", 2)
    
    for pool in pools:
        standings = calculate_pool_standings(db, str(pool.id))
        
        # Vérifier si poule terminée
        matches_left = db.query(PoolMatch).filter(PoolMatch.pool_id == pool.id, PoolMatch.is_finished == False).count()
        if matches_left > 0:
             raise ValueError(f"{pool.name} n'est pas terminée.")

        # Récupérer les qualifiés
        if len(standings) >= 1 and qualify_count >= 1:
            pool_qualifiers_winners.append(standings[0]["team"])
        
        if len(standings) >= 2 and qualify_count >= 2:
            pool_qualifiers_runners.append(standings[1]["team"])

    # 5. Construire la liste ordonnée pour le bracket (Seeding virtuel)
    # Ordre : Direct Qualifiers > Pool Winners > Pool Runners
    ranked_teams = []
    ranked_teams.extend(direct_qualifiers)
    ranked_teams.extend(pool_qualifiers_winners)
    ranked_teams.extend(pool_qualifiers_runners)
    
    # Attribuer une "seed_position" temporaire pour le placement
    for i, t in enumerate(ranked_teams):
        # On ne touche pas à l'objet Team en DB, juste pour l'algo
        t.temp_seed = i + 1

    print(f"Total Qualifiés pour Bracket: {len(ranked_teams)}")
    print(f"Taille Bracket cible: {bracket_size}")
    
    # Nettoyer ancien bracket
    existing_rounds = db.query(Round).filter(Round.tournament_id == tournament_id).all()
    for r in existing_rounds:
        db.query(Match).filter(Match.round_id == r.id).delete()
    db.query(Round).filter(Round.tournament_id == tournament_id).delete()
    db.commit()

    # Créer les rounds
    round_count = int(math.log2(bracket_size))
    rounds = []
    for i in range(round_count):
        r = Round(tournament_id=tournament_id, name=get_round_name(i + 1, round_count), order=i + 1)
        db.add(r)
        db.commit()
        db.refresh(r)
        rounds.append(r)
        
    # Placer les équipes
    # On passe tout le monde en "Seeded" pour forcer l'ordre hiérarchique
    # (Direct > Winners > Runners)
    # L'algo place_teams_in_bracket va mettre le 1 vs 32, 2 vs 31 etc.
    final_slots = place_teams_in_bracket(ranked_teams, [], bracket_size, bracket_size - len(ranked_teams))
    
    # Créer les matchs du first round
    first_round = rounds[0]
    matches_in_first = bracket_size // 2
    
    # Dictionnaire temporaire pour propager
    all_matches = {}
    bye_ids = []

    for match_num in range(1, matches_in_first + 1):
        slot1 = final_slots[(match_num - 1) * 2]
        slot2 = final_slots[(match_num - 1) * 2 + 1]
        
        m = Match(
            round_id=first_round.id, 
            match_order=match_num,
            team1_id=slot1.id if slot1 else None,
            team2_id=slot2.id if slot2 else None,
            bracket_type='winner',
            court_id=None
        )
        
        # Gestion BYE immédiate
        if slot1 and not slot2:
            m.is_finished = True
            m.winner_id = slot1.id
            m.score = "BYE"
            bye_ids.append(m) # On ne le sauve pas encore ID car pas commit
        elif slot2 and not slot1:
            m.is_finished = True
            m.winner_id = slot2.id
            m.score = "BYE"
            bye_ids.append(m)
            
        db.add(m)
        db.commit()
        db.refresh(m)
        all_matches[(0, match_num)] = m
        if m.is_finished and m.score == "BYE":
            bye_ids.append(m.id) # Sauver l'ID

    # Créer les matchs vides suivants
    for r_idx in range(1, round_count):
        matches_count = bracket_size // (2 ** (r_idx + 1))
        for m_num in range(1, matches_count + 1):
            m = Match(round_id=rounds[r_idx].id, match_order=m_num, bracket_type='winner', court_id=None)
            db.add(m)
            db.commit() # Important pour avoir l'ID pour la map
            db.refresh(m)
            all_matches[(r_idx, m_num)] = m

    # Propager les BYEs
    for r_idx in range(round_count - 1):
        count = bracket_size // (2 ** (r_idx + 1))
        for m_num in range(1, count + 1):
            m = all_matches[(r_idx, m_num)]
            if m.is_finished and m.winner_id:
                next_m_num = (m_num + 1) // 2
                next_m = all_matches.get((r_idx + 1, next_m_num))
                if next_m:
                    if m_num % 2 == 1: next_m.team1_id = m.winner_id
                    else: next_m.team2_id = m.winner_id
    
    db.commit()
    
    # Supprimer les matchs BYE
    # Attention: IDs in bye_ids are reliable now
    clean_bye_ids = [x for x in bye_ids if isinstance(x, str) or isinstance(x, int)] # ids
    if clean_bye_ids:
        db.query(Match).filter(Match.id.in_(clean_bye_ids)).delete(synchronize_session=False)
        db.commit()

    # Matchs de classement
    # Note: On passe total_teams pour limiter la profondeur
    create_classification_matches(db, tournament_id, round_count, bracket_size, len(ranked_teams))
    
    # Assignation Globale
    assign_courts_globally(db, tournament_id, court_ids)

    return {
        "success": True,
        "qualifiers": len(ranked_teams),
        "bracket_size": bracket_size,
        "rounds": round_count,
        "message": f"Phase finale générée ({len(direct_qualifiers)} Direct + {len(ranked_teams)-len(direct_qualifiers)} Pool)"
    }