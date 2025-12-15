class Event:
    def __init__(self, tInit, tEnd, name):
        self.tInit = tInit
        self.tEnd = tEnd
        self.name = name

    def __repr__(self):
        return f"Event({self.name}, {self.tInit} -> {self.tEnd})\n"
