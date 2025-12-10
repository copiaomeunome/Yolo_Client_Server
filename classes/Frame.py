import classes.Object as Object
class Frame:
    def __init__(self, time, objects):
        self.objects = objects
        self.time = time
    def __repr__(self):
        return f"Frame(t={self.time}, objs={len(self.objects)})\n"