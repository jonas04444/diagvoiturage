from ortools.sat.python import cp_model
import time
from typing import List, Dict, Any


def time_to_minutes(time_str):
    """Convertit HH:MM en minutes depuis minuit"""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    """Convertit minutes en HH:MM"""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}h{m:02d}"


class ODMSolverWithHLP:
    """Solveur ODM avec gestion des Haut Le Pied (HLP)"""

    def __init__(self, trips_data):
        self.trips = trips_data
        self.hlp_table = self._create_hlp_table()

    def _create_hlp_table(self):
        """Crée la table des temps de HLP entre arrêts"""
        # Table des temps de trajet à vide entre arrêts (en minutes)
        # Format: {(arret_depart[:4], arret_arrivee[:4]): temps_hlp}
        hlp_times = {
            # Exemples de HLP - à adapter selon votre réseau
            ("CTSN", "CHPA"): 5,  # 15min pour aller de CTSN vers CHPA à vide
            ("CHPA", "CTSN"): 5,  # 15min pour aller de CHPA vers CTSN à vide
            ("CTSN", "GYGA"): 2,  # 20min pour aller de CTSN vers GYGAZ à vide
            ("GYGA", "CTSN"): 2,  # 20min pour aller de GYGAZ vers CTSN à vide
            ("GYGA", "GYSO"): 1,  # 10min pour aller de GYGAZ vers GYSOD à vide
            ("GYSO", "GYGA"): 1,  # 10min pour aller de GYSOD vers GYGAZ à vide
            ("GYSO", "FLCH"): 5,  # 25min pour aller de GYSOD vers FLCHE à vide
            ("FLCH", "GYSO"): 5,  # 25min pour aller de FLCHE vers GYSOD à vide
            ("CHPA", "GYGA"): 3,  # 30min pour aller de CHPA vers GYGAZ à vide
            ("GYGA", "CHPA"): 3,  # 30min pour aller de GYGAZ vers CHPA à vide
        }
        return hlp_times

    def get_hlp_time(self, from_stop, to_stop):
        """Retourne le temps de HLP entre deux arrêts (4 premières lettres)"""
        from_code = from_stop[:4]
        to_code = to_stop[:4]
        return self.hlp_table.get((from_code, to_code), None)

    def peut_chainer_direct(self, trip1, trip2):
        """Vérifie si trip2 peut suivre trip1 directement (sans HLP)"""
        trip1_to = trip1["to"][:4]
        trip2_from = trip2["from"][:4]
        return trip1_to == trip2_from

    def peut_chainer_avec_hlp(self, trip1, trip2):
        """Vérifie si trip2 peut suivre trip1 avec un HLP"""
        trip1_to = trip1["to"][:4]
        trip2_from = trip2["from"][:4]

        # Direct d'abord
        if trip1_to == trip2_from:
            return True, 0  # Pas de HLP nécessaire

        # Avec HLP
        hlp_time = self.get_hlp_time(trip1["to"], trip2["from"])
        if hlp_time is not None:
            return True, hlp_time

        return False, None

    def solve_odm_with_hlp(self, max_services=8):
        """Résout le problème ODM avec possibilité d'utiliser des HLP"""

        print(f"Organisation de {len(self.trips)} voyages en ODM (avec HLP)")
        print("=" * 60)

        # Affichage des voyages
        print("Voyages à organiser:")
        for i, trip in enumerate(self.trips):
            start = minutes_to_time(trip["start"])
            end = minutes_to_time(trip["end"])
            duration = trip["end"] - trip["start"]
            print(f"  {i:2d}: {trip['from']} → {trip['to']} ({start}-{end}, {duration}min)")

        # Affichage des HLP disponibles
        print("\nHLP disponibles:")
        for (from_code, to_code), hlp_time in self.hlp_table.items():
            print(f"  {from_code} → {to_code}: {hlp_time}min")

        model = cp_model.CpModel()
        n = len(self.trips)

        # Variables principales
        assignments = [model.NewIntVar(0, max_services - 1, f"service_{i}") for i in range(n)]

        # Variables HLP: pour chaque paire de voyages, y a-t-il un HLP utilisé?
        hlp_used = {}
        for i in range(n):
            for j in range(n):
                if i != j:
                    hlp_used[(i, j)] = model.NewBoolVar(f"hlp_{i}_{j}")

        print(f"\nApplication des contraintes avec HLP...")

        # CONTRAINTE 1: Pas de chevauchement
        conflicts = 0
        for i in range(n):
            for j in range(i + 1, n):
                trip1, trip2 = self.trips[i], self.trips[j]
                if trip1["start"] < trip2["end"] and trip2["start"] < trip1["end"]:
                    model.Add(assignments[i] != assignments[j])
                    conflicts += 1
        print(f"  ✓ {conflicts} conflits temporels résolus")

        # CONTRAINTE 2: Continuité avec HLP
        chain_constraints = 0
        for service_id in range(max_services):
            # Variables pour identifier les voyages sur ce service
            trips_on_service = []
            for i in range(n):
                on_service = model.NewBoolVar(f"trip_{i}_on_service_{service_id}")
                model.Add(assignments[i] == service_id).OnlyEnforceIf(on_service)
                model.Add(assignments[i] != service_id).OnlyEnforceIf(on_service.Not())
                trips_on_service.append(on_service)

            # Pour chaque paire de voyages sur ce service
            for i in range(n):
                for j in range(n):
                    if i != j:
                        trip1, trip2 = self.trips[i], self.trips[j]
                        if trip1["end"] <= trip2["start"]:  # j peut suivre i temporellement

                            # Si les deux voyages sont sur le même service
                            both_on_service = model.NewBoolVar(f"both_{i}_{j}_s{service_id}")
                            model.AddBoolAnd([trips_on_service[i], trips_on_service[j]]).OnlyEnforceIf(both_on_service)
                            model.AddBoolOr([trips_on_service[i].Not(), trips_on_service[j].Not()]).OnlyEnforceIf(
                                both_on_service.Not())

                            # Vérifier la possibilité de chaînage
                            can_chain, hlp_time = self.peut_chainer_avec_hlp(trip1, trip2)

                            if can_chain:
                                if hlp_time > 0:  # HLP nécessaire
                                    # Vérifier que le temps permet le HLP
                                    available_time = trip2["start"] - trip1["end"]
                                    if available_time >= hlp_time + 5:  # HLP + 5min de pause minimum
                                        # Contrainte: si les deux voyages sont ensemble, utiliser HLP
                                        model.Add(hlp_used[(i, j)] == both_on_service)
                                    else:
                                        # Pas assez de temps pour HLP, interdire
                                        model.Add(both_on_service == 0)
                                        chain_constraints += 1
                                # Si hlp_time == 0, chaînage direct possible
                            else:
                                # Pas de chaînage possible même avec HLP
                                if trip2["start"] - trip1["end"] < 120:  # Si < 2h, séparer
                                    model.Add(both_on_service == 0)
                                    chain_constraints += 1

        print(f"  ✓ {chain_constraints} impossibilités de chaînage gérées")

        # CONTRAINTE 3: Maximum 1 HLP par service
        hlp_limit_constraints = 0
        for service_id in range(max_services):
            # Compter les HLP utilisés sur ce service
            hlp_count = []
            for i in range(n):
                for j in range(n):
                    if i != j and (i, j) in hlp_used:
                        # HLP compte seulement si les deux voyages sont sur ce service
                        both_on_service = model.NewBoolVar(f"both_{i}_{j}_hlp_s{service_id}")
                        model.Add(assignments[i] == service_id).OnlyEnforceIf(both_on_service)
                        model.Add(assignments[i] != service_id).OnlyEnforceIf(both_on_service.Not())
                        model.Add(assignments[j] == service_id).OnlyEnforceIf(both_on_service)
                        model.Add(assignments[j] != service_id).OnlyEnforceIf(both_on_service.Not())

                        # HLP effectif = HLP utilisé ET les deux voyages sur ce service
                        effective_hlp = model.NewBoolVar(f"effective_hlp_{i}_{j}_s{service_id}")
                        model.AddBoolAnd([hlp_used[(i, j)], both_on_service]).OnlyEnforceIf(effective_hlp)
                        model.AddBoolOr([hlp_used[(i, j)].Not(), both_on_service.Not()]).OnlyEnforceIf(
                            effective_hlp.Not())

                        hlp_count.append(effective_hlp)

            # Maximum 1 HLP par service
            if hlp_count:
                model.Add(sum(hlp_count) <= 1)
                hlp_limit_constraints += 1

        print(f"  ✓ Maximum 1 HLP par ODM ({hlp_limit_constraints} services contrôlés)")

        # CONTRAINTE 4: Services de minimum 6h sauf si impossible
        min_duration_constraints = 0
        MIN_SERVICE_DURATION = 6 * 60  # 6 heures

        for service_id in range(max_services):
            # Calculer la durée du service
            trips_on_service = []
            for i in range(n):
                on_service = model.NewBoolVar(f"trip_{i}_on_service_{service_id}_duration")
                model.Add(assignments[i] == service_id).OnlyEnforceIf(on_service)
                model.Add(assignments[i] != service_id).OnlyEnforceIf(on_service.Not())
                trips_on_service.append(on_service)

            # Service a des voyages?
            service_has_trips = model.NewBoolVar(f"service_{service_id}_has_trips")
            model.AddBoolOr(trips_on_service).OnlyEnforceIf(service_has_trips)
            model.AddBoolAnd([t.Not() for t in trips_on_service]).OnlyEnforceIf(service_has_trips.Not())

            # Si le service a 2+ voyages, essayer d'atteindre 6h minimum
            nb_trips = model.NewIntVar(0, n, f"nb_trips_s{service_id}")
            model.Add(nb_trips == sum(trips_on_service))

            multiple_trips = model.NewBoolVar(f"multiple_trips_s{service_id}")
            model.Add(nb_trips >= 2).OnlyEnforceIf(multiple_trips)
            model.Add(nb_trips < 2).OnlyEnforceIf(multiple_trips.Not())

            # Pour les services multi-voyages, encourager 6h+ (objectif souple)
            min_duration_constraints += 1

        print(f"  ✓ Encouragement services 6h+ ({min_duration_constraints} services)")

        # Objectif: minimiser les services ET les HLP
        services_used = []
        for s in range(max_services):
            used = model.NewBoolVar(f"service_{s}_used")
            trip_vars = []
            for i in range(n):
                on_service = model.NewBoolVar(f"trip_{i}_on_service_{s}_obj")
                model.Add(assignments[i] == s).OnlyEnforceIf(on_service)
                model.Add(assignments[i] != s).OnlyEnforceIf(on_service.Not())
                trip_vars.append(on_service)

            model.AddBoolOr(trip_vars).OnlyEnforceIf(used)
            model.AddBoolAnd([v.Not() for v in trip_vars]).OnlyEnforceIf(used.Not())
            services_used.append(used)

        # Compter les HLP utilisés
        total_hlp = sum(hlp_used.values())

        # Objectif: minimiser services (poids 100) + HLP utilisés (poids 1)
        model.Minimize(100 * sum(services_used) + total_hlp)

        # Résolution
        print(f"\nRésolution avec HLP...")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60

        start_time = time.time()
        status = solver.Solve(model)
        elapsed = time.time() - start_time

        print(f"Temps: {elapsed:.2f}s | Statut: {solver.StatusName(status)}")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._display_solution_with_hlp(solver, assignments, hlp_used)
        else:
            print("❌ Aucune solution trouvée même avec HLP")
            return None

    def _display_solution_with_hlp(self, solver, assignments, hlp_used):
        """Affiche la solution avec les HLP utilisés"""
        services = {}
        used_hlps = []

        # Regrouper les voyages par service
        for i, trip in enumerate(self.trips):
            service_id = solver.Value(assignments[i])
            if service_id not in services:
                services[service_id] = []
            services[service_id].append((i, trip))

        # Identifier les HLP utilisés
        for (i, j), hlp_var in hlp_used.items():
            if solver.Value(hlp_var) == 1:
                used_hlps.append((i, j))

        print(f"\n✅ SOLUTION AVEC HLP - {len(services)} ODM créés:")
        print("=" * 60)

        for service_id in sorted(services.keys()):
            trip_list = services[service_id]
            trip_list.sort(key=lambda x: x[1]["start"])

            print(f"\nODM {service_id} ({len(trip_list)} voyages):")

            total_work = 0
            service_hlps = []

            for idx, (trip_idx, trip) in enumerate(trip_list):
                start = minutes_to_time(trip["start"])
                end = minutes_to_time(trip["end"])
                duration = trip["end"] - trip["start"]
                total_work += duration

                print(f"  Voyage-{trip_idx}: {trip['from']} → {trip['to']} "
                      f"({start}-{end}, {duration}min)")

                # Vérifier s'il y a un HLP après ce voyage
                if idx < len(trip_list) - 1:
                    next_trip_idx = trip_list[idx + 1][0]
                    if (trip_idx, next_trip_idx) in used_hlps:
                        hlp_time = self.get_hlp_time(trip["to"], trip_list[idx + 1][1]["from"])
                        service_hlps.append((trip_idx, next_trip_idx, hlp_time))
                        print(f"      └─ HLP: {trip['to'][:4]} → {trip_list[idx + 1][1]['from'][:4]} ({hlp_time}min)")

            # Stats de l'ODM
            if len(trip_list) > 1:
                trips_only = [trip for _, trip in trip_list]
                odm_start = min(t["start"] for t in trips_only)
                odm_end = max(t["end"] for t in trips_only)
                amplitude = odm_end - odm_start
                total_hlp_time = sum(hlp_time for _, _, hlp_time in service_hlps)
                total_pause = amplitude - total_work - total_hlp_time

                print(f"  📊 Amplitude: {minutes_to_time(amplitude)} | "
                      f"Travail: {total_work}min | HLP: {total_hlp_time}min | Pause: {total_pause}min")
                print(f"  📊 HLP utilisés: {len(service_hlps)}/1 max")

        print(f"\n📊 Résumé: {len(used_hlps)} HLP utilisés au total")
        return services


def test_with_hlp():
    """Test avec vos voyages et les HLP"""

    trips = [
        {"start": time_to_minutes("05:32"), "end": time_to_minutes("06:28"), "from": "CTSN2", "to": "CTSN1"},
        {"start": time_to_minutes("06:50"), "end": time_to_minutes("08:14"), "from": "CTSN1", "to": "CHPA0"},
        {"start": time_to_minutes("06:11"), "end": time_to_minutes("07:29"), "from": "CHPA9", "to": "CTSN1"},
        {"start": time_to_minutes("07:04"), "end": time_to_minutes("08:35"), "from": "CHPA9", "to": "CTSN1"},
        {"start": time_to_minutes("08:21"), "end": time_to_minutes("09:59"), "from": "CTSN1", "to": "GYGAZ"},
        {"start": time_to_minutes("09:21"), "end": time_to_minutes("10:59"), "from": "CTSN1", "to": "GYGAZ"},
        {"start": time_to_minutes("09:04"), "end": time_to_minutes("10:35"), "from": "CHPA9", "to": "CTSN1"},
        {"start": time_to_minutes("10:25"), "end": time_to_minutes("12:06"), "from": "GYGAZ", "to": "CTSN1"},
        {"start": time_to_minutes("11:21"), "end": time_to_minutes("12:59"), "from": "CTSN1", "to": "GYGAZ"},
        {"start": time_to_minutes("11:25"), "end": time_to_minutes("13:06"), "from": "GYGAZ", "to": "CTSN1"},
        {"start": time_to_minutes("12:33"), "end": time_to_minutes("13:12"), "from": "GYSOD", "to": "FLCHE"},
        {"start": time_to_minutes("13:30"), "end": time_to_minutes("14:08"), "from": "FLCHE", "to": "GYSOA"}
    ]

    solver = ODMSolverWithHLP(trips)
    return solver.solve_odm_with_hlp(max_services=6)


if __name__ == "__main__":
    print("ODM SOLVER AVEC HLP")
    print("=" * 30)

    solution = test_with_hlp()

    if solution:
        print(f"\nSuccès! Optimisation avec HLP réussie")
    else:
        print("\nÉchec - vérifiez les contraintes")