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


class ProgressiveSolver:
    """Solveur qui teste progressivement chaque contrainte"""

    def __init__(self, trips_data):
        self.trips = trips_data

    def test_basic_assignment(self):
        """Test 1: Assignation de base sans contraintes"""
        print("Test 1: Assignation de base")

        model = cp_model.CpModel()
        n = len(self.trips)
        assignments = [model.NewIntVar(0, 5, f"service_{i}") for i in range(n)]

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5
        status = solver.Solve(model)

        result = status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
        print(f"  Résultat: {'✅ OK' if result else '❌ ÉCHEC'}")
        return result

    def test_with_overlaps(self):
        """Test 2: Avec contraintes de chevauchement seulement"""
        print("Test 2: Non-chevauchement seulement")

        model = cp_model.CpModel()
        n = len(self.trips)
        assignments = [model.NewIntVar(0, 6, f"service_{i}") for i in range(n)]

        # Contrainte de non-chevauchement
        conflicts = 0
        for i in range(n):
            for j in range(i + 1, n):
                trip1, trip2 = self.trips[i], self.trips[j]
                if trip1["start"] < trip2["end"] and trip2["start"] < trip1["end"]:
                    model.Add(assignments[i] != assignments[j])
                    conflicts += 1

        print(f"    {conflicts} conflits temporels gérés")

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10
        status = solver.Solve(model)

        result = status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
        print(f"  Résultat: {'✅ OK' if result else '❌ ÉCHEC'}")

        if result:
            # Afficher la solution
            services = {}
            for i, trip in enumerate(self.trips):
                service_id = solver.Value(assignments[i])
                if service_id not in services:
                    services[service_id] = []
                services[service_id].append(i)

            print(f"    Solution: {len(services)} services créés")
            for s_id, trips in services.items():
                print(f"      Service {s_id}: voyages {trips}")

        return result

    def test_with_basic_chaining(self):
        """Test 3: Avec chaînage basique (sans HLP)"""
        print("Test 3: Chaînage basique (4 premières lettres)")

        model = cp_model.CpModel()
        n = len(self.trips)
        assignments = [model.NewIntVar(0, 8, f"service_{i}") for i in range(n)]

        # Non-chevauchement
        for i in range(n):
            for j in range(i + 1, n):
                trip1, trip2 = self.trips[i], self.trips[j]
                if trip1["start"] < trip2["end"] and trip2["start"] < trip1["end"]:
                    model.Add(assignments[i] != assignments[j])

        # Chaînage simple: si deux voyages sont proches temporellement mais ne se chaînent pas, les séparer
        chain_separations = 0
        for i in range(n):
            for j in range(n):
                if i != j:
                    trip1, trip2 = self.trips[i], self.trips[j]
                    if trip1["end"] <= trip2["start"]:
                        time_gap = trip2["start"] - trip1["end"]

                        # Si gap < 2h ET pas de chaînage possible
                        if time_gap < 120:
                            can_chain = (trip1["to"][:4] == trip2["from"][:4])
                            if not can_chain:
                                model.Add(assignments[i] != assignments[j])
                                chain_separations += 1

        print(f"    {chain_separations} séparations de chaînage appliquées")

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15
        status = solver.Solve(model)

        result = status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
        print(f"  Résultat: {'✅ OK' if result else '❌ ÉCHEC'}")
        return result

    def test_minimal_hlp(self):
        """Test 4: Version HLP ultra-simplifiée"""
        print("Test 4: HLP minimal (sans limite)")

        hlp_table = {
            ("CTSN", "CHPA"): 15, ("CHPA", "CTSN"): 15,
            ("CTSN", "GYGA"): 20, ("GYGA", "CTSN"): 20,
            ("GYGA", "GYSO"): 10, ("GYSO", "GYGA"): 10,
            ("GYSO", "FLCH"): 25, ("FLCH", "GYSO"): 25,
            ("CHPA", "GYGA"): 30, ("GYGA", "CHPA"): 30,
        }

        model = cp_model.CpModel()
        n = len(self.trips)
        assignments = [model.NewIntVar(0, 6, f"service_{i}") for i in range(n)]

        # Non-chevauchement
        for i in range(n):
            for j in range(i + 1, n):
                trip1, trip2 = self.trips[i], self.trips[j]
                if trip1["start"] < trip2["end"] and trip2["start"] < trip1["end"]:
                    model.Add(assignments[i] != assignments[j])

        # Chaînage avec HLP (version permissive)
        impossible_chains = 0
        for i in range(n):
            for j in range(n):
                if i != j:
                    trip1, trip2 = self.trips[i], self.trips[j]
                    if trip1["end"] <= trip2["start"]:
                        time_gap = trip2["start"] - trip1["end"]

                        # Chaînage direct possible?
                        direct_chain = (trip1["to"][:4] == trip2["from"][:4])

                        # HLP possible?
                        hlp_key = (trip1["to"][:4], trip2["from"][:4])
                        hlp_time = hlp_table.get(hlp_key, None)
                        hlp_possible = hlp_time is not None and time_gap >= hlp_time + 5

                        # Si ni direct ni HLP possible ET gap < 3h, séparer
                        if not direct_chain and not hlp_possible and time_gap < 180:
                            model.Add(assignments[i] != assignments[j])
                            impossible_chains += 1

        print(f"    {impossible_chains} chaînages impossibles même avec HLP")

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 20
        status = solver.Solve(model)

        result = status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
        print(f"  Résultat: {'✅ OK' if result else '❌ ÉCHEC'}")

        if result:
            self._show_simple_solution(solver, assignments, hlp_table)

        return result

    def _show_simple_solution(self, solver, assignments, hlp_table):
        """Affiche une solution simple"""
        services = {}
        for i, trip in enumerate(self.trips):
            service_id = solver.Value(assignments[i])
            if service_id not in services:
                services[service_id] = []
            services[service_id].append((i, trip))

        print(f"\n    Solution trouvée: {len(services)} services")

        for service_id in sorted(services.keys()):
            trip_list = services[service_id]
            trip_list.sort(key=lambda x: x[1]["start"])

            print(f"\n    Service {service_id} ({len(trip_list)} voyages):")

            for idx, (trip_idx, trip) in enumerate(trip_list):
                start = minutes_to_time(trip["start"])
                end = minutes_to_time(trip["end"])
                print(f"      Voyage-{trip_idx}: {trip['from']} → {trip['to']} ({start}-{end})")

                # Vérifier chaînage avec le suivant
                if idx < len(trip_list) - 1:
                    next_trip = trip_list[idx + 1][1]
                    gap = next_trip["start"] - trip["end"]

                    if trip["to"][:4] == next_trip["from"][:4]:
                        print(f"        ↓ Chaînage direct (pause {gap}min)")
                    else:
                        hlp_key = (trip["to"][:4], next_trip["from"][:4])
                        if hlp_key in hlp_table:
                            hlp_time = hlp_table[hlp_key]
                            if gap >= hlp_time + 5:
                                pause_after_hlp = gap - hlp_time
                                print(f"        ↓ HLP possible: {hlp_time}min + pause {pause_after_hlp}min")
                            else:
                                print(f"        ⚠ HLP impossible: temps insuffisant")
                        else:
                            print(f"        ⚠ Pas de chaînage disponible")


def run_progressive_tests():
    """Lance tous les tests progressivement"""

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

    solver = ProgressiveSolver(trips)

    print("DIAGNOSTIC PROGRESSIF HLP")
    print("=" * 40)
    print()

    # Tests progressifs
    tests = [
        solver.test_basic_assignment,
        solver.test_with_overlaps,
        solver.test_with_basic_chaining,
        solver.test_minimal_hlp
    ]

    for i, test in enumerate(tests, 1):
        success = test()
        print()

        if not success:
            print(f"❌ ARRÊT au test {i} - contraintes trop restrictives")
            break
    else:
        print("✅ TOUS LES TESTS RÉUSSIS")
        print("Le problème est solvable avec HLP simplifiés")


if __name__ == "__main__":
    run_progressive_tests()