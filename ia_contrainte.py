from ortools.sat.python import cp_model
import sqlite3

import re

from gestion_contrainte import BusSchedulePrinter


def convert_to_minutes(horaire_str):
    horaire_str = horaire_str.strip()

    match = re.match(r"^(\d{1,2})[:hH.]?(\d{2})$", horaire_str)
    if not match:
        raise ValueError(f"Format horaire invalide : {horaire_str}")

    h, m = map(int, match.groups())
    return h * 60 + m

def voiturage_ia():
    model = cp_model.CpModel()

    #ici on met les voyages
    trips = [
        (383, 418),  # 6h23-6h58
        (390, 420),  # 6h30–7h00
        (425, 455),  # 7h05–7h35
        (460, 490),  # 7h40–8h10
        (500, 530),  # 8h20–8h50
    ]

    num_trips = len(trips)
    num_services_max = 3

    assignments = [model.NewIntVar(0, num_services_max -1, f"service_{i}") for i in range(num_trips)]

    for i in range(num_trips):
        for j in range(i + 1, num_trips):
            start_i , end_i = trips[i]
            start_j , end_j = trips[j]
            if start_i < end_j and start_j < end_i:
                model.add(assignments[i] != assignments[j])


    for s in range(num_services_max):
        is_assigned = []
        for i in range(num_trips):
            b = model.NewBoolVar(f"trip_{i}_on_service_{s}")
            model.add(assignments[i] == s).only_enforce_if(b)
            model.add(assignments[i] != s).only_enforce_if(b.Not())
            is_assigned.append(b)

        work_durations = []
        for i, b in enumerate(is_assigned):
            start, end = trips[i]
            duration = end - start
            d = model.NewIntVar(0, duration, f"work_{i}_s{s}")
            model.Add(d == duration).OnlyEnforceIf(b)
            model.Add(d == 0).OnlyEnforceIf(b.Not())
            work_durations.append(d)
        total_work = model.NewIntVar(0 , 1440, f"total_work_s{s}")
        model.add(total_work == sum(work_durations))

        pause_durations = []
        for i in range(num_trips):
            for j in range(num_trips):
                if i != j:
                    start_i, end_i = trips[i]
                    start_j, end_j = trips[j]
                    if end_i <= start_j:
                        b1 = is_assigned[i]
                        b2 = is_assigned[j]
                        pause = model.NewIntVar(0 , 1440, f"pause_{i}_{j}_s{s}")
                        model.add(pause == start_j - end_i).OnlyEnforceIf([b1,b2])

                        model.Add(pause >= 5).OnlyEnforceIf([b1, b2])

                        not_both_assigned = model.NewBoolVar(f"not_both_assigned_{i}_{j}_s{s}")
                        model.AddBoolOr([b1.Not(), b2.Not()]).OnlyEnforceIf(not_both_assigned)
                        model.AddBoolAnd([b1, b2]).OnlyEnforceIf(not_both_assigned.Not())
                        model.Add(pause == 0).OnlyEnforceIf(not_both_assigned)

                        pause_durations.append(pause)

        total_pause = model.NewIntVar(0, 1440, f"total_pause_s{s}")
        if pause_durations:
            model.Add(total_pause == sum(pause_durations))
        else:
            model.Add(total_pause == 0)
        model.add(total_pause * 100 >= total_work * 20)
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = 10

    printer = BusSchedulePrinter(assignments, trips, max_solutions=5)
    status = solver.Solve(model, printer)

    print(f"\n Status : {solver.StatusName(status)}")
    print(f"Nombre de solution trouvées = {printer.solution_count}")

voiturage_ia()