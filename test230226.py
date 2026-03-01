from objet import *

voyages_test = [
        voyage("25", "V1", "Station A", "Station B", "06:00", "07:00"),
        voyage("25", "V2", "Station B", "Station A", "07:10", "08:00"),
        voyage("35", "V3", "Station A", "Station C", "06:30", "07:30"),
        voyage("35", "V4", "Station C", "Station A", "08:15", "09:00"),
        voyage("45", "V5", "Station A", "Station B", "06:00", "07:00"),
        voyage("45", "V6", "Station B", "Station A", "07:10", "08:00"),
        voyage("55", "V7", "Station A", "Station C", "08:30", "09:30"),
        voyage("55", "V8", "Station C", "Station A", "10:15", "11:00"),
        voyage("65", "V5", "Station A", "Station B", "06:00", "07:00"),
        voyage("65", "V6", "Station B", "Station A", "07:10", "08:00"),
        voyage("75", "V7", "Station A", "Station C", "08:30", "09:30"),
        voyage("75", "V8", "Station C", "Station A", "10:15", "11:00"),
    ]

min_pause = 15
max_pause = 60
nb_max_lignes = 1
max_services = 5

def voyage_compatible(service, nouveau_voyage, min_pause, max_pause):
    for v in service.get_voyages():
        if not (nouveau_voyage.hfin <= v.hdebut or nouveau_voyage.hdebut >= v.hfin):
            return False

        if nouveau_voyage.hdebut >= v.hfin:
            pause = nouveau_voyage.hdebut - v.hfin
            if not (min_pause <= pause <= max_pause):
                return False

        if v.hdebut >= nouveau_voyage.hfin:
            pause = v.hdebut - nouveau_voyage.hfin
            if not (min_pause <= pause <= max_pause):
                return False
    return True

def creer_service(num, voy):
    type_s = "matin" if voy.hdebut <= 600 else "après-midi"
    return service_agent(num_service=num, type_service=type_s)

def verifier_nb_lignes(service, nb_max_lignes):
    lignes = set(v.num_ligne for v in service.get_voyages())
    if len(lignes) > nb_max_lignes:
        return False, f"Trop de lignes différentes : {len(lignes)} lignes ({', '.join(lignes)}) pour un max de {nb_max_lignes}"
    return True, f"OK : {len(lignes)} ligne(s) différente(s) ({', '.join(lignes)})"

def peut_ajouter_lignes(service, voy, voy2, nb_max_lignes):
    lignes_actuelles = set(v.num_ligne for v in service.get_voyages())
    lignes_actuelles.add(voy.num_ligne)
    lignes_actuelles.add(voy2.num_ligne)
    return len(lignes_actuelles) <= nb_max_lignes

service_cible = creer_service(1, voyages_test[0])
propo = proposition(num_proposition=1)
propo.ajout_service(service_cible)

for i in range(len(voyages_test)):
    for j in range(i+1, len(voyages_test)):
        voy = voyages_test[i]
        voy2 = voyages_test[j]

        pause_entre = voy2.hdebut - voy.hfin

        if (voy.hdebut <= voy2.hfin
                and voy.hfin <= voy2.hdebut
                and voy.arret_fin == voy2.arret_debut
                and voy.assigned == False
                and voy2.assigned == False
                and min_pause <= pause_entre <= max_pause):

            service_cible = None
            for s in propo.service:
                if (voyage_compatible(s, voy, min_pause, max_pause)
                        and voyage_compatible(s, voy2, min_pause, max_pause)
                        and peut_ajouter_lignes(s, voy, voy2, nb_max_lignes)):
                    service_cible = s
                    break

            if service_cible is None:
                if len(propo.service) >= max_services:
                    print(f"⚠ Max services ({max_services}) atteint, impossible d'assigner {voy.num_voyage} et {voy2.num_voyage}")
                    break
                service_cible = creer_service(len(propo.service) + 1, voy)
                propo.ajout_service(service_cible)


            service_cible.ajouter_voyage(voy)
            service_cible.ajouter_voyage(voy2)
            voy.assigned = True
            voy2.assigned = True
            break

for voy in voyages_test:
    if not voy.assigned:
        service_cible = None
        for s in propo.service:
            if (voyage_compatible(s, voy, min_pause, max_pause)
                    and peut_ajouter_lignes(s, voy, voy, nb_max_lignes)):
                service_cible = s
                break

        if service_cible is None:
            if len(propo.service) >= max_services:
                print(f"⚠ Max services ({max_services}) atteint, impossible d'assigner {voy.num_voyage} seul")
                continue
            service_cible = creer_service(len(propo.service) + 1, voy)
            propo.ajout_service(service_cible)

        service_cible.ajouter_voyage(voy)
        voy.assigned = True

voyages_non_asignes = [v for v in voyages_test if not v.assigned]
if voyages_non_asignes:
    print(f"\n⚠ {len(voyages_non_asignes)} voyages non assignés (max_services={max_services} atteint) :")
    for v in voyages_non_asignes:
        print(f"  - {v.num_voyage} ({v.arret_debut} → {v.arret_fin})")
else:
    print("\n✅ Tous les voyages sont assignés !")

print(f"\n=== Proposition {propo.num_proposition} ===")
print(f"Total voyages : {propo.total_voyages()} / {len(voyages_test)}")
print(f"Nombre de services : {len(propo.service)} / {max_services}")
for s in propo.service:
    print(f"\n{s}")