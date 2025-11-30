import customtkinter as ctk
import csv
from tkinter import ttk, messagebox as msgbox
import tkinter as tk

class TableauCSV(ctk.CTkFrame)
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
