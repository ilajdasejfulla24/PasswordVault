# 🔐 Password Vault

A secure, offline password manager built with Python.  
Stores credentials in an encrypted **SQLite** database using **Fernet** symmetric encryption.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 Master Password | AES-derived key protects the vault key (PBKDF2-HMAC-SHA256) |
| 🔒 Encryption | Every password encrypted with Fernet before being stored |
| 🗄️ SQLite Storage | Fully local – no cloud, no telemetry |
| ➕ Add / Edit / Delete | Full CRUD for credentials (site, username, password, notes) |
| 🔍 Search | Real-time filter by site or username |
| ⚙️ Password Generator | Configurable length, uppercase, digits, symbols |
| 💪 Strength Meter | Live feedback while typing or generating passwords |
| 📋 Copy to Clipboard | One-click copy of decrypted passwords |
| 📤 Export | Back up vault to a plain-text `.txt` file |
| 🌑 Dark Theme | Sleek dark UI built with Tkinter |

---

## 🛠️ Requirements

- Python **3.11+**
- Libraries: see `requirements.txt`

```bash
pip install -r requirements.txt
```

> **Note:** On Linux you may also need `xclip` or `xsel` for clipboard support:
> ```bash
> sudo apt install xclip
> ```

---

## 🚀 Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/password-vault.git
cd password-vault

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

---

