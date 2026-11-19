class proposition:

    def __init__(self, num_proposition):
        self.num_proposition = num_proposition
        self.service = []

    def ajout_service(self, service):
        self.service.append(service)

    def total_voyages(self):
        return sum(len(s.get_voyages()) for s in self.service)

    def total_hlps(self):
        return sum(len(s.get_hlps()) for s in self.service)

    def duree_hlp_totale(self):
        return sum(s.duree_hlp_totale() for s in self.service)
