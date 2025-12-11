import time
import threading
import re
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify
from datetime import datetime

# ==============================================================================
# ⚙️ CONFIGURAÇÕES GERAIS
# ==============================================================================

# --- Credenciais Z-API ---
INSTANCE_ID = "3EB781FA9D2ED1F65488AE390B3F85C2"
TOKEN = "F67179A4911B29C10BEA8F67"
CLIENT_TOKEN = "Fccf33600ef6d4bc1aa5d49ec308fea00S"  # O TOKEN DE SEGURANÇA DA CONTA

ARQUIVO_CREDENCIAIS = 'credentials.json'  # O arquivo JSON baixado do Google
NOME_PLANILHA = 'Mobilizacao WP'
NOME_ABA = 'PG1'

# --- Parâmetros de Automação ---
DELAY_ENTRE_CONTATOS = 15  # Segundos (Anti-Ban)
TERMO_FIM_GRUPO = "fim"  # Palavra-chave para fechar o grupo e enviar enquete
OPCOES_ENQUETE = ["SIM", "NÃO"]


# ==============================================================================
# 🔧 CLASSE PRINCIPAL DE AUTOMAÇÃO
# ==============================================================================

class WhatsAppAutomation:
    def __init__(self):
        self.base_url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}"
        self.headers = {
            "Client-Token": CLIENT_TOKEN,
            "Content-Type": "application/json"
        }
        self.sheet = None
        self.current_group_id = None
        self.current_group_name = None
        self.connect_sheets()

    def connect_sheets(self):
        """Conecta ao Google Sheets e autentica."""
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENCIAIS, scope)
            client = gspread.authorize(creds)
            self.sheet = client.open(NOME_PLANILHA).worksheet(NOME_ABA)
            print("✅ Conectado ao Google Sheets com sucesso.")
        except Exception as e:
            print(f"❌ Erro ao conectar no Google Sheets: {e}")
            exit()

    def validar_telefone(self, telefone):
        """Valida se o telefone tem 13 dígitos numéricos."""
        if not telefone:
            return False
        # Remove qualquer caracter que não seja número
        limpo = re.sub(r'\D', '', str(telefone))
        # Verifica se tem exatamente 13 dígitos
        return bool(re.match(r'^\d{13}$', limpo))

    # --- MÉTODOS DA API Z-API ---

    def api_criar_grupo(self, nome_grupo, primeiro_participante):
        """Cria um grupo na Z-API."""
        endpoint = f"{self.base_url}/create-group"
        payload = {
            "groupName": nome_grupo,
            "phones": [primeiro_participante],
            "autoInvite": True
        }
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            if response.status_code in [200, 201]:
                data = response.json()
                return data.get('phone') or data.get('id')
            else:
                print(f"❌ Erro API Criar Grupo: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Exceção API Criar Grupo: {e}")
            return None

    def api_adicionar_participante(self, group_id, telefone):
        """Adiciona um participante a um grupo existente."""
        endpoint = f"{self.base_url}/update-participant"  # Endpoint correto para add/remove
        payload = {
            "phone": group_id,
            "participant": telefone,
            "action": "add"
        }
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Erro ao adicionar participante: {e}")
            return False

    def api_enviar_enquete(self, group_id, titulo):
        """Envia a enquete para o grupo."""
        endpoint = f"{self.base_url}/send-poll"
        opcoes_formatadas = [{"name": op} for op in OPCOES_ENQUETE]

        payload = {
            "phone": group_id,
            "message": titulo,
            "pollMaxOptions": 1,
            "poll": opcoes_formatadas
        }
        try:
            requests.post(endpoint, json=payload, headers=self.headers)
            print(f"📊 Enquete '{titulo}' enviada para o grupo {group_id}")
            return True
        except Exception as e:
            print(f"❌ Erro ao enviar enquete: {e}")
            return False

    # --- LÓGICA DE PROCESSAMENTO ---

    def processar_linha(self, index, row):
        """Processa uma única linha da planilha."""
        # Mapeamento de colunas (ajuste conforme sua planilha, index 0-based)
        # ID=0, Grupo=1, Nome=2, Telefone=3, Situacao=4, Contato=5, Enquete=6

        grupo_nome = row[1]
        nome_contato = row[2]
        telefone = str(row[3]).strip()
        situacao_atual = row[4]

        # Validação de Telefone
        if not self.validar_telefone(telefone) and grupo_nome.lower() != TERMO_FIM_GRUPO:
            print(f"⚠️ Linha {index}: Telefone inválido '{telefone}'. Pulando.")
            return

        # Lógica de "FIM" - Enviar Enquete
        if grupo_nome.lower() == TERMO_FIM_GRUPO:
            if self.current_group_id:
                titulo_enquete = row[6] if len(row) > 6 else "Responda nossa pesquisa:"
                print(f"🏁 Termo 'fim' encontrado. Enviando enquete para {self.current_group_name}...")
                self.api_enviar_enquete(self.current_group_id, titulo_enquete)

                # Reseta para o próximo grupo
                self.current_group_id = None
                self.current_group_name = None

                # Atualiza planilha indicando fim processado
                self.sheet.update_cell(index, 5, "Enquete Enviada")  # Coluna Situação
            return

        # Lógica de Criação/Adição
        if not situacao_atual:  # Se "Situação do grupo" estiver vazia

            # Caso 1: Novo Grupo (diferente do atual em memória)
            if grupo_nome != self.current_group_name:
                print(f"🆕 Iniciando novo grupo: {grupo_nome}")
                novo_id = self.api_criar_grupo(grupo_nome, telefone)

                if novo_id:
                    self.current_group_id = novo_id
                    self.current_group_name = grupo_nome

                    # Atualiza status na planilha
                    self.sheet.update_cell(index, 5, "Criado")  # Coluna Situação
                    self.sheet.update_cell(index, 6, "Inserido")  # Coluna Contato
                    print(f"✅ Grupo criado e {nome_contato} adicionado.")
                else:
                    print("❌ Falha crítica ao criar grupo. Pulando linha.")

            # Caso 2: Grupo já existe (é o atual), apenas adicionar contato
            elif self.current_group_id:
                print(f"➕ Adicionando {nome_contato} ao grupo {grupo_nome}...")
                sucesso = self.api_adicionar_participante(self.current_group_id, telefone)

                if sucesso:
                    self.sheet.update_cell(index, 6, "Inserido")  # Coluna Contato
                    self.sheet.update_cell(index, 5, "Criado")  # Mantém consistência
                    print(f"✅ {nome_contato} inserido.")
                else:
                    print(f"❌ Falha ao inserir {nome_contato}.")

            # Delay de segurança
            print(f"⏳ Aguardando {DELAY_ENTRE_CONTATOS}s...")
            time.sleep(DELAY_ENTRE_CONTATOS)

    def loop_principal(self):
        """Loop infinito que verifica a planilha periodicamente."""
        print("🚀 Worker de processamento iniciado...")
        while True:
            try:
                # Recarrega dados para pegar atualizações
                all_values = self.sheet.get_all_values()

                # Pula o cabeçalho (começa do index 1 -> linha 2)
                for i, row in enumerate(all_values[1:], start=2):
                    # Verifica se a coluna "Situação do grupo" (index 4) está vazia
                    if len(row) > 4 and row[4] == "":
                        self.processar_linha(i, row)

                print("💤 Ciclo concluído. Aguardando 60s para próxima verificação...")
                time.sleep(60)

            except Exception as e:
                print(f"❌ Erro no loop principal: {e}")
                time.sleep(60)  # Espera antes de tentar de novo

    def atualizar_resposta_planilha(self, telefone_participante, resposta_voto, nome_grupo_webhook):
        """Busca Telefone + Grupo e atualiza apenas a linha correta."""
        try:
            # Limpa o telefone do webhook (deixa só números)
            tel_webhook_limpo = re.sub(r'\D', '', str(telefone_participante))

            # Baixa todos os dados da planilha de uma vez (Mais rápido e econômico)
            # Retorna uma lista de listas: [['ID', 'Grupo', 'Nome'...], ['1', 'PRG-0125', ...]]
            todos_dados = self.sheet.get_all_values()

            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            linha_para_atualizar = -1

            # Percorre linha por linha procurando a combinação exata
            # Começamos do index 0, mas para o gspread a linha 1 é o cabeçalho.
            for i, linha in enumerate(todos_dados):
                # Pula cabeçalho ou linhas vazias
                if i == 0 or len(linha) < 4:
                    continue

                # Coluna B (index 1) = Grupo
                # Coluna D (index 3) = Telefone
                grupo_planilha = linha[1]
                tel_planilha_limpo = re.sub(r'\D', '', str(linha[3]))

                # A LÓGICA DE OURO: Verifica se O GRUPO bate E o TELEFONE bate
                if tel_planilha_limpo == tel_webhook_limpo and grupo_planilha == nome_grupo_webhook:
                    linha_para_atualizar = i + 1  # +1 porque gspread conta a partir de 1
                    break  # Achamos! Pode parar de procurar.

            if linha_para_atualizar != -1:
                # Atualiza Resposta (Coluna H -> 8) e Data-Hora (Coluna I -> 9)
                self.sheet.update_cell(linha_para_atualizar, 8, resposta_voto)
                self.sheet.update_cell(linha_para_atualizar, 9, timestamp)
                print(f"💾 Voto salvo na linha {linha_para_atualizar} (Grupo: {nome_grupo_webhook})")
            else:
                print(f"⚠️ Não encontrei o par Telefone {tel_webhook_limpo} + Grupo {nome_grupo_webhook} na planilha.")

        except Exception as e:
            print(f"❌ Erro ao atualizar planilha: {e}")

# ==============================================================================
# 🌐 SERVIDOR FLASK (WEBHOOK)
# ==============================================================================

app = Flask(__name__)
bot = WhatsAppAutomation()


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json

        if 'pollVote' in data:
            voter = data.get('participantPhone')
            grupo_origem = data.get('chatName')  # <--- CAPTURAMOS O NOME DO GRUPO AQUI

            poll_data = data.get('pollVote')
            options = poll_data.get('options', [])

            if voter and options and grupo_origem:
                resposta = options[0].get('name')
                print(f"🗳️ Voto: {voter} | Grupo: {grupo_origem} | Escolha: {resposta}")

                # Passamos o grupo_origem como argumento extra
                threading.Thread(target=bot.atualizar_resposta_planilha, args=(voter, resposta, grupo_origem)).start()
            else:
                print("⚠️ Dados incompletos no webhook (sem remetente ou grupo).")

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return jsonify({"status": "error"}), 500


# ==============================================================================
# 🚀 INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    # Inicia a thread de processamento da planilha (Worker)
    worker_thread = threading.Thread(target=bot.loop_principal)
    worker_thread.daemon = True  # Morre se o programa principal fechar
    worker_thread.start()

    # Inicia o servidor Flask (Main Thread)
    print("🌐 Servidor Webhook rodando na porta 5000...")
    app.run(port=5000, debug=False)