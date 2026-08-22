
class voyage:

    def __init__(self, num_voyage, num_ligne, arret_debut, arret_fin, h_debut, h_fin):
        self.num_voyage = num_voyage
        self.num_ligne = num_ligne
        self.arret_debut = arret_debut
        self.arret_fin = arret_fin
        self.h_debut = self.time_to_minutes(h_debut)
        self.h_fin = self.time_to_minutes(h_fin)


    @staticmethod
    def time_to_minutes(time_str):
        h,m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def minutes_to_time(minutes):
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

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
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def add_voyage(self, nouveau_voyage):
        if nouveau_voyage.h_debut >= self.debut_service and nouveau_voyage.h_fin <= self.fin_service:
            for i in self.voyages:
                if nouveau_voyage.h_debut < i.h_fin and nouveau_voyage.h_fin > i.h_debut:
                    #print(f"Pas possible d'ajouter le voyage {nouveau_voyage.num_voyage} : chevauchement détecté.")
                    return False

            self.voyages.append(nouveau_voyage)
            #print(f"Voyage {nouveau_voyage.num_voyage} ajouté au service")
            return True
        else:
            #print("hors horaire")
            return False

    def remove_voyage(self, nouveau_voyage):
        self.voyages.remove(nouveau_voyage)

def assigner_voyages(voyages):
    services = []
    for v in voyages:
        assigne = False
        for s in services:
            if s.add_voyage(v):
                print(f"Voyage {v.num_voyage} ajouté au service {s.num_service}")
                assigne = True
                break

        if not assigne:
            debut = v.h_debut
            fin = debut + 8 * 60
            nouveau_service = service(
                len(services) +1,
                service.minutes_to_time(debut),
                service.minutes_to_time(fin),
            )
            nouveau_service.add_voyage(v)
            services.append(nouveau_service)
            print(f"Nouveau service {nouveau_service.num_service} créé pour le voyage {v.num_voyage}")

    return services


voyage91= voyage(1,91, "A", "B","8:00", "10:30")
voyage92= voyage(2,91, "A", "B","10:20", "10:50")
voyage93= voyage(3,91, "A", "B","10:50", "10:51")

listevoyage = [voyage91, voyage92, voyage93]

services = assigner_voyages(listevoyage)

for s in services:
    print(f"Service {s.num_service} : {[v.num_voyage for v in s.voyages]}")