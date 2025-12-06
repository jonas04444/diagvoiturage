import customtkinter as ctk
import csv
from tkinter import ttk, messagebox as msgbox, filedialog
import tkinter as tk

class TableauCSV(ctk.CTkFrame):
    def __init__(self, parent, fichie_csv=None):
        super().__init__(parent)
        self.fichier_csv = fichie_csv
        self.donnees = []
        self.tableau = None

        if fichie_csv:
            self.charger_csv(fichie_csv)

        self.creer_boutons()
        self.creer_tableau()

    def charger_csv(self, chemin_fichier):
        try:
            #attention à l'encodage
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
            msgbox.showerror("Erreur",f"Erreur lors du chargement du CSV : {e}")
            self.donnees = []
    def selection_csv(self):
        fichier=filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes=[("Fichiers CSV","*.csv"), ("Tous les fichiers","*.*")]
        )

        if fichier:
            self.charger_csv(fichier)
            for item in self.tableau.get_children():
                self.tableau.delete(item)
            self.remplir_tableau()
            msgbox.showinfo("Succès",f"Fichier chargé: {fichier}")

    def creer_boutons(self):
        frame_boutons = ctk.CTkFrame(self)
        frame_boutons.pack(fill="x", padx=10, pady=10)

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
        #création tableau
        frame_tableau = ctk.CTkFrame(self)
        frame_tableau.pack(fill="both", expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.theme_use('clam')

        colonnes = ('Sélection', 'Ligne', 'Voy.', 'Début', 'Fin', 'De', 'À', 'Js srv')

        self.tableau = ttk.Treeview(
            frame_tableau,
            columns=colonnes,
            show='headings',
            height=15
        )

        en_tetes={
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

    def remplir_tableau(self):
        """Remplit le tableau avec les données"""
        for idx, ligne in enumerate(self.donnees):
            # Nettoyer les espaces inutiles des données
            ligne_nettoyee = {k: v.strip() if isinstance(v, str) else v for k, v in ligne.items()}

            self.tableau.insert(
                '',
                'end',
                iid=idx,
                values=(
                    '☐',  # Case à cocher (vide)
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


class window_tableau_csv(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Affichage CSV")
        self.geometry("1000x600")

        self.tableau_widget = TableauCSV(self)
        self.tableau_widget.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = window_tableau_csv()
    app.mainloop()