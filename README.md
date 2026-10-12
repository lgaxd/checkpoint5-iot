# Checkpoint 5 – Monitoramento Inteligente de uma Máquina Industrial

**FIAP – Graduação em Tecnologia | IoT + Agentes de IA**
**Aluno responsável:** Lucas Grillo Alcântara – RM 561413
**Vídeo de demonstração:** [ADICIONAR LINK DO YOUTUBE AQUI](https://www.youtube.com/watch?v=SEU_VIDEO_ID)

---

## 1. Visão geral

Sistema que recebe, via **MQTT**, os dados de sensores de um motor industrial (`MOTOR_01`), classifica a situação da máquina como **NORMAL** ou **ALERTA**, identifica quais condições foram violadas e aciona um **agente de IA** que gera uma recomendação e notifica a equipe de manutenção por **Telegram** e **e-mail**, usando ferramentas expostas por um **servidor MCP**.

```
simulador.py ──MQTT──▶ Mosquitto ──▶ n8n
                                      │ 1. MQTT Trigger  (tópico fabrica/motor01/status)
                                      │ 2. Code: regras DETERMINÍSTICAS + validação + histórico JSON
                                      │ 3. IF situacao == ALERTA
                                      │ 4. Agente de IA (Gemini) ──MCP Client──▶ Servidor MCP (n8n)
                                      │                                           ├─ consultar_historico
                                      │                                           ├─ enviar_telegram
                                      │                                           └─ enviar_email
```

### Decisões de projeto

- **Status e problemas são calculados em código determinístico** (nó *Analisar regras*). O LLM **não** decide o status: ele apenas escreve a recomendação e aciona as ferramentas. Isso torna os testes reproduzíveis e evita alucinações em decisões críticas.
- **Validação de dados:** campo ausente, não numérico ou fora de faixa física (ex.: fator de potência fora de 0–1) resulta em `DADO_INVALIDO`; o agente não é acionado.
- **Histórico simples em JSON** (`data/historico.json`), consultado pelo agente para contextualizar a tendência (média e desvio padrão da temperatura).
- O LLM **não substitui** o CLP/relé de segurança: o sistema atua na gestão e na predição, nunca no bloqueio de segurança crítico.

## 2. Regras de análise e roteamento

| Condição de alerta | Regra |
|---|---|
| Temperatura elevada | `temperatura > 80 °C` |
| Vibração elevada | `vibracao > 7` |
| Fator de potência baixo | `fator_potencia < 0,70` |
| Produção abaixo do esperado | `taxa_producao < 80% da taxa_producao_esperada` |

| Situação | Ação |
|---|---|
| NORMAL | Nenhuma ação; fluxo encerrado |
| ALERTA por temperatura/vibração | Telegram |
| ALERTA por produção/fator de potência | Telegram + e-mail |
| DADO_INVALIDO | Nenhuma ação; agente não é acionado |

Formato da mensagem recebida (tópico `fabrica/motor01/status`):

```json
{ "id_maquina": "MOTOR_01", "temperatura": 86.5, "vibracao": 8.2, "tensao": 220,
  "corrente": 18.5, "fator_potencia": 0.62, "taxa_producao": 42, "taxa_producao_esperada": 60 }
```

Saída do agente (enviada por Telegram/e-mail):

```
Máquina: MOTOR_01
Situação: ALERTA
Problemas identificados:
- Temperatura elevada
- Vibração elevada
RECOMENDAÇÃO: Realizar inspeção do motor e verificar as condições de funcionamento.
```

## 3. Tecnologias

MQTT (Eclipse Mosquitto) · n8n 1.123 (orquestrador, servidor/cliente MCP) · Google Gemini (`gemini-3.5-flash`) · Telegram Bot API · SMTP (Gmail) · Docker Compose · Python (simulador, `paho-mqtt`).

## 4. Pré-requisitos

- Docker e Docker Compose (os testes foram feitos no WSL/Ubuntu).
- Python 3.10+ no host que executa o simulador.
- Chave de API do Gemini (https://aistudio.google.com/apikey).
- Bot do Telegram (via @BotFather) e o seu `chat_id`.
- Conta Gmail com **senha de app**.

## 5. Configuração

1. Copie `.env.example` para `.env` e preencha:

   | Variável | Descrição |
   |---|---|
   | `GEMINI_API_KEY` | Chave da API do Gemini |
   | `GEMINI_MODEL` | Modelo (padrão `gemini-3.5-flash`) |
   | `TELEGRAM_BOT_TOKEN` | Token fornecido pelo @BotFather |
   | `TELEGRAM_CHAT_ID` | Seu chat id: envie uma mensagem ao bot e abra `https://api.telegram.org/bot<TOKEN>/getUpdates`; o valor está em `message.chat.id` (não use o id do bot) |
   | `SMTP_HOST` / `SMTP_PORT` | `smtp.gmail.com` / `465` |
   | `SMTP_USER` / `SMTP_PASS` | Conta Gmail e senha de app |
   | `EMAIL_TO` | Destinatário dos relatórios |

2. Instale a dependência do simulador: `pip install -r requirements.txt`

## 6. Execução

No WSL/terminal, na pasta do projeto:

```bash
chmod 777 data            # o contêiner do n8n grava o histórico aqui
docker compose up -d
docker compose logs -f n8n
```

Acesse http://localhost:5678 e crie a conta de dono (primeiro acesso). O workflow **Monitoramento Inteligente - MOTOR_01** e as credenciais (MQTT, Gemini, SMTP) são importados e ativados automaticamente a partir do `.env`. Se o workflow aparecer inativo, ative-o (botão *Active*) e execute `docker compose restart n8n`.

> Alterou o `.env`? Recrie o contêiner: `docker compose up -d --force-recreate n8n`.

## 7. Testes

Execute no PowerShell, na pasta do projeto, com cerca de 1 minuto entre os testes (a cota gratuita do Gemini pode retornar `429`):

| # | Comando | Entrada principal | Resultado esperado |
|---|---------|-------------------|--------------------|
| 1 | `python simulador.py normal` | valores dentro dos limites | **NORMAL** – fluxo termina, nenhuma mensagem |
| 2 | `python simulador.py temp_vibracao` | temperatura 86,5; vibração 8,2 | **ALERTA** (temperatura + vibração) – **Telegram** |
| 3 | `python simulador.py producao_fp` | fator de potência 0,62; produção 42/60 | **ALERTA** (fator de potência + produção) – **Telegram + e-mail** |
| 4 | `python simulador.py normal --temperatura abc` | dado corrompido | **DADO_INVALIDO** – agente não acionado |

Qualquer campo pode ser sobrescrito, por exemplo `python simulador.py normal --vibracao 9`. Os resultados de cada execução ficam na aba *Executions* do n8n.

## 8. Estrutura do repositório

| Arquivo | Função |
|---|---|
| `docker-compose.yml`, `mosquitto/mosquitto.conf` | Infraestrutura (broker MQTT e n8n) |
| `n8n/workflow.json` | Workflow do n8n (gerado por `n8n/build_workflow.py`) |
| `n8n/analisar.js` | Regras determinísticas, validação e histórico |
| `n8n/historico_tool.js` | Ferramenta MCP `consultar_historico` |
| `n8n/init.sh`, `n8n/prepare.js` | Importam credenciais (do `.env`) e workflow ao iniciar o contêiner |
| `simulador.py` | Simulador de sensores (publica no tópico MQTT) |
| `.env.example` | Modelo das variáveis de ambiente |

## 9. Cuidados e limitações

- O `.env` contém segredos e **não** é versionado.
- Em uso industrial real, o agente de IA deve apoiar a gestão e a predição; funções de segurança continuam sob controle determinístico (CLP/relé de segurança).
- O n8n é executado com acesso a variáveis de ambiente nos nós (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`), configuração adequada a ambiente local de laboratório.
- Versões do n8n anteriores a 1.123 falham com modelos Gemini 3.x em chamadas de ferramenta (erro `thought_signature`).
