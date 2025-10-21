import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from customtkinter import CTkTabview

from gestion_contrainte import minutes_to_time


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
            messagebox.showerror("Erreur", f"Canvas dimensions invalides: {canvas_width}x{canvas_height}")
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