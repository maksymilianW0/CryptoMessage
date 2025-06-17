import hashlib

def pow(data, target):
    nonce_int = 0
    while True:
        nonce_raw = nonce_int.to_bytes(4, "big")
        test_hash = int.from_bytes(hashlib.sha3_256(data + nonce_raw).digest(), "big")
        if test_hash < target:
            return nonce_raw
        nonce_int += 1