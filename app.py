import socket
import os

HOST = "0.0.0.0"  # VERY IMPORTANT

# Get port from environment (default 9000 if not set)
PORT = int(os.getenv("PORT", 9000))

# Get flag from environment
FLAG = os.getenv("FLAG", "default_flag")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)

print("Server running on port", PORT)

while True:
    conn, addr = server.accept()
    
    conn.send(b"Your name: ")
    name = conn.recv(1024).strip()

    response = (
        b"Hiii " + name + b"\n"
        b"Here is your flag: " + FLAG.encode() + b"\n"
    )

    conn.send(response)
    conn.close()