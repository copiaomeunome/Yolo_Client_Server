import classes.Frame as Frame
class Video:
    def __init__(self, frames, width, height):
        self.frames = frames
        self.width = width
        self.height = height
    def add_frame(self, frame):
        self.frames.append(frame)
    def __repr__(self):
        return f"Video({len(self.frames)} frames, {self.width}x{self.height})\n"