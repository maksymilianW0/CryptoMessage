import struct

def encode_data(data_list, format_str):
    """
    Funkcja przyjmuje listę danych oraz string określający format np. "int:16 string:32".
    Dla każdego elementu określa typ i ilość bajtów, a następnie serializuje dane do bajtów.
    Obsługiwane typy: int, uint, string, bool, bytes, float.
    """
    tokens = format_str.split()
    if len(tokens) != len(data_list):
        raise ValueError("Liczba elementów w liście nie zgadza się z ilością pól w formacie.")

    result = b""
    for token, value in zip(tokens, data_list):
        try:
            type_part, length_str = token.split(":")
        except ValueError:
            raise ValueError("Niepoprawny format tokenu: '{}'".format(token))
        length = int(length_str)
        
        if type_part == "int":
            # Zakładamy big-endian, obsługa liczb ujemnych.
            result += int(value).to_bytes(length, byteorder="big", signed=True)
        elif type_part == "uint":
            # Wartość musi być nieujemna.
            if int(value) < 0:
                raise ValueError("Wartość uint nie może być ujemna.")
            result += int(value).to_bytes(length, byteorder="big", signed=False)
        elif type_part == "string":
            encoded = value.encode("utf-8")
            # Przycinanie lub dopełnianie bajtami zer.
            if len(encoded) > length:
                encoded = encoded[:length]
            else:
                encoded = encoded.ljust(length, b'\x00')
            result += encoded
        elif type_part == "bool":
            # Kodowanie bool: 1 bajt, 1 dla True, 0 dla False.
            b_val = b'\x01' if value else b'\x00'
            result += b_val.ljust(length, b'\x00')
        elif type_part == "bytes":
            if not isinstance(value, bytes):
                raise TypeError("Wartość dla typu 'bytes' musi być bajtami.")
            if len(value) > length:
                value = value[:length]
            else:
                value = value.ljust(length, b'\x00')
            result += value
        elif type_part == "float":
            # Używamy formatu double (8 bajtów); wymagana długość to dokładnie 8.
            if length != 8:
                raise ValueError("Float musi być zakodowany na 8 bajtach.")
            result += struct.pack(">d", value)  # big-endian
        else:
            raise ValueError("Nieznany typ: '{}'".format(type_part))
    return result


def decode_data(data_bytes, format_str):
    """
    Funkcja przyjmuje ciąg bajtów oraz string formatu, i dekoduje dane z powrotem na listę.
    Format np. "int:16 string:32". Obsługiwane typy: int, uint, string, bool, bytes, float.
    """
    tokens = format_str.split()
    result = []
    index = 0

    for token in tokens:
        try:
            type_part, length_str = token.split(":")
        except ValueError:
            raise ValueError("Niepoprawny format tokenu: '{}'".format(token))
        length = int(length_str)
        segment = data_bytes[index:index+length]
        if len(segment) != length:
            raise ValueError("Niewystarczająca ilość bajtów do dekodowania typu '{}'".format(type_part))
        index += length
        
        if type_part == "int":
            value = int.from_bytes(segment, byteorder="big", signed=True)
            result.append(value)
        elif type_part == "uint":
            value = int.from_bytes(segment, byteorder="big", signed=False)
            result.append(value)
        elif type_part == "string":
            s = segment.rstrip(b'\x00').decode("utf-8")
            result.append(s)
        elif type_part == "bool":
            value = segment[0] != 0
            result.append(value)
        elif type_part == "bytes":
            result.append(segment)
        elif type_part == "float":
            if length != 8:
                raise ValueError("Float musi być zakodowany na 8 bajtach.")
            value = struct.unpack(">d", segment)[0]
            result.append(value)
        else:
            raise ValueError("Nieznany typ: '{}'".format(type_part))
    return result