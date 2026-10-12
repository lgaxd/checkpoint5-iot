"""Simulador de sensores do MOTOR_01: publica uma leitura via MQTT.

Uso:
    python simulador.py normal
    python simulador.py temp_vibracao
    python simulador.py producao_fp
    python simulador.py todos            # envia os 3, com pausa entre eles
    python simulador.py normal --temperatura 85   # sobrescreve qualquer campo
"""
import argparse
import json
import time

import paho.mqtt.client as mqtt

TOPICO = "fabrica/motor01/status"

BASE = {
    "id_maquina": "MOTOR_01",
    "temperatura": 65.0,
    "vibracao": 3.2,
    "tensao": 220,
    "corrente": 12.4,
    "fator_potencia": 0.91,
    "taxa_producao": 58,
    "taxa_producao_esperada": 60,
}

CENARIOS = {
    # nenhuma condição de alerta
    "normal": {},
    # alerta por temperatura/vibração -> Telegram
    "temp_vibracao": {"temperatura": 86.5, "vibracao": 8.2, "corrente": 15.1},
    # alerta por produção/fator de potência -> Telegram + e-mail
    "producao_fp": {"fator_potencia": 0.62, "corrente": 18.5, "taxa_producao": 42},
}


def publicar(cliente, nome, overrides):
    payload = {**BASE, **CENARIOS[nome], **overrides}
    info = cliente.publish(TOPICO, json.dumps(payload), qos=1)
    info.wait_for_publish()
    print(f"[{nome}] publicado em {TOPICO}:\n{json.dumps(payload, indent=2)}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cenario", choices=[*CENARIOS, "todos"])
    p.add_argument("--host", default="localhost")
    p.add_argument("--porta", type=int, default=1883)
    p.add_argument("--pausa", type=int, default=20, help="segundos entre cenários em 'todos'")
    for campo, valor in BASE.items():
        p.add_argument(f"--{campo}", type=type(valor) if campo != "id_maquina" else str)
    args = p.parse_args()

    overrides = {c: getattr(args, c) for c in BASE if getattr(args, c) is not None}

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cliente.connect(args.host, args.porta)
    cliente.loop_start()
    nomes = list(CENARIOS) if args.cenario == "todos" else [args.cenario]
    for i, nome in enumerate(nomes):
        publicar(cliente, nome, overrides)
        if i < len(nomes) - 1:
            time.sleep(args.pausa)
    cliente.loop_stop()
    cliente.disconnect()


if __name__ == "__main__":
    main()
