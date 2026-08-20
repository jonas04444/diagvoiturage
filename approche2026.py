
class voyage:

    def __init__(self, num_voyage, num_ligne, h_debut, h_fin):
        self.num_voyage = num_voyage
        self.num_ligne = num_ligne
        self.h_debut = self.time_to_minutes(h_debut)
        self.h_fin = self.time_to_minutes(h_fin)


    @staticmethod
    def time_to_minutes(time_str):
        h,m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def minutes_to_time(minutes):
        return h * 60 + m

class service:

    def __init__(self, num_service, debut_service, fin_service):
        self.num_service = num_service
        self.debut_service = self.time_to_minutes(debut_service)
        self.fin_service = self.time_to_minutes(fin_service)
        self.voyages = []

    @staticmethod
    def time_to_minutes(time_str):
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def minutes_to_time(minutes):
        return h * 60 + m

    def add_voyage(self, nouveau_voyage):
        for i in self.voyages:
            if nouveau_voyage.h_debut < i.h_fin and nouveau_voyage.h_fin > i.h_debut:
                print(f"Pas possible d'ajouter le voyage {nouveau_voyage.num_voyage} : chevauchement détecté.")
                return

        self.voyages.append(nouveau_voyage)
        print(f"Voyage {nouveau_voyage.num_voyage} ajouté au service")

    def remove_voyage(self, nouveau_voyage):
        self.voyages.remove(nouveau_voyage)



voyage91= voyage(1,91, "10:00", "10:30")
voyage92= voyage(2,91, "10:20", "10:50")
voyage93= voyage(3,91, "10:40", "10:50")
service1= service(2101,"9:00", "12:00")

listevoyages = [voyage91, voyage92, voyage93]

