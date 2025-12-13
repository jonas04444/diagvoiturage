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

solvertest()