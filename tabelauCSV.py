import customtkinter as ctk
import csv
from tkinter import ttk, messagebox as msgbox, filedialog


class TableauCSV(ctk.CTkFrame):
    def __init__(self, parent, fichie_csv=None):
        super().__init__(parent)
        self.fichier_csv = fichie_csv
        self.donnees = []
        self.tableau = None
        self.tableau_selection = None

        # Configure le grid pour le frame principal
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        if fichie_csv:
            self.charger_csv(fichie_csv)

        self.creer_boutons()
        self.creer_tableau()
        self.creer_tableau_selection()

    def creer_tableau_selection(self):
        frame_selection = ctk.CTkFrame(self)
        frame_selection.grid(row=2, column=0, sticky='nsew', padx=10, pady=10)

        label = ctk.CTkLabel(frame_selection, text="Voyages sélectionnés", font=("Arial", 14, "bold"))
        label.grid(row=0, column=0, columnspan=2, pady=5)

        colonnes = ('Ligne', 'Voy.', 'Début', 'Fin', 'De', 'À', 'Js srv')

        self.tableau_selection = ttk.Treeview(
            frame_selection,
            columns=colonnes,
            show='headings',
            height=10
        )

        en_tetes = {
            'Ligne': 50,
            'Voy.': 50,
            'Début': 80,
            'Fin': 80,
            'De': 120,
            'À': 120,
            'Js srv': 100
        }

        for col, largeur in en_tetes.items():
            self.tableau_selection.column(col, width=largeur, anchor='center')
            self.tableau_selection.heading(col, text=col)

        scrollbar_y = ttk.Scrollbar(
            frame_selection,
            orient='vertical',
            command=self.tableau_selection.yview
        )

        self.tableau_selection.configure(yscrollcommand=scrollbar_y.set)
        self.tableau_selection.grid(row=1, column=0, sticky='nsew')
        scrollbar_y.grid(row=1, column=1, sticky='ns')

        frame_selection.grid_rowconfigure(1, weight=1)
        frame_selection.grid_columnconfigure(0, weight=1)

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
            text="Charger dans la db",
            width=100,
            command=lambda: msgbox.showinfo("fichier chargé dans la db")
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
            exit()

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

    def remplir_tableau(self):
        """Remplit le tableau avec les données"""
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

            # Mettre à jour le tableau de sélection
            self.mettre_a_jour_selection()

    def mettre_a_jour_selection(self):
        """Met à jour le tableau des voyages sélectionnés"""
        # Vider le tableau de sélection
        for item in self.tableau_selection.get_children():
            self.tableau_selection.delete(item)

        # Parcourir le tableau principal et récupérer les cases cochées
        for item in self.tableau.get_children():
            values = self.tableau.item(item, 'values')
            if values[0] == '☑':  # Si la case est cochée
                # Ajouter au tableau de sélection (sans la colonne "Sélection")
                self.tableau_selection.insert('', 'end', values=values[1:])


class window_tableau_csv(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Affichage CSV")
        self.geometry("1000x700")

        self.tableau_widget = TableauCSV(self)
        self.tableau_widget.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = window_tableau_csv()
    app.mainloop()