import hashlib
import os
from cryptography.hazmat.primitives.asymmetric import dh, rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, ParameterFormat, load_pem_public_key, load_pem_parameters
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class MesinKeripto:
    def __init__(self):
        self.dh_params = None

    def generate_dh_params(self):
        self.dh_params = dh.generate_parameters(generator=2, key_size=1024)
        return self.dh_params

    # ======= MANAJEMEN PARAMETER DH (P dan G) ========
    def get_dh_params_bytes(self):
        """Mengubah parameter P dan G menjadi bytes agar bisa dikirim via Socket"""
        return self.dh_params.parameter_bytes(Encoding.PEM, ParameterFormat.PKCS3)

    def set_dh_params_from_bytes(self, param_bytes):
        """Membaca parameter P dan G yang diterima dari jaringan"""
        self.dh_params = load_pem_parameters(param_bytes)

    # ======= GENERATE KUNCI RSA DAN DEFFIE-HELLMAN ========
    def generate_rsa_identity(self):
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return priv, priv.public_key()

    def generate_dh_node(self):
        priv = self.dh_params.generate_private_key()
        pub_bytes = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        return priv, pub_bytes
    
    # ======= TANDA TANGAN DIGITAL DAN VERIFIKASI DATA ========
    def sign_data(self, priv_rsa, data):
        return priv_rsa.sign(
            data,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )

    def verify_data(self, pub_rsa, sig, data):
        try:
            pub_rsa.verify(
                sig, data,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except:
            return False
        
    # ======= MENGHITUNG SHARED SECRET DARI PRIVATE KEY SENDIRI DAN PUBLIC KEY LAWAN ========    
    def get_shared_secret(self, my_dh_private_key, peer_dh_public_bytes):
        peer_public_key = load_pem_public_key(peer_dh_public_bytes)
        raw_secret = my_dh_private_key.exchange(peer_public_key)
        return hashlib.sha256(raw_secret).digest()
    
    # ======= ENKRIPSI DAN DEKRIPSI PESAN MENGGUNAKAN AES-GCM ========
    def encrypt_message(self, key, plaintext):
        aesgcm = AESGCM(key)
        nonce = os.urandom(12) 
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return nonce + ciphertext

    def decrypt_message(self, key, combined_data):
        aesgcm = AESGCM(key)
        nonce = combined_data[:12]
        ciphertext = combined_data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode()
    
    # ======= MENGHITUNG HASH DARI DATA ( DIGUNAKAN UNTUK MEMASTIKAN INTEGRITAS ) ========
    def calculate_hash(self, data):
        return hashlib.sha256(data).hexdigest()