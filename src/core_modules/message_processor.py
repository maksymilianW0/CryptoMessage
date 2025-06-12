import threading, hashlib

from utils import encoder

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

        primary_header, secondary_header, data, pow_nonce, signature, message_hash, queue_id = message

        version, message_type, scope, send_time, public = primary_header
        target = secondary_header[0]

        primary_header_raw = encoder.encode_data(primary_header, primary_header_format)
        secondary_header_raw = encoder.encode_data(secondary_header, secondary_header_format)

        if int.from_bytes(hashlib.sha3_256(primary_header_raw + secondary_header_raw + pow_nonce).digest(), "big") < int("ff"*32, 16) - app.pow_difficulty:
            raise ValueError("Wrong PoW!")

    while True:
        message = app.received_message_queue.get()

        if message[0][1] == "ping-address":
            process_ping_address(message)