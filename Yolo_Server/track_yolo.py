from ultralytics import YOLO
import cv2
import time
import json # Importante para formatar a saída

def recognize():
    # Carrega o modelo
    # Se der erro no caminho, verifique se o arquivo existe ou use barras duplas \\
    custom_model = YOLO(r"runs\detect\train3\weights\best.pt")

    video_path = "uploads\saida.mp4"
    cap = cv2.VideoCapture(video_path)

    # Dicionários para controle
    enter_time = {}
    object_classes = {} # Para lembrar qual é a classe do ID (ex: 1 = person)
    
    # Lista que vai guardar o log completo no formato solicitado
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
            verbose=False # Desativa logs do YOLO no terminal para limpar a visão
        )

        current_ids = set()
        
        # Dicionário para guardar o estado DO FRAME ATUAL
        # Ex: { "person": [...], "cell phone": [...] }
        frame_objects = {} 

        for r in results:
            if r.boxes.id is None:
                continue

            for box in r.boxes:
                cls = int(box.cls[0])
                label = custom_model.names[cls]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                obj_id = int(box.id[0])
                
                current_ids.add(obj_id)
                object_classes[obj_id] = label # Salva a classe deste ID

                # Desenho na tela
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} ID {obj_id}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # --- LÓGICA DO LOG SOLICITADO ---
                # Cria a string de posição "(x1,y1),(x2,y2)"
                pos_str = f"({x1},{y1}),({x2},{y2})"
                
                # Cria o objeto de dados
                obj_data = {
                    "ID": obj_id,
                    "pos": pos_str
                }

                # Adiciona ao dicionário do frame atual agrupado por label
                if label not in frame_objects:
                    frame_objects[label] = []
                frame_objects[label].append(obj_data)

                # --- LÓGICA DE ENTRADA (Manteve-se para debug no console) ---
                if obj_id not in enter_time:
                    enter_time[obj_id] = current_time
                    print(f"[+] {current_time:.2f}s: {label} {obj_id} entrou.")

        # --- ARMAZENAR O SNAPSHOT DO FRAME ---
        # Só salva se houve alguma detecção no frame para não encher de logs vazios
        if frame_objects:
            timestamp_key = f"{current_time:.2f}"
            # Estrutura: { "00.00": { "person": [...] } }
            snapshot = { timestamp_key: frame_objects }
            full_log_snapshots.append(snapshot)

        # --- LÓGICA DE SAÍDA ---
        ids_to_remove = []
        for obj_id in list(enter_time.keys()):
            if obj_id not in current_ids:
                entrada = enter_time[obj_id]
                saida = current_time
                duracao = saida - entrada
                
                # Recupera o label salvo (correção do bug do código original)
                lbl = object_classes.get(obj_id, "Unknown")
                
                print(f"[-] {saida:.2f}s: {lbl} {obj_id} saiu | duração {duracao:.2f}s")
                ids_to_remove.append(obj_id)

        for obj_id in ids_to_remove:
            del enter_time[obj_id]
            # Não deletamos de object_classes imediatamente caso o ID volte rápido, 
            # mas num código longo seria bom limpar.

        cv2.imshow("YOLO + ByteTrack", frame)
        if cv2.waitKey(1) == 27: # ESC para sair
            break

    cap.release()
    cv2.destroyAllWindows()

    return full_log_snapshots

def run_recognize():
    log_data = recognize()

    print("\n-------------------------------------------------\nSalvando LOG formatado...")

    # Escreve no arquivo com a formatação exata que você pediu
    with open("log_formatado.txt", "w") as f:
        for entry in log_data:
            # entry é um dict { "00.33": { ... dados ... } }
            for timestamp, content in entry.items():
                # Converter o conteúdo interno para JSON string
                # indent=4 deixa bonitinho como no seu exemplo
                content_str = json.dumps(content, indent=4)
                
                # Escreve no formato: "TIME": CONTEUDO
                f.write(f'"{timestamp}":{content_str}\n\n')

    print("Arquivo 'log_formatado.txt' salvo com sucesso!")

if __name__ == "__main__":
    run_recognize()