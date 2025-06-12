import socket, threading, hashlib, queue
from utils import encoder

def init(application_object):
    global app, server, running

    app = application_object

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(app.server_address)
    server.listen()

    running = True

    # for i in known_nodes:
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     sock.connect(i)
    #     queues[str(len(queues)+1)] = queue.Queue()
    #     th = threading.Thread(target=handle_connection, args=(sock, i, str(len(queues))))
    #     th.start()

    while running:
        sock, addr = server.accept()
        this_connection_queue_id = str(len(app.server_connection_queues)+1)
        app.server_connection_queues[this_connection_queue_id] = queue.Queue()
        th = threading.Thread(target=handle_connection, args=(sock, addr, this_connection_queue_id))
        th.start()

# 4 - PoW Nonce
# 20 - from
# 20 - to
# 32 - sender's public
# NOT USED YET!!! 1 - type (0 - message, 1 - stream, 2 - broadcast)
# 2 - message lenght
# 8 - send time
# 8 - time to live

# message ...

# 64 - sign

# app.network_difficulty = 1
# app.protocol_version = 1
# app.known_nodes = []


already_emited = set()
queues = dict()

def handle_connection(sock: socket.socket, addr, queue_id):
    global app

    def handle_sender(sock: socket.socket, addr, queue_id): # NAPRAWIĆ !!!!!!!!!!!!!!!
        global app

        full_message = app.server_connection_queues[queue_id].get()
        sock.sendall(full_message)

    threading.Thread(target=handle_sender, args=(sock, addr, queue_id)).start()

    while running:
        primary_header_raw = sock.recv(108)
        primary_header_format = "uint:4 str:32 bytes:32 uint:8 bytes:32"

        primary_header = encoder.decode_data(primary_header_raw, primary_header_format)

        if primary_header[1] == "ping-address":
            secondary_header_length = 20
            secondary_header_format = "bytes:20"

            secondary_header_raw = sock.recv(secondary_header_length)
            secondary_header = encoder.decode_data(secondary_header_raw, secondary_header_format)

            data = None
        
        elif primary_header[1] == "pong":
            secondary_header_length = 32
            secondary_header_format = "str:32"

            secondary_header_raw = sock.recv(secondary_header_length)
            secondary_header = encoder.decode_data(secondary_header_raw, secondary_header_format)

            data = None
        
        elif primary_header[1] == "broadcast-message":
            secondary_header_length = 116
            secondary_header_format = "bytes:20 bytes:20 uint:2 uint:8 str:32 str:32 uint:2"

            secondary_header_raw = sock.recv(secondary_header_length)
            secondary_header = encoder.decode_data(secondary_header_raw, secondary_header_format)

            encryption_params_raw = sock.recv(secondary_header[6])
            encryption_params = encryption_params_raw.decode("utf-8")

            secondary_header_raw = secondary_header_raw + encryption_params_raw

            secondary_header.append(encryption_params)

            data = sock.recv(secondary_header[2])
        
        pow_nonce = sock.recv(4)

        signature = sock.recv(64)


        message_hash = hashlib.sha3_256(primary_header_raw + secondary_header_raw + data + signature).digest()

        message = [primary_header, secondary_header, data, pow_nonce, signature, message_hash, queue_id]

        app.received_message_queue.put(message)