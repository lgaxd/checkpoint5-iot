#!/bin/sh
# Gera credenciais a partir do .env, importa credenciais + workflow e inicia o n8n.
set -e
node /seed/prepare.js /tmp/credentials.json /tmp/workflow.json
n8n import:credentials --input=/tmp/credentials.json
n8n import:workflow --input=/tmp/workflow.json
n8n update:workflow --id=motor-monitor --active=true || true
exec n8n start
