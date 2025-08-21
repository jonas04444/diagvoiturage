import tkinter as tk
import customtkinter as ctk

win = ctk.CTk()
win.title("mon appli")
win.geometry("400x450")

win.grid_columnconfigure(0, weight=1)
win.grid_columnconfigure(1, weight=1)
win.grid_columnconfigure(2, weight=1)

label = ctk.CTkLabel(win, text="test")
label.grid(row=0, column=1,pady=10)

saisie1 = ctk.CTkLabel(win, text="entrer ligne:")
saisie1.grid(row=1, column=0,pady=10)
saisie = ctk.CTkEntry(win)
saisie.grid(row=1, column=1,pady=10)

saisie2 = ctk.CTkLabel(win, text="entrer début:")
saisie2.grid(row=2, column=0,pady=10)
saisie = ctk.CTkEntry(win)
saisie.grid(row=2, column=1,pady=10)

saisie3 = ctk.CTkLabel(win, text="entrer fin:")
saisie3.grid(row=3, column=0,pady=10)
saisie = ctk.CTkEntry(win)
saisie.grid(row=3, column=1,pady=10)

bar= ctk.CTkProgressBar(win, orientation="horizontal")
bar.set(1)
bar.grid(row=4,column=1, pady=10)

button= ctk.CTkButton(win, text="valider")
button.grid(row=5,column=1, pady=20)



win.mainloop()