<<<<<<< HEAD
from flask import Flask, render_template, request, jsonify
=======
from flask import Flask, render_template, request, jsonify, send_from_directory
>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
import paho.mqtt.client as mqtt
import json
import random
import os

app = Flask(__name__)

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

<<<<<<< HEAD
=======
# --- ESTRUTURA COM IP E MÚLTIPLOS HORÁRIOS ---
>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
clientes = {
    "PISCINA_CLIENTE_001": {
        "nome": "Residência Conchas - Piscina Principal",
        "status": "OFF",
<<<<<<< HEAD
        "online": True,
        "timer_liga": "08:00",     # Corrigido: formato HH:mm padrão válido
        "timer_desliga": "10:00",  # Corrigido: formato HH:mm padrão válido
=======
        "ip": "Desconhecido",  # IP Local do ESP32 na rede do cliente
        "online": True,
        "qtd_programacoes": 4,
        "programacoes": [
            {"id": 1, "hora": 8, "minuto": 0, "duracao": 60, "ativo": True},
            {"id": 2, "hora": 12, "minuto": 0, "duracao": 60, "ativo": True},
            {"id": 3, "hora": 16, "minuto": 0, "duracao": 60, "ativo": True},
            {"id": 4, "hora": 20, "minuto": 0, "duracao": 60, "ativo": True}
        ],
>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
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
<<<<<<< HEAD
        # Inscreve nos tópicos dinâmicos do cliente
=======
>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
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
<<<<<<< HEAD
                    clientes[esp_id]["status"] = payload
=======
                    if payload.startswith('{') and payload.endswith('}'):
                        try:
                            dados_status = json.loads(payload)
                            clientes[esp_id]["status"] = dados_status.get("status", "OFF")
                            clientes[esp_id]["ip"] = dados_status.get("ip", clientes[esp_id]["ip"])
                        except json.JSONDecodeError:
                            clientes[esp_id]["status"] = payload
                    else:
                        clientes[esp_id]["status"] = payload
                    
>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
                    clientes[esp_id]["online"] = True
            
            elif tipo == "config":
                dados = json.loads(payload)
<<<<<<< HEAD
                h_l = str(dados.get('hora_ligar', 0)).zfill(2)
                m_l = str(dados.get('min_ligar', 0)).zfill(2)
                h_d = str(dados.get('hora_desligar', 0)).zfill(2)
                m_d = str(dados.get('min_desligar', 0)).zfill(2)
                
                clientes[esp_id]["timer_liga"] = f"{h_l}:{m_l}"
                clientes[esp_id]["timer_desliga"] = f"{h_d}:{m_d}"
                
    except Exception as e:
        print(f"⚠️ Erro ao processar mensagem MQTT recebida: {e}")

# --- CLIENT ID DINÂMICO (Impede desconexão automática no HiveMQ) ---
=======
                
                if "qtd_programacoes" in dados:
                    clientes[esp_id]["qtd_programacoes"] = dados.get("qtd_programacoes", 4)
                
                if "programacoes" in dados and isinstance(dados["programacoes"], list):
                    clientes[esp_id]["programacoes"] = dados["programacoes"]

    except Exception as e:
        print(f"⚠️ Erro ao processar mensagem MQTT recebida: {e}")

# --- CLIENT ID DINÂMICO ---
>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
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

<<<<<<< HEAD
=======
# [NOVO] ROTA PARA SERVIR O FIRMWARE.BIN DO ESP32
@app.route('/static/<path:filename>')
def servir_firmware(filename):
    return send_from_directory('static', filename)

>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
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
        
<<<<<<< HEAD
        # --- ADEQUAÇÃO PARA O ESP32 ---
        # Se o payload for texto (ex: "LIGAR_MANUAL"), empacota em JSON {"comando": "LIGAR_MANUAL"}
        # Se já for um objeto/dicionário (ex: ao programar horários), serializa normalmente.
=======
>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
        if isinstance(payload, str):
            mensagem_envio = json.dumps({"comando": payload})
        elif isinstance(payload, dict):
            mensagem_envio = json.dumps(payload)
        else:
            mensagem_envio = json.dumps({"comando": str(payload)})

<<<<<<< HEAD
        # Publica no broker MQTT
=======
>>>>>>> 0098500 (Upload do projeto adm_piscina_timer)
        info = mqtt_client.publish(topico, mensagem_envio, qos=1)
        print(f"📤 [MQTT ENVIADO] Tópico: {topico} | Payload: {mensagem_envio} | Status: {info.rc}")

        return jsonify({"status": "sucesso", "codigo_envio": info.rc})
    
    return jsonify({"status": "erro", "motivo": "Cliente não cadastrado"}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)