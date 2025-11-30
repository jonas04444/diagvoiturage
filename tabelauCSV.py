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