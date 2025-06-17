import threading, hashlib, time
from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa
from Crypto.Hash import SHA512

from utils import encoder
from utils.pow import pow

def init(application_object):
    global app

    app = application_object

    handlers_count = 1

    for _ in range(handlers_count):
        threading.Thread(target=processor).start()

def processor():
    global app

    primary_header_format = "uint:4 str:32 bytes:32 uint:8 bytes:32"

    def process_ping_address(message):
        global app

        secondary_header_format = "bytes:20"

        primary_header = encoder.decode_data(message[0], primary_header_format)
        secondary_header = encoder.decode_data(message[1], secondary_header_format)
        data_raw = message[2]
        pow_nonce_raw = message[3]
        signature_raw = message[4]

        sender_public_raw = primary_header[4]
        sender_address = hashlib.sha3_256(hashlib.sha3_256(sender_public_raw).digest()).digest()[:20]

        secondary_header_response_format = "str:32"

        primary_header_response = [app.protocol_version, "pong", b"\x00"*32, int(time.time()), app.global_private.public_key().export_key(format="raw")]
        primary_header_response_raw = encoder.encode_data(primary_header_response, primary_header_format)

        secondary_header_response = [app.state]
        secondary_header_response_raw = encoder.encode_data(secondary_header_response, secondary_header_response_format)

        data_response_raw = b""
        pow_nonce_response_raw = pow(primary_header_response_raw + secondary_header_response_raw + data_response_raw, app.pow_target)

        signature_response_raw = eddsa.new(app.global_private, "rfc8032").sign(SHA512.new(primary_header_response_raw + secondary_header_response_raw + data_response_raw + pow_nonce_response_raw))

        response_raw = primary_header_response_raw + secondary_header_response_raw + data_response_raw + pow_nonce_response_raw + signature_response_raw
        app.server_connection_queues[message[6]].put(response_raw)
    
    def process_broadcast_message(message):
        global app

        secondary_header_format = "bytes:20 bytes:20 uint:2 uint:8 str:32 str:32 uint:2"

        primary_header = encoder.decode_data(message[0], primary_header_format)
        secondary_header = encoder.decode_data(message[1][:116], secondary_header_format)
        encryption_params = encoder.decode_data(message[1][:116], "str:"+str(secondary_header[6]))[0]
        secondary_header.append(encryption_params)
        data_raw = message[2]
        pow_nonce_raw = message[3]
        signature_raw = message[4]

        if not message[5] in app.already_emited:
            app.processed_messages_pool.put([primary_header, secondary_header, data_raw, pow_nonce_raw, signature_raw])

            for queue_name in app.server_connection_queues.keys():
                app.server_connection_queues[queue_name].put(message[0]+message[1]+message[2]+message[3]+message[4])

            app.already_emited.add(message[5])

    while True:
        message = app.received_message_queue.get()

        public_raw = encoder.decode_data(message[0], primary_header_format)[4]
        public_obj = eddsa.import_public_key(public_raw)

        if not encoder.decode_data(message[0], primary_header_format)[0] == app.protocol_version:
            raise ValueError("Wrong Protocol Version!")

        if not hashlib.sha3_256(message[0]+message[1]+message[2]+message[3]+message[4]).digest() == message[5]:
            raise ValueError("Wrong Hash!")

        eddsa.new(public_obj, "rfc8032").verify(SHA512.new(message[0]+message[1]+message[2]+message[3]), message[4])

        if not int.from_bytes(hashlib.sha3_256(message[0]+message[1]+message[2]+message[3]).digest(), "big") < app.pow_target:
            raise ValueError("Wrong PoW!")

        if encoder.decode_data(message[0], primary_header_format)[1] == "ping-address":
            process_ping_address(message)