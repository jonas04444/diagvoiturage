import customtkinter as ctk
import csv
from tkinter import ttk, messagebox as msgbox, filedialog, Toplevel
import numpy as np
from ortools.math_opt.python import callback


class TableauCSV(ctk.CTkFrame):
    def __init__(self, parent, fichie_csv=None):
        super().__init__(parent)
        self.fichier_csv = fichie_csv
        self.donnees = []
        self.tableau = None

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        if fichie_csv:
            self.charger_csv(fichie_csv)

        self.creer_boutons()
        self.creer_tableau()

    def charger_csv(self, chemin_fichier):
        try:
            with open(chemin_fichier, 'r', encoding='utf-8-sig') as file:
                premiere_ligne = file.readline()
                file.seek(0)

                if ';' in premiere_ligne:
                    delimiter = ';'
                else:
                    delimiter = ','
                lecture = csv.DictReader(file, delimiter=delimiter)
                self.donnees = list(lecture)

        except Exception as e:
            msgbox.showerror("Erreur", f"Erreur lors du chargement du CSV : {e}")
            self.donnees = []

    def selection_csv(self):
        fichier = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )

        if fichier:
            self.charger_csv(fichier)
            for item in self.tableau.get_children():
                self.tableau.delete(item)
            self.remplir_tableau()
            msgbox.showinfo("Succès", f"Fichier chargé: {fichier}")

    def creer_boutons(self):
        frame_boutons = ctk.CTkFrame(self)
        frame_boutons.grid(row=0, column=0, sticky='ew', padx=10, pady=10)

        download_csv = ctk.CTkButton(
            frame_boutons,
            text="Sélectionner un fichier CSV",
            width=100,
            command=lambda: self.selection_csv()
        )
        download_csv.pack(side="left", padx=5)

        commit_csv = ctk.CTkButton(
            frame_boutons,
            text="Charger dans la matrice",
            width=100,
            command=lambda: self.creer_matrice_selection()
        )
        commit_csv.pack(side="left", padx=5)

        exit_csv_window = ctk.CTkButton(
            frame_boutons,
            text="exit",
            width=100,
            command=lambda: self.quitter_avec_confirmation()
        )
        exit_csv_window.pack(side="left", padx=5)

    def quitter_avec_confirmation(self):
        if msgbox.askyesno("Confirmation", "Êtes-vous sûr de vouloir quitter ?"):
            self.master.destroy()

    def creer_tableau(self):
        frame_tableau = ctk.CTkFrame(self)
        frame_tableau.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)

        style = ttk.Style()
        style.theme_use('clam')

        colonnes = ('Sélection', 'Ligne', 'Voy.', 'Début', 'Fin', 'De', 'À', 'Js srv')

        self.tableau = ttk.Treeview(
            frame_tableau,
            columns=colonnes,
            show='headings',
            height=15
        )

        en_tetes = {
            'Sélection': 50,
            'Ligne': 50,
            'Voy.': 50,
            'Début': 80,
            'Fin': 80,
            'De': 120,
            'À': 120,
            'Js srv': 100
        }

        for col, largeur in en_tetes.items():
            self.tableau.column(col, width=largeur, anchor='center')
            self.tableau.heading(col, text=col)

        self.remplir_tableau()

        scrollbar_y = ttk.Scrollbar(
            frame_tableau,
            orient='vertical',
            command=self.tableau.yview
        )

        self.tableau.configure(
            yscrollcommand=scrollbar_y.set,
        )

        self.tableau.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')

        frame_tableau.grid_rowconfigure(0, weight=1)
        frame_tableau.grid_columnconfigure(0, weight=1)

        self.tableau.bind('<Button-1>', self.cocher_case)

        for col in colonnes:
            self.tableau.heading(col, command=lambda c=col: self.trier_colonne(c))

    def remplir_tableau(self):

        for idx, ligne in enumerate(self.donnees):
            ligne_nettoyee = {k: v.strip() if isinstance(v, str) else v for k, v in ligne.items()}

            self.tableau.insert(
                '',
                'end',
                iid=idx,
                values=(
                    '☐',
                    ligne_nettoyee.get('Ligne', ''),
                    ligne_nettoyee.get('Voy.', ''),
                    ligne_nettoyee.get('Début', ''),
                    ligne_nettoyee.get('Fin', ''),
                    ligne_nettoyee.get('De', ''),
                    ligne_nettoyee.get('À', ''),
                    ligne_nettoyee.get('Js srv', '')
                )
            )

    def selection_voyages(self):
        return self.tableau.selection()

    def cocher_case(self, event):
        item = self.tableau.identify('item', event.x, event.y)
        column = self.tableau.identify_column(event.x)

        if column == '#1' and item:
            values = list(self.tableau.item(item, 'values'))
            values[0] = '☑' if values[0] == '☐' else '☐'
            self.tableau.item(item, values=values)

    def mettre_a_jour_selection(self):

        for item in self.tableau_selection.get_children():
            self.tableau_selection.delete(item)

        for item in self.tableau.get_children():
            values = self.tableau.item(item, 'values')
            if values[0] == '☑':  # Si la case est cochée
                self.tableau_selection.insert('', 'end', values=values[1:])


    def trier_colonne(self, col):

        items = [(self.tableau.item(item, 'values'), item) for item in self.tableau.get_children('')]

        colonnes = ('Sélection', 'Ligne', 'Voy.', 'Début', 'Fin', 'De', 'À', 'Js srv')
        col_index = colonnes.index(col)

        reverse = getattr(self, f'tri_reverse_{col}', False)
        try:
            items.sort(key=lambda x: float(x[0][col_index]) if x[0][col_index] else 0, reverse=reverse)
        except (ValueError, TypeError):
            items.sort(key=lambda x: str(x[0][col_index]).lower(), reverse=reverse)

        setattr(self, f'tri_reverse_{col}', not reverse)

        for index, (values, item) in enumerate(items):
            self.tableau.move(item, '', index)

    def creer_matrice_selection(self):
        self.donnees_selectionnees = []

        for item in self.tableau.get_children():
            values = self.tableau.item(item, 'values')
            if values[0] == '☑':
                idx = self.tableau.index(item)
                self.donnees_selectionnees.append(self.donnees[idx])

        if not self.donnees_selectionnees:
            msgbox.showwarning("Attention", "Aucun voyage sélectionné")
            return

        colonnes = ['Ligne', 'Voy.', 'Début', 'Fin', 'De', 'À', 'Js srv']
        matrice = []

        for voyage in self.donnees_selectionnees:
            ligne_matrice = []
            for col in colonnes:
                val = voyage.get(col,'').strip()
                try:
                    val = float(val)
                except (ValueError, AttributeError):
                    pass
                ligne_matrice.append(val)
            matrice.append(ligne_matrice)
        self.matrice_donnees = np.array(matrice, dtype=object)

        if self.master.callback:
            self.master.callback(self.donnees_selectionnees)

        msgbox.showinfo("Succès", f"{len(self.donnees_selectionnees)} voyage(s) chargé(s) dans la matrice")

class window_tableau_csv(ctk.CTk):
    def __init__(self, callback=None):
        super().__init__()

        self.title("Affichage CSV")
        self.geometry("1000x700")
        self.callback = callback

        self.tableau_widget = TableauCSV(self)
        self.tableau_widget.pack(fill="both", expand=True)

        self.mainloop()
