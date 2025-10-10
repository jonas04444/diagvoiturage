from ortools.sat.python import cp_model
import time
from typing import List, Dict, Any, Tuple
from itertools import combinations


def time_to_minutes(time_str):
    h, m = map(int, time_str.split(':'))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}h{m:02d}"


class AdvancedODMSolver:
    """Solveur ODM avancé avec contraintes de chaînage strictes et gestion HLP"""

    def __init__(self, trips_data):
        self.trips = trips_data
        self.MIN_SERVICE_DURATION = 3 * 60
        self.MAX_SERVICE_DURATION = 9 * 60
        self.TARGET_SERVICE_DURATION = 7.5 * 60
        self.TOLERANCE = 30
        self.MIN_PAUSE = 5
        self.MAX_PAUSE = 1 * 120

        # HLP (Haut-Le-Pied) autorisés - SEULEMENT 2
        self.hlp_connections = [
            {"from": "PTSNC", "to": "CPCEC", "duration": 5},
            {"from": "CPCEC", "to": "PTSNC", "duration": 6}
        ]
        self.max_hlp_per_service = 2

    def can_chain(self, trip1, trip2):
        """Vérifie si trip2 peut suivre trip1 avec la règle des 4 lettres"""
        return trip1["to"][:4] == trip2["from"][:4]

    def can_chain_with_hlp(self, trip1, trip2):
        """Vérifie si trip2 peut suivre trip1 avec un HLP si nécessaire"""
        if self.can_chain(trip1, trip2):
            return {"direct": True, "hlp": None}

        for hlp in self.hlp_connections:
            if trip1["to"][:4] == hlp["from"][:4] and hlp["to"][:4] == trip2["from"][:4]:
                return {"direct": False, "hlp": hlp}

        return {"direct": False, "hlp": None}

    def solve_morning_afternoon(self, nb_services_matin, nb_services_aprem):
        """Résout avec génération de plusieurs solutions alternatives"""
        print(f"CRÉATION DE SERVICES MATIN/APRÈS-MIDI (SOLUTIONS MULTIPLES)")
        print("=" * 60)
        print(f"Services matin demandés: {nb_services_matin}")
        print(f"Services après-midi demandés: {nb_services_aprem}")

        all_chains = self._generate_valid_chains_strict()

        if not all_chains:
            print("❌ Aucune chaîne valide trouvée!")
            return {'solutions': [], 'selected': None}

        print(f"\n🔍 {len(all_chains)} chaînes STRICTEMENT valides trouvées")

        print("\n📋 Chaînes importantes (6+ voyages):")
        important_chains = [c for c in all_chains if len(c['trip_indices']) >= 6]
        for chain in important_chains[:10]:
            trips_str = ','.join(str(idx) for idx in chain['trip_indices'])
            start = minutes_to_time(chain['start_time'])
            end = minutes_to_time(chain['end_time'])
            amplitude = chain['amplitude'] / 60
            print(f"   [{trips_str}] {start}-{end} ({amplitude:.1f}h)")

        noon = 12 * 60
        morning_chains = [c for c in all_chains if c['start_time'] < noon]
        afternoon_chains = [c for c in all_chains if c['start_time'] >= noon]

        print(f"\n   - Chaînes matin: {len(morning_chains)}")
        print(f"   - Chaînes après-midi: {len(afternoon_chains)}")

        solutions = self._generate_multiple_solutions(
            morning_chains, afternoon_chains,
            nb_services_matin, nb_services_aprem
        )

        if not solutions:
            print("❌ Aucune solution trouvée")
            return {'solutions': [], 'selected': None}

        self._display_multiple_solutions(solutions)
        selected_solution = self._user_select_solution(solutions)

        return {'solutions': solutions, 'selected': selected_solution}

    def _generate_multiple_solutions(self, morning_chains, afternoon_chains, nb_matin, nb_aprem):
        """Génère TOUTES les solutions possibles"""
        print(f"\n🔄 Recherche de TOUTES les solutions possibles...")
        print(f"Configuration demandée: {nb_matin} matin + {nb_aprem} après-midi")

        all_solutions = self._find_all_solutions(
            morning_chains, afternoon_chains, nb_matin, nb_aprem
        )

        if not all_solutions:
            print("❌ Aucune solution trouvée pour cette configuration")
            return []

        for i, solution in enumerate(all_solutions):
            solution['id'] = f'SOL{i + 1}'
            solution['name'] = f'Solution {i + 1}'
            solution['score'] = self._calculate_solution_score(solution)

        all_solutions.sort(key=lambda s: s['score'], reverse=True)
        print(f"🎯 {len(all_solutions)} solution(s) trouvée(s) et triée(s) par qualité")
        return all_solutions

    def _find_all_solutions(self, morning_chains, afternoon_chains, nb_matin, nb_aprem):
        """Trouve TOUTES les solutions possibles avec un callback OR-Tools"""
        model = cp_model.CpModel()

        morning_vars = []
        afternoon_vars = []

        for i, chain in enumerate(morning_chains):
            var = model.NewBoolVar(f'morning_chain_{i}')
            morning_vars.append(var)

        for i, chain in enumerate(afternoon_chains):
            var = model.NewBoolVar(f'afternoon_chain_{i}')
            afternoon_vars.append(var)

        if morning_vars and nb_matin > 0:
            model.Add(sum(morning_vars) == nb_matin)
        if afternoon_vars and nb_aprem > 0:
            model.Add(sum(afternoon_vars) == nb_aprem)

        trip_usage = {}
        for trip_idx in range(len(self.trips)):
            trip_usage[trip_idx] = []

        for i, chain in enumerate(morning_chains):
            for trip_idx in chain['trip_indices']:
                trip_usage[trip_idx].append(morning_vars[i])

        for i, chain in enumerate(afternoon_chains):
            for trip_idx in chain['trip_indices']:
                trip_usage[trip_idx].append(afternoon_vars[i])

        for trip_idx, usage_vars in trip_usage.items():
            if usage_vars:
                model.Add(sum(usage_vars) <= 1)

        class SolutionCollector(cp_model.CpSolverSolutionCallback):
            def __init__(self, morning_vars, afternoon_vars, morning_chains, afternoon_chains, trips):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self._morning_vars = morning_vars
                self._afternoon_vars = afternoon_vars
                self._morning_chains = morning_chains
                self._afternoon_chains = afternoon_chains
                self._trips = trips
                self._solutions = []

            def on_solution_callback(self):
                solution = {
                    'matin': {},
                    'apres_midi': {},
                    'orphelins': []
                }

                used_trips = set()

                service_id = 0
                for i, var in enumerate(self._morning_vars):
                    if self.Value(var) == 1:
                        chain = self._morning_chains[i]
                        trips_info = []
                        for trip_idx in chain['trip_indices']:
                            trip = self._trips[trip_idx]
                            trips_info.append((trip_idx, trip))
                            used_trips.add(trip_idx)
                        solution['matin'][service_id] = trips_info
                        service_id += 1

                service_id = 0
                for i, var in enumerate(self._afternoon_vars):
                    if self.Value(var) == 1:
                        chain = self._afternoon_chains[i]
                        trips_info = []
                        for trip_idx in chain['trip_indices']:
                            trip = self._trips[trip_idx]
                            trips_info.append((trip_idx, trip))
                            used_trips.add(trip_idx)
                        solution['apres_midi'][service_id] = trips_info
                        service_id += 1

                for trip_idx in range(len(self._trips)):
                    if trip_idx not in used_trips:
                        solution['orphelins'].append(trip_idx)

                self._solutions.append(solution)
                print(f"✅ Solution {len(self._solutions)} trouvée ({len(solution['orphelins'])} orphelins)")

            def get_solutions(self):
                return self._solutions

        solution_collector = SolutionCollector(
            morning_vars, afternoon_vars,
            morning_chains, afternoon_chains,
            self.trips
        )

        solver = cp_model.CpSolver()
        solver.parameters.enumerate_all_solutions = True
        solver.parameters.max_time_in_seconds = 120.0

        print(f"🔍 Recherche de TOUTES les solutions possibles (peut prendre jusqu'à 2 minutes)...")

        status = solver.Solve(model, solution_collector)

        solutions = solution_collector.get_solutions()

        if status == cp_model.OPTIMAL:
            print(f"✅ Recherche terminée : toutes les solutions ont été trouvées")
        elif status == cp_model.FEASIBLE:
            print(f"⏱️ Temps écoulé : {len(solutions)} solutions trouvées")

        return solutions

    def _calculate_solution_score(self, solution):
        """Calcule un score pour classer les solutions"""
        total_trips = sum(len(trips) for trips in solution['matin'].values()) + \
                      sum(len(trips) for trips in solution['apres_midi'].values())

        coverage_bonus = 100 if len(solution['orphelins']) == 0 else 0

        duration_bonus = 0
        all_services = list(solution['matin'].values()) + list(solution['apres_midi'].values())
        for service_trips in all_services:
            if len(service_trips) > 1:
                service_start = min(trip["start"] for _, trip in service_trips)
                service_end = max(trip["end"] for _, trip in service_trips)
                amplitude = service_end - service_start
                deviation = abs(amplitude - self.TARGET_SERVICE_DURATION)
                if deviation <= 60:
                    duration_bonus += 20

        return total_trips * 10 + coverage_bonus + duration_bonus

    def _display_multiple_solutions(self, solutions):
        """Affiche toutes les solutions trouvées"""
        print(f"\n🎯 {len(solutions)} SOLUTIONS TROUVÉES")
        print("=" * 80)

        display_count = min(15, len(solutions))

        for i in range(display_count):
            solution = solutions[i]
            total_trips = sum(len(trips) for trips in solution['matin'].values()) + \
                          sum(len(trips) for trips in solution['apres_midi'].values())

            print(f"\n📋 SOLUTION {i + 1}: {solution['name']}")
            print(
                f"   Score: {solution['score']} | Voyages: {total_trips}/{len(self.trips)} | Orphelins: {len(solution['orphelins'])}")

            for service_id, trips in solution['matin'].items():
                trip_ids = [str(trip_idx) for trip_idx, _ in trips]
                start_time = minutes_to_time(min(trip["start"] for _, trip in trips))
                end_time = minutes_to_time(max(trip["end"] for _, trip in trips))
                amplitude = (max(trip["end"] for _, trip in trips) - min(trip["start"] for _, trip in trips)) / 60
                print(f"     AM-{service_id}: [{','.join(trip_ids)}] {start_time}-{end_time} ({amplitude:.1f}h)")

            for service_id, trips in solution['apres_midi'].items():
                trip_ids = [str(trip_idx) for trip_idx, _ in trips]
                start_time = minutes_to_time(min(trip["start"] for _, trip in trips))
                end_time = minutes_to_time(max(trip["end"] for _, trip in trips))
                amplitude = (max(trip["end"] for _, trip in trips) - min(trip["start"] for _, trip in trips)) / 60
                print(f"     PM-{service_id}: [{','.join(trip_ids)}] {start_time}-{end_time} ({amplitude:.1f}h)")

        if len(solutions) > display_count:
            print(f"\n... et {len(solutions) - display_count} autres solutions")

    def _user_select_solution(self, solutions):
        """Permet à l'utilisateur de choisir une solution"""
        print(f"\n🎲 SÉLECTION DE SOLUTION")
        print("=" * 40)

        display_count = min(15, len(solutions))

        for i in range(display_count):
            solution = solutions[i]
            total_trips = sum(len(trips) for trips in solution['matin'].values()) + \
                          sum(len(trips) for trips in solution['apres_midi'].values())
            print(
                f"  {i + 1}. {solution['name']} (Score: {solution['score']}, {total_trips} voyages, {len(solution['orphelins'])} orphelins)")

        if len(solutions) > display_count:
            print(f"  ... {len(solutions) - display_count} autres solutions disponibles")

        while True:
            try:
                choice = input(f"\nChoisissez une solution (1-{len(solutions)}) ou 0 pour voir les détails: ")
                choice_num = int(choice)

                if choice_num == 0:
                    for i in range(min(15, len(solutions))):
                        solution = solutions[i]
                        print(f"\n🔍 DÉTAILS SOLUTION {i + 1}:")
                        self._display_final_summary(solution)
                    continue
                elif 1 <= choice_num <= len(solutions):
                    selected = solutions[choice_num - 1]
                    print(f"\n✅ Solution sélectionnée: {selected['name']}")
                    self._display_final_summary(selected)
                    return selected
                else:
                    print(f"Veuillez entrer un nombre entre 0 et {len(solutions)}")
            except ValueError:
                print("Veuillez entrer un nombre valide")
            except KeyboardInterrupt:
                print("\nSélection par défaut: meilleure solution")
                return solutions[0] if solutions else None

    def _generate_valid_chains_strict(self):
        """Génère TOUTES les chaînes valides avec toutes les combinaisons possibles"""
        chains = []

        print("🔄 Génération de toutes les combinaisons possibles...")

        n_trips = len(self.trips)

        for size in range(2, n_trips + 1):
            for combo in combinations(range(n_trips), size):
                chain_data = self._try_build_chain_strict(list(combo))
                if chain_data:
                    chains.append(chain_data)

        unique_chains = []
        seen_signatures = set()

        for chain in chains:
            signature = tuple(sorted(chain['trip_indices']))
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_chains.append(chain)

        unique_chains.sort(key=lambda c: (c['start_time'], -len(c['trip_indices'])))

        print(
            f"✅ Généré {len(unique_chains)} chaînes uniques (tailles 2 à {max(len(c['trip_indices']) for c in unique_chains) if unique_chains else 0} voyages)")

        return unique_chains

    def _try_build_chain_strict(self, trip_indices):
        """Construit une chaîne avec vérifications strictes"""
        if len(trip_indices) < 2:
            return None

        sorted_indices = sorted(trip_indices, key=lambda i: self.trips[i]["start"])

        if not self._are_trips_compatible_strict(sorted_indices):
            return None

        trips_data = [self.trips[i] for i in sorted_indices]
        start_time = min(t["start"] for t in trips_data)
        end_time = max(t["end"] for t in trips_data)
        amplitude = end_time - start_time

        if amplitude < self.MIN_SERVICE_DURATION or amplitude > self.MAX_SERVICE_DURATION:
            return None

        return {
            'trip_indices': sorted_indices,
            'start_time': start_time,
            'end_time': end_time,
            'amplitude': amplitude
        }

    def _are_trips_compatible_strict(self, trip_indices):
        """Vérification STRICTE de compatibilité (avec gestion HLP)"""
        trips_data = [self.trips[i] for i in trip_indices]
        sorted_trips = sorted(zip(trip_indices, trips_data), key=lambda x: x[1]["start"])

        hlp_count = 0

        for i in range(len(sorted_trips) - 1):
            trip1_idx, trip1 = sorted_trips[i]
            trip2_idx, trip2 = sorted_trips[i + 1]

            if trip1["end"] > trip2["start"]:
                return False

            pause_base = trip2["start"] - trip1["end"]

            if self.can_chain(trip1, trip2):
                if self.MIN_PAUSE <= pause_base <= self.MAX_PAUSE:
                    continue
                else:
                    return False

            chain_result = self.can_chain_with_hlp(trip1, trip2)
            if chain_result["hlp"] is not None:
                hlp_count += 1
                if hlp_count > self.max_hlp_per_service:
                    return False

                pause_with_hlp = pause_base + chain_result["hlp"]["duration"]
                if self.MIN_PAUSE <= pause_with_hlp <= self.MAX_PAUSE:
                    continue
                else:
                    return False

            return False

        return True

    def _display_final_summary(self, solution):
        """Affiche le résumé final"""
        print(f"\n" + "=" * 80)
        print(f"✅ SOLUTION TROUVÉE - SERVICES AVEC CHAÎNAGE STRICT")
        print("=" * 80)

        if solution['matin']:
            print(f"\n🌅 SERVICES MATIN ({len(solution['matin'])} services):")
            for service_id, trips in solution['matin'].items():
                self._display_service(service_id, trips, "MATIN")
        else:
            print(f"\n🌅 SERVICES MATIN: Aucun")

        if solution['apres_midi']:
            print(f"\n🌇 SERVICES APRÈS-MIDI ({len(solution['apres_midi'])} services):")
            for service_id, trips in solution['apres_midi'].items():
                self._display_service(service_id, trips, "AM")
        else:
            print(f"\n🌇 SERVICES APRÈS-MIDI: Aucun")

        if solution['orphelins']:
            print(f"\n⚠️ VOYAGES ORPHELINS ({len(solution['orphelins'])} voyages):")
            sorted_orphans = sorted(solution['orphelins'], key=lambda i: self.trips[i]["start"])
            for trip_idx in sorted_orphans:
                trip = self.trips[trip_idx]
                start = minutes_to_time(trip["start"])
                end = minutes_to_time(trip["end"])
                duration = trip["end"] - trip["start"]
                print(f"  Voyage-{trip_idx}: {trip['from']} → {trip['to']} ({start}-{end}, {duration}min)")
        else:
            print(f"\n✅ AUCUN VOYAGE ORPHELIN!")

        total_services = len(solution['matin']) + len(solution['apres_midi'])
        total_assigned = sum(len(trips) for trips in solution['matin'].values()) + \
                         sum(len(trips) for trips in solution['apres_midi'].values())

        print(f"\n📊 STATISTIQUES:")
        print(f"  Services créés: {total_services}")
        print(f"  Voyages assignés: {total_assigned}/{len(self.trips)}")
        print(f"  Voyages orphelins: {len(solution['orphelins'])}/{len(self.trips)}")

        if len(self.trips) > 0:
            print(f"  Taux d'assignation: {total_assigned / len(self.trips) * 100:.1f}%")

    def _display_service(self, service_id, trips, prefix):
        """Affiche un service individuel avec gestion HLP"""
        sorted_trips = sorted(trips, key=lambda x: x[1]["start"])
        trip_ids = [trip_idx for trip_idx, _ in sorted_trips]

        print(f"\n  Service {prefix}-{service_id}: Voyages {trip_ids}")

        total_work = 0
        hlp_used = []

        for i, (trip_idx, trip) in enumerate(sorted_trips):
            start = minutes_to_time(trip["start"])
            end = minutes_to_time(trip["end"])
            duration = trip["end"] - trip["start"]
            total_work += duration
            print(f"    Voyage-{trip_idx}: {trip['from']} → {trip['to']} ({start}-{end}, {duration}min)")

            if i < len(sorted_trips) - 1:
                next_trip = sorted_trips[i + 1][1]
                chain_result = self.can_chain_with_hlp(trip, next_trip)
                if not chain_result["direct"] and chain_result["hlp"] is not None:
                    hlp = chain_result["hlp"]
                    hlp_used.append(hlp)
                    print(f"      🚐 HLP: {hlp['from']} → {hlp['to']} ({hlp['duration']}min)")

        if len(sorted_trips) >= 1:
            service_start = min(trip["start"] for _, trip in sorted_trips)
            service_end = max(trip["end"] for _, trip in sorted_trips)
            amplitude = service_end - service_start
            total_pause = amplitude - total_work

            hlp_info = f" | HLP: {len(hlp_used)}" if hlp_used else ""
            print(
                f"    📊 Amplitude: {minutes_to_time(amplitude)} | Travail: {total_work}min | Pause: {total_pause}min{hlp_info}")


def run_advanced_solver():
    """Lance le solveur avancé"""

    trips = [
        {"start": time_to_minutes("06:03"), "end": time_to_minutes("06:40"), "from": "FOMET", "to": "CEN05"},
        {"start": time_to_minutes("06:54"), "end": time_to_minutes("07:48"), "from": "CEN07", "to": "PTSNC"},
        {"start": time_to_minutes("08:58"), "end": time_to_minutes("10:13"), "from": "CPCEC", "to": "MYVES"},
        {"start": time_to_minutes("10:38"), "end": time_to_minutes("11:44"), "from": "MYVES", "to": "PTPLA"},
        {"start": time_to_minutes("12:09"), "end": time_to_minutes("13:13"), "from": "PTPLA", "to": "MYVES"},
        {"start": time_to_minutes("13:38"), "end": time_to_minutes("14:56"), "from": "MYVES", "to": "CPCEC"},
        {"start": time_to_minutes("06:40"), "end": time_to_minutes("07:36"), "from": "PTSNC", "to": "CEN05"},
        {"start": time_to_minutes("07:54"), "end": time_to_minutes("08:50"), "from": "CEN07", "to": "PTSNC"}
    ]

    solver = AdvancedODMSolver(trips)

    print("🚀 SOLVEUR ODM AVANCÉ - VERSION FINALE")
    print("=" * 60)
    print(f"📋 Total voyages: {len(trips)}")
    print(f"🚐 HLP autorisés: {len(solver.hlp_connections)} connexions")
    for hlp in solver.hlp_connections:
        print(f"   - {hlp['from']} → {hlp['to']} ({hlp['duration']}min)")
    print()

    try:
        nb_matin = int(input("🌅 Nombre de services MATIN: "))
        nb_aprem = int(input("🌇 Nombre de services APRÈS-MIDI: "))

        print(f"\n🔄 Calcul en cours...")
        start_time = time.time()

        result = solver.solve_morning_afternoon(nb_matin, nb_aprem)

        elapsed = time.time() - start_time
        print(f"\n⏱️ Temps de calcul: {elapsed:.2f}s")

    except KeyboardInterrupt:
        print(f"\n\n🛑 Arrêt demandé - Au revoir!")
    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    run_advanced_solver()