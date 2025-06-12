from flask import Flask, request, jsonify
from flask_cors import CORS

def RPC():
    global queues, my_messages
    rpc = Flask("CryptoMessage RPC Server")
    CORS(rpc)

    @rpc.route("/ping", methods=["GET"])
    def ping():
        return 'pong', 200

    @rpc.route("/send", methods=["POST"])
    def send_message():
        message = request.data
        for i in queues.keys():
            queues[i].put(message)
        return 'Message sent!', 200
    
    @rpc.route("/get", methods=["GET"])
    def get_messages():
        messages_to_return = dict()
        search_for = request.args.get("address")
        for i in my_messages.keys():
            if i.hex() == search_for:
                messages_to_return[my_messages[i]["sender:" + str(random.randint(0, 9999))]] = my_messages[i]
        mess = jsonify(messages_to_return)
        return mess, 200

    rpc.run(rpc_address[0], rpc_address[1])