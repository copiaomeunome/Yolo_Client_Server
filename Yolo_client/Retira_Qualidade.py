import cv2
import numpy as np
import time


def carregar_de_video(caminho_video="Entrada.mp4", fps_destino=3, tamanho_saida=(640, 640)):
    """
    Lê um vídeo do disco, reduz o FPS e redimensiona para tamanho_saida.
    Retorna a lista de frames e o fps de saída.
    """
    cap = cv2.VideoCapture(caminho_video)

    if not cap.isOpened():
        print(f"Erro ao abrir o vídeo: {caminho_video}")
        return [], fps_destino

    fps_original = cap.get(cv2.CAP_PROP_FPS)
    if fps_original <= 0:
        # fallback se o vídeo não reportar FPS
        fps_original = fps_destino

    # não deixar o FPS de saída maior que o original, para não acelerar o vídeo
    fps_saida = min(fps_original, fps_destino)

    # de quantos em quantos frames vamos pegar 1 (para baixar o FPS)
    frame_step = max(1, int(round(fps_original / fps_saida)))

    frames = []
    frame_idx = 0

    print(f"Lendo '{caminho_video}' (fps original ≈ {fps_original:.2f}) ...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # pega somente alguns frames para reduzir o fps
        if frame_idx % frame_step == 0:
            # redimensiona para 640x640
            frame_resized = cv2.resize(frame, tamanho_saida)
            frames.append(frame_resized)

        frame_idx += 1

    cap.release()
    print(f"Total de frames lidos: {frame_idx}, frames usados: {len(frames)}")
    return frames, fps_saida


def detectar_frames_com_movimento(frames,
                                  limiar_pix_diff=25,
                                  limiar_qtd_pixels=5000,
                                  min_seq_movimento=3,
                                  padding=3):
    """
    Recebe uma lista de frames e devolve uma máscara booleana
    indicando quais frames devem ser mantidos (com movimento).
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

        motion = motion_pixels > limiar_qtd_pixels
        motion_flags.append(motion)

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

            if fim - inicio + 1 >= min_seq_movimento:
                ks = max(0, inicio - padding)
                ke = min(n - 1, fim + padding)
                for j in range(ks, ke + 1):
                    keep[j] = True
        else:
            i += 1

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

    # tamanho 640x640 (já garantido ao carregar, mas pegamos do frame)
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # codec MP4
    out = cv2.VideoWriter(nome_arquivo, fourcc, fps, (w, h))

    kept_count = 0
    for frame, keep in zip(frames, mask_keep):
        if keep:
            out.write(frame)
            kept_count += 1

    out.release()
    print(f"Vídeo salvo como {nome_arquivo}. Frames mantidos: {kept_count}, fps={fps}")


def main():
    fps_destino = 3

    # 1) Carregar o vídeo Entrada.mp4, reduzir FPS e redimensionar para 640x640
    frames, fps_saida = carregar_de_video("Entrada.mp4",
                                          fps_destino=fps_destino,
                                          tamanho_saida=(640, 640))

    if not frames:
        return

    # 2) Detectar quais frames têm movimento (opcional, pode pular se quiser manter tudo)
    print("Detectando movimento e filtrando trechos sem nada...")
    mask_keep = detectar_frames_com_movimento(frames)

    # Se não quiser filtrar por movimento, basta usar:
    # mask_keep = [True] * len(frames)

    # 3) Salvar vídeo de saída
    salvar_video_mp4(frames, mask_keep, fps=fps_saida, nome_arquivo="saida.mp4")


if __name__ == "__main__":
    main()
