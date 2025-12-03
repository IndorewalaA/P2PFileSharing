Project By: Brianna Chua, Abdul Indorewala, Dylan Tran, 



Manual Setup Instructions (1 Device, Multiple Terminals)
1. add peer_1001 folder to P2PFileSharing with test file
2. Use localhost in PeerInfo.cfg for each local terminal
    ex: "1001 localhost 6008 1 (start with complete file)" or "1002 localhost 6009 0" (start empty)
3. Make sure file size and name matches in Common.cfg
4. In terminal 1 and in P2PFileSharing directory, run "python src/peer_process.py 1001"
    * you should see "Peer 1001 starts"
5. For next terminals, use the same function but with 1002...1003...etc
6. Check for the file and verify contents (or see logs in the logs directory)
    ex. ls peer_1002 (log: log_peer_1002.log)



Manual Setup Instructions (Multiple Devices)
1. add peer_1001 folder to P2PFileSharing with test file (if device starting with file)
2. Make sure all devices are on the same network and have the same P2PFileSharing (including configuration)
3. Find the IP for each machine using ipconfig
4. Edit PeerInfo.cfg to use IP addresses
    ex. "1001 192.168.1.15 6008 1" (start with complete file) or "1002 192.168.1.87 6009 0" (start empty)
5. On machine 1 and in P2PFileSharing directory, run "python src/peer_process.py 1001"
    * you should see "Peer 1001 starts"
6. For next machines, use the same function but with 1002...1003...etc
6. Check for the file and verify contents (or see logs in the logs directory)
    ex. ls peer_1002 (log: log_peer_1002.log)


How to Run Tests (in Powershell):

run_peer.sh
    chmod +x /tests/run_peer.sh (only needed for inititalizing bash file)
    ./tests/run_peer.sh

test_peers.py
    $env:PYTHONPATH="src"; python tests/test_peers.py
