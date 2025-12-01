import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# Pasta onde os vídeos serão salvos
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Tamanho máximo do upload (ex.: 500 MB)
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


@app.route("/upload", methods=["POST"])
def upload_video():
    # Verifica se o campo "video" está na requisição
    if "video" not in request.files:
        return jsonify({"erro": 'Nenhum arquivo enviado. Use o campo "video".'}), 400

    file = request.files["video"]

    # Verifica se o arquivo tem nome
    if file.filename == "":
        return jsonify({"erro": "Arquivo sem nome."}), 400

    # Verifica se é .mp4
    if not file.filename.lower().endswith(".mp4"):
        return jsonify({"erro": "Apenas arquivos .mp4 são aceitos."}), 400

    # Garante que o nome do arquivo é seguro
    filename = secure_filename(file.filename)

    # Caminho final do arquivo salvo
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    # Salva o arquivo
    file.save(save_path)

    # Aqui você pode chamar sua lógica de detecção/corte de vídeo, por exemplo:
    # processar_video(save_path)

    return jsonify({
        "mensagem": "Upload feito com sucesso.",
        "arquivo_salvo_em": save_path
    }), 200


if __name__ == "__main__":
    # Servidor ouvindo em todas as interfaces, porta 8000
    app.run(host="0.0.0.0", port=8000, debug=True)
