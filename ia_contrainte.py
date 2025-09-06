from ortools.sat.python import cp_model
import sqlite3
import re
from typing import List, Dict, Any

# ===== CONSTANTES =====
# Rend le code plus lisible et maintenable
MIN_PAUSE_MINUTES = 5
MAX_PAUSE_MINUTES = 55
PAUSE_WORK_RATIO_PERCENT = 20  # 20% du temps de travail minimum en pause
RATIO_MULTIPLIER = 100  # Pour éviter les décimaux dans les contraintes
MAX_SOLVER_TIME_SECONDS = 30  # AJUSTEMENT : Plus de temps pour explorer les solutions
MAX_MINUTES_PER_DAY = 1440
MIN_SERVICE_DURATION_FOR_PAUSE_RULES = 360  # 6 heures en minutes


def time_to_minutes(time_str):
    """Convertit une heure au format HH:MM en minutes depuis minuit."""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    """Convertit les minutes en format hh:mm lisible."""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}h{m:02d}"


class BusSchedulePrinter(cp_model.CpSolverSolutionCallback):
    """
    Classe pour afficher les solutions trouvées de manière claire.
    Amélioration : ajout de type hints et documentation.
    """

    def __init__(self, assignments: List, trips: List[Dict[str, Any]],
                 order: List = None, max_solutions: int = 5):
        super().__init__()  # Plus pythonique que l'ancienne syntaxe
        self.assignments = assignments
        self.trips = trips
        self.order = order
        self.solution_count = 0
        self.max_solutions = max_solutions

    def OnSolutionCallback(self):
        """Callback appelé à chaque solution trouvée."""
        if self.solution_count >= self.max_solutions:
            return

        print(f"\n🟢 Solution {self.solution_count + 1}:")

        # Regrouper les trajets par service
        service_trips = self._group_trips_by_service()

        # Afficher les résultats de manière organisée
        self._display_solution(service_trips)

        self.solution_count += 1

    def _group_trips_by_service(self) -> Dict[int, List[tuple]]:
        """
        Regroupe les trajets par service.
        Amélioration : extraction en méthode séparée pour plus de clarté.
        """
        service_trips = {}
        for i in range(len(self.trips)):
            service = self.Value(self.assignments[i])
            if service not in service_trips:
                service_trips[service] = []
            order_val = self.Value(self.order[i]) if self.order else i
            service_trips[service].append((order_val, i))
        return service_trips

    def _display_solution(self, service_trips: Dict[int, List[tuple]]):
        """
        Affiche une solution de manière lisible avec durée de prestation.
        """
        for service in sorted(service_trips.keys()):
            # Calcule la durée de prestation pour ce service
            trip_indices = [trip_index for _, trip_index in service_trips[service]]
            service_start = min(self.trips[i]["start"] for i in trip_indices)
            service_end = max(self.trips[i]["end"] for i in trip_indices)
            service_duration = service_end - service_start

            print(f"  🔧 Service {service} (prestation: {minutes_to_time(service_duration)}):")
            for order_val, trip_index in sorted(service_trips[service]):
                trip = self.trips[trip_index]
                start = minutes_to_time(trip["start"])
                end = minutes_to_time(trip["end"])
                duration = trip["end"] - trip["start"]

                # AJUSTEMENT : Indication spéciale pour trajets internes (A → A)
                internal_marker = " [INTERNE]" if trip["from"] == trip["to"] else ""
                print(f"    Trajet-{trip_index} [ordre:{order_val}]: {trip['from']} → {trip['to']} "
                      f"({start}–{end}, {duration}min){internal_marker}")


def create_model_variables(model: cp_model.CpModel, num_trips: int,
                           num_services_max: int) -> tuple:
    """
    Crée les variables du modèle.
    Amélioration : extraction de la logique de création des variables.
    """
    assignments = [
        model.NewIntVar(0, num_services_max - 1, f"service_{i}")
        for i in range(num_trips)
    ]
    order = [
        model.NewIntVar(0, num_trips - 1, f"order_{i}")
        for i in range(num_trips)
    ]
    model.AddAllDifferent(order)

    return assignments, order


def add_first_trip_constraints(model: cp_model.CpModel, assignments: List,
                               order: List, num_trips: int) -> List:
    """
    Ajoute les contraintes pour identifier les premiers trajets.
    Amélioration : extraction en fonction séparée + commentaires explicatifs.
    """
    is_first = [model.NewBoolVar(f"is_first_{j}") for j in range(num_trips)]

    for j in range(num_trips):
        blockers = []  # Trajets qui peuvent "bloquer" j d'être premier

        for i in range(num_trips):
            if i != j:
                # i et j sont-ils sur le même service ?
                same_service = model.NewBoolVar(f"same_service_{i}_{j}_first")
                model.Add(assignments[i] == assignments[j]).OnlyEnforceIf(same_service)
                model.Add(assignments[i] != assignments[j]).OnlyEnforceIf(same_service.Not())

                # i vient-il avant j dans l'ordre ?
                i_before_j = model.NewBoolVar(f"order_{i}_before_{j}_first")
                model.Add(order[i] < order[j]).OnlyEnforceIf(i_before_j)
                model.Add(order[i] >= order[j]).OnlyEnforceIf(i_before_j.Not())

                # i bloque j s'ils sont sur le même service ET i vient avant j
                blocker = model.NewBoolVar(f"blocker_{i}_{j}")
                model.AddBoolAnd([same_service, i_before_j]).OnlyEnforceIf(blocker)
                model.AddBoolOr([same_service.Not(), i_before_j.Not()]).OnlyEnforceIf(blocker.Not())

                blockers.append(blocker)

        # j est premier ssi aucun autre trajet ne le bloque
        if blockers:
            model.AddBoolOr(blockers).OnlyEnforceIf(is_first[j].Not())
            model.AddBoolAnd([b.Not() for b in blockers]).OnlyEnforceIf(is_first[j])

    return is_first


def add_chaining_constraints(model: cp_model.CpModel, assignments: List,
                             order: List, trips: List[Dict], is_first: List):
    """
    Ajoute les contraintes de chaînage (un trajet peut suivre un autre).
    AJUSTEMENT : Traitement spécial des trajets internes A → A.
    """
    num_trips = len(trips)

    for j in range(num_trips):
        valid_predecessors = []

        # Pour chaque trajet j, trouvons tous ses prédécesseurs possibles
        for i in range(num_trips):
            if i != j:
                # AJUSTEMENT : Gestion spéciale des trajets internes
                if trips[i]["from"] == trips[i]["to"]:
                    # Un trajet interne peut être suivi par n'importe quel trajet partant du même arrêt
                    can_chain = (trips[i]["to"] == trips[j]["from"] and
                                 trips[i]["end"] <= trips[j]["start"])
                elif trips[j]["from"] == trips[j]["to"]:
                    # Un trajet interne peut suivre n'importe quel trajet arrivant au même arrêt
                    can_chain = (trips[i]["to"] == trips[j]["from"] and
                                 trips[i]["end"] <= trips[j]["start"])
                else:
                    # Cas normal : destination i = origine j
                    can_chain = (trips[i]["to"] == trips[j]["from"] and
                                 trips[i]["end"] <= trips[j]["start"])

                if can_chain:
                    # Contraintes pour le chaînage valide
                    same_service = model.NewBoolVar(f"chain_same_service_{i}_{j}")
                    model.Add(assignments[i] == assignments[j]).OnlyEnforceIf(same_service)
                    model.Add(assignments[i] != assignments[j]).OnlyEnforceIf(same_service.Not())

                    # i doit venir juste avant j dans l'ordre
                    consecutive_order = model.NewBoolVar(f"consecutive_{i}_{j}")
                    model.Add(order[i] == order[j] - 1).OnlyEnforceIf(consecutive_order)
                    model.Add(order[i] != order[j] - 1).OnlyEnforceIf(consecutive_order.Not())

                    # Chaînage valide = même service ET ordre consécutif
                    valid_chain = model.NewBoolVar(f"valid_chain_{i}_{j}")
                    model.AddBoolAnd([same_service, consecutive_order]).OnlyEnforceIf(valid_chain)
                    model.AddBoolOr([same_service.Not(), consecutive_order.Not()]).OnlyEnforceIf(valid_chain.Not())

                    valid_predecessors.append(valid_chain)

        # Si j n'est pas premier, il DOIT avoir exactement un prédécesseur valide
        if valid_predecessors:
            has_predecessor = model.NewBoolVar(f"has_predecessor_{j}")
            model.AddBoolOr(valid_predecessors).OnlyEnforceIf(has_predecessor)
            model.AddBoolAnd([pred.Not() for pred in valid_predecessors]).OnlyEnforceIf(has_predecessor.Not())

            # j n'est pas premier SI ET SEULEMENT SI il a un prédécesseur
            model.Add(has_predecessor == is_first[j].Not())
        else:
            # Si j n'a aucun prédécesseur possible, il doit être premier
            model.Add(is_first[j] == 1)


def add_overlap_constraints(model: cp_model.CpModel, assignments: List,
                            trips: List[Dict]):
    """
    Empêche les chevauchements temporels sur le même service ET
    les pauses excessives entre trajets consécutifs.
    """
    num_trips = len(trips)

    for i in range(num_trips):
        for j in range(i + 1, num_trips):
            # Vérifie s'il y a chevauchement temporel
            overlap_exists = (trips[i]["start"] < trips[j]["end"] and
                              trips[j]["start"] < trips[i]["end"])

            if overlap_exists:
                # Force les trajets qui se chevauchent sur des services différents
                model.Add(assignments[i] != assignments[j])

    # NOUVELLE CONTRAINTE : Empêche les pauses excessives (> 55min) sur TOUS les services
    for i in range(num_trips):
        for j in range(num_trips):
            if i != j and trips[i]["end"] <= trips[j]["start"]:
                pause_duration = trips[j]["start"] - trips[i]["end"]

                # Si pause > 55min, alors les trajets ne peuvent pas être sur le même service
                if pause_duration > MAX_PAUSE_MINUTES:
                    model.Add(assignments[i] != assignments[j])


def add_service_constraints(model: cp_model.CpModel, assignments: List,
                            trips: List[Dict], num_services_max: int):
    """
    Ajoute les contraintes par service (durées, pauses, etc.).
    NOUVEAU : Contraintes de pause seulement pour services >= 6h de prestation continue.
    """
    num_trips = len(trips)

    for service_id in range(num_services_max):
        # Détermine quels trajets sont assignés à ce service
        trip_assignments = []
        for i in range(num_trips):
            is_on_service = model.NewBoolVar(f"trip_{i}_on_service_{service_id}")
            model.Add(assignments[i] == service_id).OnlyEnforceIf(is_on_service)
            model.Add(assignments[i] != service_id).OnlyEnforceIf(is_on_service.Not())
            trip_assignments.append(is_on_service)

        # Compte le nombre de trajets sur ce service
        nb_trips_on_service = model.NewIntVar(0, num_trips, f"nb_trips_service_{service_id}")
        model.Add(nb_trips_on_service == sum(trip_assignments))

        # Calcule la durée totale de prestation continue (du premier au dernier trajet)
        service_duration = _calculate_service_duration(model, trips, trip_assignments, service_id)

        # Calcule le temps total de travail effectif
        total_work = _calculate_total_work_time(model, trips, trip_assignments, service_id)

        # Calcule le temps total de pause
        total_pause = _calculate_total_pause_time(model, trips, trip_assignments, service_id)

        # NOUVELLE LOGIQUE : Contraintes seulement pour services longs
        # 1. Service doit avoir 2+ trajets ET 6+ heures de prestation
        needs_pause_rules = model.NewBoolVar(f"needs_pause_rules_service_{service_id}")
        has_multiple_trips = model.NewBoolVar(f"multiple_trips_service_{service_id}")
        is_long_service = model.NewBoolVar(f"long_service_{service_id}")

        # Conditions
        model.Add(nb_trips_on_service >= 2).OnlyEnforceIf(has_multiple_trips)
        model.Add(nb_trips_on_service <= 1).OnlyEnforceIf(has_multiple_trips.Not())

        model.Add(service_duration >= MIN_SERVICE_DURATION_FOR_PAUSE_RULES).OnlyEnforceIf(is_long_service)
        model.Add(service_duration < MIN_SERVICE_DURATION_FOR_PAUSE_RULES).OnlyEnforceIf(is_long_service.Not())

        # Les règles s'appliquent SI (2+ trajets) ET (6+ heures)
        model.AddBoolAnd([has_multiple_trips, is_long_service]).OnlyEnforceIf(needs_pause_rules)
        model.AddBoolOr([has_multiple_trips.Not(), is_long_service.Not()]).OnlyEnforceIf(needs_pause_rules.Not())

        # Contraintes de pause seulement pour les services qui en ont besoin
        # 1. Pause minimale de 5min entre trajets
        _add_minimum_pause_constraints(model, trips, trip_assignments, service_id, needs_pause_rules)

        # 2. Contrainte 20% temps travail/pause
        model.Add(total_pause * RATIO_MULTIPLIER >= total_work * PAUSE_WORK_RATIO_PERCENT).OnlyEnforceIf(
            needs_pause_rules)


def _calculate_service_duration(model: cp_model.CpModel, trips: List[Dict],
                                trip_assignments: List, service_id: int):
    """
    Calcule la durée totale de prestation continue pour un service.
    = temps écoulé du début du premier trajet à la fin du dernier trajet.
    """
    num_trips = len(trips)

    # Variables pour le premier et dernier trajet du service
    first_trip_start = model.NewIntVar(0, MAX_MINUTES_PER_DAY, f"first_start_s{service_id}")
    last_trip_end = model.NewIntVar(0, MAX_MINUTES_PER_DAY, f"last_end_s{service_id}")

    # Trouve le début du premier trajet
    min_starts = []
    for i in range(num_trips):
        conditional_start = model.NewIntVar(0, MAX_MINUTES_PER_DAY, f"cond_start_{i}_s{service_id}")
        model.Add(conditional_start == trips[i]["start"]).OnlyEnforceIf(trip_assignments[i])
        model.Add(conditional_start == MAX_MINUTES_PER_DAY).OnlyEnforceIf(trip_assignments[i].Not())
        min_starts.append(conditional_start)

    model.AddMinEquality(first_trip_start, min_starts)

    # Trouve la fin du dernier trajet
    max_ends = []
    for i in range(num_trips):
        conditional_end = model.NewIntVar(0, MAX_MINUTES_PER_DAY, f"cond_end_{i}_s{service_id}")
        model.Add(conditional_end == trips[i]["end"]).OnlyEnforceIf(trip_assignments[i])
        model.Add(conditional_end == 0).OnlyEnforceIf(trip_assignments[i].Not())
        max_ends.append(conditional_end)

    model.AddMaxEquality(last_trip_end, max_ends)

    # Durée de service = fin du dernier - début du premier
    service_duration = model.NewIntVar(0, MAX_MINUTES_PER_DAY, f"duration_s{service_id}")
    model.Add(service_duration == last_trip_end - first_trip_start)

    return service_duration


def _add_minimum_pause_constraints(model: cp_model.CpModel, trips: List[Dict],
                                   trip_assignments: List, service_id: int,
                                   needs_pause_rules):
    """
    Ajoute les contraintes de pause minimale entre trajets consécutifs.
    """
    num_trips = len(trips)

    for i in range(num_trips):
        for j in range(num_trips):
            if i != j and trips[i]["end"] <= trips[j]["start"]:
                # Si les deux trajets sont sur ce service
                both_assigned = model.NewBoolVar(f"both_assigned_{i}_{j}_s{service_id}")
                model.AddBoolAnd([trip_assignments[i], trip_assignments[j]]).OnlyEnforceIf(both_assigned)
                model.AddBoolOr([trip_assignments[i].Not(), trip_assignments[j].Not()]).OnlyEnforceIf(
                    both_assigned.Not())

                # Pause entre les trajets
                pause_duration = trips[j]["start"] - trips[i]["end"]

                # Contrainte pause minimale seulement si service a besoin des règles
                constraint_applies = model.NewBoolVar(f"pause_constraint_{i}_{j}_s{service_id}")
                model.AddBoolAnd([both_assigned, needs_pause_rules]).OnlyEnforceIf(constraint_applies)
                model.AddBoolOr([both_assigned.Not(), needs_pause_rules.Not()]).OnlyEnforceIf(constraint_applies.Not())

                # Si la contrainte s'applique, pause doit être >= 5min
                model.Add(pause_duration >= MIN_PAUSE_MINUTES).OnlyEnforceIf(constraint_applies)


def _calculate_total_work_time(model: cp_model.CpModel, trips: List[Dict],
                               trip_assignments: List, service_id: int):
    """Calcule le temps total de travail pour un service."""
    work_durations = []

    for i, is_assigned in enumerate(trip_assignments):
        duration = trips[i]["end"] - trips[i]["start"]
        work_duration = model.NewIntVar(0, duration, f"work_{i}_s{service_id}")
        model.Add(work_duration == duration).OnlyEnforceIf(is_assigned)
        model.Add(work_duration == 0).OnlyEnforceIf(is_assigned.Not())
        work_durations.append(work_duration)

    total_work = model.NewIntVar(0, MAX_MINUTES_PER_DAY, f"total_work_s{service_id}")
    model.Add(total_work == sum(work_durations))
    return total_work


def _calculate_total_pause_time(model: cp_model.CpModel, trips: List[Dict],
                                trip_assignments: List, service_id: int):
    """Calcule le temps total de pause pour un service."""
    pause_durations = []
    num_trips = len(trips)

    for i in range(num_trips):
        for j in range(num_trips):
            if i != j and trips[i]["end"] <= trips[j]["start"]:
                pause_duration = model.NewIntVar(0, MAX_MINUTES_PER_DAY, f"pause_{i}_{j}_s{service_id}")

                # Si les deux trajets sont sur ce service
                both_assigned = model.NewBoolVar(f"both_assigned_{i}_{j}_s{service_id}")
                model.AddBoolAnd([trip_assignments[i], trip_assignments[j]]).OnlyEnforceIf(both_assigned)
                model.AddBoolOr([trip_assignments[i].Not(), trip_assignments[j].Not()]).OnlyEnforceIf(
                    both_assigned.Not())

                # Calcule la pause et applique la contrainte minimum
                model.Add(pause_duration == trips[j]["start"] - trips[i]["end"]).OnlyEnforceIf(both_assigned)
                model.Add(pause_duration == 0).OnlyEnforceIf(both_assigned.Not())

                pause_durations.append(pause_duration)

    total_pause = model.NewIntVar(0, MAX_MINUTES_PER_DAY, f"total_pause_s{service_id}")
    if pause_durations:
        model.Add(total_pause == sum(pause_durations))
    else:
        model.Add(total_pause == 0)

    return total_pause


def voiturage_ia():
    """
    Fonction principale d'optimisation des trajets.
    CORRIGÉ : Affichage cohérent entre la liste initiale et les solutions.
    """
    print("🚀 Démarrage de l'optimisation des trajets...")

    # Données d'exemple avec les trajets réels
    trips = [
        # Trajet 0: CTSN2 → CTSN1 (05:32-06:28) - A → A (même arrêt CTSN)
        {"start": time_to_minutes("05:32"), "end": time_to_minutes("06:28"), "from": "A", "to": "A"},

        # Trajet 1: GYGAZ → CTSN1 (05:40-07:10)
        {"start": time_to_minutes("05:40"), "end": time_to_minutes("07:10"), "from": "B", "to": "A"},

        # Trajet 2: FLCHE → GYSOA (05:30-06:08)
        {"start": time_to_minutes("05:30"), "end": time_to_minutes("06:08"), "from": "C", "to": "D"},

        # Trajet 3: CTSN1 → CHPA0 (06:50-08:14)
        {"start": time_to_minutes("06:50"), "end": time_to_minutes("08:14"), "from": "A", "to": "E"},

        # Trajet 4: CTSN1 → GYGAZ (06:24-07:59)
        {"start": time_to_minutes("06:24"), "end": time_to_minutes("07:59"), "from": "A", "to": "B"},

        # Trajet 5: GYGAZ → GYSOD (05:33-06:10) - B → D (GYGA vers GYSO)
        {"start": time_to_minutes("05:33"), "end": time_to_minutes("06:10"), "from": "B", "to": "D"},

        # Trajet 6: FLCHE → CHPA9 (06:11-07:29) - C → E (FLCH vers CHPA)
        {"start": time_to_minutes("06:11"), "end": time_to_minutes("07:29"), "from": "C", "to": "E"},

        # Trajet 7: CTSN1 → FLCHE (06:22-07:15)
        {"start": time_to_minutes("06:22"), "end": time_to_minutes("07:15"), "from": "A", "to": "C"},

        # Trajet 8: CTSRO → GYGAZ (06:31-08:06)
        {"start": time_to_minutes("06:31"), "end": time_to_minutes("08:06"), "from": "F", "to": "B"},

        # Trajet 9: CTSN1 → CHPA0 (07:50-09:15)
        {"start": time_to_minutes("07:50"), "end": time_to_minutes("09:15"), "from": "A", "to": "E"},

        # Trajet 10: CTSN1 → GYGAZ (07:21-08:59)
        {"start": time_to_minutes("07:21"), "end": time_to_minutes("08:59"), "from": "A", "to": "B"},

        # Trajet 11: GYGAZ → GYSOD (06:33-07:10) - B → D (GYGA vers GYSO)
        {"start": time_to_minutes("06:33"), "end": time_to_minutes("07:10"), "from": "B", "to": "D"},

        # Trajet 12: FLCHE → CHPA9 (07:04-08:35) - C → E (FLCH vers CHPA)
        {"start": time_to_minutes("07:04"), "end": time_to_minutes("08:35"), "from": "C", "to": "E"},

        # Trajet 13: GYGAZ → CTSN1 (07:25-09:06)
        {"start": time_to_minutes("07:25"), "end": time_to_minutes("09:06"), "from": "B", "to": "A"},

        # Trajet 14: FLCHE → GYSOA (07:30-08:08) - C → D (FLCH vers GYSO)
        {"start": time_to_minutes("07:30"), "end": time_to_minutes("08:08"), "from": "C", "to": "D"},

        # Trajet 15: CTSN1 → CHPA0 (08:50-10:15)
        {"start": time_to_minutes("08:50"), "end": time_to_minutes("10:15"), "from": "A", "to": "E"},

        # Trajet 16: CTSN1 → GYGAZ (08:21-09:59)
        {"start": time_to_minutes("08:21"), "end": time_to_minutes("09:59"), "from": "A", "to": "B"},

        # Trajet 17: CTSRO → FLCHE (07:15-08:08)
        {"start": time_to_minutes("07:15"), "end": time_to_minutes("08:08"), "from": "F", "to": "C"},

        # Trajet 18: FLCHE → CHPA9 (08:04-09:35) - C → E (FLCH vers CHPA)
        {"start": time_to_minutes("08:04"), "end": time_to_minutes("09:35"), "from": "C", "to": "E"},

        # Trajet 19: GYGAZ → CTSN1 (08:25-10:06)
        {"start": time_to_minutes("08:25"), "end": time_to_minutes("10:06"), "from": "B", "to": "A"}
    ]

    # Affichage des trajets d'origine pour référence
    print("\n📋 Trajets à optimiser :")
    for i, trip in enumerate(trips):
        start = minutes_to_time(trip["start"])
        end = minutes_to_time(trip["end"])
        duration = trip["end"] - trip["start"]
        internal_marker = " [INTERNE]" if trip["from"] == trip["to"] else ""
        print(f"  Trajet-{i}: {trip['from']} → {trip['to']} ({start}–{end}, {duration}min){internal_marker}")

    num_trips = len(trips)
    # AJUSTEMENT : Réduction du nombre de services maximum pour forcer plus de regroupements
    num_services_max = 8  # au lieu de 15

    # Création du modèle et des variables
    model = cp_model.CpModel()
    assignments, order = create_model_variables(model, num_trips, num_services_max)

    # Ajout des contraintes par étapes
    print("📝 Ajout des contraintes...")
    is_first = add_first_trip_constraints(model, assignments, order, num_trips)
    add_chaining_constraints(model, assignments, order, trips, is_first)
    add_overlap_constraints(model, assignments, trips)
    add_service_constraints(model, assignments, trips, num_services_max)

    # Configuration et résolution
    print("🔍 Recherche des solutions...")
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = MAX_SOLVER_TIME_SECONDS

    printer = BusSchedulePrinter(assignments, trips, order=order, max_solutions=5)
    status = solver.Solve(model, printer)

    # Résultats
    print(f"\n📊 Statut : {solver.StatusName(status)}")
    print(f"📈 Solutions trouvées : {printer.solution_count}")
    if printer.solution_count == 0:
        print("❌ Aucune solution trouvée. Vérifiez les contraintes.")


if __name__ == "__main__":
    voiturage_ia()