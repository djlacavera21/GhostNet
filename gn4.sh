#!/bin/bash

# === GHOSTNET CONFIG ===
##192.168.1.87
PORT=7777
TEXT_PORT=8888
DEFAULT_FORMAT="s16le"
DEFAULT_RATE=44100
DEFAULT_CHANNELS=1
INTERFACE=$(hostname -I | awk '{print $1}')
OUTPUT_DIR="./ghostnet_logs"
mkdir -p "$OUTPUT_DIR"

# === INSTALL DEPENDENCIES ===
function install_dependencies() {
  echo "🔧 Installing dependencies..."
  sudo apt update
  sudo apt install -y ffmpeg netcat alsa-utils sox bc curl jq miniupnpc
  echo "✅ Dependencies installed."
}

# === START GHOSTNET SERVER ===
function start_server() {
  echo "🌐 Starting GhostNet UDP Server (Port: $PORT)..."
  echo "📡 Listening for audio on $INTERFACE:$PORT..."
  nc -ul $PORT | ffplay -hide_banner -loglevel quiet -autoexit -nodisp \
    -f $DEFAULT_FORMAT -ar $DEFAULT_RATE -ac $DEFAULT_CHANNELS -
}

# === CLIENT: STANDARD BROADCAST ===
function start_client_standard() {
  read -p "Enter target server IP (leave blank for $INTERFACE): " TARGET_IP
  TARGET_IP=${TARGET_IP:-$INTERFACE}
  echo "🎙️ Broadcasting mic to $TARGET_IP:$PORT (Press Ctrl+C to stop)"
  ffmpeg -f alsa -i default -f $DEFAULT_FORMAT -ar $DEFAULT_RATE -ac $DEFAULT_CHANNELS - \
    | nc -u $TARGET_IP $PORT
}

# === CLIENT: PUSH-TO-TALK ===
function start_client_ptt() {
  read -p "Enter target server IP (leave blank for $INTERFACE): " TARGET_IP
  TARGET_IP=${TARGET_IP:-$INTERFACE}
  echo "🎙️ Push-to-Talk mode active (Press SPACEBAR to talk)"
  echo "🛑 Ctrl+C to exit."

  while true; do
    read -rsn1 key
    if [[ $key == " " ]]; then
      echo "🎤 [PTT ON] Transmitting..."
      arecord -f $DEFAULT_FORMAT -r $DEFAULT_RATE -c $DEFAULT_CHANNELS -d 69 2>/dev/null \
        | nc -u $TARGET_IP $PORT
      echo "🔇 [PTT OFF]"
    fi
  done
}

# === CLIENT: VOICE ACTIVITY DETECTION ===
function start_client_vad() {
  read -p "Enter target server IP (leave blank for $INTERFACE): " TARGET_IP
  TARGET_IP=${TARGET_IP:-$INTERFACE}
  echo "🎙️ Voice Activity Detection active. Talking triggers send. Ctrl+C to exit."

  TMPFILE="/tmp/vadchunk.wav"

  while true; do
    arecord -f cd -r 16000 -c 1 -d 1 "$TMPFILE" 2>/dev/null
    DETECT=$(sox "$TMPFILE" -n stat 2>&1 | grep "RMS" | awk '{print $3}' | head -n1)
    if (( $(echo "$DETECT > 0.01" | bc -l) )); then
      echo "🎤 VAD Triggered (RMS: $DETECT)"
      cat "$TMPFILE" | ffmpeg -f wav -i - -f $DEFAULT_FORMAT -ar $DEFAULT_RATE -ac $DEFAULT_CHANNELS - 2>/dev/null \
        | nc -u $TARGET_IP $PORT
    fi
  done
}

# === TEXT CHAT FUNCTION ===
function start_text_chat() {
  echo "💬 GhostNet Text Chat Mode"
  echo "1) Start as Server"
  echo "2) Start as Client"
  echo -n "Choose: "; read chat_option

  case $chat_option in
    1)
      echo "📡 Listening for text on port $TEXT_PORT..."
      nc -ul $TEXT_PORT | tee -a "$OUTPUT_DIR/chat_log.txt"
      ;;
    2)
      read -p "Enter target server IP: " TARGET_IP
      echo "💬 Type your messages below. Ctrl+C to quit."
      while true; do
        read -p "You> " message
        echo "[$(date +"%H:%M")] $message" | nc -u $TARGET_IP $TEXT_PORT
      done
      ;;
    *)
      echo "❌ Invalid option."
      ;;
  esac
}

# === CLIENT SUBMENU ===
function client_submenu() {
  echo "=== 🎙️ GhostNet Transmit Modes ==="
  echo "1) Continuous Broadcast"
  echo "2) Push-to-Talk (SPACEBAR)"
  echo "3) Voice Activity Detection (VAD)"
  echo "4) Back"
  echo "==================================="
  echo -n "Choose option: "; read sub_option

  case $sub_option in
    1) start_client_standard ;;
    2) start_client_ptt ;;
    3) start_client_vad ;;
    4) return ;;
    *) echo "❌ Invalid option." ;;
  esac
}

# === GLOBAL NETWORK DISCOVERY ===
function discover_network_scope() {
  echo "🌍 Discovering Network Info..."
  echo "🔌 Local IP Address: $INTERFACE"
  PUBLIC_IP=$(curl -s https://api.ipify.org)
  echo "🌐 Public IP Address: $PUBLIC_IP"
  echo "🧠 Tip: Ensure UDP Ports $PORT (voice) and $TEXT_PORT (text) are forwarded on your router."
}

# === TRY AUTO-UPNP PORT FORWARDING ===
function auto_upnp_forward() {
  echo "📡 Attempting to open UDP ports via UPnP..."
  upnpc -a "$INTERFACE" "$PORT" "$PORT" UDP
  upnpc -a "$INTERFACE" "$TEXT_PORT" "$TEXT_PORT" UDP
  echo "✅ UPnP Port Forwarding Attempted (if supported by router)"
}

# === GLOBAL TOOLS MENU ===
function global_network_menu() {
  echo "=== 🌐 Global Comms Setup ==="
  echo "1) Discover IP Info (Local/Public)"
  echo "2) Try UPnP Port Forwarding"
  echo "3) Back"
  echo "=============================="
  echo -n "Choose option: "; read net_opt

  case $net_opt in
    1) discover_network_scope ;;
    2) auto_upnp_forward ;;
    3) return ;;
    *) echo "❌ Invalid option." ;;
  esac
}

# === MAIN MENU ===
function menu() {
  clear
  echo "===== 🔐 GhostNet v1.4 | OSS Secure Voice Mesh ====="
  echo "1) Install Dependencies"
  echo "2) Start GhostNet Server (Receiver)"
  echo "3) Start GhostNet Client (Sender)"
  echo "4) Auto Configure Network Info"
  echo "5) Start Text Chat"
  echo "6) Exit"
  echo "7) 🌐 Global Network Tools"
  echo "===================================================="
  echo -n "Select Option: "; read option

  case $option in
    1) install_dependencies ;;
    2) start_server ;;
    3) client_submenu ;;
    4) discover_network_scope ;;
    5) start_text_chat ;;
    6) echo "👋 Shutting down GhostNet."; exit 0 ;;
    7) global_network_menu ;;
    *) echo "❌ Invalid option." ;;
  esac
}

# === MAIN LOOP ===
while true; do
  menu
done
