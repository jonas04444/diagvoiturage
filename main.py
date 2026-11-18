"""Point d'entrée de l'application : fenêtre principale et onglets."""

import customtkinter as ctk
from customtkinter import CTkTabview

from onglet_lignes_lieux import construire_onglet_lignes_lieux
from onglet_liste_voyages import construire_onglet_liste_voyages
from onglet_solveur import OngletSolveur
from onglet_voyage import construire_onglet_voyage


def main():
    """Crée la fenêtre principale, ses onglets, et lance la boucle Tk."""
    win = ctk.CTk()
    win.title("menu")
    win.geometry("1400x900")
    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)

    tabview = CTkTabview(master=win, width=1350, height=850, corner_radius=15)
    tabview.grid(row=0, column=0, columnspan=3, padx=20, pady=20, sticky="nsew")

    tab_voyage = tabview.add("Création voyage")
    tab_lignes_lieux = tabview.add("Création ligne et lieux")
    tab_liste = tabview.add("Liste voyage")
    tab_solveur = tabview.add("Voiturage")
    tabview.add("Gestion des voitures")  # onglet pas encore implémenté

    construire_onglet_voyage(tab_voyage)
    construire_onglet_lignes_lieux(tab_lignes_lieux)
    construire_onglet_liste_voyages(tab_liste)
    OngletSolveur(tab_solveur)

    win.mainloop()


if __name__ == "__main__":
    main()