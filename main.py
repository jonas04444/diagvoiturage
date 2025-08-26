import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkTabview

def main():
    win = ctk.CTk()
    win.title("menu")
    win.geometry("1000x800")

    tabview = CTkTabview(master=win, width=950, height=750, corner_radius=15)
    tabview.grid(row=0, column=0, columnspan=3, padx=20, pady=20, sticky="nsew")


    tab1 = tabview.add("Création voyage")
    tab2 = tabview.add("création ligne")
    tab3 = tabview.add("Paramètres")

    tab1.grid_columnconfigure(0, weight=1)
    tab1.grid_columnconfigure(1, weight=1)
    tab1.grid_columnconfigure(2, weight=1)

    label = ctk.CTkLabel(master=tab1, text="création voyage")
    label.grid(row=0, column=1,pady=10, sticky="ew")

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

    button= ctk.CTkButton(master=tab1, text="valider")
    button.grid(row=5,column=1, pady=20)

    add_data = ctk.CTkButton(master=tab1, text="ajout de données")
    add_data.grid(row=6,column=1, pady=20)

    label2 = ctk.CTkLabel(master=tab2, text="Création de ligne")
    label2.grid(row=0, column=1, pady=10)

    saisieaddline = ctk.CTkLabel(master=tab2, text="entrer ligne:")
    saisieaddline.grid(row=1, column=0, pady=10)
    num_ligne = ctk.CTkEntry(master=tab2)
    num_ligne.grid(row=1, column=1, pady=10)

    win.mainloop()

main()