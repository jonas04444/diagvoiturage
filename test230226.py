from objet import *

voyages_test = [
        voyage("25", "V1", "Station A", "Station B", "06:00", "07:00"),
        voyage("25", "V2", "Station B", "Station A", "07:10", "08:00"),
        voyage("35", "V3", "Station A", "Station C", "06:30", "07:30"),
        voyage("35", "V4", "Station C", "Station A", "08:15", "09:00"),
        voyage("25", "V5", "Station A", "Station B", "06:00", "07:00"),
        voyage("25", "V6", "Station B", "Station A", "07:10", "08:00"),
        voyage("35", "V7", "Station A", "Station C", "08:30", "09:30"),
        voyage("35", "V8", "Station C", "Station A", "10:15", "11:00"),
    ]


def chevauche_service(service, nouveau_voyage):
    for v in service.get_voyages():  # ← utilise le paramètre "service" et non servicetest
        if not (nouveau_voyage.hfin <= v.hdebut or nouveau_voyage.hdebut >= v.hfin):
            return True
    return False

def creer_service(num, voy):
    type_s = "matin" if voy.hdebut <= 600 else "après-midi"
    return service_agent(num_service=num, type_service=type_s)

services = [creer_service(1, voyages_test[0])]  # on crée le premier service

for i in range(len(voyages_test)):
    for j in range(i+1, len(voyages_test)):
        voy = voyages_test[i]
        voy2 = voyages_test[j]

        if (voy.hdebut <= voy2.hfin
                and voy.hfin <= voy2.hdebut
                and voy.arret_fin == voy2.arret_debut
                and voy.assigned == False
                and voy2.assigned == False):

            # Chercher un service existant sans chevauchement
            service_cible = None
            for s in services:
                if not chevauche_service(s, voy) and not chevauche_service(s, voy2):
                    service_cible = s
                    break

            # Aucun service compatible → en créer un nouveau
            if service_cible is None:
                service_cible = creer_service(len(services) + 1, voy)
                services.append(service_cible)

            service_cible.ajouter_voyage(voy)
            service_cible.ajouter_voyage(voy2)
            voy.assigned = True
            voy2.assigned = True
            break

for s in services:
    print(f"\n--- {s} ---")
    for v in s.get_voyages():
        print(v.arret_fin, v.num_voyage, v.num_ligne)