"""Onglet « Création voyage »."""

import customtkinter as ctk

from sqlite import add_trajet, charger_csv, get_lieux_from_db, get_lignes_from_db
from ui_helpers import ajouter_entree, ajouter_liste_deroulante


def construire_onglet_voyage(tab):
    """Construit le contenu de l'onglet de création de voyage.

    Args:
        tab: Onglet CTkTabview dans lequel placer les widgets.
    """
    for col in range(3):
        tab.grid_columnconfigure(col, weight=1)

    ctk.CTkLabel(master=tab, text="création voyage").grid(
        row=0, column=1, pady=10, sticky="ew"
    )

    lieux = get_lieux_from_db()
    ligne_dropdown = ajouter_liste_deroulante(
        tab, 1, "sélectionner ligne:", get_lignes_from_db()
    )
    numvoyage = ajouter_entree(tab, 2, "entrez numéro de voyage")
    debutarret = ajouter_entree(tab, 3, "entrer début:")
    finarret = ajouter_entree(tab, 4, "entrer fin:")
    lieux_debut = ajouter_liste_deroulante(tab, 5, "entrer lieux de début:", lieux)
    lieux_fin = ajouter_liste_deroulante(tab, 6, "entrer lieux de fin:", lieux)

    def ajouter_un_trajet():
        """Lit le formulaire et enregistre le trajet en base."""
        ligne = ligne_dropdown.get().split()
        add_trajet([{
            "Num_ligne": int(ligne[1]),
            "variant": int(ligne[-1]),
            "Num_trajet": int(numvoyage.get()),
            "DP_arret": lieux_debut.get().strip(),
            "DR_arret": lieux_fin.get().strip(),
            "Heure_Start": debutarret.get().strip(),
            "Heure_End": finarret.get().strip(),
        }])

    ctk.CTkButton(
        master=tab, text="ajouter un trajet", command=ajouter_un_trajet
    ).grid(row=7, column=1, pady=10)

    ctk.CTkButton(
        master=tab, text="Charger CSV", command=charger_csv, width=200
    ).grid(row=8, column=1, pady=10)