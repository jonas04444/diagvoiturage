from objet import *

voyages_test = [
        voyage("25", "V1", "Station A", "Station B", "06:00", "07:00"),
        voyage("25", "V2", "Station B", "Station A", "07:10", "08:00"),
        voyage("35", "V3", "Station A", "Station C", "06:30", "07:30"),
        voyage("35", "V4", "Station C", "Station A", "08:15", "09:00"),
    ]

service_agent = []
for i in range(len(voyages_test)):
    for j in range(i+1, len(voyages_test)):
        voy = voyages_test[i]
        voy2 = voyages_test[j]

        """if voy.num_ligne == voy2.num_ligne:
            print(voy.num_ligne)"""
        print (min(voy.hdebut))
        if voy.hdebut < voy2.hfin and voy.arret_fin == voy2.arret_debut:
            """print(voy.arret_debut, voy.num_voyage, voy2.num_voyage)
            service_agent.append(voy)"""
            pass