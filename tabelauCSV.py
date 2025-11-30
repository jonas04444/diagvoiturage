import customtkinter as ctk
import csv
from tkinter import ttk, messagebox as msgbox
import tkinter as tk

class TableauCSV(ctk.CTkFrame):
    def __init__(self, parent, fichie_csv=None):
        super().__init__(parent)
        self.fichier_csv = fichie_csv
        self.donnee = []

        if fichie_csv:
            self.charger_csv(fichie_csv)

        self.creer_boutons()
        self.creer_tableau()

    def charger_csv(self, chemin_fichier):
        try:
            #attention à l'encodage
            with open(chemin_fichier, 'r', encoding='utf-8') as file:
                lecture = csv.DictReader(file)
                self.donnee = list(lecture)

        except Exception as e:
            msgbox.showerror("Erreur",f"Erreur lors du chargement du CSV : {e}")
            self.donnee = []

    def creer_boutons(self):
        frame_boutons = ctk.CTkFrame(self)
        frame_boutons.pack(fill="x", padx=10, pady=10)

        download_csv = ctk.CTkButton(
            frame_boutons,
            text="Sélectionner un fichier CSV",
            width=100,
            command=lambda : msgbox.showinfo("csv chargé")
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
            command=lambda: msgbox.showinfo("exit")
        )
        exit_csv_window.pack(side="left", padx=5)

    def creer_tableau(self):
        #création tableau
        frame_tableau = ctk.CTkFrame(self)
        frame_tableau.pack(fill="both", expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.theme_use('dark')

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

        scrollbar_x = ttk.Scrollbar(
            frame_tableau,
            orient='horizontal',
        command = self.tableau.yview
        )

        self.tableau.configure(
            yscroll=scrollbar_y.set,
            xscroll=scrollbar_x.set
        )

        self.tableau.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')

        frame_tableau.grid_rowconfigure(0, weight=1)
        frame_tableau.grid_columnconfigure(0, weight=1)

