from ortools.sat.python import cp_model
import time
from typing import List, Dict, Any


def time_to_minutes(time_str):
    h, m = map(int, time_str.split(':'))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}h{m:02d}"


class CorrectedODMSolver:
    """Solveur ODM corrigé pour trouver la solution optimale"""

    def __init__(self, trips_data):
        self.trips = trips_data

    def can_chain(self, trip1, trip2):
        """Vérifie si trip2 peut suivre trip1 avec la règle des 4 lettres"""
        # Règle: trip2 commence où trip1 finit (4 premières lettres)
        return trip1["to"][:4] == trip2["from"][:4]

    def test_user_solution(self):
        """Teste la solution proposée par l'utilisateur: voyages 0,1,6,8"""
        print("Test de votre solution: Voyages 0,1,6,8")
        print("=" * 50)

        user_service = [0, 1, 6, 8]

        print("Vérification des contraintes:")

        # Vérifier les chevauchements
        overlaps = False
        for i in range(len(user_service)):
            for j in range(i + 1, len(user_service)):
                trip1 = self.trips[user_service[i]]
                trip2 = self.trips[user_service[j]]
                if trip1["start"] < trip2["end"] and trip2["start"] < trip1["end"]:
                    overlaps = True
                    print(f"  ❌ Chevauchement entre voyage {user_service[i]} et {user_service[j]}")

        if not overlaps:
            print("  ✅ Pas de chevauchement temporel")

        # Trier par heure de début
        sorted_trips = sorted(user_service, key=lambda x: self.trips[x]["start"])

        print(f"\nOrdre chronologique: {sorted_trips}")

        # Vérifier chaînage et pauses
        valid_chain = True
        total_work = 0

        for i, trip_idx in enumerate(sorted_trips):
            trip = self.trips[trip_idx]
            start = minutes_to_time(trip["start"])
            end = minutes_to_time(trip["end"])
            duration = trip["end"] - trip["start"]
            total_work += duration

            print(f"\n  Voyage {trip_idx}: {trip['from']} → {trip['to']} ({start}-{end}, {duration}min)")

            if i < len(sorted_trips) - 1:
                next_trip_idx = sorted_trips[i + 1]
                next_trip = self.trips[next_trip_idx]

                pause = next_trip["start"] - trip["end"]
                can_chain = self.can_chain(trip, next_trip)

                print(f"    Pause jusqu'au voyage {next_trip_idx}: {pause}min")
                print(f"    Chaînage {trip['to'][:4]} → {next_trip['from'][:4]}: {'✅' if can_chain else '❌'}")

                if pause < 5:
                    print(f"    ❌ Pause trop courte ({pause}min < 5min)")
                    valid_chain = False
                elif pause > 120:  # Plus de 2h
                    print(f"    ⚠️ Pause longue ({pause}min)")

                if not can_chain:
                    print(f"    ❌ Pas de chaînage possible")
                    valid_chain = False

        # Statistiques globales
        service_start = min(self.trips[i]["start"] for i in sorted_trips)
        service_end = max(self.trips[i]["end"] for i in sorted_trips)
        amplitude = service_end - service_start
        total_pause = amplitude - total_work

        print(f"\n📊 Statistiques du service:")
        print(f"  Amplitude: {minutes_to_time(amplitude)} ({amplitude}min)")
        print(f"  Temps de travail: {total_work}min")
        print(f"  Temps de pause: {total_pause}min")
        print(f"  Règle 6h: {'✅' if amplitude >= 360 else '❌'} ({'≥' if amplitude >= 360 else '<'}6h)")

        if valid_chain and not overlaps:
            print(f"\n✅ VOTRE SOLUTION EST VALIDE!")
            return True
        else:
            print(f"\n❌ Votre solution a des problèmes")
            return False

    def solve_with_fixed_services(self, target_services):
        """Algorithme avec nombre de services FIXE et impératif"""
        print(f"\nCréation de EXACTEMENT {target_services} services (impératif)")
        print("=" * 60)

        model = cp_model.CpModel()
        n = len(self.trips)

        # Variables d'assignation (de 0 à target_services-1)
        assignments = [model.NewIntVar(0, target_services - 1, f"service_{i}") for i in range(n)]

        # CONTRAINTE IMPÉRATIVE: Utiliser EXACTEMENT target_services services
        services_used = []
        for s in range(target_services):
            used = model.NewBoolVar(f"service_{s}_used")

            trip_vars = []
            for i in range(n):
                on_service = model.NewBoolVar(f"trip_{i}_on_service_{s}")
                model.Add(assignments[i] == s).OnlyEnforceIf(on_service)
                model.Add(assignments[i] != s).OnlyEnforceIf(on_service.Not())
                trip_vars.append(on_service)

            # Service utilisé si au moins un voyage assigné
            model.AddBoolOr(trip_vars).OnlyEnforceIf(used)
            model.AddBoolAnd([v.Not() for v in trip_vars]).OnlyEnforceIf(used.Not())
            services_used.append(used)

        # FORCE: TOUS les services doivent être utilisés
        for s in range(target_services):
            model.Add(services_used[s] == 1)

        print(f"Contrainte impérative: EXACTEMENT {target_services} services utilisés")

        # CONTRAINTE 1: Non-chevauchement
        overlaps = 0
        for i in range(n):
            for j in range(i + 1, n):
                trip1, trip2 = self.trips[i], self.trips[j]
                if trip1["start"] < trip2["end"] and trip2["start"] < trip1["end"]:
                    model.Add(assignments[i] != assignments[j])
                    overlaps += 1
        print(f"Contraintes de chevauchement: {overlaps}")

        # CONTRAINTE 2: Pauses minimum 5min
        pause_constraints = 0
        for i in range(n):
            for j in range(n):
                if i != j:
                    trip1, trip2 = self.trips[i], self.trips[j]
                    if trip1["end"] <= trip2["start"]:
                        pause = trip2["start"] - trip1["end"]
                        if pause < 5:
                            model.Add(assignments[i] != assignments[j])
                            pause_constraints += 1
        print(f"Contraintes de pause courte: {pause_constraints}")

        # OBJECTIF: Maximiser le chaînage parfait
        chain_violations = []

        for s in range(target_services):
            trip_vars = []
            for i in range(n):
                on_service = model.NewBoolVar(f"trip_{i}_on_service_{s}_chain")
                model.Add(assignments[i] == s).OnlyEnforceIf(on_service)
                model.Add(assignments[i] != s).OnlyEnforceIf(on_service.Not())
                trip_vars.append(on_service)

            # Compter violations de chaînage sur ce service
            for i in range(n):
                for j in range(n):
                    if i != j:
                        trip1, trip2 = self.trips[i], self.trips[j]
                        if trip1["end"] <= trip2["start"] - 5:

                            both_on_service = model.NewBoolVar(f"both_chain_{i}_{j}_s{s}")
                            model.AddBoolAnd([trip_vars[i], trip_vars[j]]).OnlyEnforceIf(both_on_service)
                            model.AddBoolOr([trip_vars[i].Not(), trip_vars[j].Not()]).OnlyEnforceIf(
                                both_on_service.Not())

                            can_chain = self.can_chain(trip1, trip2)
                            if not can_chain:
                                chain_violation = model.NewBoolVar(f"violation_{i}_{j}_s{s}")
                                model.Add(chain_violation == both_on_service)
                                chain_violations.append(chain_violation)

        # Objectif: minimiser SEULEMENT les violations de chaînage
        model.Minimize(sum(chain_violations))
        print(f"Objectif: maximiser le chaînage parfait")

        # Résolution
        print(f"Résolution avec {target_services} services fixes...")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60

        start_time = time.time()
        status = solver.Solve(model)
        elapsed = time.time() - start_time

        print(f"Temps: {elapsed:.2f}s | Statut: {solver.StatusName(status)}")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            total_violations = solver.ObjectiveValue()
            print(f"Violations de chaînage: {int(total_violations)}")
            return self._display_fixed_solution(solver, assignments, target_services)
        else:
            print(f"❌ IMPOSSIBLE de créer exactement {target_services} services")
            print("Essayez un nombre différent de services")
            return None
        """Algorithme corrigé pour trouver des solutions comme la vôtre"""
        print(f"\nAlgorithme corrigé pour {len(self.trips)} voyages")
        print("=" * 50)

        model = cp_model.CpModel()
        n = len(self.trips)

        # Variables d'assignation
        assignments = [model.NewIntVar(0, max_services - 1, f"service_{i}") for i in range(n)]

        # CONTRAINTE 1: Non-chevauchement (obligatoire)
        overlaps = 0
        for i in range(n):
            for j in range(i + 1, n):
                trip1, trip2 = self.trips[i], self.trips[j]
                if trip1["start"] < trip2["end"] and trip2["start"] < trip1["end"]:
                    model.Add(assignments[i] != assignments[j])
                    overlaps += 1
        print(f"Contraintes de chevauchement: {overlaps}")

        # CONTRAINTE 2: Pauses minimum 5min (seulement si très proche temporellement)
        pause_constraints = 0
        for i in range(n):
            for j in range(n):
                if i != j:
                    trip1, trip2 = self.trips[i], self.trips[j]
                    if trip1["end"] <= trip2["start"]:
                        pause = trip2["start"] - trip1["end"]
                        if pause < 5:  # Pause trop courte
                            model.Add(assignments[i] != assignments[j])
                            pause_constraints += 1
        print(f"Contraintes de pause courte: {pause_constraints}")

        # CONTRAINTE 3: Chaînage PERMISSIF (pas trop restrictif)
        chain_constraints = 0
        for service_id in range(max_services):
            # Identifier les voyages sur ce service
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
                        if trip1["end"] <= trip2["start"] - 5:  # Au moins 5min de pause

                            # Les deux voyages sont sur ce service?
                            both_on_service = model.NewBoolVar(f"both_{i}_{j}_s{service_id}")
                            model.AddBoolAnd([trips_on_service[i], trips_on_service[j]]).OnlyEnforceIf(both_on_service)
                            model.AddBoolOr([trips_on_service[i].Not(), trips_on_service[j].Not()]).OnlyEnforceIf(
                                both_on_service.Not())

                            # Peuvent-ils se chaîner?
                            can_chain = self.can_chain(trip1, trip2)
                            time_gap = trip2["start"] - trip1["end"]

                            # NOUVELLE LOGIQUE: seulement interdire si vraiment impossible
                            if not can_chain and time_gap > 180:  # Plus de 3h SANS chaînage
                                # C'est probablement deux services différents
                                model.Add(both_on_service == 0)
                                chain_constraints += 1

                            # Sinon, on permet (même sans chaînage parfait si temps raisonnable)

        print(f"Contraintes de chaînage strict: {chain_constraints}")

        # OBJECTIF AMÉLIORÉ: Minimiser services ET maximiser le chaînage parfait
        services_used = []
        chain_violations = []

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

            # Compter les violations de chaînage sur ce service
            for i in range(n):
                for j in range(n):
                    if i != j:
                        trip1, trip2 = self.trips[i], self.trips[j]
                        if trip1["end"] <= trip2["start"] - 5:

                            # Les deux sur ce service ?
                            both_on_service = model.NewBoolVar(f"both_chain_{i}_{j}_s{s}")
                            model.AddBoolAnd([trip_vars[i], trip_vars[j]]).OnlyEnforceIf(both_on_service)
                            model.AddBoolOr([trip_vars[i].Not(), trip_vars[j].Not()]).OnlyEnforceIf(
                                both_on_service.Not())

                            # Violation si même service MAIS pas de chaînage
                            can_chain = self.can_chain(trip1, trip2)
                            if not can_chain:
                                chain_violation = model.NewBoolVar(f"violation_{i}_{j}_s{s}")
                                model.Add(chain_violation == both_on_service)
                                chain_violations.append(chain_violation)

        # Objectif: minimiser services (priorité 1000) + violations chaînage (priorité 100)
        model.Minimize(1000 * sum(services_used) + 100 * sum(chain_violations))

        # Résolution
        print("Résolution avec contraintes assouplies...")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30

        start_time = time.time()
        status = solver.Solve(model)
        elapsed = time.time() - start_time

        print(f"Temps: {elapsed:.2f}s | Statut: {solver.StatusName(status)}")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._display_corrected_solution(solver, assignments)
        else:
            print("❌ Échec même avec contraintes assouplies")
            return None

    def _display_corrected_solution(self, solver, assignments):
        """Affiche la solution corrigée"""
        services = {}
        for i, trip in enumerate(self.trips):
            service_id = solver.Value(assignments[i])
            if service_id not in services:
                services[service_id] = []
            services[service_id].append((i, trip))

        print(f"\n✅ Solution trouvée: {len(services)} services")
        print("=" * 60)

        for service_id in sorted(services.keys()):
            trip_list = services[service_id]
            trip_list.sort(key=lambda x: x[1]["start"])

            voyage_ids = [trip_idx for trip_idx, _ in trip_list]
            print(f"\nService {service_id}: Voyages {voyage_ids}")

            total_work = 0
            for trip_idx, trip in trip_list:
                start = minutes_to_time(trip["start"])
                end = minutes_to_time(trip["end"])
                duration = trip["end"] - trip["start"]
                total_work += duration

                print(f"  Voyage-{trip_idx}: {trip['from']} → {trip['to']} ({start}-{end}, {duration}min)")

            # Stats du service
            if len(trip_list) > 1:
                trips_only = [trip for _, trip in trip_list]
                service_start = min(t["start"] for t in trips_only)
                service_end = max(t["end"] for t in trips_only)
                amplitude = service_end - service_start
                total_pause = amplitude - total_work

                print(
                    f"  📊 Amplitude: {minutes_to_time(amplitude)} | Travail: {total_work}min | Pause: {total_pause}min")

                # Vérifier le chaînage
                chain_issues = []
                for i in range(len(trip_list) - 1):
                    trip1 = trip_list[i][1]
                    trip2 = trip_list[i + 1][1]
                    pause = trip2["start"] - trip1["end"]
                    can_chain = self.can_chain(trip1, trip2)

                    if pause < 5:
                        chain_issues.append(f"pause {pause}min")
                    if not can_chain:
                        chain_issues.append(f"pas de chaînage {trip1['to'][:4]}≠{trip2['from'][:4]}")

                if chain_issues:
                    print(f"  ⚠️ Issues: {'; '.join(chain_issues)}")
                else:
                    print(f"  ✅ Toutes contraintes OK")

                if amplitude >= 360:
                    print(f"  ✅ Service ≥6h")
                else:
                    print(f"  ⚠️ Service <6h")

    def _display_fixed_solution(self, solver, assignments, target_services):
        """Affiche la solution avec nombre de services fixe"""
        services = {}
        for i, trip in enumerate(self.trips):
            service_id = solver.Value(assignments[i])
            if service_id not in services:
                services[service_id] = []
            services[service_id].append((i, trip))

        print(f"\n✅ Solution avec EXACTEMENT {target_services} services:")
        print("=" * 70)

        # Vérifier que tous les services sont bien utilisés
        services_used_count = len([s for s in services.values() if len(s) > 0])
        print(f"Services créés: {services_used_count}/{target_services}")

        total_chain_violations = 0
        services_6h_plus = 0

        for service_id in range(target_services):
            if service_id in services:
                trip_list = services[service_id]
                trip_list.sort(key=lambda x: x[1]["start"])

                voyage_ids = [trip_idx for trip_idx, _ in trip_list]
                print(f"\nService {service_id}: Voyages {voyage_ids}")

                total_work = 0
                for trip_idx, trip in trip_list:
                    start = minutes_to_time(trip["start"])
                    end = minutes_to_time(trip["end"])
                    duration = trip["end"] - trip["start"]
                    total_work += duration

                    print(f"  Voyage-{trip_idx}: {trip['from']} → {trip['to']} ({start}-{end}, {duration}min)")

                # Stats du service
                if len(trip_list) > 1:
                    trips_only = [trip for _, trip in trip_list]
                    service_start = min(t["start"] for t in trips_only)
                    service_end = max(t["end"] for t in trips_only)
                    amplitude = service_end - service_start
                    total_pause = amplitude - total_work

                    print(
                        f"  📊 Amplitude: {minutes_to_time(amplitude)} | Travail: {total_work}min | Pause: {total_pause}min")

                    # Vérifier le chaînage
                    chain_violations = 0
                    chain_details = []

                    for i in range(len(trip_list) - 1):
                        trip1 = trip_list[i][1]
                        trip2 = trip_list[i + 1][1]
                        pause = trip2["start"] - trip1["end"]
                        can_chain = self.can_chain(trip1, trip2)

                        if pause < 5:
                            chain_details.append(f"pause {pause}min")
                        if not can_chain:
                            chain_details.append(f"chaînage {trip1['to'][:4]}≠{trip2['from'][:4]}")
                            chain_violations += 1

                    total_chain_violations += chain_violations

                    if chain_details:
                        print(f"  ⚠️ Issues: {'; '.join(chain_details)}")
                    else:
                        print(f"  ✅ Chaînage parfait")

                    if amplitude >= 360:
                        print(f"  ✅ Service ≥6h")
                        services_6h_plus += 1
                    else:
                        print(f"  ⚠️ Service <6h ({minutes_to_time(amplitude)})")
                else:
                    print(f"  📊 Service à 1 voyage")
            else:
                print(f"\nService {service_id}: VIDE")

        # Résumé global
        print(f"\n📊 RÉSUMÉ:")
        print(f"  Services créés: {target_services} (comme demandé)")
        print(f"  Services ≥6h: {services_6h_plus}/{target_services}")
        print(f"  Violations de chaînage: {total_chain_violations}")

        if total_chain_violations == 0:
            print(f"  🎯 CHAÎNAGE PARFAIT! Solution optimale.")

        return services


def run_interactive_solver():
    """Lance le solveur interactif avec choix du nombre de services"""

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

    solver = CorrectedODMSolver(trips)

    print("SOLVEUR ODM INTERACTIF")
    print("=" * 40)
    print(f"Nombre de voyages à organiser: {len(trips)}")
    print()

    while True:
        try:
            target_services = int(input("Combien de services souhaitez-vous créer ? "))

            if target_services <= 0:
                print("Le nombre de services doit être positif!")
                continue
            elif target_services > len(trips):
                print(f"Maximum {len(trips)} services possible (1 voyage par service)")
                continue

            print()
            solution = solver.solve_with_fixed_services(target_services)

            if solution:
                print(f"\n🎯 Mission accomplie: {target_services} services créés!")

                # Demander si l'utilisateur veut essayer un autre nombre
                retry = input("\nVoulez-vous essayer avec un autre nombre de services ? (o/n): ").lower()
                if retry != 'o':
                    break
            else:
                print(f"\nImpossible avec {target_services} services.")
                retry = input("Essayer avec un autre nombre ? (o/n): ").lower()
                if retry != 'o':
                    break

            print("\n" + "=" * 60)

        except ValueError:
            print("Veuillez entrer un nombre valide!")
        except KeyboardInterrupt:
            print("\nAu revoir!")
            break


def run_corrected_test():
    """Test avec l'algorithme corrigé"""

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

    solver = CorrectedODMSolver(trips)

    print("ALGORITHME ODM CORRIGÉ")
    print("=" * 30)

    # 1. Tester votre solution
    user_solution_valid = solver.test_user_solution()

    # 2. Essayer l'algorithme corrigé
    if user_solution_valid:
        print("\nVotre solution est valide. Essayons de la retrouver avec l'algo...")
        solution = solver.solve_corrected()

        if solution:
            # Vérifier si on a trouvé votre combinaison
            found_user_combo = False
            for service_trips in solution.values():
                trip_ids = sorted([trip_idx for trip_idx, _ in service_trips])
                if trip_ids == [0, 1, 6, 8]:
                    found_user_combo = True
                    print(f"\n🎯 TROUVÉ! L'algorithme a retrouvé votre combinaison optimale: {trip_ids}")
                    break

            if not found_user_combo:
                print(f"\n⚠️ L'algorithme n'a pas trouvé votre combinaison exacte")
                print("Il faut encore ajuster les contraintes...")


if __name__ == "__main__":
    run_interactive_solver()