import time
import threading
from flask import Flask, request, jsonify

# Cria a instância do nosso servidor web
app = Flask(__name__)


# --- LÓGICA DO NOSSO BOT (Ainda simulada) ---

def executar_logica_de_grupo():
    """
    Função que simula o trabalho pesado: criar grupo, adicionar pessoas, etc.
    Ela vai rodar em "segundo plano" (thread) para não travar o servidor.
    """
    print("🚀 Automação iniciada! Simulação em andamento...")

    print("1. Lendo a planilha (simulado)...")
    time.sleep(2)  # Pausa para simular a leitura

    print("2. Criando o grupo no WhatsApp (simulado)...")
    time.sleep(3)  # Pausa para simular a criação

    print("3. Adicionando participantes (simulado)...")
    for i in range(1, 4):
        print(f"   - Adicionando participante {i}...")
        time.sleep(5)  # Pausa longa para simular o delay anti-ban

    print("4. Enviando a enquete (simulado)...")
    time.sleep(2)

    print("🏁 Automação simulada finalizada com sucesso!")


# --- ROTAS DA NOSSA APLICAÇÃO (ENDPOINTS) ---

@app.route('/')
def home():
    """Esta função roda quando alguém acessa a página inicial."""
    return "Servidor do Bot Ativo. Pronto para receber ordens! ✅"


@app.route('/iniciar-campanha', methods=['GET'])
def iniciar_campanha():
    """
    Este é o nosso "gatilho". Quando acessado, dispara a lógica do bot.
    """
    print("🟢 Rota /iniciar-campanha acessada! Disparando a automação...")

    # Criamos uma 'thread' para executar a função pesada sem travar a resposta da página.
    thread = threading.Thread(target=executar_logica_de_grupo)
    thread.start()

    # Retornamos uma resposta imediata para o usuário.
    return jsonify(
        {"status": "sucesso", "mensagem": "Campanha iniciada em segundo plano. Verifique os logs do PyCharm."})


@app.route('/webhook', methods=['POST'])
def webhook_whatsapp():
    """
    Este endpoint vai receber os dados que a API do WhatsApp enviar (webhooks).
    """
    print("\n🔔 Webhook recebido!")

    # O método 'request.json' pega os dados que chegam no corpo da requisição.
    dados = request.json

    # Apenas imprimimos os dados recebidos no console por enquanto.
    print("Dados recebidos:", dados)

    # É uma boa prática sempre responder com um status de sucesso.
    return jsonify({"status": "recebido"}), 200


# Esta parte faz o servidor rodar quando executamos o arquivo
if __name__ == '__main__':
    app.run(port=5000, debug=True)
