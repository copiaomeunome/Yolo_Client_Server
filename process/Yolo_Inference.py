from classes.Video import Video
from classes.Frame import Frame
from classes.Object import Object
from ultralytics import YOLO
import cv2
import time

def recognize(video_path, custom_model):
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
                label = custom_model.names[int(cls)]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                obj_id = int(box.id[0])

                # cria Object()
                obj = Object(obj_id, x1, y1, x2, y2, label)
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
