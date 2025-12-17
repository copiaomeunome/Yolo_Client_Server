from classes.Video import Video
from classes.Frame import Frame
from classes.Object import Object
from ultralytics import YOLO
import cv2
import time
import json
import sys
import os


def recognize_multi(video_path, models):
    """
    Roda inferencia com multiplos modelos em um unico passeio pelo video.
    """
    cap = cv2.VideoCapture(video_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    video_obj = Video([], width, height)

    tracker_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "botsort_custom.yaml"))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        detected_objects = []

        for model_idx, (model_name, model) in enumerate(models):
            # offset de IDs para evitar colisao entre modelos
            id_offset = model_idx * 100000
            results = model.track(
                frame,
                tracker=tracker_path,
                stream=False,
                persist=True,
                verbose=False
            )

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
                    label = model.names[int(cls)] if hasattr(model, "names") else f"class_{cls}"
                    points = list(map(int, box.xyxy[0]))
                    obj_id = int(box.id[0]) + id_offset

                    # Usa apenas o nome da classe (sem prefixar com o nome do modelo)
                    obj = Object(points, label, obj_id)
                    detected_objects.append(obj)

                    # Desenha bounding box na imagem exibida
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

        frame_obj = Frame(current_time, detected_objects)
        video_obj.add_frame(frame_obj)

        # Exibe janela com bounding boxes, se nao estiver em ambiente headless
        if os.environ.get("NO_DISPLAY", "0") != "1":
            cv2.imshow("YOLO + ByteTrack (multi-model)", frame)
            if cv2.waitKey(1) == 27:  # ESC para sair
                break

    cap.release()
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
                    "topLeft": {"x": obj.points[0], "y": obj.points[1]},
                    "bottomRight": {"x": obj.points[2], "y": obj.points[3]},
                    "name": obj.nome,
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
    if len(sys.argv) < 3:
        print("Uso: python Yolo_Inference.py <video_path> <model1> [model2 ...]", file=sys.stderr)
        sys.exit(1)

    video_path = sys.argv[1]

    model_paths = sys.argv[2:]
    if len(model_paths) == 0:
        print("Nenhum modelo fornecido.", file=sys.stderr)
        sys.exit(1)

    models = []
    for mp in model_paths:
        models.append((os.path.basename(mp).replace(".pt", ""), YOLO(mp)))

    video_obj = recognize_multi(video_path, models)

    # Emite JSON no stdout para ser consumido pelo Manager.cs
    json_payload = video_to_json(video_obj)
    print(json.dumps(json_payload))
