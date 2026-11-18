"""Fonctions utilitaires pour construire rapidement les formulaires CustomTkinter."""

import customtkinter as ctk


def ajouter_entree(master, row, texte, pady=10):
    """Ajoute une ligne « libellé + champ de saisie » dans une grille.

    Args:
        master: Widget parent (onglet ou cadre).
        row: Numéro de ligne dans la grille.
        texte: Texte du libellé affiché à gauche.
        pady: Marge verticale autour des widgets.

    Returns:
        Le widget CTkEntry créé.
    """
    ctk.CTkLabel(master=master, text=texte).grid(row=row, column=0, pady=pady)
    entree = ctk.CTkEntry(master=master)
    entree.grid(row=row, column=1, pady=pady)
    return entree


def ajouter_liste_deroulante(master, row, texte, valeurs, width=200, pady=10):
    """Ajoute une ligne « libellé + liste déroulante » dans une grille.

    Args:
        master: Widget parent (onglet ou cadre).
        row: Numéro de ligne dans la grille.
        texte: Texte du libellé affiché à gauche.
        valeurs: Liste des choix proposés.
        width: Largeur de la liste déroulante.
        pady: Marge verticale autour des widgets.

    Returns:
        Le widget CTkComboBox créé.
    """
    ctk.CTkLabel(master=master, text=texte).grid(row=row, column=0, pady=pady)
    liste = ctk.CTkComboBox(master=master, values=valeurs, width=width)
    liste.grid(row=row, column=1, pady=pady)
    return liste