import cv2
import numpy as np
import time


def capturar_da_camera(fps_destino=3):
    """
    Captura vídeo da webcam, mostrando na tela,
    mas só guarda frames na memória na taxa fps_destino (ex: 3 fps).
    Aperte 'q' para parar.
    """
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Erro ao acessar a câmera.")
        return []

    frames = []
    intervalo = 1.0 / fps_destino
    ultimo_salvo = 0.0

    print("Gravando... Aperte 'q' na janela de vídeo para parar.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        agora = time.time()

        # Mostra na tela
        cv2.imshow("Gravando (aperte 'q' para parar)", frame)

        # Guarda apenas na taxa desejada (3 fps)
        if agora - ultimo_salvo >= intervalo:
            frames.append(frame.copy())
            ultimo_salvo = agora

        # Tecla 'q' para parar
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    print(f"Captura finalizada. Total de frames capturados: {len(frames)}")
    return frames


def detectar_frames_com_movimento(frames,
                                  limiar_pix_diff=25,
                                  limiar_qtd_pixels=5000,
                                  min_seq_movimento=3,
                                  padding=3):
    """
    Recebe uma lista de frames e devolve uma máscara booleana
    indicando quais frames devem ser mantidos (com movimento).

    - limiar_pix_diff: diferença mínima de intensidade para considerar mudança.
    - limiar_qtd_pixels: número mínimo de pixels diferentes para considerar movimento.
    - min_seq_movimento: número mínimo de frames com movimento para considerar um trecho válido.
    - padding: quantos frames antes e depois do movimento manter.
    """
    if not frames:
        return []

    motion_flags = []
    prev_gray = None

    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_gray is None:
            prev_gray = gray
            motion_flags.append(False)
            continue

        frame_delta = cv2.absdiff(prev_gray, gray)
        _, thresh = cv2.threshold(frame_delta, limiar_pix_diff, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        motion_pixels = cv2.countNonZero(thresh)

        # Considera que há movimento se pixels suficientes mudaram
        motion = motion_pixels > limiar_qtd_pixels
        motion_flags.append(motion)

        # Atualiza "background" para próxima comparação
        prev_gray = gray

    # Suaviza a máscara para formar trechos contínuos com padding
    n = len(motion_flags)
    keep = [False] * n
    i = 0
    while i < n:
        if motion_flags[i]:
            inicio = i
            while i < n and motion_flags[i]:
                i += 1
            fim = i - 1

            # Só considera um trecho se tiver pelo menos min_seq_movimento frames
            if fim - inicio + 1 >= min_seq_movimento:
                ks = max(0, inicio - padding)
                ke = min(n - 1, fim + padding)
                for j in range(ks, ke + 1):
                    keep[j] = True
        else:
            i += 1

    # Se nada foi marcado como movimento, por segurança mantém tudo
    if not any(keep):
        keep = [True] * n

    return keep


def salvar_video_mp4(frames, mask_keep, fps=3, nome_arquivo="saida.mp4"):
    """
    Salva apenas os frames marcados como True em mask_keep em um arquivo MP4.
    """
    if not frames:
        print("Nenhum frame para salvar.")
        return

    if len(frames) != len(mask_keep):
        print("Erro: tamanho da máscara não bate com os frames.")
        return

    # Pega tamanho do vídeo a partir do primeiro frame
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # codec MP4
    out = cv2.VideoWriter(nome_arquivo, fourcc, fps, (w, h))

    kept_count = 0
    for frame, keep in zip(frames, mask_keep):
        if keep:
            out.write(frame)
            kept_count += 1

    out.release()
    print(f"Vídeo salvo como {nome_arquivo}. Frames mantidos: {kept_count}")


def main():
    #  Capturar vídeo da câmera em aproximadamente 3 FPS
    fps_destino = 3
    frames = capturar_da_camera(fps_destino=fps_destino)

    if not frames:
        return

    #  Detectar quais frames têm movimento
    print("Detectando movimento e filtrando trechos sem nada...")
    mask_keep = detectar_frames_com_movimento(frames)

    #  Salvar apenas as partes com movimento em formato MP4
    salvar_video_mp4(frames, mask_keep, fps=fps_destino, nome_arquivo="saida.mp4")


if __name__ == "__main__":
    main()
