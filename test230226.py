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

servicetest = service_agent(num_service=1, type_service="matin")
def chevauche_service (service, nouveau_voyage):
    for v in servicetest.get_voyages():
        if not (nouveau_voyage.hfin <= v.hdebut or nouveau_voyage.hdebut >= v.hfin):
            return True
    return False

for i in range(len(voyages_test)):
    for j in range(i+1, len(voyages_test)):
        voy = voyages_test[i]
        voy2 = voyages_test[j]


        if (voy.hdebut <= voy2.hfin
                and voy.hfin <= voy2.hdebut
                and voy.arret_fin == voy2.arret_debut
                and voy.assigned == False
                and voy2.assigned == False
                and not chevauche_service(servicetest, voy)
                and not chevauche_service(servicetest, voy2)):
            #print(voy.arret_debut, voy.num_voyage, voy2.num_voyage)
            servicetest.ajouter_voyage(voy)
            servicetest.ajouter_voyage(voy2)
            voy.assigned = True
            voy2.assigned = True
            break

for v in servicetest.get_voyages():
    print(v.arret_fin, v.num_voyage, v.num_ligne)

print(servicetest)