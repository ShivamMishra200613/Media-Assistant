import customtkinter as ctk
import sqlite3
import requests
import csv
from tkinter import messagebox, ttk
import threading
import time

# --- Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- Colors ---
COLOR_PRIMARY = "#1f538d"
COLOR_SECONDARY = "#2b2b2b"
COLOR_BG = "#1a1a1a"
COLOR_CHAT_USER = "#1f538d"
COLOR_CHAT_BOT = "#333333"
COLOR_TEXT = "#ffffff"

class DatabaseManager:
    def __init__(self, db_name="media_sources.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                url TEXT,
                category TEXT
            )
        ''')
        self.cursor.execute("SELECT * FROM users")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO users VALUES (?, ?)", ("admin", "admin123"))
        self.conn.commit()

    def verify_login(self, username, password):
        self.cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        return self.cursor.fetchone() is not None

    def add_site(self, name, url, category):
        try:
            self.cursor.execute("INSERT INTO websites (name, url, category) VALUES (?, ?, ?)", (name, url, category))
            self.conn.commit()
            return True
        except:
            return False

    def get_all_sites(self):
        self.cursor.execute("SELECT * FROM websites")
        return self.cursor.fetchall()

    def delete_site(self, site_id):
        self.cursor.execute("DELETE FROM websites WHERE id=?", (site_id,))
        self.conn.commit()

# --- Main Application ---
class MediaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Media Source Assistant")
        
        # Set Full Screen / Maximized
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()
        self.geometry(f"{width}x{height}+0+0")
        self.minsize(1000, 700)
        
        # Database
        self.db = DatabaseManager()
        
        # Main Container
        self.container = ctk.CTkFrame(self, fg_color=COLOR_BG)
        self.container.pack(fill="both", expand=True)
        
        self.frames = {}
        for F in (LoginFrame, DashboardFrame):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.show_frame("LoginFrame")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if page_name == "DashboardFrame":
            frame.update_summary()

# --- Login Module ---
class LoginFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG)
        self.controller = controller

        # Center Card
        card = ctk.CTkFrame(self, width=600, height=600, corner_radius=20, fg_color=COLOR_SECONDARY)
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(card, text="MEDIA\nACCESS", font=("Arial Black", 30), text_color=COLOR_PRIMARY).pack(pady=(50, 20))
        ctk.CTkLabel(card, text="Sign in to your dashboard", font=("Roboto", 14), text_color="gray").pack(pady=(0, 30))

        self.user_entry = ctk.CTkEntry(card, placeholder_text="Username", width=400, height=40, font=("Roboto", 14))
        self.user_entry.pack(pady=10)

        self.pass_entry = ctk.CTkEntry(card, placeholder_text="Password", show="*", width=400, height=40, font=("Roboto", 14))
        self.pass_entry.pack(pady=10)

        ctk.CTkButton(card, text="LOGIN", command=self.login, width=250, height=45, font=("Roboto", 14, "bold")).pack(pady=30)

    def login(self):
        if self.controller.db.verify_login(self.user_entry.get(), self.pass_entry.get()):
            self.controller.show_frame("DashboardFrame")
        else:
            messagebox.showerror("Access Denied", "Invalid Credentials")

# --- Dashboard Module ---
class DashboardFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG)
        self.controller = controller

        # 1. Sidebar (Left)
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=COLOR_SECONDARY)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False) # Fixed width

        # App Logo/Title
        ctk.CTkLabel(self.sidebar, text="MEDIA\nBOT", font=("Arial Black", 24), text_color="white").pack(pady=(40, 40))

        # Nav Buttons
        self.btn_chat = self.create_nav_btn("💬  Chat Assistant", "chat")
        self.btn_crud = self.create_nav_btn("🛠  Manage Sites", "crud")
        self.btn_report = self.create_nav_btn("📊  View Report", "report")

        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray").pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(self.sidebar, text="↪ Log Out", fg_color="transparent", hover_color="#8B0000", 
                      anchor="w", command=lambda: controller.show_frame("LoginFrame")).pack(fill="x", padx=20, pady=10)

        # 2. Content Area (Right)
        self.content_area = ctk.CTkFrame(self, fg_color=COLOR_BG)
        self.content_area.pack(side="right", fill="both", expand=True)

        self.views = {
            "chat": ChatView(self.content_area, controller),
            "crud": CRUDView(self.content_area, controller),
            "report": ReportView(self.content_area, controller)
        }
        self.show_view("chat")

    def create_nav_btn(self, text, view_name):
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", text_color="gray90", hover_color=COLOR_PRIMARY, 
                            anchor="w", height=50, font=("Roboto", 16),
                            command=lambda: self.show_view(view_name))
        btn.pack(fill="x", padx=10, pady=5)
        return btn

    def show_view(self, view_name):
        # Reset buttons styling
        for btn in [self.btn_chat, self.btn_crud, self.btn_report]:
            btn.configure(fg_color="transparent", text_color="gray90")
        
        # Highlight active
        if view_name == "chat": self.btn_chat.configure(fg_color=COLOR_PRIMARY, text_color="white")
        elif view_name == "crud": self.btn_crud.configure(fg_color=COLOR_PRIMARY, text_color="white")
        elif view_name == "report": self.btn_report.configure(fg_color=COLOR_PRIMARY, text_color="white")

        # Show frame
        for view in self.views.values():
            view.pack_forget()
        self.views[view_name].pack(fill="both", expand=True, padx=20, pady=20)
        
        if view_name == "report":
            self.views["report"].refresh_table()

    def update_summary(self):
        pass

# --- Chat View (Modern Bubbles) ---
class ChatView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Header
        ctk.CTkLabel(self, text="Assistant", font=("Roboto", 24, "bold")).pack(anchor="w", pady=(0, 20))

        # Chat History (Scrollable)
        self.chat_area = ctk.CTkScrollableFrame(self, fg_color=COLOR_SECONDARY, corner_radius=15)
        self.chat_area.pack(fill="both", expand=True, pady=(0, 20))

        # Input Area
        input_frame = ctk.CTkFrame(self, height=60, fg_color=COLOR_SECONDARY, corner_radius=30)
        input_frame.pack(fill="x", pady=10)
        
        self.entry_msg = ctk.CTkEntry(input_frame, placeholder_text="Ask for a movie, series, or check status...", 
                                      border_width=0, fg_color="transparent", font=("Roboto", 14))
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=20, pady=10)
        self.entry_msg.bind("<Return>", lambda event: self.send_message())
        
        send_btn = ctk.CTkButton(input_frame, text="➤", width=50, height=40, corner_radius=20, command=self.send_message)
        send_btn.pack(side="right", padx=10)

        # Initial Message
        self.add_bubble("Hello! I can check your site list and recommend active ones. Try asking 'Recommend a movie site'.", "Bot")

    def send_message(self):
        msg = self.entry_msg.get()
        if not msg: return
        
        self.add_bubble(msg, "User")
        self.entry_msg.delete(0, "end")
        
        # Bot Logic
        if any(x in msg.lower() for x in ["movie", "series", "watch", "check", "recommend"]):
            self.add_bubble("Scanning repository for fastest mirrors... 🔍", "Bot")
            threading.Thread(target=self.check_sites_and_recommend).start()
        else:
            self.add_bubble("I can help you check site availability. Try asking 'Recommend a site to watch a movie'.", "Bot")

    def add_bubble(self, text, sender):
        if sender == "User":
            bubble_color = COLOR_CHAT_USER
            anchor = "e"
            text_color = "white"
        else:
            bubble_color = COLOR_CHAT_BOT
            anchor = "w"
            text_color = "gray90"

        bubble = ctk.CTkLabel(
            self.chat_area, 
            text=text, 
            fg_color=bubble_color, 
            text_color=text_color,
            corner_radius=15,
            wraplength=600,
            padx=15, pady=10,
            font=("Roboto", 14),
            justify="left"
        )
        bubble.pack(anchor=anchor, pady=5, padx=10)
        
        # Auto scroll to bottom
        self.after(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        self.chat_area._parent_canvas.yview_moveto(1.0)

    def check_sites_and_recommend(self):
        sites = self.controller.db.get_all_sites()
        if not sites:
            self.add_bubble("Your list is empty. Add sites in the 'Manage Sites' tab.", "Bot")
            return

        active_sites = []
        for site in sites:
            site_name = site[1]
            url = site[2]
            try:
                check_url = url if url.startswith("http") else "https://" + url
                start = time.time()
                response = requests.head(check_url, timeout=3)
                latency = round((time.time() - start) * 1000)
                
                if response.status_code < 400:
                    active_sites.append((site_name, latency, url))
            except:
                pass 
        
        active_sites.sort(key=lambda x: x[1])
        
        if active_sites:
            response = "✅ Here are the top 3 active sites:\n\n"
            for i, s in enumerate(active_sites[:3]):
                response += f"{i+1}. {s[0]}\n   ⚡ {s[1]}ms | 🔗 {s[2]}\n\n"
        else:
            response = "❌ All sites in your list appear to be down."
            
        self.add_bubble(response, "Bot")

# --- CRUD View ---
class CRUDView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        ctk.CTkLabel(self, text="Manage Sites", font=("Roboto", 24, "bold")).pack(anchor="w", pady=(0, 20))

        # Form Container
        form_frame = ctk.CTkFrame(self, fg_color=COLOR_SECONDARY, corner_radius=15)
        form_frame.pack(fill="x", pady=10, ipady=10)
        
        # Grid Layout for Form
        form_frame.grid_columnconfigure((0,1,2), weight=1)
        
        ctk.CTkLabel(form_frame, text="Site Name", font=("Roboto", 12, "bold")).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.name_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g. Archive", height=40)
        self.name_entry.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        ctk.CTkLabel(form_frame, text="URL", font=("Roboto", 12, "bold")).grid(row=0, column=1, padx=20, pady=(20, 5), sticky="w")
        self.url_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g. archive.org", height=40)
        self.url_entry.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="ew")
        
        ctk.CTkLabel(form_frame, text="Category", font=("Roboto", 12, "bold")).grid(row=0, column=2, padx=20, pady=(20, 5), sticky="w")
        self.cat_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g. Movies", height=40)
        self.cat_entry.grid(row=1, column=2, padx=20, pady=(0, 20), sticky="ew")
        
        ctk.CTkButton(form_frame, text="+ ADD SITE", height=40, font=("Roboto", 12, "bold"), 
                      fg_color="#2ecc71", hover_color="#27ae60",
                      command=self.add_record).grid(row=1, column=3, padx=20, pady=(0, 20))

        ctk.CTkLabel(self, text="💡 Tip: Enter the base URL. The bot will ping this to check availability.", text_color="gray").pack(pady=10)

    def add_record(self):
        if self.controller.db.add_site(self.name_entry.get(), self.url_entry.get(), self.cat_entry.get()):
            messagebox.showinfo("Success", "Site added to repository.")
            self.name_entry.delete(0, "end")
            self.url_entry.delete(0, "end")
            self.cat_entry.delete(0, "end")
        else:
            messagebox.showerror("Error", "Could not add site.")

# --- Report View ---
class ReportView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Header
        head_frame = ctk.CTkFrame(self, fg_color="transparent")
        head_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(head_frame, text="Repository Data", font=("Roboto", 24, "bold")).pack(side="left")
        ctk.CTkButton(head_frame, text="⬇ Export CSV", height=35, command=self.export_csv).pack(side="right")

        # Table Container
        table_container = ctk.CTkFrame(self, fg_color=COLOR_SECONDARY, corner_radius=15)
        table_container.pack(fill="both", expand=True)

        # Treeview Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                        background=COLOR_SECONDARY, 
                        foreground="white", 
                        fieldbackground=COLOR_SECONDARY, 
                        borderwidth=0, 
                        rowheight=30, 
                        font=("Roboto", 12))
        style.configure("Treeview.Heading", 
                        background="#1a1a1a", 
                        foreground="white", 
                        font=("Roboto", 12, "bold"),
                        borderwidth=0)
        style.map("Treeview", background=[("selected", COLOR_PRIMARY)])

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(table_container)
        scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)

        self.tree = ttk.Treeview(table_container, columns=("ID", "Name", "URL", "Category"), show="headings", yscrollcommand=scrollbar.set)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("URL", text="URL")
        self.tree.heading("Category", text="Category")
        
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=200)
        self.tree.column("URL", width=300)
        self.tree.column("Category", width=150)
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar.configure(command=self.tree.yview)

    def refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in self.controller.db.get_all_sites():
            self.tree.insert("", "end", values=row)

    def export_csv(self):
        try:
            with open("my_sites_report.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Name", "URL", "Category"])
                writer.writerows(self.controller.db.get_all_sites())
            messagebox.showinfo("Export", "Data exported to my_sites_report.csv")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = MediaApp()
    app.mainloop()