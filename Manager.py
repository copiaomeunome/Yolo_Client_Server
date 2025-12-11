from process.Yolo_Inference import recognize
from ultralytics import YOLO
from process.ListEvents import ListEvents
from process.Call_OpenAI import callOpenAI

if __name__ == "__main__":
    video = recognize("uploads/Vídeo_de_Trabalhador_da_CEMIG.mp4", YOLO(r"C:\Users\heito\OneDrive\Desktop\dev13\DataSetYolo\runs\detect\train\weights\best.pt"))
    events = ListEvents(video)
    callOpenAI(events)
