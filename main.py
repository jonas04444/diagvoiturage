import csv
import tkinter as tk
from tkinter import messagebox as msgbox, ttk
import customtkinter as ctk
import self
from customtkinter import CTkTabview, filedialog
from gestion_contrainte import minutes_to_time, AdvancedODMSolver, time_to_minutes
from sqlite import add_line, get_lignes_from_db, add_lieux, get_lieux_from_db, add_trajet, charger_csv
from tabelauCSV import window_tableau_csv
class TimelineCanvas:

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

    def _generate_colors(self,i):
        """couleur pour les différents voyages"""
        colors = {
            "A1": "#FF6B6B",
            "25": "#4ECDC4",
            "35": "#45B7D1",
            "43": "#FFA07A",
            "83": "#98D8C8",
            "86": "#F7DC6F",
            "85": "#BB8FCE",
            "63": "#85C1E2",
            "41": "#F8B88B",
            "M4": "#AED6F1"

        }
        return colors

    def draw_solution(self, solution):
        """dessine un solution par timeline"""
        self.canvas.delete("all")

        self.canvas.update()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            msgbox.showerror("Erreur", f"Canvas dimensions invalides: {canvas_width}x{canvas_height}")
            return

        self._draw_timeline_background()
        self._draw_time_labels()

        current_y =  self.padding_top

        """affichage matin"""
        if solution['matin']:
            self.canvas.create_text(
                10, current_y, text="MATIN", font=("Arial", 10, "bold"),
                anchor="w", fill="white"
            )
            current_y += 20

            for service_id, trips in solution['matin'].items():
                self._draw_service_line(current_y, trips, f"AM-{service_id}")
                current_y += self.service_height + 5

        """affichage après-midi"""
        if solution['apres_midi']:
            self.canvas.create_text(
                10, current_y, text="APRES-MIDI", font=("Arial", 10, "bold"),
                anchor="w", fill="white"
            )
            current_y += 20

            for service_id, trips in solution['matin'].items():
                self._draw_service_line(current_y, trips, f"PM-{service_id}")
                current_y += self.service_height + 5

        """affiche les voyages orphelins"""
        if solution['orphelins']:
            current_y += 15
            self.canvas.create_text(
                10, current_y, text="⚠️ ORPHELINS", font=("Arial", 10, "bold"),
                anchor="w", fill="#FF6B6B"
            )
            current_y += 20

            for trip_idx in solution['orphelins']:
                trip = self.trips[trip_idx]
                self._draw_trip_rect(
                    current_y, trip_idx, trip,
                    "#FF6B6B", f"Orphelin-{trip_idx}"
                )
                current_y += 25

    def _draw_timeline_background(self):
        """Dessine le fond de la timeline"""
        """faut ajouter les paramètre de couleur"""
        self.canvas.create_rectangle(
            self.padding_left, self.padding_top,
            self.padding_left + self.timeline_width,
            self.padding_top + self.timeline_height,
            fill="#2b2b2b", outline="#555555"
        )

    def _draw_time_labels(self):
        """affiche les lobels horaires"""
        for hour in range (4, 25, 2):
            x = self._time_to_x(hour * 60)
            self.canvas.create_line(
                x , self.padding_top,
                x , self.padding_top + self.timeline_height,
                fill="#444444", dash=(2,2)
            )
            self.canvas.create_text(
                x, self.padding_top - 20,
                text=f"{hour:02d}h",
                font=("Arial", 9),
                fill="white"
            )

    def _draw_trip_rect(self, y, trip_idx, trip, color, label):
        """dessine les rectangles pour les voyages"""
        x1 = self._time_to_x(trip["start"])
        x2 = self._time_to_x(trip["end"])
        y1 = y
        y2 = y + self.service_height

        """rectangel du voyage"""
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color, outline="white", width = 2
        )

        """texte avec heure et code"""
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        start_time = minutes_to_time(trip["start"])
        end_time = minutes_to_time(trip["end"])

        self.canvas.create_text(
            mid_x , mid_y - 8,
            text=label,
            font=("Arial", 8, "bold"),
            fill="black"
        )
        self.canvas.create_text(
            mid_x, mid_y + 8,
            text=f"{start_time}-{end_time}",
            font=("Arial", 7),
            fill="black"
        )

    def _time_to_x(self, minutes):
        """Convertit une heure en coordonnée X"""
        ratio = (minutes - self.timeline_start) / (self.timeline_end - self.timeline_start)
        return self.padding_left + ratio * self.timeline_width

    def _draw_service_line(self,y , trips, service_labe):
        """dessine une ligne de service avec les voyages"""
        self.canvas.create_text(
            10, y + self.service_height // 2,
            text=service_labe, font=("Arial", 9, "bold"),
            anchor="w", fill="white"
        )

        sorted_trips = sorted(trips, key=lambda x: x[1]["start"])

        for i, (trip_idx, trip) in enumerate(sorted_trips):
            line_name = trip.get("line", "default")
            color = self.colors.get(line_name, "#CCCCCC")
            self._draw_trip_rect(
                y, trip_idx, trip, color, f"{trip['from'][:3]}-{trip['to'][:3]}"
            )

def main():
    win = ctk.CTk()
    win.title("menu")
    win.geometry("1400x900")

    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)

    tabview = CTkTabview(master=win, width=1350, height=850, corner_radius=15)
    tabview.grid(row=0, column=0, columnspan=3, padx=20, pady=20, sticky="nsew")


    tab1 = tabview.add("Création voyage")
    tab2 = tabview.add("création ligne et lieux")
    tab3 = tabview.add("liste voyage")
    tab4 = tabview.add("voiturage")

    """TAB 1"""
    tab1.grid_columnconfigure(0, weight=1)
    tab1.grid_columnconfigure(1, weight=1)
    tab1.grid_columnconfigure(2, weight=1)

    label = ctk.CTkLabel(master=tab1, text="création voyage")
    label.grid(row=0, column=1,pady=10, sticky="ew")

    saisie1 = ctk.CTkLabel(master=tab1, text="sélectionner ligne:")
    saisie1.grid(row=1, column=0,pady=10)
    ligne_dropdown = ctk.CTkComboBox(
        master=tab1,
        values=get_lignes_from_db(),
        width=200
    )
    ligne_dropdown.grid(row=1, column=1, pady=10)

    saisienumvoyage = ctk.CTkLabel(master=tab1, text="entrez numéro de voyage")
    saisienumvoyage.grid(row=2, column=0, pady=10)
    numvoyage= ctk.CTkEntry(master=tab1)
    numvoyage.grid(row=2, column=1,pady=10)

    saisie2 = ctk.CTkLabel(master=tab1, text="entrer début:")
    saisie2.grid(row=3, column=0,pady=10)
    debutarret = ctk.CTkEntry(master=tab1)
    debutarret.grid(row=3, column=1,pady=10)

    saisie3 = ctk.CTkLabel(master=tab1, text="entrer fin:")
    saisie3.grid(row=4, column=0,pady=10)
    finarret = ctk.CTkEntry(master=tab1)
    finarret.grid(row=4, column=1,pady=10)

    saisie4 = ctk.CTkLabel(master=tab1, text="entrer lieux de début:")
    saisie4.grid(row=5, column=0, pady=10)
    lieux1_dropdown = ctk.CTkComboBox(
        master=tab1,
        values=get_lieux_from_db(),
        width=200
    )
    lieux1_dropdown.grid(row=5, column=1, pady=10)

    saisie5 = ctk.CTkLabel(master=tab1, text="entrer lieux de fin:")
    saisie5.grid(row=6, column=0, pady=10)
    lieux2_dropdown = ctk.CTkComboBox(
        master=tab1,
        values=get_lieux_from_db(),
        width=200
    )
    lieux2_dropdown.grid(row=6, column=1, pady=10)

    button = ctk.CTkButton(master=tab1,
                           text="ajouter un trajet",
                           command=lambda: add_trajet([{
                               "Num_ligne": int(ligne_dropdown.get().split()[1]),
                               "variant": int(ligne_dropdown.get().split()[-1]),
                               "Num_trajet": int(numvoyage.get()),
                               "DP_arret": lieux1_dropdown.get().strip(),
                               "DR_arret": lieux2_dropdown.get().strip(),
                               "Heure_Start": debutarret.get().strip(),
                               "Heure_End": finarret.get().strip()
                           }]))
    button.grid(row=7, column=1, pady=10)

    button_csv = ctk.CTkButton(
        master=tab1,
        text="Charger CSV",
        command=lambda: charger_csv(),
        width=200
    )
    button_csv.grid(row=8, column=1, pady=10)

    """TAB 2: création des lignes et lieu"""
    tab2.grid_columnconfigure(0, weight=1)
    tab2.grid_columnconfigure(1, weight=1)

    label2 = ctk.CTkLabel(master=tab2, text="Création de ligne et lieu")
    label2.grid(row=0, column=1, pady=10)

    saisieaddline = ctk.CTkLabel(master=tab2, text="entrer ligne:")
    saisieaddline.grid(row=1, column=0, pady=10)
    num_ligne = ctk.CTkEntry(master=tab2)
    num_ligne.grid(row=1, column=1, pady=10)

    saisieaddlinevar = ctk.CTkLabel(master=tab2, text="entrer variant:")
    saisieaddlinevar.grid(row=2, column=0, pady=10)
    num_lignevar = ctk.CTkEntry(master=tab2)
    num_lignevar.grid(row=2, column=1, pady=10)

    button = ctk.CTkButton(master=tab2,
                           text="valider",
                           command=lambda: add_line([{"num_ligne": int(num_ligne.get()), "Variante": int(num_lignevar.get())}]))
    button.grid(row=5, column=1, pady=20)

    saisielieu = ctk.CTkLabel(master=tab2, text="entrer lieu:")
    saisielieu.grid(row=6, column=0, pady=10)
    addidlieu = ctk.CTkEntry(master=tab2)
    addidlieu.grid(row=6, column=1, pady=10)

    saisiecommune = ctk.CTkLabel(master=tab2, text="entrer commune:")
    saisiecommune.grid(row=7, column=0, pady=10)
    addcommune = ctk.CTkEntry(master=tab2)
    addcommune.grid(row=7, column=1, pady=10)

    saisiedescription = ctk.CTkLabel(master=tab2, text="entrer description:")
    saisiedescription.grid(row=8, column=0, pady=10)
    adddescription = ctk.CTkEntry(master=tab2)
    adddescription.grid(row=8, column=1, pady=10)

    saisiezone = ctk.CTkLabel(master=tab2, text="entrer zone:")
    saisiezone.grid(row=9, column=0, pady=10)
    addzone = ctk.CTkEntry(master=tab2)
    addzone.grid(row=9, column=1, pady=10)

    buttonlieu = ctk.CTkButton(master=tab2,
                               text="ajouter lieu",
                               command=lambda: add_lieux([{"id_lieux": addidlieu.get().strip(),
                                                           "commune": addcommune.get().strip(),
                                                           "description": adddescription.get().strip(),
                                                           "zone": int(addzone.get())}])
                               )
    buttonlieu.grid(row=10, column=1, pady=10)

    """TAB 3: liste de selction des voyages"""
    tab3.grid_columnconfigure(0, weight=0)
    tab3.grid_columnconfigure(1, weight=1)
    tab3.grid_rowconfigure(0, weight=0)
    tab3.grid_rowconfigure(1, weight=1)
    tab3.grid_rowconfigure(2, weight=0)

    choixligne = ctk.CTkLabel(master=tab3, text="sélection ligne:")
    choixligne.grid(row=0, column=0, pady=10)
    ligneselect = ctk.CTkComboBox(
        master=tab3,
        values=get_lignes_from_db(),
        width=200
    )
    ligneselect.grid(row=0, column=1, pady=10)

    """TAB 4: solveur ODM"""
    tab4.grid_columnconfigure(0, weight=0)
    tab4.grid_columnconfigure(1, weight=1)
    tab4.grid_rowconfigure(0, weight=0)
    tab4.grid_rowconfigure(1, weight=1)
    tab4.grid_rowconfigure(2, weight=0)

    label_solver = ctk.CTkLabel(

        master=tab4,
        text="Configuration du solveur ODM",
        font=("Arial", 14, "bold")
    )
    label_solver.grid(row=0, column=0, pady=10)

    config_frame = ctk.CTkFrame(tab4)
    config_frame.grid(row=1, column=0, sticky="nw", padx=10, pady=10, rowspan=2)

    label_matin = ctk.CTkLabel(master=config_frame, text="Services MATIN:")
    label_matin.grid(row=0, column=0, pady=10, sticky="e", padx=10)
    entry_matin = ctk.CTkEntry(master=config_frame, width=100)
    entry_matin.insert(0, " ")
    entry_matin.grid(row=0, column=1, pady=10, sticky="w", padx=10)

    label_aprem = ctk.CTkLabel(master=config_frame, text="Services APRÈS-MIDI:")
    label_aprem.grid(row=1, column=0, pady=10, sticky="e", padx=10)
    entry_aprem = ctk.CTkEntry(master=config_frame, width=100)
    entry_aprem.insert(0, " ")
    entry_aprem.grid(row=1, column=1, pady=10, sticky="w", padx=10)

    solutions_data = {'solutions': [], 'trips': []}
    canvas_ref = {'canvas': None, 'timeline': None}

    def afficher_matrice(matrice_donnees):
        """Affiche la matrice dans un tableau"""

        # Créer une nouvelle fenêtre
        fenetre_matrice = ctk.CTkToplevel()
        fenetre_matrice.title("Matrice des voyages")
        fenetre_matrice.geometry("800x500")

        # Créer un frame pour le tableau
        frame_tableau = ctk.CTkFrame(fenetre_matrice)
        frame_tableau.pack(fill="both", expand=True, padx=10, pady=10)

        # Créer le Treeview
        colonnes = ('Ligne', 'Voy.', 'Début', 'Fin', 'De', 'À', 'Js srv')
        tableau = ctk.Treeview(
            frame_tableau,
            columns=colonnes,
            show='headings',
            height=15
        )

        # Configurer les en-têtes et largeurs
        en_tetes = {
            'Ligne': 80,
            'Voy.': 80,
            'Début': 80,
            'Fin': 80,
            'De': 120,
            'À': 120,
            'Js srv': 100
        }

        for col, largeur in en_tetes.items():
            tableau.column(col, width=largeur, anchor='center')
            tableau.heading(col, text=col)

        # Remplir le tableau avec les données de la matrice
        for idx, ligne in enumerate(matrice_donnees):
            tableau.insert('', 'end', values=tuple(ligne))

        # Ajouter une scrollbar
        scrollbar_y =  ctk.Scrollbar(
            frame_tableau,
            orient='vertical',
            command=tableau.yview
        )

        tableau.configure(yscrollcommand=scrollbar_y.set)

        tableau.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')

        frame_tableau.grid_rowconfigure(0, weight=1)
        frame_tableau.grid_columnconfigure(0, weight=1)

    def solve():
        try:
            nb_matin = int(entry_matin.get())
            nb_aprem = int(entry_aprem.get())

            def traiter_voyages(voyages_data, matrice_donnees):
                trips = []
                for voyage in voyages_data:
                    trip = {
                        "ligne": voyage.get('Ligne', ''),
                        "voy": voyage.get('Voy.', ''),
                        "start": time_to_minutes(voyage.get('Début', '00:00')),
                        "end": time_to_minutes(voyage.get('Fin', '00:00')),
                        "from": voyage.get('De', ''),
                        "to": voyage.get('À', ''),
                        "js_srv": voyage.get('Js srv', '')
                    }
                    trips.append(trip)

                solver = AdvancedODMSolver(trips)
                result = solver.solve_morning_afternoon(nb_matin, nb_aprem)

                solutions_data['solutions'] = result['solutions']
                solutions_data['trips'] = trips

                canvas_ref['timeline'] = TimelineCanvas(trips)

                display_solution(result['solutions'], trips)

                remplir_tableau_matrice(solutions_data['tableau'], matrice_donnees)

            window_tableau_csv(callback=traiter_voyages)

        except ValueError:
            error_label.configure(text="Erreur: entrez des nombres valides")  # ✅ Corrigé

        except Exception as e:
            error_label.configure(text=f"Erreur: {str(e)}")  # ✅ Espace supprimé


    button_solve = ctk.CTkButton(master=config_frame, text="Résoudre", command=solve, width=200, height=40)
    button_solve.grid(row=2, column=0, columnspan=2, pady=20)

    button_charge_csv = ctk.CTkButton(master=config_frame, text="Charger voyage CSV", command=window_tableau_csv, width=200, height=40)
    button_charge_csv.grid(row=3, column=0, columnspan=2, pady=20)

    error_label = ctk.CTkLabel(master=config_frame, text="", text_color="red")
    error_label.grid(row=3, column=0, columnspan=2)

    solutions_frame = ctk.CTkFrame(tab4)
    solutions_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

    style = ttk.Style()
    style.theme_use('clam')

    colonnes = ('Ligne', 'Voy.', 'Début', 'Fin', 'De', 'À', 'Js srv')

    self.tableau = ttk.Treeview(
        solutions_frame,
        columns=colonnes,
        show='headings',
        height=15
    )

    en_tetes= {
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

    scrollbar_y = ttk.Scrollbar(
        solutions_frame,
        orient="vertical",
        command=self.tableau.yview
    )

    self.tableau.configure(
        yscrollcommand=scrollbar_y.set
    )

    self.tableau.grid(row=0, column=0, sticky='nsew')
    scrollbar_y.grid(row=0, column=1, sticky='ns')

    solutions_frame.grid_rowconfigure(0, weight=1)
    solutions_frame.grid_columnconfigure(0, weight=1)

    def remplir_tableau_matrice(tableau, matrice_donnees):
        """Remplit le tableau avec les données de la matrice"""
        # Supprimer les anciennes données
        for item in tableau.get_children():
            tableau.delete(item)

        # Remplir avec les nouvelles données
        if matrice_donnees is not None:
            for idx, ligne in enumerate(matrice_donnees):
                tableau.insert('', 'end', values=tuple(ligne))

    def display_solution(solutions, trips):
        for widget in solutions_frame.winfo_children():
            widget.destroy()

        if not solutions:
            error_label.configure(text="Aucune solution trouvée")
            return

        error_label.configure(text="")

        label_solutions = ctk.CTkLabel(
            master=solutions_frame,
            text=f"Solutions trouvées ({len(solutions)}",
            font=("Arial", 12, "bold")
        )
        label_solutions.pack(pady=10)

    win.mainloop()

main()

