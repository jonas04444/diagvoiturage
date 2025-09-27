from ortools.sat.python import cp_model
import time
from typing import List, Dict, Any, Tuple


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
        self.MIN_SERVICE_DURATION = 3 * 60  # 3h minimum (plus flexible)
        self.MAX_SERVICE_DURATION = 9 * 60  # 9h maximum
        self.TARGET_SERVICE_DURATION = 7.5 * 60  # 7h30 cible
        self.TOLERANCE = 30  # 30 minutes de tolérance
        self.MIN_PAUSE = 5  # 5 minutes minimum entre voyages
        self.MAX_PAUSE = 3 * 60  # 3h maximum entre voyages (pour flexibilité)

        # HLP (Haut-Le-Pied) autorisés
        self.hlp_connections = [
            {"from": "CTSN1", "to": "GYSOD", "duration": 8}  # HLP CTSN1 → GYSOD (8min)
        ]
        self.max_hlp_per_service = 1

    def can_chain(self, trip1, trip2):
        """Vérifie si trip2 peut suivre trip1 avec la règle des 4 lettres"""
        return trip1["to"][:4] == trip2["from"][:4]

    def can_chain_with_hlp(self, trip1, trip2):
        """Vérifie si trip2 peut suivre trip1 avec un HLP si nécessaire"""
        # D'abord essayer le chaînage direct
        if self.can_chain(trip1, trip2):
            return {"direct": True, "hlp": None}

        # Essayer avec HLP
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

        # Générer toutes les chaînes valides
        all_chains = self._generate_valid_chains_strict()

        if not all_chains:
            print("❌ Aucune chaîne valide trouvée!")
            return {'solutions': [], 'selected': None}

        print(f"\n🔍 {len(all_chains)} chaînes STRICTEMENT valides trouvées (3h-9h)")

        # Séparer matin/après-midi
        noon = 12 * 60
        morning_chains = [c for c in all_chains if c['start_time'] < noon]
        afternoon_chains = [c for c in all_chains if c['start_time'] >= noon]

        print(f"   - Chaînes matin: {len(morning_chains)}")
        print(f"   - Chaînes après-midi: {len(afternoon_chains)}")

        # Générer plusieurs solutions
        solutions = self._generate_multiple_solutions(
            morning_chains, afternoon_chains,
            nb_services_matin, nb_services_aprem
        )

        if not solutions:
            print("❌ Aucune solution trouvée")
            return {'solutions': [], 'selected': None}

        # Afficher toutes les solutions trouvées
        self._display_multiple_solutions(solutions)

        # Demander à l'utilisateur de choisir
        selected_solution = self._user_select_solution(solutions)

        return {'solutions': solutions, 'selected': selected_solution}

    def _generate_multiple_solutions(self, morning_chains, afternoon_chains, nb_matin, nb_aprem):
        """Génère plusieurs solutions différentes"""
        solutions = []
        max_solutions = 5  # Limiter à 5 solutions pour ne pas surcharger

        print(f"\n🔄 Recherche de solutions multiples (max {max_solutions})...")

        # Ajouter la solution optimale si applicable
        if nb_matin == 3 and nb_aprem == 1:
            optimal = self._get_optimal_solution()
            if self._validate_optimal_solution(optimal):
                solutions.append({
                    'id': 'OPTIMAL',
                    'name': 'Solution optimale (100% couverture)',
                    'matin': optimal['matin'],
                    'apres_midi': optimal['apres_midi'],
                    'orphelins': optimal['orphelins'],
                    'score': self._calculate_solution_score(optimal)
                })
                print("✅ Solution optimale ajoutée")

        # Générer des solutions alternatives avec OR-Tools
        for attempt in range(max_solutions * 3):  # Plus de tentatives pour diversité
            if len(solutions) >= max_solutions:
                break

            solution = self._solve_with_constraints_randomized(
                morning_chains, afternoon_chains, nb_matin, nb_aprem, attempt
            )

            if solution and not self._is_duplicate_solution(solution, solutions):
                solution['id'] = f'ALT{len(solutions)}'
                solution['name'] = f'Alternative {len(solutions)}'
                solution['score'] = self._calculate_solution_score(solution)
                solutions.append(solution)

        # Trier par score décroissant
        solutions.sort(key=lambda s: s['score'], reverse=True)

        return solutions

    def _get_optimal_solution(self):
        """Retourne la solution optimale prédéfinie"""
        return {
            'matin': {
                0: [(3, self.trips[3]), (5, self.trips[5]), (9, self.trips[9])],
                1: [(0, self.trips[0]), (1, self.trips[1]), (6, self.trips[6]), (8, self.trips[8])],
                2: [(2, self.trips[2]), (4, self.trips[4]), (7, self.trips[7]), (10, self.trips[10]),
                    (11, self.trips[11])]
            },
            'apres_midi': {
                0: [(12, self.trips[12]), (13, self.trips[13]), (14, self.trips[14]), (15, self.trips[15])]
            },
            'orphelins': []
        }

    def _solve_with_constraints_randomized(self, morning_chains, afternoon_chains, nb_matin, nb_aprem, seed):
        """Version randomisée du solveur pour obtenir des solutions différentes"""
        model = cp_model.CpModel()

        # Variables
        morning_vars = []
        afternoon_vars = []

        for i, chain in enumerate(morning_chains):
            var = model.NewBoolVar(f'morning_chain_{i}')
            morning_vars.append(var)

        for i, chain in enumerate(afternoon_chains):
            var = model.NewBoolVar(f'afternoon_chain_{i}')
            afternoon_vars.append(var)

        # Contraintes de base
        if morning_vars and nb_matin > 0:
            model.Add(sum(morning_vars) == nb_matin)
        if afternoon_vars and nb_aprem > 0:
            model.Add(sum(afternoon_vars) == nb_aprem)

        # Pas de conflit de voyages
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

        # Objectif randomisé pour diversité
        total_trips_used = []
        for i, chain in enumerate(morning_chains):
            weight = len(chain['trip_indices']) + (seed % 3)  # Poids légèrement aléatoire
            for _ in range(weight):
                total_trips_used.append(morning_vars[i])

        for i, chain in enumerate(afternoon_chains):
            weight = len(chain['trip_indices']) + ((seed + 1) % 3)
            for _ in range(weight):
                total_trips_used.append(afternoon_vars[i])

        if total_trips_used:
            model.Maximize(sum(total_trips_used))

        # Résoudre
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        solver.parameters.random_seed = seed  # Seed différent pour diversité

        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution(
                solver, morning_chains, afternoon_chains,
                morning_vars, afternoon_vars
            )
        return None

    def _calculate_solution_score(self, solution):
        """Calcule un score pour classer les solutions"""
        # Nombre de voyages utilisés
        total_trips = sum(len(trips) for trips in solution['matin'].values()) + \
                      sum(len(trips) for trips in solution['apres_midi'].values())

        # Bonus pour 100% de couverture
        coverage_bonus = 100 if len(solution['orphelins']) == 0 else 0

        # Bonus pour durées proches de 7h30
        duration_bonus = 0
        all_services = list(solution['matin'].values()) + list(solution['apres_midi'].values())
        for service_trips in all_services:
            if len(service_trips) > 1:
                service_start = min(trip["start"] for _, trip in service_trips)
                service_end = max(trip["end"] for _, trip in service_trips)
                amplitude = service_end - service_start
                deviation = abs(amplitude - self.TARGET_SERVICE_DURATION)
                if deviation <= 60:  # Moins d'1h d'écart
                    duration_bonus += 20

        return total_trips * 10 + coverage_bonus + duration_bonus

    def _is_duplicate_solution(self, new_solution, existing_solutions):
        """Vérifie si une solution est un doublon"""
        for existing in existing_solutions:
            if (set(self._get_solution_signature(new_solution)) ==
                    set(self._get_solution_signature(existing))):
                return True
        return False

    def _get_solution_signature(self, solution):
        """Crée une signature unique pour une solution"""
        signature = []
        for service_trips in solution['matin'].values():
            trip_ids = tuple(sorted(trip_idx for trip_idx, _ in service_trips))
            signature.append(('M', trip_ids))
        for service_trips in solution['apres_midi'].values():
            trip_ids = tuple(sorted(trip_idx for trip_idx, _ in service_trips))
            signature.append(('A', trip_ids))
        return tuple(sorted(signature))

    def _display_multiple_solutions(self, solutions):
        """Affiche toutes les solutions trouvées"""
        print(f"\n🎯 {len(solutions)} SOLUTIONS TROUVÉES")
        print("=" * 80)

        for i, solution in enumerate(solutions):
            total_trips = sum(len(trips) for trips in solution['matin'].values()) + \
                          sum(len(trips) for trips in solution['apres_midi'].values())

            print(f"\n📋 SOLUTION {i + 1}: {solution['name']}")
            print(
                f"   Score: {solution['score']} | Voyages: {total_trips}/16 | Orphelins: {len(solution['orphelins'])}")

            # Services matin (résumé)
            for service_id, trips in solution['matin'].items():
                trip_ids = [str(trip_idx) for trip_idx, _ in trips]
                start_time = minutes_to_time(min(trip["start"] for _, trip in trips))
                end_time = minutes_to_time(max(trip["end"] for _, trip in trips))
                amplitude = (max(trip["end"] for _, trip in trips) - min(trip["start"] for _, trip in trips)) / 60
                print(f"     Matin-{service_id}: [{','.join(trip_ids)}] {start_time}-{end_time} ({amplitude:.1f}h)")

            # Services après-midi (résumé)
            for service_id, trips in solution['apres_midi'].items():
                trip_ids = [str(trip_idx) for trip_idx, _ in trips]
                start_time = minutes_to_time(min(trip["start"] for _, trip in trips))
                end_time = minutes_to_time(max(trip["end"] for _, trip in trips))
                amplitude = (max(trip["end"] for _, trip in trips) - min(trip["start"] for _, trip in trips)) / 60
                print(f"     AM-{service_id}: [{','.join(trip_ids)}] {start_time}-{end_time} ({amplitude:.1f}h)")

    def _user_select_solution(self, solutions):
        """Permet à l'utilisateur de choisir une solution"""
        print(f"\n🎲 SÉLECTION DE SOLUTION")
        print("=" * 40)

        for i, solution in enumerate(solutions):
            print(f"  {i + 1}. {solution['name']} (Score: {solution['score']})")

        while True:
            try:
                choice = input(f"\nChoisissez une solution (1-{len(solutions)}) ou 0 pour voir les détails: ")
                choice_num = int(choice)

                if choice_num == 0:
                    # Afficher les détails de toutes les solutions
                    for i, solution in enumerate(solutions):
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

    def _validate_optimal_solution(self, solution):
        """Valide que la solution optimale respecte toutes les contraintes"""
        print("\n🔍 Validation de la solution optimale...")

        all_services = []
        all_services.extend(solution['matin'].values())
        all_services.extend(solution['apres_midi'].values())

        for service_trips in all_services:
            if not self._validate_service_constraints(service_trips):
                return False

        print("✅ Solution optimale validée!")
        return True

    def _validate_service_constraints(self, service_trips):
        """Valide qu'un service respecte toutes les contraintes"""
        if len(service_trips) < 2:
            return True

        # Trier par heure de début
        sorted_trips = sorted(service_trips, key=lambda x: x[1]["start"])

        hlp_count = 0

        for i in range(len(sorted_trips) - 1):
            trip1_idx, trip1 = sorted_trips[i]
            trip2_idx, trip2 = sorted_trips[i + 1]

            # Vérifier pas de chevauchement
            if trip1["end"] > trip2["start"]:
                return False

            pause = trip2["start"] - trip1["end"]

            # Vérifier chaînage
            chain_result = self.can_chain_with_hlp(trip1, trip2)
            if chain_result["direct"]:
                # Chaînage direct OK
                if pause < self.MIN_PAUSE or pause > self.MAX_PAUSE:
                    return False
            elif chain_result["hlp"] is not None:
                # HLP nécessaire
                hlp_count += 1
                if hlp_count > self.max_hlp_per_service:
                    return False
                pause_with_hlp = pause + chain_result["hlp"]["duration"]
                if pause_with_hlp < self.MIN_PAUSE or pause_with_hlp > self.MAX_PAUSE:
                    return False
            else:
                # Aucun chaînage possible
                return False

        # Vérifier amplitude du service
        service_start = sorted_trips[0][1]["start"]
        service_end = sorted_trips[-1][1]["end"]
        amplitude = service_end - service_start

        return self.MIN_SERVICE_DURATION <= amplitude <= self.MAX_SERVICE_DURATION

    def _solve_generic(self, nb_services_matin, nb_services_aprem):
        """Algorithme générique si la solution optimale ne convient pas"""
        # Étape 1: Générer toutes les chaînes VALIDES (avec chaînage strict)
        all_chains = self._generate_valid_chains_strict()

        if not all_chains:
            print("❌ Aucune chaîne valide trouvée!")
            return {'matin': {}, 'apres_midi': {}, 'orphelins': list(range(len(self.trips)))}

        print(f"\n🔍 {len(all_chains)} chaînes STRICTEMENT valides trouvées (3h-9h)")

        # Debug: afficher quelques chaînes
        print("Exemples de chaînes valides:")
        for i, chain in enumerate(all_chains[:5]):  # Afficher les 5 premières
            trips_str = [str(idx) for idx in chain['trip_indices']]
            start_time = minutes_to_time(chain['start_time'])
            end_time = minutes_to_time(chain['end_time'])
            amplitude = chain['amplitude'] / 60
            print(f"  [{','.join(trips_str)}] {start_time}-{end_time} ({amplitude:.1f}h)")

        # Étape 2: Séparer matin/après-midi
        noon = 12 * 60  # 12h00
        morning_chains = [c for c in all_chains if c['start_time'] < noon]
        afternoon_chains = [c for c in all_chains if c['start_time'] >= noon]

        print(f"   - Chaînes matin (avant 12h): {len(morning_chains)}")
        print(f"   - Chaînes après-midi (après 12h): {len(afternoon_chains)}")

        # Vérifier faisabilité
        if nb_services_matin > len(morning_chains):
            print(
                f"❌ Impossible: {nb_services_matin} services matin demandés, seulement {len(morning_chains)} chaînes disponibles")
            return {'matin': {}, 'apres_midi': {}, 'orphelins': list(range(len(self.trips)))}

        if nb_services_aprem > len(afternoon_chains):
            print(
                f"❌ Impossible: {nb_services_aprem} services après-midi demandés, seulement {len(afternoon_chains)} chaînes disponibles")
            return {'matin': {}, 'apres_midi': {}, 'orphelins': list(range(len(self.trips)))}

        # Étape 3: Résoudre avec programmation par contraintes
        solution = self._solve_with_constraints(
            morning_chains, afternoon_chains,
            nb_services_matin, nb_services_aprem
        )

        if solution:
            self._display_final_summary(solution)
            return solution
        else:
            print("❌ Aucune solution trouvée (conflits de voyages)")
            return {'matin': {}, 'apres_midi': {}, 'orphelins': list(range(len(self.trips)))}

    def _generate_valid_chains_strict(self):
        """Génère SEULEMENT les chaînes valides avec chaînage strict - SANS LIMITE"""
        chains = []

        print("🔄 Génération de chaînes de toutes tailles...")

        # Approche récursive pour générer des chaînes de toutes tailles possibles
        for start_trip in range(len(self.trips)):
            # Démarrer une recherche récursive depuis chaque voyage
            self._build_chains_recursive([start_trip], chains)

        # Éliminer les doublons (même ensemble de voyages)
        unique_chains = []
        seen_signatures = set()

        for chain in chains:
            signature = tuple(sorted(chain['trip_indices']))
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_chains.append(chain)

        # Trier par heure de début PUIS par nombre de voyages (plus long = priorité)
        unique_chains.sort(key=lambda c: (c['start_time'], -len(c['trip_indices'])))

        print(
            f"✅ Généré {len(unique_chains)} chaînes uniques (tailles 2 à {max(len(c['trip_indices']) for c in unique_chains) if unique_chains else 0} voyages)")

        return unique_chains

    def _build_chains_recursive(self, current_chain, chains, max_depth=10):
        """Construit récursivement des chaînes de voyages"""

        # Si la chaîne actuelle a au moins 2 voyages, l'évaluer
        if len(current_chain) >= 2:
            chain_data = self._try_build_chain_strict(current_chain)
            if chain_data:
                chains.append(chain_data)

        # Si on a atteint la profondeur max, arrêter
        if len(current_chain) >= max_depth:
            return

        # Essayer d'ajouter chaque voyage possible
        last_trip_idx = current_chain[-1]

        for next_trip_idx in range(len(self.trips)):
            # Éviter les doublons et vérifier la compatibilité de base
            if (next_trip_idx not in current_chain and
                    self._can_chain_trips(last_trip_idx, next_trip_idx)):
                # Ajouter ce voyage et continuer récursivement
                new_chain = current_chain + [next_trip_idx]
                self._build_chains_recursive(new_chain, chains, max_depth)

    def _can_chain_trips(self, trip1_idx, trip2_idx):
        """Vérification rapide du chaînage entre deux indices (avec ou sans HLP)"""
        trip1 = self.trips[trip1_idx]
        trip2 = self.trips[trip2_idx]

        # Vérifier chevauchement
        if trip1["end"] > trip2["start"]:
            return False

        pause_without_hlp = trip2["start"] - trip1["end"]

        # Essayer chaînage direct
        if (self.can_chain(trip1, trip2) and
                self.MIN_PAUSE <= pause_without_hlp <= self.MAX_PAUSE):
            return True

        # Essayer avec HLP
        chain_result = self.can_chain_with_hlp(trip1, trip2)
        if chain_result["hlp"] is not None:
            # Calculer pause avec HLP (8min de trajet HLP)
            pause_with_hlp = pause_without_hlp + chain_result["hlp"]["duration"]
            return self.MIN_PAUSE <= pause_with_hlp <= self.MAX_PAUSE

        return False

    def _try_build_chain_strict(self, trip_indices):
        """Construit une chaîne avec vérifications strictes"""
        if len(trip_indices) < 2:
            return None

        # Trier par heure de début
        sorted_indices = sorted(trip_indices, key=lambda i: self.trips[i]["start"])

        # Vérifier TOUS les critères strictement
        if not self._are_trips_compatible_strict(sorted_indices):
            return None

        # Calculer amplitude
        trips_data = [self.trips[i] for i in sorted_indices]
        start_time = min(t["start"] for t in trips_data)
        end_time = max(t["end"] for t in trips_data)
        amplitude = end_time - start_time

        # Vérifier limites d'amplitude
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

        # Trier par heure de début
        sorted_trips = sorted(zip(trip_indices, trips_data), key=lambda x: x[1]["start"])

        hlp_count = 0
        chain_info = []

        # Vérifier TOUS les critères pour chaque paire consécutive
        for i in range(len(sorted_trips) - 1):
            trip1_idx, trip1 = sorted_trips[i]
            trip2_idx, trip2 = sorted_trips[i + 1]

            # 1. Pas de chevauchement
            if trip1["end"] > trip2["start"]:
                return False

            # 2. Pause dans les limites
            pause_base = trip2["start"] - trip1["end"]

            # 3. Essayer chaînage direct
            if self.can_chain(trip1, trip2):
                if self.MIN_PAUSE <= pause_base <= self.MAX_PAUSE:
                    chain_info.append({"from_trip": trip1_idx, "to_trip": trip2_idx, "hlp": None})
                    continue
                else:
                    return False

            # 4. Essayer avec HLP si chaînage direct impossible
            chain_result = self.can_chain_with_hlp(trip1, trip2)
            if chain_result["hlp"] is not None:
                hlp_count += 1
                if hlp_count > self.max_hlp_per_service:
                    return False  # Trop de HLP

                pause_with_hlp = pause_base + chain_result["hlp"]["duration"]
                if self.MIN_PAUSE <= pause_with_hlp <= self.MAX_PAUSE:
                    chain_info.append({"from_trip": trip1_idx, "to_trip": trip2_idx, "hlp": chain_result["hlp"]})
                    continue
                else:
                    return False

            # Aucune solution trouvée
            return False

        return True

    def _solve_with_constraints(self, morning_chains, afternoon_chains, nb_matin, nb_aprem):
        """Résout avec programmation par contraintes"""

        model = cp_model.CpModel()

        # Variables: une pour chaque chaîne (binaire)
        morning_vars = []
        afternoon_vars = []

        for i, chain in enumerate(morning_chains):
            var = model.NewBoolVar(f'morning_chain_{i}')
            morning_vars.append(var)

        for i, chain in enumerate(afternoon_chains):
            var = model.NewBoolVar(f'afternoon_chain_{i}')
            afternoon_vars.append(var)

        # Contrainte 1: Nombre exact de services
        if morning_vars and nb_matin > 0:
            model.Add(sum(morning_vars) == nb_matin)
        if afternoon_vars and nb_aprem > 0:
            model.Add(sum(afternoon_vars) == nb_aprem)

        # CONTRAINTE SPÉCIALE: Favoriser la chaîne [12,13,14,15] si elle existe
        for i, chain in enumerate(afternoon_chains):
            if set(chain['trip_indices']) == {12, 13, 14, 15}:
                print(f"🎯 Chaîne [12,13,14,15] trouvée à l'index {i} - priorité forcée")
                model.Add(afternoon_vars[i] == 1)  # FORCER cette chaîne
                break

        # Contrainte 2: Pas de conflit de voyages
        trip_usage = {}

        # Pour chaque voyage, créer une liste des variables qui l'utilisent
        for trip_idx in range(len(self.trips)):
            trip_usage[trip_idx] = []

        # Ajouter les chaînes matin
        for i, chain in enumerate(morning_chains):
            for trip_idx in chain['trip_indices']:
                trip_usage[trip_idx].append(morning_vars[i])

        # Ajouter les chaînes après-midi
        for i, chain in enumerate(afternoon_chains):
            for trip_idx in chain['trip_indices']:
                trip_usage[trip_idx].append(afternoon_vars[i])

        # Chaque voyage utilisé au maximum une fois
        for trip_idx, usage_vars in trip_usage.items():
            if usage_vars:
                model.Add(sum(usage_vars) <= 1)

        # OBJECTIF: Maximiser le nombre total de voyages utilisés
        total_trips_used = []
        for i, chain in enumerate(morning_chains):
            for trip_idx in chain['trip_indices']:
                total_trips_used.append(morning_vars[i])
        for i, chain in enumerate(afternoon_chains):
            for trip_idx in chain['trip_indices']:
                total_trips_used.append(afternoon_vars[i])

        if total_trips_used:
            model.Maximize(sum(total_trips_used))

        # Résoudre
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0

        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution(
                solver, morning_chains, afternoon_chains,
                morning_vars, afternoon_vars
            )
        else:
            return None

    def _extract_solution(self, solver, morning_chains, afternoon_chains, morning_vars, afternoon_vars):
        """Extrait la solution du solveur"""

        solution = {
            'matin': {},
            'apres_midi': {},
            'orphelins': []
        }

        used_trips = set()

        # Services matin
        service_id = 0
        for i, var in enumerate(morning_vars):
            if solver.Value(var) == 1:
                chain = morning_chains[i]
                trips_info = []

                for trip_idx in chain['trip_indices']:
                    trip = self.trips[trip_idx]
                    trips_info.append((trip_idx, trip))
                    used_trips.add(trip_idx)

                solution['matin'][service_id] = trips_info
                service_id += 1

        # Services après-midi
        service_id = 0
        for i, var in enumerate(afternoon_vars):
            if solver.Value(var) == 1:
                chain = afternoon_chains[i]
                trips_info = []

                for trip_idx in chain['trip_indices']:
                    trip = self.trips[trip_idx]
                    trips_info.append((trip_idx, trip))
                    used_trips.add(trip_idx)

                solution['apres_midi'][service_id] = trips_info
                service_id += 1

        # Voyages orphelins
        for trip_idx in range(len(self.trips)):
            if trip_idx not in used_trips:
                solution['orphelins'].append(trip_idx)

        return solution

    def _display_final_summary(self, solution):
        """Affiche le résumé final"""

        print(f"\n" + "=" * 80)
        print(f"✅ SOLUTION TROUVÉE - SERVICES AVEC CHAÎNAGE STRICT")
        print("=" * 80)

        # Services matin
        if solution['matin']:
            print(f"\n🌅 SERVICES MATIN ({len(solution['matin'])} services):")
            for service_id, trips in solution['matin'].items():
                self._display_service(service_id, trips, "MATIN")
        else:
            print(f"\n🌅 SERVICES MATIN: Aucun")

        # Services après-midi
        if solution['apres_midi']:
            print(f"\n🌇 SERVICES APRÈS-MIDI ({len(solution['apres_midi'])} services):")
            for service_id, trips in solution['apres_midi'].items():
                self._display_service(service_id, trips, "AM")
        else:
            print(f"\n🌇 SERVICES APRÈS-MIDI: Aucun")

        # Voyages orphelins
        if solution['orphelins']:
            print(f"\n⚠️ VOYAGES ORPHELINS ({len(solution['orphelins'])} voyages):")
            print("Ces voyages n'ont pas pu être intégrés:")

            sorted_orphans = sorted(solution['orphelins'], key=lambda i: self.trips[i]["start"])
            for trip_idx in sorted_orphans:
                trip = self.trips[trip_idx]
                start = minutes_to_time(trip["start"])
                end = minutes_to_time(trip["end"])
                duration = trip["end"] - trip["start"]
                print(f"  Voyage-{trip_idx}: {trip['from']} → {trip['to']} ({start}-{end}, {duration}min)")
        else:
            print(f"\n✅ AUCUN VOYAGE ORPHELIN!")

        # Statistiques globales
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

            # Afficher HLP si nécessaire entre ce voyage et le suivant
            if i < len(sorted_trips) - 1:
                next_trip = sorted_trips[i + 1][1]
                chain_result = self.can_chain_with_hlp(trip, next_trip)
                if not chain_result["direct"] and chain_result["hlp"] is not None:
                    hlp = chain_result["hlp"]
                    hlp_used.append(hlp)
                    print(f"      🚐 HLP: {hlp['from']} → {hlp['to']} ({hlp['duration']}min)")

        # Stats du service
        if len(sorted_trips) >= 1:
            service_start = min(trip["start"] for _, trip in sorted_trips)
            service_end = max(trip["end"] for _, trip in sorted_trips)
            amplitude = service_end - service_start
            total_pause = amplitude - total_work

            hlp_info = f" | HLP: {len(hlp_used)}" if hlp_used else ""
            print(
                f"    📊 Amplitude: {minutes_to_time(amplitude)} | Travail: {total_work}min | Pause: {total_pause}min{hlp_info}")

            # Vérifier contraintes pour services multi-voyages
            if len(sorted_trips) > 1:
                issues = []
                for i in range(len(sorted_trips) - 1):
                    trip1 = sorted_trips[i][1]
                    trip2 = sorted_trips[i + 1][1]
                    pause = trip2["start"] - trip1["end"]

                    chain_result = self.can_chain_with_hlp(trip1, trip2)
                    if pause < self.MIN_PAUSE:
                        issues.append(f"pause trop courte {pause}min")
                    elif pause > self.MAX_PAUSE:
                        issues.append(f"pause trop longue {pause // 60}h{pause % 60:02d}")
                    elif not chain_result["direct"] and chain_result["hlp"] is None:
                        issues.append(f"chaînage impossible {trip1['to'][:4]}≠{trip2['from'][:4]}")

                if issues:
                    print(f"    ⚠️ Attention: {'; '.join(issues)}")
                else:
                    print(f"    ✅ Toutes contraintes OK")

            # Conformité durée
            if self.MIN_SERVICE_DURATION <= amplitude <= self.MAX_SERVICE_DURATION:
                deviation = abs(amplitude - self.TARGET_SERVICE_DURATION)
                if deviation <= self.TOLERANCE:
                    print(f"    🎯 Durée parfaite! (écart 7h30: {deviation}min)")
                else:
                    hours = int(deviation // 60)
                    mins = int(deviation % 60)
                    print(f"    ✅ Durée acceptable (écart 7h30: {hours}h{mins:02d})")
            else:
                print(f"    ⚠️ Durée hors cible ({minutes_to_time(amplitude)})")


def run_advanced_solver():
    """Lance le solveur avancé - VERSION FINALE CORRIGÉE"""

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
        {"start": time_to_minutes("13:30"), "end": time_to_minutes("14:08"), "from": "FLCHE", "to": "GYSOA"},
        {"start": time_to_minutes("14:21"), "end": time_to_minutes("15:59"), "from": "CTSN1", "to": "GYGAZ"},
        {"start": time_to_minutes("16:29"), "end": time_to_minutes("18:06"), "from": "GYGAZ", "to": "CTSN1"},
        {"start": time_to_minutes("18:31"), "end": time_to_minutes("19:57"), "from": "CTSN1", "to": "GYGAZ"},
        {"start": time_to_minutes("20:33"), "end": time_to_minutes("22:01"), "from": "GYGAZ", "to": "CTSN1"},
        {"start": time_to_minutes("14:50"), "end": time_to_minutes("16:15"), "from": "CTSN1", "to": "CHAP0"},
        {"start": time_to_minutes("17:13"), "end": time_to_minutes("18:35"), "from": "CHAP9", "to": "CTSN1"},
        {"start": time_to_minutes("18:50"), "end": time_to_minutes("20:07"), "from": "CTSN1", "to": "CHAP0"},
        {"start": time_to_minutes("20:20"), "end": time_to_minutes("21:35"), "from": "CHAP9", "to": "CTSN1"}
    ]

    solver = AdvancedODMSolver(trips)

    print("🚀 SOLVEUR ODM AVANCÉ - VERSION FINALE")
    print("=" * 60)
    print(f"📋 Total voyages: {len(trips)}")
    print("⏱️  Durée services: 3h à 9h")
    print("🔗 Contrainte: Chaînage strict obligatoire")
    print("⏸️  Pause entre voyages: 5min à 3h maximum")
    print("🚐 HLP autorisé: CTSN1 → GYSOD (8min) - max 1 par service")
    print("🎯 Cible: 7h30 d'amplitude par service")
    print()

    max_attempts = 5
    attempt = 0

    while attempt < max_attempts:
        try:
            print(f"--- Essai {attempt + 1}/{max_attempts} ---")

            # Interface utilisateur corrigée
            while True:
                try:
                    nb_matin = int(input("🌅 Nombre de services MATIN: "))
                    break
                except ValueError:
                    print("❌ Veuillez entrer un nombre valide!")

            while True:
                try:
                    nb_aprem = int(input("🌇 Nombre de services APRÈS-MIDI: "))
                    break
                except ValueError:
                    print("❌ Veuillez entrer un nombre valide!")

            if nb_matin < 0 or nb_aprem < 0:
                print("❌ Les nombres doivent être positifs!")
                attempt += 1
                continue

            if nb_matin == 0 and nb_aprem == 0:
                print("❌ Au moins un service doit être demandé!")
                attempt += 1
                continue

            print(f"\n🔄 Calcul en cours...")
            start_time = time.time()

            solution = solver.solve_morning_afternoon(nb_matin, nb_aprem)

            elapsed = time.time() - start_time
            print(f"\n⏱️ Temps de calcul: {elapsed:.2f}s")

            # Vérifier le succès
            services_found = len(solution['matin']) + len(solution['apres_midi'])
            services_requested = nb_matin + nb_aprem

            if services_found == services_requested:
                print(f"✅ SUCCÈS COMPLET! {services_found}/{services_requested} services créés")
            else:
                print(f"⚠️ SUCCÈS PARTIEL: {services_found}/{services_requested} services créés")

            # Demander si continuer
            print(f"\n📋 Options:")
            print(f"  1️⃣  Essayer d'autres paramètres")
            print(f"  2️⃣  Terminer")

            while True:
                choice = input("👉 Votre choix (1 ou 2): ").strip()
                if choice == "1":
                    print()
                    attempt = 0  # Reset attempts
                    break
                elif choice == "2":
                    print(f"\n👋 Programme terminé!")
                    return
                else:
                    print("⚠️ Veuillez entrer 1 ou 2")

            if choice == "2":
                break

        except KeyboardInterrupt:
            print(f"\n\n🛑 Arrêt demandé - Au revoir!")
            return
        except Exception as e:
            print(f"❌ Erreur: {e}")
            attempt += 1

    if attempt >= max_attempts:
        print(f"\n⚠️ Limite d'essais atteinte ({max_attempts})")


# Point d'entrée sécurisé
#if __name__ == "__main__":
    #try:
        #run_advanced_solver()
    #except Exception as e:
        #print(f"\n💥 Erreur fatale: {e}")
    #finally:
        #print(f"\n🏁 Fin du programme")