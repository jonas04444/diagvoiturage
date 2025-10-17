import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkTabview
from testiacontrainte import AdvancedODMSolver, time_to_minutes, minutes_to_time


class TimelineCanvas:
    """Classe pour gérer la timeline visuelle"""

    def __init__(self, canvas, trips_data):
        self.canvas = canvas
        self.trips = trips_data
        self.timeline_start = 4 * 60  # 4h en minutes
        self.timeline_end = 24 * 60  # 24h en minutes
        self.timeline_height = 600
        self.timeline_width = 1200
        self.service_height = 50
        self.padding_top = 50
        self.padding_left = 80
        self.padding_bottom = 50
        self.colors = self._generate_colors()

    def _generate_colors(self):
        """Génère des couleurs pour les différents voyages"""
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
            "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B88B", "#AED6F1"
        ]
        return colors

    def draw_solution(self, solution):
        """Dessine une solution complète sur la timeline"""
        self.canvas.delete("all")

        # Récupérer les dimensions réelles du canvas
        self.canvas.update()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            print(f"Canvas dimensions invalides: {canvas_width}x{canvas_height}")
            return

        print(f"Canvas dimensions: {canvas_width}x{canvas_height}")

        # Dessiner la timeline
        self._draw_timeline_background()
        self._draw_time_labels()

        current_y = self.padding_top

        # Afficher les services MATIN
        if solution['matin']:
            self.canvas.create_text(
                10, current_y, text="MATIN", font=("Arial", 10, "bold"),
                anchor="w", fill="white"
            )
            current_y += 20

            for service_id, trips in solution['matin'].items():
                self._draw_service_line(current_y, trips, f"M-{service_id}")
                current_y += self.service_height + 5

        # Afficher les services APRÈS-MIDI
        if solution['apres_midi']:
            self.canvas.create_text(
                10, current_y, text="APRÈS-MIDI", font=("Arial", 10, "bold"),
                anchor="w", fill="white"
            )
            current_y += 20

            for service_id, trips in solution['apres_midi'].items():
                self._draw_service_line(current_y, trips, f"A-{service_id}")
                current_y += self.service_height + 5

        # Afficher les orphelins
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
        self.canvas.create_rectangle(
            self.padding_left, self.padding_top,
            self.padding_left + self.timeline_width,
            self.padding_top + self.timeline_height,
            fill="#2b2b2b", outline="#555555"
        )

    def _draw_time_labels(self):
        """Affiche les labels horaires"""
        for hour in range(4, 25, 2):
            x = self._time_to_x(hour * 60)
            self.canvas.create_line(
                x, self.padding_top,
                x, self.padding_top + self.timeline_height,
                fill="#444444", dash=(2, 2)
            )
            self.canvas.create_text(
                x, self.padding_top - 20,
                text=f"{hour:02d}h",
                font=("Arial", 9),
                fill="white"
            )

    def _time_to_x(self, minutes):
        """Convertit une heure en coordonnée X"""
        ratio = (minutes - self.timeline_start) / (self.timeline_end - self.timeline_start)
        return self.padding_left + ratio * self.timeline_width

    def _draw_service_line(self, y, trips, service_label):
        """Dessine une ligne de service avec ses voyages"""
        # Label du service
        self.canvas.create_text(
            10, y + self.service_height // 2,
            text=service_label, font=("Arial", 9, "bold"),
            anchor="w", fill="white"
        )

        sorted_trips = sorted(trips, key=lambda x: x[1]["start"])

        for i, (trip_idx, trip) in enumerate(sorted_trips):
            color = self.colors[i % len(self.colors)]
            self._draw_trip_rect(
                y, trip_idx, trip, color, f"{trip['from'][:3]}-{trip['to'][:3]}"
            )

    def _draw_trip_rect(self, y, trip_idx, trip, color, label):
        """Dessine un rectangle représentant un voyage"""
        x1 = self._time_to_x(trip["start"])
        x2 = self._time_to_x(trip["end"])
        y1 = y
        y2 = y + self.service_height

        # Rectangle du voyage
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color, outline="white", width=2
        )

        # Texte avec heure et code
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        start_time = minutes_to_time(trip["start"])
        end_time = minutes_to_time(trip["end"])

        self.canvas.create_text(
            mid_x, mid_y - 8,
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


def main():
    win = ctk.CTk()
    win.title("menu")
    win.geometry("1400x900")

    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)

    tabview = CTkTabview(master=win, width=1350, height=850, corner_radius=15)
    tabview.grid(row=0, column=0, columnspan=3, padx=20, pady=20, sticky="nsew")

    tab1 = tabview.add("Création voyage")
    tab2 = tabview.add("création ligne")
    tab3 = tabview.add("Paramètres")
    tab4 = tabview.add("Solveur ODM")

    # === TAB 1: Création voyage ===
    tab1.grid_columnconfigure(0, weight=1)
    tab1.grid_columnconfigure(1, weight=1)
    tab1.grid_columnconfigure(2, weight=1)

    label = ctk.CTkLabel(master=tab1, text="création voyage")
    label.grid(row=0, column=1, pady=10, sticky="ew")

    saisie1 = ctk.CTkLabel(master=tab1, text="entrer ligne:")
    saisie1.grid(row=1, column=0, pady=10)
    ligne = ctk.CTkEntry(master=tab1)
    ligne.grid(row=1, column=1, pady=10)

    saisie2 = ctk.CTkLabel(master=tab1, text="entrer début:")
    saisie2.grid(row=2, column=0, pady=10)
    debutarret = ctk.CTkEntry(master=tab1)
    debutarret.grid(row=2, column=1, pady=10)

    saisie3 = ctk.CTkLabel(master=tab1, text="entrer fin:")
    saisie3.grid(row=3, column=0, pady=10)
    finarret = ctk.CTkEntry(master=tab1)
    finarret.grid(row=3, column=1, pady=10)

    button = ctk.CTkButton(master=tab1, text="valider")
    button.grid(row=5, column=1, pady=20)

    add_data = ctk.CTkButton(master=tab1, text="ajout de données")
    add_data.grid(row=6, column=1, pady=20)

    # === TAB 2: création ligne ===
    tab2.grid_columnconfigure(0, weight=1)
    tab2.grid_columnconfigure(1, weight=1)

    label2 = ctk.CTkLabel(master=tab2, text="Création de ligne")
    label2.grid(row=0, column=1, pady=10)

    saisieaddline = ctk.CTkLabel(master=tab2, text="entrer ligne:")
    saisieaddline.grid(row=1, column=0, pady=10)
    num_ligne = ctk.CTkEntry(master=tab2)
    num_ligne.grid(row=1, column=1, pady=10)

    # === TAB 4: Solveur ODM ===
    tab4.grid_columnconfigure(0, weight=0)
    tab4.grid_columnconfigure(1, weight=1)
    tab4.grid_rowconfigure(0, weight=0)
    tab4.grid_rowconfigure(1, weight=1)
    tab4.grid_rowconfigure(2, weight=0)

    label_solveur = ctk.CTkLabel(
        master=tab4,
        text="Configuration du Solveur ODM",
        font=("Arial", 14, "bold")
    )
    label_solveur.grid(row=0, column=0, pady=10)

    config_frame = ctk.CTkFrame(tab4)
    config_frame.grid(row=1, column=0, sticky="nw", padx=10, pady=10, rowspan=2)

    label_matin = ctk.CTkLabel(master=config_frame, text="Services MATIN:")
    label_matin.grid(row=0, column=0, pady=10, sticky="e", padx=10)
    entry_matin = ctk.CTkEntry(master=config_frame, width=100)
    entry_matin.insert(0, "2")
    entry_matin.grid(row=0, column=1, pady=10, sticky="w", padx=10)

    label_aprem = ctk.CTkLabel(master=config_frame, text="Services APRÈS-MIDI:")
    label_aprem.grid(row=1, column=0, pady=10, sticky="e", padx=10)
    entry_aprem = ctk.CTkEntry(master=config_frame, width=100)
    entry_aprem.insert(0, "1")
    entry_aprem.grid(row=1, column=1, pady=10, sticky="w", padx=10)

    # Variable globale pour stocker les solutions et trips
    solutions_data = {'solutions': [], 'trips': []}
    canvas_ref = {'canvas': None, 'timeline': None}

    def solve():
        try:
            nb_matin = int(entry_matin.get())
            nb_aprem = int(entry_aprem.get())

            # Données de test (à remplacer par tes données réelles)
            trips = [
                {"start": time_to_minutes("06:03"), "end": time_to_minutes("06:40"), "from": "FOMET", "to": "CEN05"},
                {"start": time_to_minutes("06:54"), "end": time_to_minutes("07:48"), "from": "CEN07", "to": "PTSNC"},
                {"start": time_to_minutes("08:58"), "end": time_to_minutes("10:13"), "from": "CPCEC", "to": "MYVES"},
                {"start": time_to_minutes("10:38"), "end": time_to_minutes("11:44"), "from": "MYVES", "to": "PTPLA"},
                {"start": time_to_minutes("12:09"), "end": time_to_minutes("13:13"), "from": "PTPLA", "to": "MYVES"},
                {"start": time_to_minutes("13:38"), "end": time_to_minutes("14:56"), "from": "MYVES", "to": "CPCEC"},
                {"start": time_to_minutes("06:40"), "end": time_to_minutes("07:36"), "from": "PTSNC", "to": "CEN05"},
                {"start": time_to_minutes("07:54"), "end": time_to_minutes("08:50"), "from": "CEN07", "to": "PTSNC"}
            ]

            solver = AdvancedODMSolver(trips)
            result = solver.solve_morning_afternoon(nb_matin, nb_aprem)

            solutions_data['solutions'] = result['solutions']
            solutions_data['trips'] = trips

            # Mettre à jour la timeline avec les bonnes données
            canvas_ref['timeline'] = TimelineCanvas(canvas, trips)

            # Afficher les solutions
            display_solutions(result['solutions'], trips)

            # Afficher la première solution automatiquement
            if result['solutions']:
                canvas_ref['timeline'].draw_solution(result['solutions'][0])

        except ValueError:
            error_label.configure(text="❌ Erreur: entrez des nombres valides")
        except Exception as e:
            error_label.configure(text=f"❌ Erreur: {str(e)}")

    button_solve = ctk.CTkButton(master=config_frame, text="Résoudre", command=solve, width=200, height=40)
    button_solve.grid(row=2, column=0, columnspan=2, pady=20)

    error_label = ctk.CTkLabel(master=config_frame, text="", text_color="red")
    error_label.grid(row=3, column=0, columnspan=2)

    # Frame pour les boutons de solutions
    solutions_frame = ctk.CTkFrame(tab4)
    solutions_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

    def display_solutions(solutions, trips):
        # Nettoyer les anciens boutons
        for widget in solutions_frame.winfo_children():
            widget.destroy()

        if not solutions:
            error_label.configure(text="❌ Aucune solution trouvée")
            return

        error_label.configure(text="")

        label_solutions = ctk.CTkLabel(
            master=solutions_frame,
            text=f"Solutions trouvées ({len(solutions)})",
            font=("Arial", 12, "bold")
        )
        label_solutions.pack(pady=10)

        for i, sol in enumerate(solutions):
            def show_sol(s=sol):
                if canvas_ref['canvas']:
                    canvas_ref['timeline'].draw_solution(s)

            btn = ctk.CTkButton(
                master=solutions_frame,
                text=f"Solution {i + 1}\nScore: {sol.get('score', 0)}",
                command=show_sol,
                width=120,
                height=60
            )
            btn.pack(side="left", padx=5)

    # Canvas pour la timeline
    canvas_frame = ctk.CTkFrame(tab4, fg_color="#1a1a1a")
    canvas_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
    tab4.grid_columnconfigure(1, weight=1)
    tab4.grid_rowconfigure(1, weight=1)

    canvas = tk.Canvas(canvas_frame, bg="#1a1a1a", highlightthickness=0, width=800, height=600)
    canvas.pack(fill="both", expand=True, side="left")
    canvas_ref['canvas'] = canvas

    scrollbar = ctk.CTkScrollbar(canvas_frame, command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Données de test (globales pour la timeline)
    test_trips = [
        {"start": time_to_minutes("06:03"), "end": time_to_minutes("06:40"), "from": "FOMET", "to": "CEN05"},
        {"start": time_to_minutes("06:54"), "end": time_to_minutes("07:48"), "from": "CEN07", "to": "PTSNC"},
        {"start": time_to_minutes("08:58"), "end": time_to_minutes("10:13"), "from": "CPCEC", "to": "MYVES"},
        {"start": time_to_minutes("10:38"), "end": time_to_minutes("11:44"), "from": "MYVES", "to": "PTPLA"},
        {"start": time_to_minutes("12:09"), "end": time_to_minutes("13:13"), "from": "PTPLA", "to": "MYVES"},
        {"start": time_to_minutes("13:38"), "end": time_to_minutes("14:56"), "from": "MYVES", "to": "CPCEC"},
        {"start": time_to_minutes("06:40"), "end": time_to_minutes("07:36"), "from": "PTSNC", "to": "CEN05"},
        {"start": time_to_minutes("07:54"), "end": time_to_minutes("08:50"), "from": "CEN07", "to": "PTSNC"}
    ]

    # Initialiser la timeline avec les données de test
    canvas_ref['timeline'] = TimelineCanvas(canvas, test_trips)

    win.mainloop()


if __name__ == "__main__":
    main()