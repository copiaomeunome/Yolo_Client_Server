from python.processPy.Yolo_Inference import recognize
from ultralytics import YOLO
from python.processPy.ListEvents import ListEvents
from python.processPy.Call_OpenAI import callOpenAI

if __name__ == "__main__":
    custom_model = YOLO(r"C:\Users\heito\OneDrive\Desktop\dev13\DataSetYolo\runs\detect\train\weights\best.pt")
    # lane_model = YOLO("yolov8n-seg.pt")  # modelo de segmentacao para faixas continuas (desativado)
    video = recognize("uploads/carro.mp4", custom_model)
    events = ListEvents(video)
    callOpenAI(events)
