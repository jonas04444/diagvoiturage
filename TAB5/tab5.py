import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, Canvas, filedialog
from objet import voyage, service_agent
from tabelauCSV import window_tableau_csv

class Interface(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        self.creer_interface()

    def creer_interface(self):

        panel_gauche = ctk.CTkFrame(self, width=500)
        panel_gauche.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        panel_gauche.grid_propagate(False)

        label_titre_gauche = ctk.CTkLabel(
            panel_gauche, text="Voyages Disponibles",
            font=("Arial", 18, "bold")
        )
        label_titre_gauche.pack(pady=10)

        btn_charger = ctk.CTkButton(
            panel_gauche, text="Charger voyages CSV",
            command=window_tableau_csv, height=50
        )
        btn_charger.pack(pady=10, padx=10, fill="x")

        frame_liste_voyages = ctk.CTkFrame(panel_gauche)
        frame_liste_voyages.pack(fill="both", expand=True, padx=10, pady=10)

        colonnes = ('✓', 'Voy.', 'Ligne', 'Début', 'Fin', 'De→À')
        self.tree_voyages = ttk.Treeview(
            frame_liste_voyages, columns=colonnes,
            show="headings", height=25, selectmode="extended"
        )

        largeurs = {'✓': 35, 'Voy.': 60, 'Ligne': 70, 'Début': 70, 'Fin': 70, 'De→À': 120}
        for col, largeur in largeurs.items():
            self.tree_voyages.column(col, width=largeur, anchor="center")
            self.tree_voyages.heading(col, text=col)

        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree_voyages.tag_configure('disabled', foreground="#666666", background="#3a3a3a")

        scrollbar = ttk.Scrollbar(
            frame_liste_voyages, orient="vertical",
            command=self.tree_voyages.yview
        )
        self.tree_voyages.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree_voyages.bind('<Button-1>', self.toggle_voyage_selection)

        self.label_selection = ctk.CTkLabel(
            panel_gauche, text=" 0 voyages sélectionés",
            font=("Arial", 11, "bold")
        )

        self.label_selection.pack(pady=5)

    def toggle_voyage_selection(self, event):
        pass

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Test Interface - Tab 5")
    app.geometry("1920x1080")

    interface = Interface(app)
    interface.pack(fill="both", expand=True)


    app.mainloop()