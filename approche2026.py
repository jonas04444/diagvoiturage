#from objet import *

#voyage1 = voyage(91,1,"CEN01", "CEN02", "10:00", "11:00", 5)

class voyage:

    def __init__(self, num_voyage, num_ligne, h_debut, h_fin):
        self.num_voyage = num_voyage
        self.num_ligne = num_ligne
        self.h_debut = h_debut
        self.h_fin = h_fin

class service:

    def __init__(self, num_service):
        self.num_service = num_service
        self.voyages = []

    def add_voyage(self, nouveau_voyage):
        for i in self.voyages:
            if nouveau_voyage.h_debut < i.h_fin and nouveau_voyage.h_fin > i.h_debut:
                print(f"Pas possible d'ajouter le voyage {nouveau_voyage.num_voyage} : chevauchement détecté.")
                return

        self.voyages.append(nouveau_voyage)
        print(f"Voyage {nouveau_voyage.num_voyage} ajouté au service")

voyage91= voyage(1,91, 1000, 1030)
voyage92= voyage(2,91, 1020, 1050)
voyage93= voyage(2,91, 1040, 1050)
service1= service(2101)
service1.add_voyage(voyage91)
service1.add_voyage(voyage92)
service1.add_voyage(voyage93)