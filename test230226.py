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
        ]

min_pause = 15
max_pause = 60
nb_max_lignes = 1
max_services = 10
max_propositions = 5
min_duree_service = 6 * 60
max_duree_service = 8 * 60 + 30
cible_duree = 7 * 60 + 15
variation = 0

def voyage_compatible(service, nouveau_voyage, min_pause, max_pause):
    for v in service.get_voyages():
        if not (nouveau_voyage.hfin <= v.hdebut or nouveau_voyage.hdebut >= v.hfin):
            return False

    voyages_tries = sorted(service.get_voyages() + [nouveau_voyage], key=lambda v: v.hdebut)
    idx = voyages_tries.index(nouveau_voyage)

    if idx > 0:
        pause = nouveau_voyage.hdebut - voyages_tries[idx - 1].hfin
        if not (min_pause <= pause <= max_pause):
            return False

    if idx < len(voyages_tries) - 1:
        pause = voyages_tries[idx + 1].hdebut - nouveau_voyage.hfin
        if not (min_pause <= pause <= max_pause):
            return False

    return True

def creer_service(num, voy, petit=False):
    type_s = "matin" if voy.hdebut <= 600 else "après-midi"
    s = service_agent(num_service=num, type_service=type_s)
    s.petit_service = petit
    return s

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

def tous_services_ont_pause(propo, pause_min=20):
    for s in propo.service:
        if not verifier_pause_minimum(s, pause_min):
            return False
    return True

def verifier_duree_service(service, min_duree, max_duree):
    duree = service.duree_travail_effective()
    if duree < min_duree:
        return False, f"Service trop court : {duree} min (min {min_duree} min)"
    if duree > max_duree:
        return False, f"Service trop long : {duree} min (max {max_duree} min)"
    return True, f"OK : {duree} min"

def tous_services_duree_valide(propo, min_duree, max_duree):
    for s in propo.service:
        if s.get_voyages() and not s.petit_service:
            valide, msg = verifier_duree_service(s, min_duree, max_duree)
            if not valide:
                return False
    return True

def verifier_pause_minimum(service, pause_min=20):
    voyages_tries = sorted(service.get_voyages(), key=lambda v: v.hdebut)

    for i in range(len(voyages_tries) - 1):
        pause = voyages_tries[i + 1].hdebut - voyages_tries[i].hfin
        if pause >= pause_min:
            return True

    return False

def petits_services_valides(propo, max_duree_petit=4*60):
    for s in propo.service:
        if s.get_voyages() and s.petit_service:
            if s.duree_travail_effective() > max_duree_petit:
                return False
    return True

def creer_petits_services(voyages, propo, max_services, min_pause, max_pause, nb_max_lignes, max_duree_petit=4 * 60):
    voyages_non_assignes = [v for v in voyages if not v.assigned]

    if not voyages_non_assignes:
        return

    print(
        f"\n🔧 {len(voyages_non_assignes)} voyages non assignés → création de petits services (max {max_duree_petit // 60}h)")

    for voy in voyages_non_assignes:
        service_cible = None

        for s in propo.service:
            tous_voyages = s.get_voyages() + [voy]
            debut_simule = min(v.hdebut for v in tous_voyages)
            fin_simulee = max(v.hfin for v in tous_voyages)
            duree_simulee = fin_simulee - debut_simule

            if (voyage_compatible(s, voy, min_pause, max_pause)
                    and peut_ajouter_lignes(s, voy, voy, nb_max_lignes)
                    and duree_simulee <= max_duree_petit):  # ← max 4h
                service_cible = s
                break

        if service_cible is None:
            if len(propo.service) >= max_services:
                print(f"  ⚠ Max services atteint, impossible d'assigner {voy.num_voyage}")
                continue
            service_cible = creer_service(len(propo.service) + 1, voy, petit=True)
            propo.ajout_service(service_cible)
            print(f"  ➕ Nouveau petit service {service_cible.num_service} créé pour {voy.num_voyage}")

        service_cible.ajouter_voyage(voy)
        voy.assigned = True
        print(f"  ✅ {voy.num_voyage} ajouté au service {service_cible.num_service}")

def essayer_proposition(voyages, min_pause, max_pause, nb_max_lignes, max_services, num_proposition):
    for v in voyages:
        v.assigned = False

    propo = proposition(num_proposition=num_proposition)
    service_cible = creer_service(1, voyages[0])
    propo.ajout_service(service_cible)

    # ── Boucle 1 : services normaux entre 6h et 8h30 ──────────────────────────
    min_duree = 6 * 60
    max_duree = 8 * 60 + 30

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
                    if s.petit_service:  # ← on ignore les petits services
                        continue
                    tous_voyages = s.get_voyages() + [voy, voy2]
                    debut_simule = min(v.hdebut for v in tous_voyages)
                    fin_simulee = max(v.hfin for v in tous_voyages)
                    duree_simulee = fin_simulee - debut_simule
                    if (voyage_compatible(s, voy, min_pause, max_pause)
                            and voyage_compatible(s, voy2, min_pause, max_pause)
                            and peut_ajouter_lignes(s, voy, voy2, nb_max_lignes)
                            and min_duree <= duree_simulee <= max_duree):
                        service_cible = s
                        break

                if service_cible is None:
                    if len(propo.service) >= max_services:
                        break

                    # ← Vérifier que la paire seule respecte déjà min_duree avant de créer un service normal
                    duree_paire = voy2.hfin - voy.hdebut
                    if not (min_duree <= duree_paire <= max_duree):
                        break  # ← paire trop courte, elle ira en boucle 2

                    service_cible = creer_service(len(propo.service) + 1, voy, petit=False)
                    propo.ajout_service(service_cible)

                if service_cible is None:  # ← si toujours None après le check, on passe au i suivant
                    break

                service_cible.ajouter_voyage(voy)
                service_cible.ajouter_voyage(voy2)
                voy.assigned = True
                voy2.assigned = True
                break

    # ── Boucle 2 : petits services < 4h pour les voyages restants ─────────────
    max_duree_petit = 4 * 60
    voyages_non_assignes = [v for v in voyages if not v.assigned]

    if voyages_non_assignes:
        print(f"\n🔧 {len(voyages_non_assignes)} voyages non assignés → création de petits services (max 4h)")
        for voy in voyages_non_assignes:
            service_cible = None

            # Chercher un petit service existant compatible
            for s in propo.service:
                if not s.petit_service:  # ← on ne complète que les petits services
                    continue
                tous_voyages = s.get_voyages() + [voy]
                debut_simule = min(v.hdebut for v in tous_voyages)
                fin_simulee = max(v.hfin for v in tous_voyages)
                duree_simulee = fin_simulee - debut_simule
                if (voyage_compatible(s, voy, min_pause, max_pause)
                        and peut_ajouter_lignes(s, voy, voy, nb_max_lignes)
                        and duree_simulee <= max_duree_petit):
                    service_cible = s
                    break

            # Aucun petit service compatible → en créer un nouveau
            if service_cible is None:
                if len(propo.service) >= max_services:
                    print(f"  ⚠ Max services atteint, impossible d'assigner {voy.num_voyage}")
                    continue
                service_cible = creer_service(len(propo.service) + 1, voy, petit=True)
                propo.ajout_service(service_cible)
                print(f"  ➕ Petit service {service_cible.num_service} créé pour {voy.num_voyage}")

            service_cible.ajouter_voyage(voy)
            voy.assigned = True
            print(f"  ✅ {voy.num_voyage} → service {service_cible.num_service}")

    return propo

propositions = []
num_proposition  = 1
max_propositions = 5  # nombre max de propositions à générer

while len(propositions) < max_propositions:
    min_duree_service = max(360, cible_duree - variation)
    max_duree_service = min(510, cible_duree + variation)

    print(f"\n🔄 Tentative {num_proposition} | min_pause={min_pause} max_pause={max_pause} "
          f"nb_max_lignes={nb_max_lignes} max_services={max_services} "
          f"durée=[{min_duree_service//60}h{min_duree_service%60:02d} - {max_duree_service//60}h{max_duree_service%60:02d}]")

    propo = essayer_proposition(voyages_test, min_pause, max_pause, nb_max_lignes,
                                max_services, num_proposition)

    voyages_non_assignes = [v for v in voyages_test if not v.assigned]

    if (not voyages_non_assignes
            and tous_services_duree_valide(propo, min_duree_service, max_duree_service)
            and petits_services_valides(propo)):  # ← ajout
        print(f"✅ Proposition {num_proposition} valide !")
        propositions.append(propo)
        num_proposition += 1
        variation += 15


    else:  # relaxation uniquement si échec
        variation += 15  # ← on élargit d'abord la fenêtre de durée
        if min_pause > 0:
            min_pause = max(0, min_pause - 5)
        elif max_pause < 120:
            max_pause += 15
        elif nb_max_lignes < 4:
            nb_max_lignes += 1
        elif max_services < 15:
            max_services += 1
        else:
            print("⚠ Impossible de trouver d'autres solutions")
            break

for p in propositions:
    print(f"\n=== Proposition {p.num_proposition} ===")
    print(f"Total voyages : {p.total_voyages()} / {len(voyages_test)}")
    print(f"Nombre de services : {len(p.service)}")
    for s in p.service:
        duree = s.duree_travail_effective()
        print(f"\n{s}")
        print(f"  → Durée effective : {duree//60}h{duree%60:02d}")