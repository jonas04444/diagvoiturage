"""Onglet « Liste voyage »."""

import customtkinter as ctk

from sqlite import get_lignes_from_db
from ui_helpers import ajouter_liste_deroulante


def construire_onglet_liste_voyages(tab):
    """Construit le contenu de l'onglet de sélection des voyages.

    Args:
        tab: Onglet CTkTabview dans lequel placer les widgets.
    """
    tab.grid_columnconfigure(0, weight=0)
    tab.grid_columnconfigure(1, weight=1)
    tab.grid_rowconfigure(0, weight=0)
    tab.grid_rowconfigure(1, weight=1)
    tab.grid_rowconfigure(2, weight=0)

    return ajouter_liste_deroulante(tab, 0, "sélection ligne:", get_lignes_from_db())