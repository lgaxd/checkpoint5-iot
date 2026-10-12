"""Gera n8n/workflow.json a partir dos scripts .js. Execute: python n8n/build_workflow.py"""
import json, pathlib

here = pathlib.Path(__file__).parent
analisar = (here / "analisar.js").read_text(encoding="utf-8")
hist_tool = (here / "historico_tool.js").read_text(encoding="utf-8")

SYSTEM = """Você é um agente de manutenção industrial. Você recebe uma análise JÁ CALCULADA de forma determinística (status e problemas). NÃO recalcule nem altere o status e NUNCA invente valores: use somente os dados fornecidos. Se algo faltar, diga que é necessária ajuda humana.

Passos obrigatórios, nesta ordem:
1. Chame a ferramenta consultar_historico (argumento: id da máquina) para contextualizar a tendência.
2. Escreva o relatório no formato exato:
Máquina: <id>
Situação: ALERTA
Problemas identificados:
- <um item por problema>
RECOMENDAÇÃO: <ação objetiva de manutenção, 1 a 2 frases, coerente com os problemas e o histórico>
3. Chame enviar_telegram com o relatório completo (campo mensagem).
4. SOMENTE se o campo canais contiver "email", chame também enviar_email (assunto: "ALERTA <id>: <problemas resumidos>", corpo: o relatório completo).
Não chame nenhuma outra ferramenta. Ao final, responda com o relatório e a lista de ferramentas acionadas."""

PROMPT = "={{ 'Análise determinística recebida:\\n' + JSON.stringify($json, null, 2) }}"


def node(id_, name, type_, ver, pos, params, **extra):
    n = {"id": id_, "name": name, "type": type_, "typeVersion": ver, "position": pos, "parameters": params}
    n.update(extra)
    return n


def link(target, kind="main"):
    return {"node": target, "type": kind, "index": 0}


nodes = [
    node("n1", "MQTT fabrica/motor01/status", "n8n-nodes-base.mqttTrigger", 1, [0, 0],
         {"topics": "fabrica/motor01/status", "options": {"jsonParseBody": True, "onlyMessage": True}},
         credentials={"mqtt": {"id": "cred-mqtt", "name": "Mosquitto local"}}),
    node("n2", "Analisar regras", "n8n-nodes-base.code", 2, [260, 0], {"jsCode": analisar}),
    node("n3", "É ALERTA?", "n8n-nodes-base.if", 2, [520, 0],
         {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                         "conditions": [{"id": "c1", "leftValue": "={{ $json.situacao }}", "rightValue": "ALERTA",
                                         "operator": {"type": "string", "operation": "equals"}}],
                         "combinator": "and"}, "options": {}}),
    node("n4", "Sem ação (NORMAL / dado inválido)", "n8n-nodes-base.noOp", 1, [780, 200], {}),
    node("n5", "Agente de manutenção", "@n8n/n8n-nodes-langchain.agent", 1.7, [780, -80],
         {"promptType": "define", "text": PROMPT, "options": {"systemMessage": SYSTEM, "maxIterations": 8}}),
    node("n6", "Gemini", "@n8n/n8n-nodes-langchain.lmChatGoogleGemini", 1, [700, 300],
         {"modelName": "models/__GEMINI_MODEL__", "options": {"temperature": 0.2}},
         credentials={"googlePalmApi": {"id": "cred-gemini", "name": "Gemini"}}),
    node("n7", "Cliente MCP", "@n8n/n8n-nodes-langchain.mcpClientTool", 1, [920, 300],
         {"sseEndpoint": "http://localhost:5678/mcp/motor-mcp/sse",
          "authentication": "none", "include": "all"}),
    node("n8", "Servidor MCP", "@n8n/n8n-nodes-langchain.mcpTrigger", 1, [0, 500],
         {"path": "motor-mcp"}, webhookId="motor-mcp-0001"),
    node("n9", "enviar_telegram", "n8n-nodes-base.httpRequestTool", 4.2, [-300, 760],
         {"toolDescription": "Envia uma mensagem de alerta ao operador no Telegram. Argumento: mensagem (texto completo).",
          "method": "POST",
          "url": "=https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage",
          "sendBody": True, "specifyBody": "json",
          "jsonBody": "={{ JSON.stringify({ chat_id: $env.TELEGRAM_CHAT_ID, text: $fromAI('mensagem', 'Texto completo do alerta', 'string') }) }}",
          "options": {}}),
    node("n10", "enviar_email", "n8n-nodes-base.emailSendTool", 2.1, [0, 760],
         {"descriptionType": "manual",
          "toolDescription": "Envia relatório detalhado de alerta por e-mail. Argumentos: assunto e corpo.",
          "fromEmail": "={{ $env.SMTP_USER }}", "toEmail": "={{ $env.EMAIL_TO }}",
          "subject": "={{ $fromAI('assunto', 'Assunto do e-mail', 'string') }}",
          "emailFormat": "text",
          "text": "={{ $fromAI('corpo', 'Corpo do relatório de alerta', 'string') }}",
          "options": {}},
         credentials={"smtp": {"id": "cred-smtp", "name": "SMTP Gmail"}}),
    node("n11", "consultar_historico", "@n8n/n8n-nodes-langchain.toolCode", 1.1, [300, 760],
         {"name": "consultar_historico",
          "description": "Consulta o histórico recente (últimas 10 leituras, média e desvio padrão da temperatura) de uma máquina. Entrada: id da máquina, ex.: MOTOR_01.",
          "language": "javaScript", "jsCode": hist_tool}),
]

connections = {
    "MQTT fabrica/motor01/status": {"main": [[link("Analisar regras")]]},
    "Analisar regras": {"main": [[link("É ALERTA?")]]},
    "É ALERTA?": {"main": [[link("Agente de manutenção")], [link("Sem ação (NORMAL / dado inválido)")]]},
    "Gemini": {"ai_languageModel": [[link("Agente de manutenção", "ai_languageModel")]]},
    "Cliente MCP": {"ai_tool": [[link("Agente de manutenção", "ai_tool")]]},
}
for tool in ("enviar_telegram", "enviar_email", "consultar_historico"):
    connections[tool] = {"ai_tool": [[link("Servidor MCP", "ai_tool")]]}

wf = {"id": "motor-monitor", "name": "Monitoramento Inteligente - MOTOR_01", "active": False,
      "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}}
(here / "workflow.json").write_text(json.dumps(wf, ensure_ascii=False, indent=1), encoding="utf-8")
print("workflow.json gerado")
