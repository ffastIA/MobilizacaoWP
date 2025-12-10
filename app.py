import time
import threading
import requests
from flask import Flask, request, jsonify

# 1. INICIALIZAÇÃO DO SERVIDOR
app = Flask(__name__)

# 2. CONFIGURAÇÕES E CONSTANTES GLOBAIS
# ⚠️ VERIFIQUE PELA ÚLTIMA VEZ, COM MÁXIMA ATENÇÃO, SE ESTAS 3 CHAVES ESTÃO CORRETAS
# ⚠️ GARANTA QUE NÃO HÁ ESPAÇOS ANTES OU DEPOIS DAS ASPAS
INSTANCE_ID = "3EB781FA9D2ED1F65488AE390B3F85C2"
TOKEN = "F67179A4911B29C10BEA8F67"
CLIENT_TOKEN = "Fccf33600ef6d4bc1aa5d49ec308fea00S"  # O TOKEN DE SEGURANÇA DA CONTA

BASE_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}"
HEADERS = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}

LISTA_CONTATOS = [
    {"nome": "Fernando", "telefone": "5511982960271"},
    {"nome": "Kaylhane", "telefone": "5585988988446"},
    {"nome": "Beatriz", "telefone": "5585992535934"},

]


# 3. DEFINIÇÃO DAS FUNÇÕES AUXILIARES
def criar_grupo(nome_do_grupo, participantes):
    print(f"2. Criando o grupo '{nome_do_grupo}' no WhatsApp...")
    endpoint = f"{BASE_URL}/create-group"
    payload = {
        "autoInvite": True,
        "groupName": nome_do_grupo,
        "phones": participantes
    }

    try:
        response = requests.post(endpoint, json=payload, headers=HEADERS)
        print(f"🕵️ RESPOSTA BRUTA DO SERVIDOR (Status: {response.status_code}):")
        print(response.text)

        try:
            data = response.json()
            if response.status_code in [200, 201] and 'error' not in data:
                group_id = data.get('phone') or data.get('id')
                if group_id:
                    print(f"✅ Grupo criado com sucesso! ID: {group_id}")
                    return group_id
                else:
                    print("❌ Erro: Resposta de sucesso, mas sem ID.")
                    return None
            else:
                print("❌ Erro retornado pela API (dentro do JSON).")
                return None
        except requests.exceptions.JSONDecodeError:
            print("❌ Erro Crítico: A resposta do servidor não é um JSON válido.")
            return None

    except Exception as e:
        print(f"❌ Erro de conexão geral: {e}")
        return None


def enviar_enquete(group_id, pergunta, opcoes_lista):
    print("4. Enviando a enquete...")
    endpoint = f"{BASE_URL}/send-poll"

    # Transforma a lista ["Opção 1", "Opção 2"] em [{"name": "Opção 1"}, {"name": "Opção 2"}]
    opcoes_formatadas = [{"name": opcao} for opcao in opcoes_lista]

    payload = {
        "phone": group_id,
        "message": pergunta,
        "pollMaxOptions": 1,  # Define que só pode escolher 1 opção
        "poll": opcoes_formatadas
    }

    try:
        response = requests.post(endpoint, json=payload, headers=HEADERS)

        # Vamos usar nosso inspetor de novo para garantir
        print(f"🕵️ RESPOSTA DA ENQUETE (Status: {response.status_code}):")
        print(response.text)

        if response.status_code == 200:
            print("📊 Enquete enviada com sucesso!")
        else:
            print(f"❌ Erro ao enviar enquete.")

    except Exception as e:
        print(f"❌ Erro de conexão ao enviar enquete: {e}")


# 4. DEFINIÇÃO DA FUNÇÃO DE LÓGICA PRINCIPAL (que usa as funções acima)
def executar_logica_de_grupo():
    print("🚀 Automação real iniciada!")
    print("1. Lendo a lista de contatos...")

    # Esta linha usa a variável LISTA_CONTATOS
    todos_os_telefones = [contato['telefone'] for contato in LISTA_CONTATOS]

    # Esta linha usa a função criar_grupo
    group_id = criar_grupo("Grupo Teste Robô Idear", todos_os_telefones)

    if not group_id:
        print("🛑 Processo interrompido. Não foi possível criar o grupo.")
        return

    time.sleep(5)

    # Esta linha usa a função enviar_enquete
    enviar_enquete(group_id, "Funcionou?", ["Sim", "Não", "Com certeza!"])

    print("🏁 Automação real finalizada com sucesso!")


# 5. DEFINIÇÃO DAS ROTAS (ENDPOINTS) DO SERVIDOR
@app.route('/')
def home():
    return "Servidor do Bot Ativo."


@app.route('/iniciar-campanha', methods=['GET'])
def iniciar_campanha():
    # Esta linha usa a função executar_logica_de_grupo
    thread = threading.Thread(target=executar_logica_de_grupo)
    thread.start()
    return jsonify({"status": "sucesso", "mensagem": "Campanha iniciada."})


@app.route('/webhook', methods=['POST'])
def webhook_whatsapp():
    dados = request.json
    print("\n🔔 Webhook recebido:", dados)
    return jsonify({"status": "recebido"}), 200


# 6. EXECUÇÃO DO SERVIDOR
if __name__ == '__main__':
    app.run(port=5000, debug=True)