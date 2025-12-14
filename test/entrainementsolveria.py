from ortools.sat.python import cp_model

class voyage:
    def __init__(self, heure_debut, heure_fin):
        self.hdebut = heure_debut
        self.hfin = heure_fin

def egalite(x,y,z):
    return x + y == z


def solvertest():
    model = cp_model.CpModel()

    num_val = 3
    x = model.NewIntVar(0, num_val - 1, 'x')
    y = model.NewIntVar(0, num_val - 1, 'y')
    z = model.NewIntVar(0, num_val - 1, 'z')

    #model.Add(egalite(x,y,z))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)


    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"x = {solver.Value(x)}")
        print(f"y = {solver.Value(y)}")
        print(f"z = {solver.Value(z)}")

    else:
        print("No solution!")

    solution = SolutionPrinter([x, y, z])
    solver.parameters.enumerate_all_solutions = True
    status = solver.Solve(model, solution)

class SolutionPrinter(cp_model.CpSolverSolutionCallback):

    def __init__(self, variables: list[cp_model.IntVar]):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0

    def on_solution_callback(self) -> None:
        self.__solution_count += 1
        for v in self.__variables:
            print(f"{v}={self.Value(v)}", end=" ")
        print()
    def solution_count(self) -> int:
        return self.__solution_count


voyage1 = voyage(800,900)
voyage2 = voyage(900,1000)

listes = [voyage1, voyage2]

for i, v in enumerate(listes):
    print(f"Voyage {i+1}: {v.hdebut}")