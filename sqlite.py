import sqlite3
import tkinter.messagebox as msgbox

conn = sqlite3.connect("dbdiaggrantt.db")
cur = conn.cursor()
conn.close()

def add_line(donnees_ligne):
    conn = sqlite3.connect("dbdiaggrantt.db")
    cur =  conn.cursor()

    for version in donnees_ligne:
        cur.execute("""
                    SELECT 1 FROM Version_linge
                    WHERE num_ligne = ? AND Version_ligne = ?
                """, (version["num_ligne"], version["Version_ligne"]))

        existe = cur.fetchone()

        if existe:
            msgbox.showwarning(
                "Doublon détecté",
                f"La ligne {version['num_ligne']} avec la version {version['Version_ligne']} existe déjà."
            )
        else:
            cur.execute("""
                    INSERT INTO Version_linge (
                        num_ligne, Version_ligne
                    ) VALUES (?, ?)
                """, (
                    version["num_ligne"],
                    version["Version_ligne"]
                ))

    conn.commit()
    conn.close()

def add_trajet(donnees_trajet):
    conn = sqlite3.connect("dbdiaggrantt.db")
    cur = conn.cursor()

    for trajet in donnees_trajet:
        cur.execute("""
                    SELECT 1 FROM 
            
            """)