import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkTabview

class Timelinegraphique:

    def __init__(self, canvas, trips_data, line):
        self.canvas = canvas
        self.trips = trips_data
        self.timeline_start = 4*60
        self.timeline_end = 24*60
        self.timeline_height = 600
        self.timeline_width = 1200
        self.service_height = 50
        self.padding_top = 50
        self.padding_left = 80
        self.padding_bottom = 50
        self.colors = self._generate_colors()

    def _generate_colors(self):

        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
            "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B88B", "#AED6F1"
        ]
        return colors

def main():
    win = ctk.CTk()
    win.title("menu")
    win.geometry("1000x800")

    tabview = CTkTabview(master=win, width=950, height=750, corner_radius=15)
    tabview.grid(row=0, column=0, columnspan=3, padx=20, pady=20, sticky="nsew")


    tab1 = tabview.add("Création voyage")
    tab2 = tabview.add("création ligne")
    tab3 = tabview.add("Paramètres")
    tab4 = tabview.add("voiturage")

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

    canvas_frame = ctk.CTkFrame(tab4, fg_color="white")
    canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

    win.canva= ctk.CTkCanvas(canvas_frame, bg="white", highlightthickness=0)
    win.canva.pack(side="left", expand=True, padx=10, pady=10)

    scrollbar = ctk.CTkScrollbar(canvas_frame, command=win.canva.yview)
    scrollbar.pack(side="right", fill="y")
    win.canva.configure(yscrollcommand=scrollbar.set)

    win.mainloop()

main()