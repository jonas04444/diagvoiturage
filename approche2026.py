#from objet import *

#voyage1 = voyage(91,1,"CEN01", "CEN02", "10:00", "11:00", 5)

class voyage:

    def __init__(self, num_voyage, num_ligne, h_debut, h_fin):
        self.num_voyage = num_voyage
        self.num_ligne = num_ligne
        self.h_debut = self.time_to_minutes(h_debut)
        self.h_fin = self.time_to_minutes(h_fin)
        self.h_fin = h_fin

    @staticmethod
    def time_to_minutes(time_str):
        h,m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def minutes_to_time(minutes):
        return h * 60 + m

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
voyage93= voyage(3,91, 1040, 1050)
service1= service(2101)

listevoyage = [voyage91, voyage92, voyage93]

for v in listevoyage:
    service1.add_voyage(v)

for v in service1.voyages:
    print(v.num_ligne, v.num_voyage)