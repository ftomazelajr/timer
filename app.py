from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
import paho.mqtt.client as mqtt
import json
import random
import os

app = Flask(__name__)
# Permite ler o IP real se estiver atrás de proxy (Render/Cloudflare)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

# --- VARIÁVEL GLOBAL DO MQTT ---
mqtt_client = None
mqtt_iniciado = False

# --- ESTRUTURA COM IP, RTC E MÚLTIPLOS HORÁRIOS ---
clientes = {
    "PISCINA_CLIENTE_001": {
        "nome": "Residência Conchas - Piscina Principal",
        "status": "OFF",
        "ip": "Desconhecido",
        "online": True,
        "rtc_status": "OK",
        "qtd_programacoes": 4,
        "programacoes": [
            {"id": 1, "hora": 8, "minuto": 0, "duracao": 60, "ativo": True},
            {"id": 2, "hora": 12, "minuto": 0, "duracao": 60, "ativo": True},
            {"id": 3, "hora": 16, "minuto": 0, "duracao": 60, "ativo": True},
            {"id": 4, "hora": 20, "minuto": 0, "duracao": 60, "ativo": True}
        ],
        "logs": []
    },
    "PISCINA_CLIENTE_002": {
        "nome": "Residência Conchas - Piscina Secundária",
        "status": "OFF",
        "ip": "Desconhecido",
        "online": True,
        "rtc_status": "OK",
        "qtd_programacoes": 1,
        "programacoes": [
            {"id": 1, "hora": 9, "minuto": 0, "duracao": 30, "ativo": True}
        ],
        "logs": []
    }
}

def adicionar_log(esp_id, mensagem):
    if esp_id in clientes:
        clientes[esp_id]["logs"].append(mensagem)
        if len(clientes[esp_id]["logs"]) > 20:
            clientes[esp_id]["logs"].pop(0)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ [MQTT] Conectado com sucesso ao Broker HiveMQ!", flush=True)
        client.subscribe("piscina/+/logs")
        client.subscribe("piscina/+/status")
        client.subscribe("piscina/+/config")
    else:
        print(f"❌ [MQTT] Erro ao conectar ao Broker, código de retorno: {rc}", flush=True)

def on_message(client, userdata, msg):
    try:
        topico = msg.topic.split('/')
        esp_id = topico[1]
        tipo = topico[2]
        payload = msg.payload.decode("utf-8")

        print(f"📥 [MQTT RECEBIDO] Tópico: {msg.topic} | Payload: {payload}", flush=True)

        if esp_id in clientes:
            if tipo == "logs":
                adicionar_log(esp_id, payload)
                if "RTC não encontrado" in payload:
                    clientes[esp_id]["rtc_status"] = "ERRO"
                elif "sincronizado com a internet" in payload or "sincronizado via NTP" in payload:
                    clientes[esp_id]["rtc_status"] = "SINCRONIZADO"
            
            elif tipo == "status":
                if payload == "OFFLINE":
                    clientes[esp_id]["online"] = False
                    clientes[esp_id]["status"] = "OFF"
                    adicionar_log(esp_id, "⚠️ Placa desconectada ou sem energia.")
                else:
                    if payload.startswith('{') and payload.endswith('}'):
                        try:
                            dados_status = json.loads(payload)
                            clientes[esp_id]["status"] = dados_status.get("status", "OFF")
                            clientes[esp_id]["ip"] = dados_status.get("ip", clientes[esp_id]["ip"])
                        except json.JSONDecodeError:
                            clientes[esp_id]["status"] = payload
                    else:
                        clientes[esp_id]["status"] = payload
                    clientes[esp_id]["online"] = True
            
            elif tipo == "config":
                dados = json.loads(payload)
                if "qtd_programacoes" in dados:
                    clientes[esp_id]["qtd_programacoes"] = dados.get("qtd_programacoes", 4)
                if "programacoes" in dados and isinstance(dados["programacoes"], list):
                    clientes[esp_id]["programacoes"] = dados["programacoes"]

    except Exception as e:
        print(f"⚠️ Erro ao processar mensagem MQTT recebida: {e}", flush=True)

def iniciar_mqtt():
    global mqtt_client, mqtt_iniciado
    if mqtt_iniciado:
        return
    mqtt_iniciado = True
    
    CLIENT_ID = f"SERVER_FLASK_{random.randint(10000, 99999)}"
    mqtt_client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2, 
        client_id=CLIENT_ID
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        print("🚀 [MQTT] Loop iniciado no Render.", flush=True)
    except Exception as e:
        print(f"🚨 Erro fatal ao conectar no MQTT: {e}", flush=True)

# Inicia o MQTT apenas uma vez quando a primeira requisição chegar
@app.before_request
def before_request():
    if not mqtt_iniciado:
        iniciar_mqtt()

# --- ROTAS FLASK ---
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/static/<path:filename>')
def servir_firmware(filename):
    return send_from_directory('static', filename)

@app.route('/api/clientes', methods=['GET'])
def listar_clientes():
    return jsonify(clientes)

@app.route('/api/comando', methods=['POST'])
def enviar_comando():
    # Garante que o MQTT está vivo antes de tentar enviar
    if not mqtt_iniciado or mqtt_client is None:
        iniciar_mqtt()
        
    dados = request.json
    esp_id = dados.get('esp_id')
    payload = dados.get('payload')
    
    if esp_id in clientes:
        topico = f"piscina/{esp_id}/comando"
        
        if isinstance(payload, str):
            mensagem_envio = json.dumps({"comando": payload})
        elif isinstance(payload, dict):
            mensagem_envio = json.dumps(payload)
        else:
            mensagem_envio = json.dumps({"comando": str(payload)})

        # Verifica se está conectado antes de publicar
        if mqtt_client:
            info = mqtt_client.publish(topico, mensagem_envio, qos=1)
            print(f"📤 [MQTT ENVIADO] Tópico: {topico} | Payload: {mensagem_envio} | Status: {info.rc}", flush=True)
            return jsonify({"status": "sucesso", "codigo_envio": info.rc})
        else:
            print("❌ [MQTT ERRO] Cliente MQTT não inicializado.", flush=True)
            return jsonify({"status": "erro", "motivo": "MQTT offline"}), 500
    
    return jsonify({"status": "erro", "motivo": "Cliente não cadastrado"}), 404

@app.route('/api/check_time', methods=['POST'])
def checar_tempo_rtc():
    if not mqtt_iniciado or mqtt_client is None:
        iniciar_mqtt()

    dados = request.json
    esp_id = dados.get('esp_id')
    
    if esp_id in clientes:
        topico = f"piscina/{esp_id}/comando"
        mensagem_envio = json.dumps({"comando": "CHECK_TIME"})
        if mqtt_client:
            info = mqtt_client.publish(topico, mensagem_envio, qos=1)
            print(f"📤 [MQTT ENVIADO CHECK] Tópico: {topico} | Status: {info.rc}", flush=True)
            return jsonify({"status": "sucesso", "mensagem": "Solicitação de hora enviada ao RTC."})
    
    return jsonify({"status": "erro", "motivo": "Cliente não encontrado"}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)