from ultralytics import YOLO
import cv2
import time
import json

def recognize():
    #COLOQUE O CAMINHO AQUI
    custom_model = YOLO(r"C:\Users\heito\OneDrive\Desktop\dev13\DataSetYolo\runs\detect\train\weights\best.pt")

    video_path = "uploads\saida.mp4"
    cap = cv2.VideoCapture(video_path)

    enter_time = {}
    object_classes = {} # Para lembrar qual é a classe do ID (ex: 1 = person)
    
    full_log_snapshots = [] 

    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # fim do vídeo

        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0 

        results = custom_model.track(
            frame,
            tracker="botsort_custom.yaml", 
            stream=True,
            persist=True,
            verbose=False
        )

        current_ids = set()
        
        frame_objects = {} 

        for r in results:
            if r.boxes.id is None:
                continue

            for box in r.boxes:
                if box.cls is None or len(box.cls) == 0:
                    continue
                if box.conf is None or len(box.conf) == 0:
                    continue
                if box.xyxy is None or len(box.xyxy) == 0:
                    continue
                if box.id is None or len(box.id) == 0:
                    continue

                cls = int(box.cls[0])
                label = custom_model.names[int(cls)]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                obj_id = int(box.id[0])

                
                current_ids.add(obj_id)
                object_classes[obj_id] = label # Salva a classe deste ID

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} ID {obj_id}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                pos_str = f"({x1},{y1}),({x2},{y2})"
                
                obj_data = {
                    "ID": obj_id,
                    "pos": pos_str
                }

                if label not in frame_objects:
                    frame_objects[label] = []
                frame_objects[label].append(obj_data)

                if obj_id not in enter_time:
                    enter_time[obj_id] = current_time
                    print(f"[+] {current_time:.2f}s: {label} {obj_id} entrou.")

        if frame_objects:
            timestamp_key = f"{current_time:.2f}"
            snapshot = { timestamp_key: frame_objects }
            full_log_snapshots.append(snapshot)

        ids_to_remove = []
        for obj_id in list(enter_time.keys()):
            if obj_id not in current_ids:
                entrada = enter_time[obj_id]
                saida = current_time
                duracao = saida - entrada
                
                lbl = object_classes.get(obj_id, "Unknown")
                
                print(f"[-] {saida:.2f}s: {lbl} {obj_id} saiu | duração {duracao:.2f}s")
                ids_to_remove.append(obj_id)

        for obj_id in ids_to_remove:
            del enter_time[obj_id]

        cv2.imshow("YOLO + ByteTrack", frame)
        if cv2.waitKey(1) == 27: #27 = ESC
            break

    cap.release()
    cv2.destroyAllWindows()

    return full_log_snapshots

def run_recognize():
    log_data = recognize() 

    print("\n-------------------------------------------------\nSalvando LOG em JSON")

    with open("log_output.json", "w") as f:
        json.dump(log_data, f, indent=4)

    print("Arquivo 'log_output.json' salvo com sucesso!")

if __name__ == "__main__":
    run_recognize()