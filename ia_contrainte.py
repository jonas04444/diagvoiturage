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
MAX_SOLVER_TIME_SECONDS = 10
MAX_MINUTES_PER_DAY = 1440
MIN_SERVICE_DURATION_FOR_PAUSE_RULES = 360  # 6 heures en minutes


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
                print(f"    Trajet-{trip_index} [ordre:{order_val}]: {trip['from']} → {trip['to']} "
                      f"({start}–{end}, {duration}min)")


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
    CORRIGÉ : Logique de chaînage renforcée pour garantir la continuité.
    """
    num_trips = len(trips)

    for j in range(num_trips):
        valid_predecessors = []

        # Pour chaque trajet j, trouvons tous ses prédécesseurs possibles
        for i in range(num_trips):
            if i != j:
                # Vérifie si i peut précéder j (destination i = origine j + temps compatible)
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

    # Données d'exemple
    trips = [
        # === Trajets originaux ===
        {"start": 383, "end": 418, "from": "A", "to": "B"},  # Trajet-0 (06h23-06h58)
        {"start": 390, "end": 420, "from": "B", "to": "A"},  # Trajet-1 (06h30-07h00) - CONFLIT avec 0
        {"start": 425, "end": 455, "from": "A", "to": "C"},  # Trajet-2 (07h05-07h35)
        {"start": 460, "end": 490, "from": "C", "to": "D"},  # Trajet-3 (07h40-08h10)
        {"start": 500, "end": 530, "from": "D", "to": "A"},  # Trajet-4 (08h20-08h50)

        # Chaîne alternative longue
        {"start": 420, "end": 440, "from": "A", "to": "H"},  # Trajet-5 (07h00-07h20)
        {"start": 445, "end": 465, "from": "H", "to": "I"},  # Trajet-6 (07h25-07h45) → chaîne avec 5
        {"start": 470, "end": 500, "from": "I", "to": "J"},  # Trajet-7 (07h50-08h20) → chaîne avec 6
        {"start": 505, "end": 525, "from": "J", "to": "A"},  # Trajet-8 (08h25-08h45) → chaîne avec 7
    ]

    # Affichage des trajets d'origine pour référence
    print("\n📋 Trajets à optimiser :")
    for i, trip in enumerate(trips):
        start = minutes_to_time(trip["start"])
        end = minutes_to_time(trip["end"])
        duration = trip["end"] - trip["start"]
        print(f"  Trajet-{i}: {trip['from']} → {trip['to']} ({start}–{end}, {duration}min)")

    num_trips = len(trips)
    num_services_max = 5

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

    printer = BusSchedulePrinter(assignments, trips, order=order, max_solutions=10)
    status = solver.Solve(model, printer)

    # Résultats
    print(f"\n📊 Statut : {solver.StatusName(status)}")
    print(f"📈 Solutions trouvées : {printer.solution_count}")
    if printer.solution_count == 0:
        print("❌ Aucune solution trouvée. Vérifiez les contraintes.")


if __name__ == "__main__":
    voiturage_ia()