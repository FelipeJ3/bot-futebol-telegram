import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

# Configurações via Variáveis de Ambiente (segurança)
API_KEY_FOOTBALL = os.environ.get("API_KEY_FOOTBALL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Ligas monitoradas
# IDs mantidos: 88 (Eredivisie), 78 (Bundesliga), 103 (Eliteserien), 207 (Superliga Suíça)
TARGET_LEAGUES = [88, 78, 103, 207]
alerted_matches = set()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro Telegram: {e}")

def monitor_matches():
    """Loop de monitoramento rodando em segundo plano."""
    while True:
        try:
            url = "https://v3.football.api-sports.io/fixtures?live=all"
            headers = {"x-apisports-key": API_KEY_FOOTBALL}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                fixtures = response.json().get("response", [])
                for fixture in fixtures:
                    league_id = fixture["league"]["id"]
                    fixture_id = fixture["fixture"]["id"]

                    if league_id in TARGET_LEAGUES and fixture_id not in alerted_matches:
                        status = fixture["fixture"]["status"]["short"]
                        elapsed = fixture["fixture"]["status"]["elapsed"]
                        
                        # Filtro Over 0.5 HT (15-20 min, 0x0)
                        if status == "1H" and 15 <= elapsed <= 20:
                            home_g = fixture["goals"]["home"] or 0
                            away_g = fixture["goals"]["away"] or 0
                            
                            if home_g == 0 and away_g == 0:
                                stats = fixture.get("statistics", [])
                                if len(stats) >= 2:
                                    shots, attacks = 0, 0
                                    for team in stats:
                                        for s in team.get("statistics", []):
                                            if s["type"] == "Shots on Goal":
                                                shots += (s["value"] or 0)
                                            elif s["type"] == "Dangerous Attacks":
                                                attacks += (s["value"] or 0)
                                                
                                    if shots >= 4 and attacks >= 10:
                                        msg = (
                                            f"🔥 *ALERTA OVER 0.5 HT*\n\n"
                                            f"🏆 *Liga:* {fixture['league']['name']}\n"
                                            f"⚔️ *Jogo:* {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}\n"
                                            f"⏱️ *Tempo:* {elapsed}' min\n"
                                            f"🎯 Chutes no Gol: *{shots}*\n"
                                            f"⚡ Ataques Perigosos: *{attacks}*"
                                        )
                                        send_telegram(msg)
                                        alerted_matches.add(fixture_id)
        except Exception as e:
            print(f"Erro no loop: {e}")
            
        time.sleep(120) # Consulta a cada 2 minutos

# Inicia o loop em uma thread paralela
threading.Thread(target=monitor_matches, daemon=True).start()

@app.route('/')
def home():
    return "Bot de Futebol Ativo 24/7!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
