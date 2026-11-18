"""Onglet « Voiturage » : configuration et lancement du solveur ODM."""

from tkinter import messagebox as msgbox, ttk

import customtkinter as ctk

from solveur import solvertest
from tableauCSV import window_tableau_csv

# Paramètres fixes transmis au solveur (en minutes depuis minuit)
BATTEMENT_MAXIMUM = 50
HEURE_DEBUT_APRES_MIDI = 660
HEURE_FIN_MATIN = 1080
DUREE_MAX_SERVICE = 540

# Colonnes du tableau des voyages : nom -> largeur
COLONNES_TABLEAU = {
    "Ligne": 50,
    "Voy.": 50,
    "Début": 80,
    "Fin": 80,
    "De": 120,
    "À": 120,
    "Js srv": 100,
}


class OngletSolveur:
    """Construit l'onglet du solveur et gère ses interactions."""

    def __init__(self, tab):
        """Initialise l'onglet.

        Args:
            tab: Onglet CTkTabview dans lequel placer les widgets.
        """
        self.tab = tab
        self.donnees_chargees = {"voyages": None, "matrice": None}

        self._configurer_grille()
        self._construire_formulaire()
        self._construire_tableau()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    def _configurer_grille(self):
        """Configure la grille de l'onglet et son titre."""
        self.tab.grid_columnconfigure(0, weight=0)
        self.tab.grid_columnconfigure(1, weight=1)
        self.tab.grid_rowconfigure(0, weight=0)
        self.tab.grid_rowconfigure(1, weight=1)
        self.tab.grid_rowconfigure(2, weight=0)

        ctk.CTkLabel(
            master=self.tab,
            text="Configuration du solveur ODM",
            font=("Arial", 14, "bold"),
        ).grid(row=0, column=0, pady=10)

    def _ajouter_champ(self, parent, row, texte, valeur_defaut):
        """Ajoute un champ de configuration (libellé + saisie) dans `parent`.

        Returns:
            Le widget CTkEntry créé, prérempli avec `valeur_defaut`.
        """
        ctk.CTkLabel(master=parent, text=texte).grid(
            row=row, column=0, pady=10, sticky="e", padx=10
        )
        entree = ctk.CTkEntry(master=parent, width=100)
        entree.insert(0, valeur_defaut)
        entree.grid(row=row, column=1, pady=10, sticky="w", padx=10)
        return entree

    def _construire_formulaire(self):
        """Construit le cadre de configuration et ses boutons."""
        config_frame = ctk.CTkFrame(self.tab)
        config_frame.grid(row=1, column=0, sticky="nw", padx=10, pady=10, rowspan=2)

        self.entry_matin = self._ajouter_champ(config_frame, 0, "Services MATIN:", "1")
        self.entry_aprem = self._ajouter_champ(
            config_frame, 1, "Services APRÈS-MIDI:", "1"
        )
        self.entry_battement = self._ajouter_champ(
            config_frame, 2, "Battement minimum:", "5"
        )
        self.entry_max_sol = self._ajouter_champ(
            config_frame, 3, "Nombre max solutions:", "10"
        )

        ctk.CTkButton(
            master=config_frame, text="résoudre", command=self._resoudre,
            width=200, height=40,
        ).grid(row=4, column=0, columnspan=2, pady=10)

        ctk.CTkButton(
            master=config_frame, text="📂 Charger voyages CSV",
            command=self._charger_csv, width=200, height=40,
        ).grid(row=5, column=0, columnspan=2, pady=10)

        self.error_label = ctk.CTkLabel(master=config_frame, text="", text_color="gray")
        self.error_label.grid(row=6, column=0, columnspan=2, pady=10)

    def _construire_tableau(self):
        """Construit le tableau (Treeview) qui liste les voyages chargés."""
        solutions_frame = ctk.CTkFrame(self.tab)
        solutions_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        solutions_frame.grid_rowconfigure(0, weight=1)
        solutions_frame.grid_columnconfigure(0, weight=1)

        ttk.Style().theme_use("clam")

        self.tableau_voyages = ttk.Treeview(
            solutions_frame,
            columns=tuple(COLONNES_TABLEAU),
            show="headings",
            height=15,
        )
        for colonne, largeur in COLONNES_TABLEAU.items():
            self.tableau_voyages.column(colonne, width=largeur, anchor="center")
            self.tableau_voyages.heading(colonne, text=colonne)

        scrollbar_y = ttk.Scrollbar(
            solutions_frame, orient="vertical", command=self.tableau_voyages.yview
        )
        self.tableau_voyages.configure(yscrollcommand=scrollbar_y.set)

        self.tableau_voyages.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

    # ------------------------------------------------------------------
    # Chargement des données
    # ------------------------------------------------------------------
    def _remplir_tableau(self, matrice_donnees):
        """Remplace le contenu du tableau par les lignes de la matrice."""
        self.tableau_voyages.delete(*self.tableau_voyages.get_children())
        if matrice_donnees is not None:
            for ligne in matrice_donnees:
                self.tableau_voyages.insert("", "end", values=tuple(ligne))

    def _on_voyages_charges(self, objets_voyages, matrice_donnees):
        """Callback appelé quand l'utilisateur valide le CSV.

        Args:
            objets_voyages: Liste des objets voyage à transmettre au solveur.
            matrice_donnees: Données brutes à afficher dans le tableau.
        """
        self.donnees_chargees["voyages"] = objets_voyages
        self.donnees_chargees["matrice"] = matrice_donnees
        self._remplir_tableau(matrice_donnees)

    def _charger_csv(self):
        """Ouvre la fenêtre de chargement d'un CSV de voyages."""
        window_tableau_csv(callback=self._on_voyages_charges)

    # ------------------------------------------------------------------
    # Résolution
    # ------------------------------------------------------------------
    def _resoudre(self):
        """Lit la configuration, lance le solveur et affiche le résultat."""
        try:
            if self.donnees_chargees["voyages"] is None:
                msgbox.showerror("Erreur", "Il n'y a aucun voyage selectionné")
                return

            solutions = solvertest(
                self.donnees_chargees["voyages"],
                battement_minimum=int(self.entry_battement.get()),
                verifier_arrets=True,
                battement_maximum=BATTEMENT_MAXIMUM,
                max_solutions=int(self.entry_max_sol.get()),
                max_services_matin=int(self.entry_matin.get()),
                max_services_apres_midi=int(self.entry_aprem.get()),
                heure_debut_apres_midi=HEURE_DEBUT_APRES_MIDI,
                heure_fin_matin=HEURE_FIN_MATIN,
                duree_max_service=DUREE_MAX_SERVICE,
            )

            if solutions:
                self.error_label.configure(
                    text=f"{len(solutions)} solution(s) trouvée(s)", text_color="green"
                )
                self._afficher_resultats(solutions)
            else:
                self.error_label.configure(
                    text="Aucune solution trouvée", text_color="orange"
                )
                msgbox.showwarning("Résultat", "Aucune solution trouvée")

        except ValueError as erreur:
            self.error_label.configure(
                text="Erreur: entrez des nombres valides", text_color="red"
            )
            msgbox.showerror("Erreur", f"Erreur de saisie: {erreur}")
        except Exception as erreur:
            self.error_label.configure(text=f"Erreur: {erreur}", text_color="red")
            msgbox.showerror("Erreur", f"Erreur lors de la résolution: {erreur}")

    @staticmethod
    def _afficher_resultats(solutions):
        """Affiche toutes les solutions dans une seule zone de texte.

        Args:
            solutions: Liste de solutions, chacune étant une liste de services.
        """
        fenetre = ctk.CTkToplevel()
        fenetre.title("Résultats du solveur")
        fenetre.geometry("900x700")

        ctk.CTkLabel(
            fenetre,
            text=f"{len(solutions)} solution(s) trouvée(s)",
            font=("Arial", 16, "bold"),
        ).pack(pady=10)

        zone_texte = ctk.CTkTextbox(fenetre, font=("Consolas", 12))
        zone_texte.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        lignes = []
        for idx, services in enumerate(solutions, 1):
            lignes.extend(["=" * 70, f"SOLUTION {idx}", "=" * 70])
            for service in services:
                lignes.extend([str(service), ""])
            lignes.append("")

        zone_texte.insert("1.0", "\n".join(lignes))
        zone_texte.configure(state="disabled")
        fenetre.lift()