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
max_propositions = 5

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


def verifier_pause_minimum(service, pause_min=20):
    voyages_tries = sorted(service.get_voyages(), key=lambda v: v.hdebut)
    for i in range(len(voyages_tries) - 1):
        pause = voyages_tries[i + 1].hdebut - voyages_tries[i].hfin
        if pause >= pause_min:
            return True
    return False

def tous_services_ont_pause(propo, pause_min=20):
    for s in propo.service:
        if not verifier_pause_minimum(s, pause_min):
            return False
    return True

def essayer_proposition(voyages, min_pause, max_pause, nb_max_lignes, max_services, num_proposition):
    # Réinitialiser les voyages
    for v in voyages:
        v.assigned = False

    propo = proposition(num_proposition=num_proposition)
    service_cible = creer_service(1, voyages[0])
    propo.ajout_service(service_cible)

    for i in range(len(voyages)):
        for j in range(i+1, len(voyages)):
            voy = voyages[i]
            voy2 = voyages[j]
            pause_entre = voy2.hdebut - voy.hfin

            if (voy.hdebut <= voy2.hfin
                    and voy.hfin <= voy2.hdebut
                    and voy.arret_fin == voy2.arret_debut
                    and not voy.assigned
                    and not voy2.assigned
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
                        break
                    service_cible = creer_service(len(propo.service) + 1, voy)
                    propo.ajout_service(service_cible)

                service_cible.ajouter_voyage(voy)
                service_cible.ajouter_voyage(voy2)
                voy.assigned = True
                voy2.assigned = True
                break

    for voy in voyages:
        if not voy.assigned:
            service_cible = None
            for s in propo.service:
                if (voyage_compatible(s, voy, min_pause, max_pause)
                        and peut_ajouter_lignes(s, voy, voy, nb_max_lignes)):
                    service_cible = s
                    break

            if service_cible is None:
                if len(propo.service) >= max_services:
                    continue
                service_cible = creer_service(len(propo.service) + 1, voy)
                propo.ajout_service(service_cible)

            service_cible.ajouter_voyage(voy)
            voy.assigned = True

    return propo
propositions = []
num_proposition  = 1
max_propositions = 5  # nombre max de propositions à générer

while len(propositions) < max_propositions:
    print(f"\n🔄 Tentative proposition {num_proposition} | min_pause={min_pause} max_pause={max_pause} nb_max_lignes={nb_max_lignes} max_services={max_services}")

    propo = essayer_proposition(voyages_test, min_pause, max_pause, nb_max_lignes, max_services, num_proposition)
    voyages_non_assignes = [v for v in voyages_test if not v.assigned]

    if not voyages_non_assignes:
        print(f"✅ Proposition {num_proposition} valide !")
        propositions.append(propo)
        num_proposition += 1

    # ← Relaxation progressive des paramètres si échec
    if min_pause > 0:
        min_pause = max(0, min_pause - 5)       # on réduit la pause minimum
    elif max_pause < 120:
        max_pause += 15                          # on augmente la pause maximum
    elif nb_max_lignes < 3:
        nb_max_lignes += 1                       # on accepte plus de lignes
    elif max_services < 10:
        max_services += 1                        # on autorise plus de services
    else:
        print("⚠ Impossible de trouver d'autres solutions même en relaxant les paramètres")
        break

# ── Affichage des propositions ─────────────────────────────────────────────────
for p in propositions:
    print(f"\n=== Proposition {p.num_proposition} ===")
    print(f"Total voyages : {p.total_voyages()} / {len(voyages_test)}")
    print(f"Nombre de services : {len(p.service)}")
    for s in p.service:
        print(f"\n{s}")