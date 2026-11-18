"""Onglet « Création ligne et lieux »."""

import customtkinter as ctk

from sqlite import add_line, add_lieux
from ui_helpers import ajouter_entree


def construire_onglet_lignes_lieux(tab):
    """Construit le contenu de l'onglet de création de lignes et de lieux.

    Args:
        tab: Onglet CTkTabview dans lequel placer les widgets.
    """
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(master=tab, text="Création de ligne et lieu").grid(
        row=0, column=1, pady=10
    )

    # --- Création d'une ligne ---
    num_ligne = ajouter_entree(tab, 1, "entrer ligne:")
    num_variante = ajouter_entree(tab, 2, "entrer variant:")

    def ajouter_une_ligne():
        """Enregistre la ligne saisie en base."""
        add_line([{
            "num_ligne": int(num_ligne.get()),
            "Variante": int(num_variante.get()),
        }])

    ctk.CTkButton(master=tab, text="valider", command=ajouter_une_ligne).grid(
        row=3, column=1, pady=20
    )

    # --- Création d'un lieu ---
    id_lieu = ajouter_entree(tab, 4, "entrer lieu:")
    commune = ajouter_entree(tab, 5, "entrer commune:")
    description = ajouter_entree(tab, 6, "entrer description:")
    zone = ajouter_entree(tab, 7, "entrer zone:")

    def ajouter_un_lieu():
        """Enregistre le lieu saisi en base."""
        add_lieux([{
            "id_lieux": id_lieu.get().strip(),
            "commune": commune.get().strip(),
            "description": description.get().strip(),
            "zone": int(zone.get()),
        }])

    ctk.CTkButton(master=tab, text="ajouter lieu", command=ajouter_un_lieu).grid(
        row=8, column=1, pady=10
    )