from pprint import pp
import socket
import threading
import time
import sys
import os
import logging
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
from Kripton import MesinKeripto
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_public_key

 # ======== KONFIGURASI LIBRARY LOGGING ========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)

ctk.set_appearance_mode("dark")

def resource_path(relative_path):
    """Mendapatkan path absolut ke resource, berfungsi untuk dev dan PyInstaller"""
    try:
        # PyInstaller membuat folder temp dan menyimpan path-nya di _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Aplikasi(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WEEK 5 - WhisperNET (DH + RSA)")
        self.engine = MesinKeripto()
        self.shared_key = None
        self.conn = None
        self.server_socket = None # - Untuk Nyimpanin Socket Server -
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        try:
            self.iconbitmap(resource_path("makimak.ico"))
        except Exception:
            pass

    # ======== SET-UP USER INTERFACE ( GUI) ========
    def setup_ui(self):
        # === HEADER FRAME ===
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(pady=(20, 10))

        try:
            from PIL import Image
            # Gunakan resource_path di sini
            img_data = Image.open(resource_path("makima.png"))
            logo_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(45, 45))
            self.logo_label = ctk.CTkLabel(self.frame_header, image=logo_img, text="")
            self.logo_label.pack(side="left", padx=10)
        except Exception:
            pass

        self.label = ctk.CTkLabel(self.frame_header, text="WhisperNET - By Kelompok 6", font=("Segoe UI Black", 26))
        self.label.pack(side="left")

        # -=== CONTROL FRAME ===-
        self.frame_ctrl = ctk.CTkFrame(self, corner_radius=15, border_width=1, border_color="#333333")
        self.frame_ctrl.pack(pady=10, padx=20, fill="x")

        # -=== ENTRY IP ===-
        self.ip_entry = ctk.CTkEntry(
            self.frame_ctrl, placeholder_text="IP Target", width=140, height=38, corner_radius=8,
            font=("Segoe UI", 14, "bold")
        )
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(side="left", padx=15, pady=15)

        # -=== TOMBOL MODE SERVER ===-
        self.btn_server = ctk.CTkButton(
            self.frame_ctrl, text="Mode Server", height=38, corner_radius=8,
            font=("Segoe UI", 14, "bold"),
            fg_color="#106A43", hover_color="#1A8C5A", 
            border_width=2, border_color="#20E28B", text_color="white",
            command=self.start_server
        )
        self.btn_server.pack(side="left", padx=5)

        # -=== TOMBOL MODE CLIENT ===-
        self.btn_client = ctk.CTkButton(
            self.frame_ctrl, text="🚀 Mode Client", height=38, corner_radius=8,
            font=("Segoe UI", 14, "bold"),
            fg_color="#1A5276", hover_color="#2471A3", 
            border_width=2, border_color="#5DADE2", text_color="white",
            command=self.start_client
        )
        self.btn_client.pack(side="left", padx=5)

        # -=== TOMBOL RESET ATAU SETOP ===-
        self.btn_reset = ctk.CTkButton(
            self.frame_ctrl, text="⏹ Stop / Reset", height=38, corner_radius=8,
            font=("Segoe UI", 14, "bold"),
            fg_color="#922B21", hover_color="#C0392B", 
            border_width=2, border_color="#E6B0AA", text_color="white",
            command=self.reset_koneksi
        )
        self.btn_reset.pack(side="left", padx=5)

        # -=== CHECKBOX MITM ===-
        self.mitm_checkbox = ctk.CTkCheckBox(
            self.frame_ctrl, text="🚨 Simulasi MITM", text_color="#FF4444", 
            font=("Segoe UI", 13, "bold"), hover_color="#FF4444"
        )
        self.mitm_checkbox.pack(side="right", padx=15)

        # -=== LOG TERMINAL ( DALEM KOTAK ) ===-
        self.txt_log = ctk.CTkTextbox(
            self, width=860, height=350, font=("Cascadia Code", 13), 
            corner_radius=10, border_width=1, border_color="#444444", fg_color="#1A1A1A"
        )
        self.txt_log.pack(pady=10, padx=20)

        # -=== CHAT AREA ATAU KOLOM CHATTINGAN ===-
        self.frame_chat = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_chat.pack(pady=10, padx=20, fill="x")
        self.chat_entry = ctk.CTkEntry(
            self.frame_chat, placeholder_text="Ketik pesan yang ingin dikirim.", 
            width=700, height=45, corner_radius=20, state="disabled",
            font=("Segoe UI", 15)
        )
        self.chat_entry.pack(side="left", padx=(0, 10))
        self.chat_entry.bind("<Return>", lambda e: self.send_chat())

        # -=== TOMBOL BUAT KIRIM PESAN ===-
        self.btn_send = ctk.CTkButton(
            self.frame_chat, text="Kirim Pesan ➔", height=45, corner_radius=20,
            font=("Segoe UI", 14, "bold"),
            fg_color="#D35400", hover_color="#E67E22",
            border_width=2, border_color="#F5B041",
            state="disabled", command=self.send_chat
        )
        self.btn_send.pack(side="left")

    # ======== GUI BUAT LOG ========
    def gui_log(self, msg, level="INFO"):
        prefix = f"[{time.strftime('%H:%M:%S')}] "
        self.txt_log.insert("end", prefix + msg + "\n")
        self.txt_log.see("end")
        
        if level == "ERROR":
            logging.error(msg)
        elif level == "WARNING":
            logging.warning(msg)
        else:
            logging.info(msg)

     # ======== MANAJEMEN CHAT BIAR BISA DIGUNAKAN ATAU DITUTUP ========
    def enable_chat(self):
        self.chat_entry.configure(state="normal")
        self.btn_send.configure(state="normal")

    def disable_chat(self):
        self.chat_entry.delete(0, "end")
        self.chat_entry.configure(state="disabled")
        self.btn_send.configure(state="disabled")

    # ======== RESET KONEKSI ========
    def reset_koneksi(self):
        self.gui_log("[*] Memutus jaringan dan mereset sistem...", "WARNING")
        
        # -=== Tutup jalur komunikasi (Client/Server yang aktif) ===-
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None

        # -=== Tutup jalur antrean (Jika sedang mode Server yang menunggu) ===-
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None

        # -=== Hapus kunci rahasia dari memori ===-
        self.shared_key = None

        # -=== Kembalikan tampilan UI seperti semula ===-
        self.btn_server.configure(state="normal")
        self.btn_client.configure(state="normal")
        self.disable_chat()
        self.gui_log("[*] Sistem Sepenuhnya Siap. Anda bisa memulai ulang koneksi.\n" + "-"*50)

    def send_chat(self):
        msg = self.chat_entry.get()
        if msg and self.conn and self.shared_key:
            try:
                encrypted_data = self.engine.encrypt_message(self.shared_key, msg)
                self.conn.send(b"MSG:" + encrypted_data)
                self.gui_log(f"- [Kamu]: (Chat Terenkripsi)")
                self.chat_entry.delete(0, "end")
            except Exception as e:
                self.gui_log(f"[!] Gagal mengirim, koneksi terputus.", "ERROR")
                self.reset_koneksi()

    def listen_chat(self):
        while True:
            try:
                data = self.conn.recv(4096)
                if not data: 
                    self.gui_log("[!] Koneksi telah diputus oleh seseorang itu.", "WARNING")
                    self.reset_koneksi()
                    break
                if data.startswith(b"MSG:"):
                    decrypted_msg = self.engine.decrypt_message(self.shared_key, data[4:])
                    self.gui_log(f"✅ [Seseorang]: {decrypted_msg}", "SUCCESS")
            except:
                break

    # ================= SERVER ( IBRA ) =================
    def start_server(self):
        self.btn_server.configure(state="disabled")
        self.btn_client.configure(state="disabled")
        threading.Thread(target=self.server_logic, daemon=True).start()

    def server_logic(self):
        try:
            self.gui_log("[*] Membuka Port Komunikasi (Port : 55555)...")
            self.gui_log("[1] Menyiapkan parameter aturan (P & G)...")
            self.engine.generate_dh_params()
            param_bytes = self.engine.get_dh_params_bytes()

            self.gui_log("[2] Menyiapkan Identitas Digital RSA...")
            priv_rsa, pub_rsa = self.engine.generate_rsa_identity()
            pub_rsa_bytes = pub_rsa.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', 55555))
            self.server_socket.listen(1)
            self.gui_log("[*] Menunggu koneksi masuk dari Alvin...")

            # -=== Jika tombol Reset ditekan saat ini, server_socket.accept() bakal digagalkan ===-
            self.conn, addr = self.server_socket.accept()
            self.gui_log(f"[+] Alvin terhubung dari {addr}")

            self.gui_log("[*] Mengirim aturan (P & G) ke Alvin...")
            self.conn.send(param_bytes)
            time.sleep(0.5)

            alvin_rsa_bytes = self.conn.recv(4096)
            self.conn.send(pub_rsa_bytes)
            alvin_rsa_obj = load_pem_public_key(alvin_rsa_bytes)

            self.gui_log("[*] Menerima paket kunci dan memeriksa segel Alvin...")
            packet = self.conn.recv(4096).split(b"||SIG||")
            alvin_dh_pub = packet[0]
            alvin_sig = packet[1]

            if self.engine.verify_data(alvin_rsa_obj, alvin_sig, alvin_dh_pub):
                self.gui_log("    [✓] Segel Utuh! Integritas paket Alvin terjamin.")
            else:
                self.gui_log("    [!] FATAL: Segel Rusak/Palsu! Koneksi Diputus.", "ERROR")
                self.reset_koneksi()
                return

            self.gui_log("[*] Mengirim Kunci DH & Segel Ibra ke Alvin...")
            b_dh_priv, b_dh_pub = self.engine.generate_dh_node()
            b_sig = self.engine.sign_data(priv_rsa, b_dh_pub)
            self.conn.send(b_dh_pub + b"||SIG||" + b_sig)

            self.shared_key = self.engine.get_shared_secret(b_dh_priv, alvin_dh_pub)
            self.gui_log(f"🎉 SUKSES! Jalur Komunikasi Aman terbentuk.")
            self.gui_log(f"    Hash Kunci: {self.engine.calculate_hash(self.shared_key)[:30]}...")
            self.enable_chat()
            self.listen_chat()

        except Exception as e:
            # -=== Mengabaikan error jika disebabkan oleh tombol Reset ===-
            if self.conn is not None or self.server_socket is not None:
                self.gui_log(f"[!] Proses Server Terhenti.", "WARNING")

    # ================= CLIENT ( ALVIN ) =================
    def start_client(self):
        self.btn_server.configure(state="disabled")
        self.btn_client.configure(state="disabled")
        threading.Thread(target=self.client_logic, daemon=True).start()

    def client_logic(self):
        try:
            target_ip = self.ip_entry.get()
            self.gui_log(f"[*] Menghubungi Ibra di {target_ip}...")
            
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((target_ip, 55555))

            self.gui_log("[1] Menerima aturan dasar (P & G) dari Ibra...")
            param_bytes = self.conn.recv(4096)
            self.engine.set_dh_params_from_bytes(param_bytes)

            self.gui_log("[2] Menyiapkan Identitas Digital RSA...")
            priv_rsa, pub_rsa = self.engine.generate_rsa_identity()
            pub_rsa_bytes = pub_rsa.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

            self.conn.send(pub_rsa_bytes)
            ibra_rsa_bytes = self.conn.recv(4096)
            ibra_rsa_obj = load_pem_public_key(ibra_rsa_bytes)

            self.gui_log("[*] Mengirim Kunci DH & Segel Alvin ke Ibra...")
            a_dh_priv, a_dh_pub = self.engine.generate_dh_node()
            a_sig = self.engine.sign_data(priv_rsa, a_dh_pub)

            if self.mitm_checkbox.get() == 1:
                self.gui_log("🚨 [BAHAYA] Abrar baru saja memanipulasi paket di jaringan!", "ERROR")
                abrar = MesinKeripto()
                abrar.set_dh_params_from_bytes(param_bytes)
                _, a_dh_pub = abrar.generate_dh_node()

            self.conn.send(a_dh_pub + b"||SIG||" + a_sig)

            self.gui_log("[*] Menunggu balasan dan memeriksa segel Ibra...")
            packet_raw = self.conn.recv(4096)
            if not packet_raw:
                self.gui_log("    [!] Koneksi diputus paksa oleh Ibra.", "ERROR")
                self.reset_koneksi()
                return
            
            packet = packet_raw.split(b"||SIG||")
            ibra_dh_pub = packet[0]
            ibra_sig = packet[1]

            if self.engine.verify_data(ibra_rsa_obj, ibra_sig, ibra_dh_pub):
                self.gui_log("    [✓] Segel Utuh! Integritas paket Ibra terjamin.")
            else:
                self.gui_log("    [!] FATAL: Segel Ibra Palsu!", "ERROR")
                self.reset_koneksi()
                return

            self.shared_key = self.engine.get_shared_secret(a_dh_priv, ibra_dh_pub)
            self.gui_log(f"🎉 SUKSES! Jalur Komunikasi AMAN.")
            self.gui_log(f"    Hash Kunci: {self.engine.calculate_hash(self.shared_key)[:30]}...")
            self.enable_chat()
            self.listen_chat()

        except Exception as e:
            self.gui_log(f"[!] Gagal Connect: Pastikan Servernya sudah siap.", "ERROR")
            self.reset_koneksi()

    def on_closing(self):
        os._exit(0)

if __name__ == "__main__":
    app = Aplikasi()
    app.mainloop()