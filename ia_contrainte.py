from ortools.sat.python import cp_model
import sqlite3

import re

from gestion_contrainte import BusSchedulePrinter


def minutes_to_time(minutes):
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}h{m:02d}"

class BusSchedulePrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, assignments, trips, order=None, max_solutions=5):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.assignments = assignments
        self.trips = trips
        self.order = order
        self.solution_count = 0
        self.max_solutions = max_solutions

    def OnSolutionCallback(self):
        if self.solution_count >= self.max_solutions:
            return

        print(f"\n🟢 Solution {self.solution_count + 1}:")

        # Regrouper les trajets par service
        service_trips = {}
        for i in range(len(self.trips)):
            service = self.Value(self.assignments[i])
            if service not in service_trips:
                service_trips[service] = []
            order_val = self.Value(self.order[i]) if self.order else i
            service_trips[service].append((order_val, i))

        # Afficher les trajets triés par ordre dans chaque service
        for service in sorted(service_trips.keys()):
            print(f"  🔧 Service {service}:")
            for order_val, i in sorted(service_trips[service]):
                trip = self.trips[i]
                start = minutes_to_time(trip["start"])
                end = minutes_to_time(trip["end"])
                print(f"    [{order_val}] {trip['from']} → {trip['to']} ({start}–{end})")

        self.solution_count += 1

def voiturage_ia():
    model = cp_model.CpModel()

    trips = [
        {"start": 383, "end": 418, "from": "A", "to": "B"},
        {"start": 390, "end": 420, "from": "B", "to": "A"},
        {"start": 425, "end": 455, "from": "A", "to": "C"},
        {"start": 460, "end": 490, "from": "C", "to": "D"},
        {"start": 500, "end": 530, "from": "D", "to": "A"},
    ]

    num_trips = len(trips)
    num_services_max = 5

    assignments = [model.NewIntVar(0, num_services_max - 1, f"service_{i}") for i in range(num_trips)]
    order = [model.NewIntVar(0, num_trips - 1, f"order_{i}") for i in range(num_trips)]
    model.AddAllDifferent(order)

    # Détection des premiers trajets
    is_first = [model.NewBoolVar(f"is_first_{j}") for j in range(num_trips)]
    for j in range(num_trips):
        blockers = []
        for i in range(num_trips):
            if i != j:
                same_service = model.NewBoolVar(f"same_service_{i}_{j}_first")
                model.Add(assignments[i] == assignments[j]).OnlyEnforceIf(same_service)
                model.Add(assignments[i] != assignments[j]).OnlyEnforceIf(same_service.Not())

                i_before_j = model.NewBoolVar(f"order_{i}_before_{j}_first")
                model.Add(order[i] < order[j]).OnlyEnforceIf(i_before_j)
                model.Add(order[i] >= order[j]).OnlyEnforceIf(i_before_j.Not())

                blocker = model.NewBoolVar(f"blocker_{i}_{j}")
                model.AddBoolAnd([same_service, i_before_j]).OnlyEnforceIf(blocker)
                model.AddBoolOr([same_service.Not(), i_before_j.Not()]).OnlyEnforceIf(blocker.Not())

                blockers.append(blocker)
        if blockers:
            model.AddBoolOr(blockers).OnlyEnforceIf(is_first[j].Not())
            model.AddBoolAnd([b.Not() for b in blockers]).OnlyEnforceIf(is_first[j])

    # Chaînage renforcé pour les trajets non premiers
    for j in range(num_trips):
        predecessors = []
        for i in range(num_trips):
            if i != j:
                if trips[i]["to"] == trips[j]["from"] and trips[i]["end"] <= trips[j]["start"]:
                    same_service = model.NewBoolVar(f"same_service_{i}_{j}")
                    model.Add(assignments[i] == assignments[j]).OnlyEnforceIf(same_service)
                    model.Add(assignments[i] != assignments[j]).OnlyEnforceIf(same_service.Not())

                    i_before_j = model.NewBoolVar(f"order_{i}_before_{j}")
                    model.Add(order[i] < order[j]).OnlyEnforceIf(i_before_j)
                    model.Add(order[i] >= order[j]).OnlyEnforceIf(i_before_j.Not())

                    valid_chain = model.NewBoolVar(f"valid_chain_{i}_{j}")
                    model.AddBoolAnd([same_service, i_before_j]).OnlyEnforceIf(valid_chain)
                    model.AddBoolOr([same_service.Not(), i_before_j.Not()]).OnlyEnforceIf(valid_chain.Not())

                    predecessors.append(valid_chain)
        if predecessors:
            model.AddBoolOr(predecessors).OnlyEnforceIf(is_first[j].Not())

    # Interdire les chevauchements sur le même service
    for i in range(num_trips):
        for j in range(i + 1, num_trips):
            if trips[i]["start"] < trips[j]["end"] and trips[j]["start"] < trips[i]["end"]:
                model.Add(assignments[i] != assignments[j])

    # Contraintes par service
    for s in range(num_services_max):
        is_assigned = []
        for i in range(num_trips):
            b = model.NewBoolVar(f"trip_{i}_on_service_{s}")
            model.Add(assignments[i] == s).OnlyEnforceIf(b)
            model.Add(assignments[i] != s).OnlyEnforceIf(b.Not())
            is_assigned.append(b)

        work_durations = []
        for i, b in enumerate(is_assigned):
            duration = trips[i]["end"] - trips[i]["start"]
            d = model.NewIntVar(0, duration, f"work_{i}_s{s}")
            model.Add(d == duration).OnlyEnforceIf(b)
            model.Add(d == 0).OnlyEnforceIf(b.Not())
            work_durations.append(d)

        total_work = model.NewIntVar(0, 1440, f"total_work_s{s}")
        model.Add(total_work == sum(work_durations))

        pause_durations = []
        for i in range(num_trips):
            for j in range(num_trips):
                if i != j and trips[i]["end"] <= trips[j]["start"]:
                    b1 = is_assigned[i]
                    b2 = is_assigned[j]
                    pause = model.NewIntVar(0, 1440, f"pause_{i}_{j}_s{s}")
                    model.Add(pause == trips[j]["start"] - trips[i]["end"]).OnlyEnforceIf([b1, b2])
                    model.Add(pause >= 5).OnlyEnforceIf([b1, b2])

                    not_both = model.NewBoolVar(f"not_both_{i}_{j}_s{s}")
                    model.AddBoolOr([b1.Not(), b2.Not()]).OnlyEnforceIf(not_both)
                    model.AddBoolAnd([b1, b2]).OnlyEnforceIf(not_both.Not())
                    model.Add(pause == 0).OnlyEnforceIf(not_both)

                    pause_durations.append(pause)

        total_pause = model.NewIntVar(0, 1440, f"total_pause_s{s}")
        if pause_durations:
            model.Add(total_pause == sum(pause_durations))
        else:
            model.Add(total_pause == 0)
        model.Add(total_pause * 100 >= total_work * 5)

    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = 10

    printer = BusSchedulePrinter(assignments, trips, order=order, max_solutions=10)
    status = solver.Solve(model, printer)

    print(f"\nStatus : {solver.StatusName(status)}")
    print(f"Nombre de solution trouvées = {printer.solution_count}")

voiturage_ia()
