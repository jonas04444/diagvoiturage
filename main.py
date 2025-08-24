import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkTabview


def ajout_date():
    ajout_donnee = ctk.CTkToplevel()
    ajout_donnee.title("Ajout de données")
    ajout_donnee.geometry("400x450")

    ajout_donnee.columnconfigure(0, weight=1)
    ajout_donnee.columnconfigure(1, weight=1)
    ajout_donnee.columnconfigure(2, weight=1)

    labeldata = ctk.CTkLabel(ajout_donnee, text="ajout d'un ligne")
    labeldata.grid(row=0, column=1, pady=10)

    ajout_donnee.mainloop()



def main():
    win = ctk.CTk()
    win.title("menu")
    win.geometry("400x450")

    tabview = CTkTabview(master=win, width=650, height=400, corner_radius=15)
    tabview.pack(padx=20, pady=20, fill="both", expand=True)

    tab1 = tabview.add("Création voyage")
    tab2 = tabview.add("Autre")
    tab3 = tabview.add("Paramètres")

    win.grid_columnconfigure(0, weight=1)
    win.grid_columnconfigure(1, weight=1)
    win.grid_columnconfigure(2, weight=1)

    label = ctk.CTkLabel(master=tab1, text="création voyage")
    label.grid(row=0, column=1,pady=10)

    saisie1 = ctk.CTkLabel(master=tab1, text="entrer ligne:")
    saisie1.grid(row=1, column=0,pady=10)
    ligne = ctk.CTkEntry(master=tab1)
    ligne.grid(row=1, column=1,pady=10)

    saisie2 = ctk.CTkLabel(master=tab1, text="entrer début:")
    saisie2.grid(row=2, column=0,pady=10)
    debutarret = ctk.CTkEntry(master=tab1)
    debutarret.grid(row=2, column=1,pady=10)

    saisie3 = ctk.CTkLabel(master=tab1, text="entrer fin:")
    saisie3.grid(row=3, column=0,pady=10)
    finarret = ctk.CTkEntry(master=tab1)
    finarret.grid(row=3, column=1,pady=10)

    bar= ctk.CTkProgressBar(master=tab1, orientation="horizontal")
    bar.set(1)
    bar.grid(row=4,column=1, pady=10)

    button= ctk.CTkButton(master=tab1, text="valider")
    button.grid(row=5,column=1, pady=20)

    add_data = ctk.CTkButton(master=tab1, text="ajout de données")
    add_data.grid(row=6,column=1, pady=20)

    ctk.CTkLabel(master=tab2, text="Ici un autre onglet").pack(pady=20)

    win.mainloop()

main()