from ortools.sat.python import cp_model

def solvertest():
    model = cp_model.CpModel()

    num_val = 3
    x = model.NewIntVar(0, num_val - 1, 'x')
    y = model.NewIntVar(0, num_val - 1, 'y')
    z = model.NewIntVar(0, num_val - 1, 'z')

    model.Add(x != y)

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

solvertest()