
import os
import platform
import cv2
import json
import time
from ultralytics import YOLO

def recognize(show=False):

    SO = platform.system()

    if SO == "Windows":
        model_path = r"C:\Users\heito\OneDrive\Desktop\dev13\DataSetYolo\runs\detect\train\weights\best.pt"
        video_path = r"uploads\saida.mp4"
    else:
        # Ajuste para seu Linux/VM
        model_path = "/home/ubuntu/DataSetYolo/runs/detect/train/weights/best.pt"
        video_path = "/home/ubuntu/Yolo_Server/uploads/saida.mp4"

    model_path = os.path.normpath(model_path)
    video_path = os.path.normpath(video_path)

    print(f"[INFO] Sistema detectado: {SO}")
    print(f"[INFO] Usando modelo: {model_path}")
    print(f"[INFO] Usando vídeo: {video_path}")

    custom_model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(f"Erro ao abrir vídeo: {video_path}")

    enter_time = {}
    object_classes = {}
    full_log_snapshots = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        results_stream = custom_model.track(
            frame,
            tracker="botsort_custom.yaml",
            stream=True,
            persist=True,
            verbose=False
        )

        current_ids = set()
        frame_objects = {}

        for r in results_stream:
            if r.boxes.id is None:
                continue

            for box in r.boxes:
                if len(box.cls) == 0 or len(box.conf) == 0 or len(box.xyxy) == 0 or len(box.id) == 0:
                    continue

                cls = int(box.cls[0])
                obj_id = int(box.id[0])
                label = custom_model.names[cls]
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                current_ids.add(obj_id)
                object_classes[obj_id] = label

                pos_str = f"({x1},{y1}),({x2},{y2})"

                frame_objects.setdefault(label, []).append({
                    "ID": obj_id,
                    "pos": pos_str
                })

                if obj_id not in enter_time:
                    enter_time[obj_id] = current_time
                    print(f"[+] {current_time:.2f}s: {label} {obj_id} entrou.")

        if frame_objects:
            full_log_snapshots.append({f"{current_time:.2f}": frame_objects})

        # Detect exits
        for obj_id in list(enter_time.keys()):
            if obj_id not in current_ids:
                entrada = enter_time[obj_id]
                duracao = current_time - entrada
                lbl = object_classes.get(obj_id, "Unknown")

                print(f"[-] {current_time:.2f}s: {lbl} {obj_id} saiu | duração {duracao:.2f}s")
                del enter_time[obj_id]

        # SHOW only if requested (for headless safety)
        if show:
            cv2.imshow("YOLO Tracking", frame)
            if cv2.waitKey(1) == 27:
                break

    cap.release()
    if show:
        cv2.destroyAllWindows()

    return full_log_snapshots
