from ortools.sat.python import cp_model

class BusSchedulePrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, assignments, trips, max_solutions=5):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.assignments = assignments
        self.trips = trips
        self.solution_count = 0
        self.max_solutions = max_solutions

    def on_solution_callback(self):
        if self.solution_count >= self.max_solutions:
            self.StopSearch()
            return
        self.solution_count += 1
        print(f"\n🟢 Solution {self.solution_count}:")
        for i, var in enumerate(self.assignments):
            start, end = self.trips[i]
            print(f"  Voyage {i} ({start//60:02d}h{start%60:02d}–{end//60:02d}h{end%60:02d}) → Service {self.Value(var)}")

def bus_schedule_with_pause():
    model = cp_model.CpModel()

    # 🕒 Voyages en minutes (start, end)
    trips = [
        (383, 418),  # 6h23–6h58
        (390, 420),  # 6h30–7h00
        (425, 455),  # 7h05–7h35
        (460, 490),  # 7h40–8h10
        (500, 530),  # 8h20–8h50
    ]

    num_trips = len(trips)
    num_services = 2

    # 🔢 Variables : service assigné à chaque voyage
    assignments = [model.NewIntVar(0, num_services - 1, f"service_{i}") for i in range(num_trips)]

    # 🚫 Contrainte de chevauchement
    for i in range(num_trips):
        for j in range(i + 1, num_trips):
            start_i, end_i = trips[i]
            start_j, end_j = trips[j]
            if start_i < end_j and start_j < end_i:
                model.Add(assignments[i] != assignments[j])

    # ⏸️ Pause minimale de 20 minutes + 20% du temps de travail
    for s in range(num_services):
        is_assigned = []
        for i in range(num_trips):
            b = model.NewBoolVar(f"trip_{i}_on_service_{s}")
            model.Add(assignments[i] == s).OnlyEnforceIf(b)
            model.Add(assignments[i] != s).OnlyEnforceIf(b.Not())
            is_assigned.append(b)

        # Durées de travail
        work_durations = []
        for i, b in enumerate(is_assigned):
            start, end = trips[i]
            duration = end - start
            d = model.NewIntVar(0, duration, f"work_{i}_s{s}")
            model.Add(d == duration).OnlyEnforceIf(b)
            model.Add(d == 0).OnlyEnforceIf(b.Not())
            work_durations.append(d)

        total_work = model.NewIntVar(0, 1440, f"total_work_s{s}")
        model.Add(total_work == sum(work_durations))

        # Pauses entre voyages consécutifs
        pause_durations = []
        for i in range(num_trips):
            for j in range(num_trips):
                if i != j:
                    start_i, end_i = trips[i]
                    start_j, end_j = trips[j]
                    if end_i <= start_j:
                        b1 = is_assigned[i]
                        b2 = is_assigned[j]
                        pause = model.NewIntVar(0, 1440, f"pause_{i}_{j}_s{s}")
                        model.Add(pause == start_j - end_i).OnlyEnforceIf([b1, b2])

                        # Si les deux voyages sont assignés, pause ≥ 20 minutes
                        model.Add(pause >= 5).OnlyEnforceIf([b1, b2])

                        # Si au moins un n'est pas assigné, pause = 0
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

        # Contrainte : pause ≥ 20% du travail
        model.Add(total_pause * 100 >= total_work * 20)

    # 🔍 Résolution
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = 10

    printer = BusSchedulePrinter(assignments, trips, max_solutions=5)
    status = solver.Solve(model, printer)

    print(f"\n🔎 Status : {solver.StatusName(status)}")
    print(f"✅ Nombre de solutions trouvées : {printer.solution_count}")

bus_schedule_with_pause()