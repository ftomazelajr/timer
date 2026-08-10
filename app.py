from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json
import random
import os

app = Flask(__name__)

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

clientes = {
    "PISCINA_CLIENTE_001": {
        "nome": "Residência Conchas - Piscina Principal",
        "status": "OFF",
        "online": True,
        "timer_liga": "08:00",     # Corrigido: formato HH:mm padrão válido
        "timer_desliga": "10:00",  # Corrigido: formato HH:mm padrão válido
        "logs": []
    }
}

def adicionar_log(esp_id, mensagem):
    if esp_id in clientes:
        clientes[esp_id]["logs"].append(mensagem)
        if len(clientes[esp_id]["logs"]) > 20:
            clientes[esp_id]["logs"].pop(0)

# --- CALLBACK DE CONEXÃO ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ [MQTT] Conectado com sucesso ao Broker HiveMQ!")
        # Inscreve nos tópicos dinâmicos do cliente
        client.subscribe("piscina/+/logs")
        client.subscribe("piscina/+/status")
        client.subscribe("piscina/+/config")
    else:
        print(f"❌ [MQTT] Erro ao conectar ao Broker, código de retorno: {rc}")

# --- CALLBACK DE MENSAGENS RECEBIDAS DO ESP32 ---
def on_message(client, userdata, msg):
    try:
        topico = msg.topic.split('/')
        esp_id = topico[1]
        tipo = topico[2]
        payload = msg.payload.decode("utf-8")

        print(f"📥 [MQTT RECEBIDO] Tópico: {msg.topic} | Payload: {payload}")

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
        print(f"⚠️ Erro ao processar mensagem MQTT recebida: {e}")

# --- CLIENT ID DINÂMICO (Impede desconexão automática no HiveMQ) ---
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
except Exception as e:
    print(f"🚨 Erro fatal ao conectar no MQTT: {e}")

# --- ROTAS FLASK ---
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
        
        # --- ADEQUAÇÃO PARA O ESP32 ---
        # Se o payload for texto (ex: "LIGAR_MANUAL"), empacota em JSON {"comando": "LIGAR_MANUAL"}
        # Se já for um objeto/dicionário (ex: ao programar horários), serializa normalmente.
        if isinstance(payload, str):
            mensagem_envio = json.dumps({"comando": payload})
        elif isinstance(payload, dict):
            mensagem_envio = json.dumps(payload)
        else:
            mensagem_envio = json.dumps({"comando": str(payload)})

        # Publica no broker MQTT
        info = mqtt_client.publish(topico, mensagem_envio, qos=1)
        print(f"📤 [MQTT ENVIADO] Tópico: {topico} | Payload: {mensagem_envio} | Status: {info.rc}")

        return jsonify({"status": "sucesso", "codigo_envio": info.rc})
    
    return jsonify({"status": "erro", "motivo": "Cliente não cadastrado"}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)