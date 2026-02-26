import socket

HOST = '127.0.0.1'
PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

print(f"UDP受信待機中... ({HOST}:{PORT}) 終了は Ctrl+C")

while True:
    data, addr = sock.recvfrom(1024)
    print(f"受信: {data.decode()}")
