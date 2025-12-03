import os
import time
from track_yolo import run_recognize

PASTA_VIDEOS = r"./uploads/"  # <- ALTERE AQUI

INTERVALO_VERIFICACAO = 5  # em segundos, tempo entre varreduras
TEMPO_ESPERA_ARQUIVO = 2   # segundos para verificar se o arquivo terminou de ser escrito
NUM_CHECAGENS_TAMANHO = 3  # quantas vezes conferir se o tamanho estabilizou


def arquivo_pronto(caminho_arquivo: str) -> bool:
    """
    Verifica se o arquivo terminou de ser escrito:
    confere algumas vezes se o tamanho do arquivo não muda.
    """
    tamanho_anterior = -1

    for _ in range(NUM_CHECAGENS_TAMANHO):
        try:
            tamanho_atual = os.path.getsize(caminho_arquivo)
        except FileNotFoundError:
            # Pode ter sido removido no meio do processo
            return False

        if tamanho_atual == tamanho_anterior:
            # Tamanho estabilizou, provavelmente terminou de ser escrito
            return True

        tamanho_anterior = tamanho_atual
        time.sleep(TEMPO_ESPERA_ARQUIVO)

    # Se chegou aqui, o tamanho não estabilizou
    return False


def enviar_arquivo(caminho_arquivo: str) -> bool:
    """
    Envia o arquivo .mp4 para a URL_DESTINO via HTTP POST.
    Retorna True se deu certo (status 2xx), False caso contrário.
    """
    nome_arquivo = os.path.basename(caminho_arquivo)
    print(f"Enviando arquivo: {nome_arquivo}")

    try:
        with open(caminho_arquivo, "rb") as f:
            files = {"file": (nome_arquivo, f, "video/mp4")}
            run_recognize()
            return True


    except Exception as e:
        print(f"✗ Exceção ao enviar {nome_arquivo}: {e}")
        return False


def remover_arquivo(caminho_arquivo: str) -> None:
    """
    Remove o arquivo do disco.
    """
    try:
        os.remove("uploads\saida.mp4")
        print(f"\nArquivo uploads\saida.mp4' removido com sucesso!")
    except Exception as e:
        print(f"\nErro ao remover arquivo: {e}")


def monitorar_pasta():
    print(f"Monitorando pasta: {PASTA_VIDEOS}")

    while True:
        try:
            # Varre todos os arquivos na pasta
            for entrada in os.scandir(PASTA_VIDEOS):
                if not entrada.is_file():
                    continue

                if not entrada.name.lower().endswith(".mp4"):
                    continue

                caminho_video = entrada.path

                # Verificar se o arquivo terminou de ser escrito
                if not arquivo_pronto(caminho_video):
                    print(f"Arquivo ainda sendo escrito, pulando por enquanto: {entrada.name}")
                    continue

                # Tenta enviar
                if enviar_arquivo(caminho_video):
                    # Se deu certo, remove
                    remover_arquivo(caminho_video)

            # Espera um pouco antes da próxima varredura
            time.sleep(INTERVALO_VERIFICACAO)

        except KeyboardInterrupt:
            print("\nEncerrando monitoramento...")
            break
        except Exception as e:
            print(f"Erro no loop de monitoramento: {e}")
            # Evita travar o script por um erro isolado
            time.sleep(INTERVALO_VERIFICACAO)


if __name__ == "__main__":
    monitorar_pasta()
