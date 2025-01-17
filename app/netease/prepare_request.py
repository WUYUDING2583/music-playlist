import json
import random
import string
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

MODULUS = "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7"
NONCE = "0CoJUm6Qyw8W8jud"
PUBKEY = "010001"
VI = "0102030405060708"


def create_secret_key(length):
    """Generate random string of specified length"""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def aes_encrypt(text, key):
    """AES encrypt the text with given key"""
    iv = bytes(VI, "utf-8")
    text = text.encode("utf-8")
    pad_text = pad(text, AES.block_size)

    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad_text)
    return base64.b64encode(encrypted).decode("utf-8")


def rsa_encode(text):
    """RSA encrypt (just like the C# RSAEncode)"""
    text = text[::-1]  # reverse string
    rs = pow(int(text.encode("utf-8").hex(), 16), int(PUBKEY, 16), int(MODULUS, 16))
    return format(rs, "x").zfill(256)


def prepare_request(data):
    """Prepare the encrypted request parameters"""
    secret_key = create_secret_key(16)

    # First AES encryption
    params = aes_encrypt(json.dumps(data), NONCE)
    # Second AES encryption
    params = aes_encrypt(params, secret_key)

    # RSA encryption for key
    enc_sec_key = rsa_encode(secret_key)

    return {"params": params, "encSecKey": enc_sec_key}


if __name__ == "__main__":

    # Example usage for playlist
    playlist_data = {
        "csrf_token": "",
        "id": "5137419858",  # replace with your playlist ID
        "offset": "0",
        "total": "true",
        "limit": "1000",
        "n": "1000",
    }

    encrypted = prepare_request(playlist_data)
    print("params:", encrypted["params"])
    print("encSecKey:", encrypted["encSecKey"])
