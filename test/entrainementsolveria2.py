from ortools.sat.python import cp_model

class voyage:
    def __init__(self, num_ligne, num_voyage, arret_debut, arret_fin, heure_debut, heure_fin):
        self.num_ligne = (num_ligne)
        self.num_voyage = num_voyage
        self.arret_debut = arret_debut
        self.arret_fin = arret_fin
        self.hdebut = heure_debut
        self.hfin = heure_fin

voyage1 = voyage(
    "A1",
    1,
    "CEN05",
    "GOCAR",
    745,
    803
    )
voyage2 = voyage(
    "A1",
    2,
    "GOCAR",
    "CEN18",
    845,
    903
    )
listes = [voyage1, voyage2]

for i in listes:
    print(f"voyage {i}", i.hdebut, i.hfin)

def solvertest():
    model = cp_model.CpModel()

    voyage_vars = [model.NewBoolVar(f'voyages_{i}') for i in range(len(listes))]

    for i in range(len(listes)):
        for j in range(len(listes)):
            if i != j:
                if listes[i].hfin < listes[j].hdebut:
                    print(f"ok: voyage {i} peut précéder voyage {j}")
                    suit = model.NewBoolVar(f'suit_{i}_{j}')
                    model.AddImplication(suit, voyage_vars[i])
                    model.AddImplication(suit, voyage_vars[j])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        print("solution trouvée")
        for i in range(len(voyage_vars)):
            if solver.Value(voyage_vars[i]) == 1:
                print(f"voyage {i}: début={listes[i].hdebut}, fin={listes[i].hfin}")
    else:
        print("non solution")

solvertest()