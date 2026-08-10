from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json
from datetime import datetime

app = Flask(__name__)

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

clientes = {
    "PISCINA_CLIENTE_001": {
        "nome": "Residência Conchas - Piscina Principal",
        "status": "OFF",
        "online": True,
        "timer_liga": "--:--",
        "timer_desliga": "--:--",
        "logs": []
    }
}

def adicionar_log(esp_id, mensagem):
    if esp_id in clientes:
        clientes[esp_id]["logs"].append(mensagem)
        if len(clientes[esp_id]["logs"]) > 20:
            clientes[esp_id]["logs"].pop(0)

# --- CALLBACK DE CONEXÃO (Garante re-inscrição se a conexão oscilar no Render) ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Conectado ao Broker MQTT no Render!")
        # Inscreve nos tópicos SEMPRE que conectar/reconectar
        client.subscribe("piscina/+/logs")
        client.subscribe("piscina/+/status")
        client.subscribe("piscina/+/config")
    else:
        print(f"❌ Falha ao conectar ao MQTT, código de retorno: {rc}")

# --- CALLBACK DE MENSAGENS RECEBIDAS ---
def on_message(client, userdata, msg):
    try:
        topico = msg.topic.split('/')
        esp_id = topico[1]
        tipo = topico[2]
        payload = msg.payload.decode("utf-8")

        if esp_id in clientes:
            if tipo == "logs":
                adicionar_log(esp_id, payload)
            
            elif tipo == "status":
                if payload == "OFFLINE":
                    clientes[esp_id]["online"] = False
                    clientes[esp_id]["status"] = "OFF"
                    adicionar_log(esp_id, "⚠️ Placa desconectada ou sem energia.")
                else:
                    clientes[esp_id]["status"] = payload
                    clientes[esp_id]["online"] = True
            
            elif tipo == "config":
                dados = json.loads(payload)
                h_l = str(dados.get('hora_ligar', 0)).zfill(2)
                m_l = str(dados.get('min_ligar', 0)).zfill(2)
                h_d = str(dados.get('hora_desligar', 0)).zfill(2)
                m_d = str(dados.get('min_desligar', 0)).zfill(2)
                
                clientes[esp_id]["timer_liga"] = f"{h_l}:{m_l}"
                clientes[esp_id]["timer_desliga"] = f"{h_d}:{m_d}"
                
    except Exception as e:
        print(f"Erro ao processar mensagem MQTT: {e}")

# --- INICIALIZAÇÃO MQTT (COMPATÍVEL COM PAHO V2 E RENDER) ---
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="SERVER_FLASK_PISCINA")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"Erro ao iniciar cliente MQTT: {e}")

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/clientes', methods=['GET'])
def listar_clientes():
    return jsonify(clientes)

@app.route('/api/comando', methods=['POST'])
def enviar_comando():
    dados = request.json
    esp_id = dados.get('esp_id')
    payload = dados.get('payload')
    
    if esp_id in clientes:
        topico = f"piscina/{esp_id}/comando"
        mqtt_client.publish(topico, json.dumps(payload))
        return jsonify({"status": "sucesso"})
    
    return jsonify({"status": "erro"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)