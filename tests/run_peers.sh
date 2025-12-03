CONFIG_FILE="./configuration/PeerInfo.cfg"
LOG_DIR="./logs"

mkdir -p "$LOG_DIR"

echo "Starting all peers listed in $CONFIG_FILE..."
sleep 1

while read -r line; do
    [ -z "$line" ] && continue

    peer_id=$(echo $line | awk '{print $1}')
    host=$(echo $line | awk '{print $2}')
    port=$(echo $line | awk '{print $3}')
    has_file=$(echo $line | awk '{print $4}')

    echo "Launching peer $peer_id on port $port"

    # Open each peer in a new terminal window
    gnome-terminal -- bash -c "python3 src/peer_process.py $peer_id; exec bash" 2>/dev/null \
    || xterm -hold -e "python3 src/peer_process.py $peer_id" 2>/dev/null \
    || {
        echo "Could not open new terminal, running in background instead."
        python3 src/peer_process.py "$peer_id" > "$LOG_DIR/peer_${peer_id}_stdout.log" 2>&1 &
    }

done < "$CONFIG_FILE"

echo "All peers launched!"
