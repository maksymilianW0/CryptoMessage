import socket, threading, encoder, time, hashlib, queue
from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa
from Crypto.Hash import SHA512
from flask import Flask, request, jsonify
from flask_cors import CORS

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

network_difficulty = 1
known_nodes = [("127.0.0.1", 5010)]

address = ("127.0.0.1", 5000)
rpc_address = ("127.0.0.1", 5001)

my_addresses = (b"",)

already_emited = set()
queues = dict()
messages = list()
my_messages = dict()

def RPC():
    global queues, my_messages
    rpc = Flask("CryptoMessage RPC Server")
    CORS(rpc)

    @rpc.route("/send", methods=["POST"])
    def send_message():
        message = request.data
        for i in queues.keys():
            queues[i].put(message)
        return 'Message sent!', 200
    
    @rpc.route("/get", methods=["GET"])
    def get_messages():
        mess = jsonify(my_messages)
        my_messages = dict()
        return mess, 200

    rpc.run(rpc_address[0], rpc_address[1])

def process_messages(search_for: list):
    global messages
    while running:
        for message in messages[:]:
            if message["recipient"] in search_for:
                my_messages[message["sender"]] = message
            if message["time_to_live"] < int(time.time()):
                messages.remove(message)

def handle_connection(sock: socket.socket, addr, queue_id):
    def handle_sender(sock: socket.socket, addr, queue_id):
        full_message = queues[queue_id].get()
        sock.sendall(full_message)

    threading.Thread(target=handle_sender, args=(sock, addr, queue_id)).start()

    while running:
        header = sock.recv(94)
        header_format = "uint:4 bytes:20 bytes:20 bytes:32 uint:2 uint:8 uint:8"
        pow_nonce, sender, recipient, senders_public, msg_length, send_time, time_to_live = encoder.decode_data(header, header_format)
        print("przyjęst")
        data = sock.recv(msg_length)
        sign = sock.recv(64)

        full_hash = hashlib.sha3_256(header + data + sign).digest()
        pow_proof = int("ff"*32, 16) - int.from_bytes(full_hash, "big")

        if full_hash in already_emited:
            continue
        if pow_proof < network_difficulty:
            continue
        if int(time.time()) > time_to_live:
            continue
        if time_to_live > int(time.time()) + 60 * 60 * 24:
            continue
        try:
            public = eddsa.import_public_key(senders_public)
            eddsa.new(public, "rfc8032").verify(SHA512.new(header[4:] + data), sign)
        except Exception as e:
            continue
        
        already_emited.add(full_hash)
        messages.append({"pow_nonce": pow_nonce,
                         "sender": sender,
                         "recipient": recipient,
                         "senders_public": senders_public,
                         "msg_length": msg_length,
                         "send_time": send_time,
                         "time_to_live": time_to_live,
                         "message": data,
                         "sign": sign
                         })
        for i in queues.keys():
            queues[i].put(header + data + sign)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(address)
server.listen()

running = True

threading.Thread(target=process_messages, args=my_addresses).start()
threading.Thread(target=RPC).start()

for i in known_nodes:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(i)
    queues[str(len(queues)+1)] = queue.Queue()
    th = threading.Thread(target=handle_connection, args=(sock, i, str(len(queues))))
    th.start()

while running:
    sock, addr = server.accept()
    queues[str(len(queues)+1)] = queue.Queue()
    th = threading.Thread(target=handle_connection, args=(sock, addr, str(len(queues))))
    th.start()