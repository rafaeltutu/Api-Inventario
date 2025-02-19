from flask import Flask, request, jsonify
import paramiko
from datetime import datetime
from io import StringIO

app = Flask(__name__)

# Configurações do servidor SFTP
SFTP_HOST = "sftp.inforcloudsuite.com"
SFTP_PORT = 22
SFTP_USER = "eletrofrio_prd_ftp"
SFTP_PASSWORD = "wn#vEK!&43L,RQ@"

# Diretório onde os arquivos serão salvos no servidor SFTP
SFTP_DIR = "/PRD/Inventario/PROCESS"


def generate_filename(index):
    """Gera um nome de arquivo baseado na data, hora e índice do item."""
    now = datetime.now()
    return f"{now.strftime('%Y%m%d_%H%M%S')}_{index + 1}.txt"  # Exemplo: 20231128_153045_1.txt


def upload_to_sftp(filename, content):
    """Faz upload de um arquivo para o servidor SFTP."""
    try:
        # Configuração do cliente SFTP
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)

        sftp = paramiko.SFTPClient.from_transport(transport)

        # Verifica se o diretório existe no servidor e cria, se necessário
        try:
            sftp.chdir(SFTP_DIR)
        except IOError:
            # Diretório não existe, tenta criá-lo
            path_parts = SFTP_DIR.split("/")
            current_path = ""
            for part in path_parts:
                if part:  # Ignora strings vazias
                    current_path += f"/{part}"
                    try:
                        sftp.chdir(current_path)
                    except IOError:
                        sftp.mkdir(current_path)
                        sftp.chdir(current_path)

        # Cria o arquivo remoto
        remote_file_path = f"{SFTP_DIR}/{filename}"
        file_buffer = StringIO(content)

        # Envia o arquivo para o servidor SFTP
        with sftp.file(remote_file_path, "w") as remote_file:
            remote_file.write(file_buffer.getvalue())

        # Fecha a conexão
        sftp.close()
        transport.close()

        return {"status": "success", "message": f"File {filename} uploaded successfully to {SFTP_DIR}."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.route("/upload", methods=["POST"])
def upload():
    """Endpoint para receber os dados e salvar no SFTP."""
    try:
        # Recebe os dados do corpo da requisição
        data = request.json

        # Validação básica do corpo da requisição
        if not data or "items" not in data:
            return jsonify({"status": "error", "message": "Invalid data format. Expected JSON with 'items'."}), 400
        if not isinstance(data["items"], list):
            return jsonify({"status": "error", "message": "'items' must be a list."}), 400

        # Lista de itens a serem processados
        items = data["items"]

        # Armazena o resultado do upload de cada arquivo
        results = []

        # Para cada item, gera um arquivo e faz o upload
        for index, item in enumerate(items):
            if not isinstance(item, str):
                results.append({"status": "error", "message": f"Invalid item at index {index}. Must be a string."})
                continue

            filename = generate_filename(index)  # Gera o nome único do arquivo
            response = upload_to_sftp(filename, item)  # Faz o upload do arquivo
            results.append(response)  # Armazena o resultado

        # Retorna os resultados para o cliente
        return jsonify(results), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
