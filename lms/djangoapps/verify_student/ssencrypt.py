"""
NOTE: Anytime a `key` is passed into a function here, we assume it's a raw byte
string. It should *not* be a string representation of a hex value. In other
words, passing the `str` value of
`"32fe72aaf2abb44de9e161131b5435c8d37cbdb6f5df242ae860b283115f2dae"` is bad.
You want to pass in the result of calling .decode('hex') on that, so this instead:
"'2\xfer\xaa\xf2\xab\xb4M\xe9\xe1a\x13\x1bT5\xc8\xd3|\xbd\xb6\xf5\xdf$*\xe8`\xb2\x83\x11_-\xae'"

The RSA functions take any key format that RSA.importKey() accepts, so...

An RSA public key can be in any of the following formats:
* X.509 subjectPublicKeyInfo DER SEQUENCE (binary or PEM encoding)
* PKCS#1 RSAPublicKey DER SEQUENCE (binary or PEM encoding)
* OpenSSH (textual public key only)

An RSA private key can be in any of the following formats:
* PKCS#1 RSAPrivateKey DER SEQUENCE (binary or PEM encoding)
* PKCS#8 PrivateKeyInfo DER SEQUENCE (binary or PEM encoding)
* OpenSSH (textual public key only)

In case of PEM encoding, the private key can be encrypted with DES or 3TDES
according to a certain pass phrase. Only OpenSSL-compatible pass phrases are
supported.
"""
from collections import OrderedDict
from email.utils import formatdate
from hashlib import md5, sha256
from uuid import uuid4
import base64
import binascii
import json
import hmac
import logging
import sys

from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA

log = logging.getLogger(__name__)

def encrypt_and_encode(data, key):
    return base64.urlsafe_b64encode(aes_encrypt(data, key))

def decode_and_decrypt(encoded_data, key):
    return aes_decrypt(base64.urlsafe_b64decode(encoded_data), key)

def aes_encrypt(data, key):
    """
    Return a version of the `data` that has been encrypted to
    """
    cipher = aes_cipher_from_key(key)
    padded_data = pad(data)
    return cipher.encrypt(padded_data)

def aes_decrypt(encrypted_data, key):
    cipher = aes_cipher_from_key(key)
    padded_data = cipher.decrypt(encrypted_data)
    return unpad(padded_data)

def aes_cipher_from_key(key):
    """
    Given an AES key, return a Cipher object that has `encrypt()` and
    `decrypt()` methods. It will create the cipher to use CBC mode, and create
    the initialization vector as Software Secure expects it.
    """
    return AES.new(key, AES.MODE_CBC, generate_aes_iv(key))

def generate_aes_iv(key):
    """
    Return the initialization vector Software Secure expects for a given AES
    key (they hash it a couple of times and take a substring).
    """
    return md5(key + md5(key).hexdigest()).hexdigest()[:AES.block_size]

def random_aes_key():
    return Random.new().read(32)

def pad(data):
    bytes_to_pad = AES.block_size - len(data) % AES.block_size
    return data + (bytes_to_pad * chr(bytes_to_pad))

def unpad(padded_data):
    num_padded_bytes = ord(padded_data[-1])
    return padded_data[:-num_padded_bytes]

def rsa_encrypt(data, rsa_pub_key_str):
    """
    `rsa_pub_key` is a string with the public key
    """
    key = RSA.importKey(rsa_pub_key_str)
    cipher = PKCS1_OAEP.new(key)
    encrypted_data = cipher.encrypt(data)
    return encrypted_data

def rsa_decrypt(data, rsa_priv_key_str):
    key = RSA.importKey(rsa_priv_key_str)
    cipher = PKCS1_OAEP.new(key)
    return cipher.decrypt(data)

def has_valid_signature(method, headers_dict, body_dict, access_key, secret_key):
    """
    Given a message (either request or response), say whether it has a valid
    signature or not.
    """
    _, expected_signature, _ = generate_signed_message(
        method, headers_dict, body_dict, access_key, secret_key
    )

    authorization = headers_dict["Authorization"]
    auth_token, post_signature = authorization.split(":")
    _, post_access_key = auth_token.split()

    if post_access_key != access_key:
        log.error("Posted access key does not match ours")
        log.debug("Their access: %s; Our access: %s", post_access_key, access_key)
        return False

    if post_signature != expected_signature:
        log.error("Posted signature does not match expected")
        log.debug("Their sig: %s; Expected: %s", post_signature, expected_signature)
        return False

    return True

def generate_signed_message(method, headers_dict, body_dict, access_key, secret_key):
    """
    Returns a (message, signature) pair.
    """
    headers_str = "{}\n\n{}".format(method, header_string(headers_dict))
    body_str = body_string(body_dict)
    message = headers_str + body_str

    hashed = hmac.new(secret_key, message, sha256)
    signature = binascii.b2a_base64(hashed.digest()).rstrip('\n')
    authorization_header = "SSI {}:{}".format(access_key, signature)

    message += '\n'
    return message, signature, authorization_header

def header_string(headers_dict):
    """Given a dictionary of headers, return a canonical string representation."""
    header_list = []

    if 'Content-Type' in headers_dict:
        header_list.append(headers_dict['Content-Type'] + "\n")
    if 'Date' in headers_dict:
        header_list.append(headers_dict['Date'] + "\n")
    if 'Content-MD5' in headers_dict:
        header_list.append(headers_dict['Content-MD5'] + "\n")

    return "".join(header_list) # Note that trailing \n's are important

def body_string(body_dict):
    """
    This version actually doesn't support nested lists and dicts. The code for
    that was a little gnarly and we don't use that functionality, so there's no
    real test for correctness.
    """
    body_list = []
    for key, value in sorted(body_dict.items()):
        if value is None:
            value = "null"
        body_list.append(u"{}:{}\n".format(key, value))

    return "".join(body_list) # Note that trailing \n's are important

