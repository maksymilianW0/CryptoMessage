from Crypto.Hash import HMAC, SHA256
from Crypto.Hash import SHA512

from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa
from Crypto.Protocol.DH import key_agreement

from Crypto.Cipher import AES

import os

class HKDF:
    def __init__(self, length: int = 32, salt: bytes = b'', info: bytes = b''):
        self.length = length
        self.salt = salt
        self.info = info
    
    def __call__(self, ikm):
        hash_len = SHA256.digest_size
        _salt = self.salt or (b'\x00' * hash_len)

        # Extract
        prk = HMAC.new(_salt, ikm, SHA256).digest()

        # Expand
        okm = b""
        previous = b""
        n = (self.length + hash_len - 1) // hash_len
        for i in range(1, n + 1):
            previous = HMAC.new(prk, previous + self.info + bytes([i]), SHA256).digest()
            okm += previous

        return okm[:self.length]

# Funkcja KDF uzgadniana wcześniej
def hkdf(length: int, salt: bytes = b'', info: bytes = b''):

    def kdf(ikm):
        hash_len = SHA256.digest_size
        _salt = salt or (b'\x00' * hash_len)

        # Extract
        prk = HMAC.new(_salt, ikm, SHA256).digest()

        # Expand
        okm = b""
        previous = b""
        n = (length + hash_len - 1) // hash_len
        for i in range(1, n + 1):
            previous = HMAC.new(prk, previous + info + bytes([i]), SHA256).digest()
            okm += previous

        return okm[:length]

    return kdf

def ed25519_to_x25519(ed_priv: bytes) -> bytes:
    """
    Konwersja klucza prywatnego Ed25519 na scalar prywatny X25519.

    Args:
        ed_priv: bytes – 32-bajtowy seed Ed25519 lub 64-bajtowy klucz prywatny Ed25519 (seed||pub).

    Returns:
        32-bajtowy scalar prywatny do użycia z X25519.
    """
    # 1. Wyciągamy seed (jeśli ed_priv ma 64 bajty, to pierwsze 32 to seed)
    seed = ed_priv[:32]

    # 2. Hashujemy seed SHA-512
    h = SHA512.new(seed).digest()

    # 3. Bierzemy pierwsze 32 bajty i „clampujemy” je zgodnie z RFC7748
    a = bytearray(h[:32])
    a[0]  &= 248
    a[31] &= 127
    a[31] |= 64

    # 4. Wynik to 32-bajtowy scalar prywatny X25519
    return bytes(a)


import hmac
import hashlib

def pbkdf2_hmac_sha256(password: bytes,
                       salt: bytes,
                       iterations: int,
                       dklen: int) -> bytes:
    """
    PBKDF2-HMAC-SHA256:
      password   – hasło/sekret (bytes)
      salt       – sól (bytes)
      iterations – liczba iteracji (work factor)
      dklen      – docelowa długość klucza (bytes)
    """
    hash_len = hashlib.sha256().digest_size
    # liczba bloków T_i, które musimy wygenerować
    blocks = (dklen + hash_len - 1) // hash_len

    def F(block_index: int) -> bytes:
        # U1 = PRF(password, salt ∥ INT_32_BE(block_index))
        U = hmac.new(password, salt + block_index.to_bytes(4, 'big'),
                     hashlib.sha256).digest()
        result = bytearray(U)
        # kolejne iteracje: Ui = PRF(password, U_{i-1})
        for _ in range(1, iterations):
            U = hmac.new(password, U, hashlib.sha256).digest()
            # XOR z poprzednim stanem
            for i in range(hash_len):
                result[i] ^= U[i]
        return bytes(result)

    # łączymy bloki i obcinamy do dklen
    okm = b''.join(F(i + 1) for i in range(blocks))
    return okm[:dklen]

print(pbkdf2_hmac_sha256(b"haslo", b"qwertyuiop", 200000, 32))