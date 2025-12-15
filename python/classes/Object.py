class Object:
    def __init__(self, points, nome, id):
        self.id = id
        self.points = points
        self.nome = nome

    def __repr__(self):
        return f"{self.nome}(ID={self.id}, [{self.p1},{self.p2}])"