import csv

import customtkinter as ctk
import numpy as np
from tkinter import ttk, messagebox as msgbox, filedialog

from objet import voyage


def _en_nombre(val):
    """Convertit une chaîne en int/float si possible, sinon la renvoie telle quelle."""
    try:
        nombre = float(val)
    except (ValueError, TypeError):
        return val
    return int(nombre) if nombre.is_integer() else nombre


class TableauCSV(ctk.CTkFrame):
    COLONNES_DONNEES = ('Ligne', 'Voy.', 'Début', 'Fin', 'De', 'À', 'Js srv')
    COLONNES = ('Sélection',) + COLONNES_DONNEES
    LARGEURS = {
        'Sélection': 50, 'Ligne': 50, 'Voy.': 50, 'Début': 80,
        'Fin': 80, 'De': 120, 'À': 120, 'Js srv': 100,
    }
    COCHE, DECOCHE = '☑', '☐'

    def __init__(self, parent, fichier_csv=None, callback=None):
        super().__init__(parent)
        self.callback = callback
        self.donnees = []
        self.donnees_selectionnees = []
        self.matrice_donnees = None
        self.tableau = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        if fichier_csv:
            self.charger_csv(fichier_csv)

        self.creer_boutons()
        self.creer_tableau()

    # ------------------------------------------------------------------ CSV
    def charger_csv(self, chemin_fichier):
        try:
            with open(chemin_fichier, 'r', encoding='utf-8-sig') as file:
                delimiter = ';' if ';' in file.readline() else ','
                file.seek(0)
                self.donnees = list(csv.DictReader(file, delimiter=delimiter))
        except Exception as e:
            msgbox.showerror("Erreur", f"Erreur lors du chargement du CSV : {e}")
            self.donnees = []

    def selection_csv(self):
        fichier = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        if not fichier:
            return

        self.charger_csv(fichier)
        self.tableau.delete(*self.tableau.get_children())
        self.remplir_tableau()
        msgbox.showinfo("Succès", f"Fichier chargé : {fichier}")

    # ------------------------------------------------------------------ UI
    def creer_boutons(self):
        frame_boutons = ctk.CTkFrame(self)
        frame_boutons.grid(row=0, column=0, sticky='ew', padx=10, pady=10)

        boutons = [
            ("Sélectionner un fichier CSV", 100, {}, self.selection_csv),
            ("Sélectionner tous", 120,
             {"fg_color": "#4CAF50", "hover_color": "#388E3C"},
             lambda: self.definir_selection(self.COCHE)),
            ("Désélectionner tous", 120,
             {"fg_color": "#FF9800", "hover_color": "#F57C00"},
             lambda: self.definir_selection(self.DECOCHE)),
            ("Charger dans la matrice", 100, {}, self.creer_matrice_selection),
            ("Quitter", 100, {}, self.quitter_avec_confirmation),
        ]
        for texte, largeur, style, commande in boutons:
            ctk.CTkButton(
                frame_boutons, text=texte, width=largeur, command=commande, **style
            ).pack(side="left", padx=5)

    def creer_tableau(self):
        frame_tableau = ctk.CTkFrame(self)
        frame_tableau.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        frame_tableau.grid_rowconfigure(0, weight=1)
        frame_tableau.grid_columnconfigure(0, weight=1)

        ttk.Style().theme_use('clam')

        self.tableau = ttk.Treeview(
            frame_tableau, columns=self.COLONNES, show='headings', height=15
        )
        for col in self.COLONNES:
            self.tableau.column(col, width=self.LARGEURS[col], anchor='center')
            self.tableau.heading(col, text=col, command=lambda c=col: self.trier_colonne(c))

        scrollbar_y = ttk.Scrollbar(frame_tableau, orient='vertical', command=self.tableau.yview)
        self.tableau.configure(yscrollcommand=scrollbar_y.set)

        self.tableau.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')

        self.tableau.bind('<Button-1>', self.cocher_case)
        self.remplir_tableau()

    def remplir_tableau(self):
        for idx, ligne in enumerate(self.donnees):
            valeurs = [self.DECOCHE] + [
                (ligne.get(col) or '').strip() for col in self.COLONNES_DONNEES
            ]
            self.tableau.insert('', 'end', iid=idx, values=valeurs)

    def quitter_avec_confirmation(self):
        if msgbox.askyesno("Confirmation", "Êtes-vous sûr de vouloir quitter ?"):
            self.master.destroy()

    # ------------------------------------------------------------ Sélection
    def definir_selection(self, symbole):
        """Coche ou décoche toutes les lignes du tableau."""
        for item in self.tableau.get_children():
            valeurs = list(self.tableau.item(item, 'values'))
            valeurs[0] = symbole
            self.tableau.item(item, values=valeurs)

    def cocher_case(self, event):
        item = self.tableau.identify('item', event.x, event.y)
        if item and self.tableau.identify_column(event.x) == '#1':
            valeurs = list(self.tableau.item(item, 'values'))
            valeurs[0] = self.DECOCHE if valeurs[0] == self.COCHE else self.COCHE
            self.tableau.item(item, values=valeurs)

    def trier_colonne(self, col):
        col_index = self.COLONNES.index(col)
        items = [(self.tableau.item(i, 'values'), i) for i in self.tableau.get_children('')]
        reverse = getattr(self, f'tri_reverse_{col}', False)

        try:
            items.sort(key=lambda x: float(x[0][col_index] or 0), reverse=reverse)
        except (ValueError, TypeError):
            items.sort(key=lambda x: str(x[0][col_index]).lower(), reverse=reverse)

        setattr(self, f'tri_reverse_{col}', not reverse)
        for index, (_, item) in enumerate(items):
            self.tableau.move(item, '', index)

    # --------------------------------------------------------------- Matrice
    def _lignes_cochees(self):
        """Renvoie les dictionnaires CSV des lignes cochées."""
        return [
            self.donnees[int(item)]
            for item in self.tableau.get_children()
            if self.tableau.item(item, 'values')[0] == self.COCHE
        ]

    def creer_matrice_selection(self):
        self.donnees_selectionnees = []
        objets_voyages = []

        for ligne in self._lignes_cochees():
            champ = lambda nom, defaut='': (ligne.get(nom) or defaut).strip()
            try:
                objets_voyages.append(voyage(
                    num_ligne=champ('Ligne'),
                    num_voyage=champ('Voy.'),
                    arret_debut=champ('De'),
                    arret_fin=champ('À'),
                    heure_debut=champ('Début', '00:00'),
                    heure_fin=champ('Fin', '00:00'),
                    js_srv=champ('Js srv'),
                ))
                self.donnees_selectionnees.append(ligne)
            except Exception as e:
                msgbox.showerror("Erreur", f"Erreur lors de la création du voyage : {e}")

        if not self.donnees_selectionnees:
            msgbox.showwarning("Attention", "Aucun voyage sélectionné")
            return

        matrice = [
            [_en_nombre((ligne.get(col) or '').strip()) for col in self.COLONNES_DONNEES]
            for ligne in self.donnees_selectionnees
        ]
        self.matrice_donnees = np.array(matrice, dtype=object)

        if self.callback:
            self.callback(objets_voyages, self.matrice_donnees)

        msgbox.showinfo(
            "Succès", f"{len(self.donnees_selectionnees)} voyage(s) chargé(s) dans la matrice"
        )


class window_tableau_csv(ctk.CTkToplevel):
    """Fenêtre de sélection de voyages depuis un CSV (fenêtre secondaire)."""

    def __init__(self, callback=None):
        super().__init__()
        self.title("Affichage CSV")
        self.geometry("1000x700")

        self.tableau_widget = TableauCSV(self, callback=callback)
        self.tableau_widget.pack(fill="both", expand=True)

        self.lift()