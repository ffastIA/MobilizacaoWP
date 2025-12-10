import time
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURAÇÕES DA Z-API ---
# ⚠️ FAÇA UMA VERIFICAÇÃO DETALHADA AQUI. UM ESPAÇO A MAIS PODE CAUSAR O ERRO.
INSTANCE_ID = "3EB781FA9D2ED1F65488AE390B3F85C2"
TOKEN = "F67179A4911B29C10BEA8F67"
CLIENT_TOKEN = "F81e975abedfa4db7b71b0de1b141a07fS"

# --- CONSTANTES ---
BASE_URL = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}"
HEADERS = {"Client-Token": CLIENT_TOKEN, "Content-Type": "application/json"}

# --- LISTA DE CONTATOS ---
LISTA_CONTATOS = [
    {"nome": "Meu Numero Pessoal", "telefone": "5511999999999"},
    {"nome": "Contato Teste 2", "telefone": "5511888888888"}
]


# --- FUNÇÕES REAIS DO WHATSAPP ---

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

        # --- NOSSO NOVO INSPETOR ---
        print(f"🕵️ RESPOSTA BRUTA DO SERVIDOR (Status: {response.status_code}):")
        print(response.text)
        # --- FIM DO INSPETOR ---

        try:
            data = response.json()

            if response.status_code in [200, 201] and 'error' not in data:
                group_id = data.get('phone') or data.get('id')
                if group_id:
                    print(f"✅ Grupo criado com sucesso! ID: {group_id}")
                    return group_id
                else:
                    print("❌ Erro Inesperado: Resposta de sucesso, mas sem ID.")
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


# (O restante do código não precisa de alteração agora)
def enviar_enquete(group_id, pergunta, opcoes):
    print("Enviando a enquete...")
    endpoint = f"{BASE_URL}/send-poll"
    # ... (código da enquete) ...


def executar_logica_de_grupo():
    print("🚀 Automação real iniciada!")
    print("1. Lendo a lista de contatos...")
    todos_os_telefones = [contato['telefone'] for contato in LISTA_CONTATOS]
    group_id = criar_grupo("Grupo Teste Final", todos_os_telefones)

    if not group_id:
        print("🛑 Processo interrompido. Não foi possível criar o grupo.")
        return

    time.sleep(5)
    enviar_enquete(group_id, "Funcionou?", ["Sim", "Não", "Com certeza!"])
    print("🏁 Automação real finalizada com sucesso!")


# --- ROTAS E EXECUÇÃO ---
@app.route('/')
def home():
    return "Servidor do Bot Ativo."


@app.route('/iniciar-campanha', methods=['GET'])
def iniciar_campanha():
    thread = threading.Thread(target=executar_logica_de_grupo)
    thread.start()
    return jsonify({"status": "sucesso", "mensagem": "Campanha iniciada."})


@app.route('/webhook', methods=['POST'])
def webhook_whatsapp():
    dados = request.json
    print("\n🔔 Webhook recebido:", dados)
    return jsonify({"status": "recebido"}), 200


if __name__ == '__main__':
    app.run(port=5000, debug=True)