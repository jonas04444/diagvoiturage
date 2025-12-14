from ortools.sat.python import cp_model

class voyage:
    def __init__(self, heure_debut, heure_fin):
        self.hdebut = heure_debut
        self.hfin = heure_fin

voyage1 = voyage(800,900)
voyage2 = voyage(900,1000)
listes = [voyage1, voyage2]

def solvertest():
    model = cp_model.CpModel()

    voyage_vars = [model.NewBoolVar(f'voyages_{i}') for i in range(len(listes))]

    for i in range(len(listes)):
        for j in range(len(listes)):
            if i != j:
                if listes[i].hfin < listes[j].hdebut:
                    print("ok")
                    suit = model.NewBoolVar(f'suit_{i}_{j}')
                    model.AddImplication(suit, voyage_vars[i])
                    model.AddImplication(suit, voyage_vars[j])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("solution trouvée")
        for i in range(len(voyage_vars)):
            if solver.Value(voyage_vars[i]) == 1:
                print(f"voyage {i}: début={listes[i].hdebut}, fin={listes[i].hfin}")
    else:
        print("non solution")

solvertest()