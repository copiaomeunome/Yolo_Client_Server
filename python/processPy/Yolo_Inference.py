from classes.Video import Video
from classes.Frame import Frame
from classes.Object import Object
from ultralytics import YOLO
import cv2
import time
import json
import sys
import os


def recognize(video_path, custom_model, lane_model=None):
    """
    Roda inferencia apenas com o modelo custom (deteccao). A antiga inferencia
    com o modelo COCO/YOLO de segmentacao foi comentada para ficar desativada.
    """
    # fallback para modelo de segmentacao padrao (desativado)
    # if lane_model is None:
    #     lane_model = YOLO("yolov8n-seg.pt")
    #
    # COCO_CLASSES = lane_model.names if hasattr(lane_model, "names") else {}
    # LANE_ID_OFFSET = 200000  # evita colisao de IDs entre deteccao e segmentacao

    cap = cv2.VideoCapture(video_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    video_obj = Video([], width, height)

    enter_time = {}
    object_classes = {}

    start_time = time.time()
    tracker_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "botsort_custom.yaml"))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        # Detecao com modelo custom
        results = custom_model.track(
            frame,
            tracker=tracker_path,
            stream=True,
            persist=True,
            verbose=False
        )

        detected_objects = []

        for r in results:
            if r.boxes.id is None:
                continue

            for box in r.boxes:
                if (
                    box.cls is None or len(box.cls) == 0 or
                    box.conf is None or len(box.conf) == 0 or
                    box.xyxy is None or len(box.xyxy) == 0 or
                    box.id is None or len(box.id) == 0
                ):
                    continue

                cls = int(box.cls[0])
                label = custom_model.names[int(cls)] if hasattr(custom_model, "names") else f"class_{cls}"
                points = list(map(int, box.xyxy[0]))
                obj_id = int(box.id[0])

                # Desenha bounding box com label e ID na imagem exibida
                color = (0, 255, 0)
                cv2.rectangle(frame, (points[0], points[1]), (points[2], points[3]), color, 2)
                text = f"{label} {obj_id}"
                cv2.putText(
                    frame,
                    text,
                    (points[0], max(points[1] - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                    cv2.LINE_AA,
                )

                obj = Object(points, label, obj_id)
                detected_objects.append(obj)

                object_classes[obj_id] = label

                if obj_id not in enter_time:
                    enter_time[obj_id] = current_time

        
        frame_obj = Frame(current_time, detected_objects)
        video_obj.add_frame(frame_obj)

        cv2.imshow("YOLO + ByteTrack", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    return video_obj


def video_to_json(video_obj):
    """
    Converte o objeto Video para um dict serializavel em JSON.
    """
    frames = []
    for fr in video_obj.frames:
        frames.append({
            "time": fr.time,
            "objects": [
                {
                    "id": obj.id,
                    "points[0]": obj.points[0],
                    "points[1]": obj.points[1],
                    "points[2]": obj.points[2],
                    "points[3]": obj.points[3],
                    "nome": obj.nome,
                }
                for obj in fr.objects
            ]
        })

    return {
        "width": video_obj.width,
        "height": video_obj.height,
        "frames": frames,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python Yolo_Inference.py <video_path>", file=sys.stderr)
        sys.exit(1)

    video_path = sys.argv[1]

    model_path = r"C:\Users\heito\OneDrive\Desktop\dev13\DataSetYolo\runs\detect\train\weights\best.pt"
    custom_model = YOLO(model_path)

    video_obj = recognize(video_path, custom_model)

    # Emite JSON no stdout para ser consumido pelo Manager.cs
    json_payload = video_to_json(video_obj)
    print(json.dumps(json_payload))
