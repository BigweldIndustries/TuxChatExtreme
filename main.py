import socket,urllib.request,json
from threading import Thread

ServerConfig = json.loads(open('Config.json').read())[0]

SERVERHOST = ServerConfig['BindAddress']
SERVERPORT = int(ServerConfig['Port'])
MAXCONNECTION = int(ServerConfig['MaxConnections'])
SERVERNAME = ServerConfig['ServerName']

FORMAT = {"username":"","content":"","color":[0,0,0]}

client_sockets = set()

s = socket.socket()

s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind((SERVERHOST, SERVERPORT))

s.listen(5)
Xip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
Iip = socket.gethostbyname(socket.gethostname())
print(f"Server started on:\nLocal IP - {Iip}\nExternal IP - {Xip}\nPort - {str(SERVERPORT)}")


def listen_for_client(cs):
    while True:
        try:
            msg = json.loads(cs.recv(1024).decode())
        except Exception as e:
            print(f"[!] Error: {e}")
            client_sockets.remove(cs)

        for client_socket in client_sockets:
            if cs != client_socket:
                client_socket.send(json.dumps({"content": f'{str(msg["username"])} {str(msg["address"])} -> {str(msg["content"])}', "color": msg["color"]}).encode())
        NAME = msg['username']
        print(f'RECIVED PACKET {msg} FROM {NAME}')

while True:
    ClientSocket, ClientAddress = s.accept()
    print(f"[+] {ClientAddress} connected.")
    client_sockets.add(ClientSocket)
    t = Thread(target=listen_for_client, args=(ClientSocket,))
    t.daemon = True
    t.start()

for cs in client_sockets:
    cs.close()

s.close()