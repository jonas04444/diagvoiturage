from ortools.sat.python import cp_model
import sqlite3

import re

import re


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
        (383, 418),     #6h23-6h58
        (390, 420),  # 6h30–7h00
        (425, 455),  # 7h05–7h35
        (460, 490),  # 7h40–8h10
        (500, 530),  # 8h20–8h50
    ]

    num_trips = len(trips)
    num_services_max = 3

    assignments = [model.NewIntVar(0, num_services_max -1, f"service_{i}") for i in range(num_trips)]