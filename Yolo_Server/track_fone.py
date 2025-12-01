from ultralytics import YOLO
import cv2
import time
import os

def recognize():

    coco_model = YOLO("yolo12m.pt")
    custom_model = YOLO("runs/detect/train3/weights/best.pt")

    video_path = "uploads\saida.mp4"
    cap = cv2.VideoCapture(video_path)

    fone_enter_time = {}
    events = []
    event_log = []

    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # fim do vídeo ✔

        #tempo do vídeo
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0  # segundos

        coco_results = coco_model(frame, stream=True)
        fone_results = custom_model.track(
            frame,
            tracker="botsort_custom.yaml", #botsort_custom
            stream=True,
            persist=True
        )

        #COCO
        for r in coco_results:
            for box in r.boxes:
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                label = coco_model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                cv2.rectangle(frame, (x1,y1), (x2,y2), (255,255,0), 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (x1,y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)

        #FONE
        current_fone_ids = set()

        for r in fone_results:
            if r.boxes.id is None:
                continue

            for box in r.boxes:

                cls = int(box.cls[0])
                label = custom_model.names[cls]
                conf = float(box.conf[0])
                x1,y1,x2,y2 = map(int, box.xyxy[0])

                if label.lower() != "fone":
                    cv2.rectangle(frame, (x1,y1), (x2,y2), (0,165,255), 2)
                    cv2.putText(frame, f"{label} {conf:.2f}", (x1,y1-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,165,255), 2)
                    continue

                # rastrear fone
                obj_id = int(box.id[0])
                current_fone_ids.add(obj_id)

                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
                cv2.putText(frame, f"Fone ID {obj_id}", (x1,y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

                if obj_id not in fone_enter_time:
                    fone_enter_time[obj_id] = current_time

                    msg = f"{current_time:.2f}s: Fone {obj_id} entrou"
                    print("[+]", msg)
                    event_log.append(msg)

        #SAÍDA
        ids_to_remove = []

        for obj_id in list(fone_enter_time.keys()):
            if obj_id not in current_fone_ids:
                entrada = fone_enter_time[obj_id]
                saida = current_time
                duracao = saida - entrada

                msg = f"{saida:.2f}s: Fone {obj_id} saiu | duração {duracao:.2f}s"
                print("[-]", msg)

                events.append((obj_id, entrada, saida, duracao))
                event_log.append(msg)

                ids_to_remove.append(obj_id)

        for obj_id in ids_to_remove:
            del fone_enter_time[obj_id]

        cv2.imshow("YOLO + ByteTrack", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    # 🔥 APAGAR O ARQUIVO DEPOIS DE USAR
    

    return event_log


def run_recognize():
    log = recognize()

    print("\n-------------------------------------------------\nLOG:")

    for item in log:
        print(item)
        
    with open("log_fone.txt", "w") as f:
        for item in log:
            f.write(item + "\n")

    print("\nArquivo 'log_fone.txt' salvo com sucesso!")
