from classes.Video import Video
from classes.Frame import Frame
from classes.Object import Object
from ultralytics import YOLO
import cv2
import time

def recognize(video_path, custom_model):
    # COCO/YOLO default classes (v8/11/12 family) as fallback to custom names
    COCO_CLASSES = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
        "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
        "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
        "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
        "hair drier", "toothbrush"
    ]

    cap = cv2.VideoCapture(video_path)

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    video_obj = Video([], width, height)

    enter_time = {}
    object_classes = {}
    
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        results = custom_model.track(
            frame,
            tracker="botsort_custom.yaml",
            stream=True,
            persist=True,
            verbose=False
        )

        detected_objects = []

        for r in results:
            if r.boxes.id is None:
                continue

            for box in r.boxes:
                if (box.cls is None or len(box.cls) == 0 or
                    box.conf is None or len(box.conf) == 0 or
                    box.xyxy is None or len(box.xyxy) == 0 or
                    box.id is None or len(box.id) == 0):
                    continue

                cls = int(box.cls[0])
                # Prioriza nomes customizados e cai para classes default do YOLO
                if hasattr(custom_model, "names") and cls in custom_model.names:
                    label = custom_model.names[int(cls)]
                elif cls < len(COCO_CLASSES):
                    label = COCO_CLASSES[cls]
                else:
                    label = f"class_{cls}"
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                obj_id = int(box.id[0])

                # Desenha bounding box com label e ID na imagem exibida
                color = (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                text = f"{label} {obj_id}"
                cv2.putText(
                    frame,
                    text,
                    (x1, max(y1 - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                    cv2.LINE_AA,
                )

                # cria Object()
                obj = Object(x1, y1, x2, y2, label, obj_id)
                detected_objects.append(obj)

                object_classes[obj_id] = label

                if obj_id not in enter_time:
                    enter_time[obj_id] = current_time

        # cria Frame()
        frame_obj = Frame(current_time, detected_objects)
        video_obj.add_frame(frame_obj)

        cv2.imshow("YOLO + ByteTrack", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    return video_obj
