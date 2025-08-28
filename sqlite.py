import sqlite3

conn = sqlite3.connect("dbdiaggrantt.db")
cur = conn.cursor()
conn.close()

def add_line(donnees_ligne):
    conn = sqlite3.connect("dbdiaggrantt.db")
    cur =  conn.cursor()

    for version in donnees_ligne:
        cur.execute("""
            INSERT INTO Version_linge (
                id_version, num_ligne, Version_ligne
            ) VALUES (?, ?, ?)
        """, (
            version["id_version"],
            version["num_ligne"],
            version["Version_ligne"]
        ))

    conn.commit()
    conn.close()