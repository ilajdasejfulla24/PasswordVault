"""
gui.py
------
Tkinter-based graphical user interface for the Password Vault.

Window hierarchy
----------------
App (root)
 ├── MasterPasswordScreen   – set or enter master password
 └── MainScreen             – tabbed vault manager
      ├── CredentialListFrame
      ├── AddEditDialog
      └── GeneratorDialog
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyperclip

from vault import Vault


# ======================================================================= #
#  Colour palette & font constants                                         #
# ======================================================================= #

BG        = "#1e1e2e"
SURFACE   = "#2a2a3d"
ACCENT    = "#7c3aed"
ACCENT_H  = "#6d28d9"
TEXT      = "#e2e8f0"
SUBTEXT   = "#94a3b8"
RED       = "#ef4444"
GREEN     = "#22c55e"
YELLOW    = "#eab308"

FONT_H1   = ("Segoe UI", 18, "bold")
FONT_H2   = ("Segoe UI", 13, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 10)


def _style_entry(w: tk.Entry | tk.Text):
    w.configure(
        bg=SURFACE, fg=TEXT, insertbackground=TEXT,
        relief="flat", highlightthickness=1,
        highlightbackground=ACCENT, highlightcolor=ACCENT,
    )


def _btn(parent, text, command, bg=ACCENT, fg=TEXT, **kw):
    b = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=ACCENT_H, activeforeground=TEXT,
        font=FONT_BODY, relief="flat", padx=14, pady=6, cursor="hand2",
        **kw,
    )
    return b


# ======================================================================= #
#  Master-password screen                                                  #
# ======================================================================= #

class MasterPasswordScreen(tk.Toplevel):
    """
    Shown on startup.
    – First run : asks the user to create a master password (with confirmation).
    – Subsequent runs : asks the user to enter the existing master password.
    """

    def __init__(self, parent: tk.Tk, vault: Vault, on_success):
        super().__init__(parent)
        self._vault = vault
        self._on_success = on_success
        self._first_run = vault.is_first_run()

        self.title("Password Vault – Unlock")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()          # Modal behaviour
        self.protocol("WM_DELETE_WINDOW", self._quit)

        self._build()
        self._center()

    # ------------------------------------------------------------------ #

    def _build(self):
        pad = {"padx": 30, "pady": 10}

        tk.Label(self, text="🔐 Password Vault", font=FONT_H1,
                 bg=BG, fg=ACCENT).pack(pady=(30, 4))

        subtitle = "Create a master password" if self._first_run else "Enter master password"
        tk.Label(self, text=subtitle, font=FONT_BODY, bg=BG, fg=SUBTEXT).pack()

        # Password field
        tk.Label(self, text="Master Password", font=FONT_BODY,
                 bg=BG, fg=TEXT, anchor="w").pack(fill="x", **pad)
        self._pw_var = tk.StringVar()
        pw_entry = tk.Entry(self, textvariable=self._pw_var, show="•",
                            font=FONT_MONO, width=30)
        _style_entry(pw_entry)
        pw_entry.pack(**pad)
        pw_entry.focus()

        # Confirmation field (first-run only)
        if self._first_run:
            tk.Label(self, text="Confirm Password", font=FONT_BODY,
                     bg=BG, fg=TEXT, anchor="w").pack(fill="x", **pad)
            self._pw2_var = tk.StringVar()
            pw2_entry = tk.Entry(self, textvariable=self._pw2_var, show="•",
                                 font=FONT_MONO, width=30)
            _style_entry(pw2_entry)
            pw2_entry.pack(**pad)

        self._msg = tk.Label(self, text="", font=FONT_BODY, bg=BG, fg=RED)
        self._msg.pack()

        label = "Create Vault" if self._first_run else "Unlock Vault"
        _btn(self, label, self._submit).pack(pady=(6, 30))

        self.bind("<Return>", lambda _: self._submit())

    def _submit(self):
        pw = self._pw_var.get()
        if not pw:
            self._msg.config(text="Password cannot be empty.")
            return

        if self._first_run:
            pw2 = self._pw2_var.get()
            if pw != pw2:
                self._msg.config(text="Passwords do not match.")
                return
            if len(pw) < 6:
                self._msg.config(text="Password must be at least 6 characters.")
                return
            try:
                self._vault.setup_master_password(pw)
                self._on_success()
                self.destroy()
            except Exception as exc:
                self._msg.config(text=str(exc))
        else:
            ok = self._vault.unlock(pw)
            if ok:
                self._on_success()
                self.destroy()
            else:
                self._msg.config(text="Incorrect password. Try again.")

    def _quit(self):
        self.master.destroy()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


# ======================================================================= #
#  Add / Edit dialog                                                       #
# ======================================================================= #

class AddEditDialog(tk.Toplevel):
    """
    Modal dialog for adding or editing a credential.
    Pre-fills fields when *credential* dict is provided (edit mode).
    """

    def __init__(self, parent, vault: Vault, credential: dict | None = None, on_save=None):
        super().__init__(parent)
        self._vault = vault
        self._cred = credential
        self._on_save = on_save
        self._edit_mode = credential is not None

        self.title("Edit Credential" if self._edit_mode else "Add Credential")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()

        self._build()
        self._center()

    def _build(self):
        pad = {"padx": 24, "pady": 6}

        heading = "✏️  Edit Credential" if self._edit_mode else "➕  Add Credential"
        tk.Label(self, text=heading, font=FONT_H2, bg=BG, fg=ACCENT).pack(pady=(20, 4))

        fields = [("Site / App *", "site"), ("Username / Email *", "username")]
        self._vars: dict[str, tk.StringVar] = {}

        for label, key in fields:
            tk.Label(self, text=label, font=FONT_BODY, bg=BG, fg=SUBTEXT, anchor="w"
                     ).pack(fill="x", **pad)
            var = tk.StringVar(value=self._cred[key] if self._cred else "")
            entry = tk.Entry(self, textvariable=var, font=FONT_BODY, width=36)
            _style_entry(entry)
            entry.pack(**pad)
            self._vars[key] = var

        # Password row
        tk.Label(self, text="Password *", font=FONT_BODY, bg=BG, fg=SUBTEXT, anchor="w"
                 ).pack(fill="x", **pad)
        pw_frame = tk.Frame(self, bg=BG)
        pw_frame.pack(**pad)
        self._pw_var = tk.StringVar(value=self._cred["password"] if self._cred else "")
        self._pw_show = False
        self._pw_entry = tk.Entry(pw_frame, textvariable=self._pw_var, show="•",
                                  font=FONT_MONO, width=26)
        _style_entry(self._pw_entry)
        self._pw_entry.pack(side="left")
        _btn(pw_frame, "👁", self._toggle_pw, bg=SURFACE, pady=4).pack(side="left", padx=4)
        _btn(pw_frame, "⚙ Generate", self._open_generator, bg=SURFACE, pady=4).pack(side="left")

        # Strength label
        self._strength_lbl = tk.Label(self, text="", font=FONT_BODY, bg=BG)
        self._strength_lbl.pack()
        self._pw_var.trace_add("write", self._update_strength)
        self._update_strength()

        # Notes
        tk.Label(self, text="Notes", font=FONT_BODY, bg=BG, fg=SUBTEXT, anchor="w"
                 ).pack(fill="x", **pad)
        self._notes = tk.Text(self, height=3, width=36, font=FONT_BODY)
        _style_entry(self._notes)
        self._notes.pack(**pad)
        if self._cred and self._cred.get("notes"):
            self._notes.insert("1.0", self._cred["notes"])

        self._msg = tk.Label(self, text="", font=FONT_BODY, bg=BG, fg=RED)
        self._msg.pack()

        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(pady=(4, 20))
        _btn(btn_row, "Save", self._save).pack(side="left", padx=6)
        _btn(btn_row, "Cancel", self.destroy, bg=SURFACE).pack(side="left")

    def _toggle_pw(self):
        self._pw_show = not self._pw_show
        self._pw_entry.config(show="" if self._pw_show else "•")

    def _update_strength(self, *_):
        pw = self._pw_var.get()
        if not pw:
            self._strength_lbl.config(text="", fg=SUBTEXT)
            return
        strength = self._vault.password_strength(pw)
        colour = {
            "Weak": RED, "Fair": YELLOW, "Strong": GREEN, "Very Strong": GREEN
        }.get(strength, SUBTEXT)
        self._strength_lbl.config(text=f"Strength: {strength}", fg=colour)

    def _open_generator(self):
        def on_use(pw: str):
            self._pw_var.set(pw)
        GeneratorDialog(self, self._vault, on_use)

    def _save(self):
        site = self._vars["site"].get().strip()
        username = self._vars["username"].get().strip()
        password = self._pw_var.get()
        notes = self._notes.get("1.0", "end-1c").strip()

        try:
            if self._edit_mode:
                self._vault.update_credential(
                    self._cred["id"], site, username, password, notes
                )
            else:
                self._vault.add_credential(site, username, password, notes)

            if self._on_save:
                self._on_save()
            self.destroy()
        except ValueError as exc:
            self._msg.config(text=str(exc))

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


# ======================================================================= #
#  Password generator dialog                                               #
# ======================================================================= #

class GeneratorDialog(tk.Toplevel):
    """Standalone password generator with copy / use buttons."""

    def __init__(self, parent, vault: Vault, on_use=None):
        super().__init__(parent)
        self._vault = vault
        self._on_use = on_use

        self.title("Password Generator")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self._build()
        self._generate()
        self._center()

    def _build(self):
        pad = {"padx": 24, "pady": 6}

        tk.Label(self, text="⚙️  Password Generator", font=FONT_H2,
                 bg=BG, fg=ACCENT).pack(pady=(20, 4))

        # Length slider
        tk.Label(self, text="Length", font=FONT_BODY, bg=BG, fg=SUBTEXT).pack()
        self._length_var = tk.IntVar(value=16)
        slider = ttk.Scale(self, from_=8, to=40, variable=self._length_var,
                           orient="horizontal", length=220,
                           command=lambda _: self._update_length_label())
        slider.pack()
        self._length_lbl = tk.Label(self, text="16", font=FONT_BODY, bg=BG, fg=TEXT)
        self._length_lbl.pack()

        # Options
        self._upper = tk.BooleanVar(value=True)
        self._digits = tk.BooleanVar(value=True)
        self._symbols = tk.BooleanVar(value=True)

        for text, var in [("Uppercase letters", self._upper),
                          ("Digits", self._digits),
                          ("Symbols", self._symbols)]:
            tk.Checkbutton(self, text=text, variable=var, font=FONT_BODY,
                           bg=BG, fg=TEXT, selectcolor=SURFACE,
                           activebackground=BG, activeforeground=TEXT).pack(anchor="w", **pad)

        # Generated password display
        self._pw_var = tk.StringVar()
        pw_entry = tk.Entry(self, textvariable=self._pw_var, font=FONT_MONO,
                            width=30, state="readonly")
        _style_entry(pw_entry)
        pw_entry.pack(**pad)

        self._strength_lbl = tk.Label(self, text="", font=FONT_BODY, bg=BG)
        self._strength_lbl.pack()

        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(pady=(4, 20))
        _btn(btn_row, "🔄 Generate", self._generate).pack(side="left", padx=4)
        _btn(btn_row, "📋 Copy", self._copy, bg=SURFACE).pack(side="left", padx=4)
        if self._on_use:
            _btn(btn_row, "✅ Use This", self._use, bg=GREEN, fg="#000").pack(side="left", padx=4)

    def _update_length_label(self):
        length = self._length_var.get()
        self._length_lbl.config(text=str(length))

    def _generate(self):
        try:
            pw = self._vault.generate_password(
                length=self._length_var.get(),
                use_uppercase=self._upper.get(),
                use_digits=self._digits.get(),
                use_symbols=self._symbols.get(),
            )
            self._pw_var.set(pw)
            strength = self._vault.password_strength(pw)
            colour = {
                "Weak": RED, "Fair": YELLOW, "Strong": GREEN, "Very Strong": GREEN
            }.get(strength, SUBTEXT)
            self._strength_lbl.config(text=f"Strength: {strength}", fg=colour)
        except ValueError as exc:
            messagebox.showerror("Generator Error", str(exc), parent=self)

    def _copy(self):
        try:
            pyperclip.copy(self._pw_var.get())
            messagebox.showinfo("Copied", "Password copied to clipboard!", parent=self)
        except Exception:
            messagebox.showinfo("Password", self._pw_var.get(), parent=self)

    def _use(self):
        if self._on_use:
            self._on_use(self._pw_var.get())
        self.destroy()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


# ======================================================================= #
#  Main application screen                                                 #
# ======================================================================= #

class MainScreen:
    """
    The primary vault management interface.
    Displayed after the user successfully unlocks the vault.
    """

    def __init__(self, root: tk.Tk, vault: Vault):
        self._root = root
        self._vault = vault
        self._all_creds: list[dict] = []
        self._build()
        self._refresh()

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #

    def _build(self):
        self._root.title("🔐 Password Vault")
        self._root.configure(bg=BG)
        self._root.minsize(820, 540)

        # ── Top bar ──────────────────────────────────────────────────── #
        top = tk.Frame(self._root, bg=SURFACE, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="🔐 Password Vault", font=FONT_H1,
                 bg=SURFACE, fg=ACCENT).pack(side="left", padx=20)

        btn_frame = tk.Frame(top, bg=SURFACE)
        btn_frame.pack(side="right", padx=10)

        _btn(btn_frame, "➕ Add",     self._open_add).pack(side="left", padx=4)
        _btn(btn_frame, "⚙ Generate", self._open_generator, bg=SURFACE).pack(side="left", padx=4)
        _btn(btn_frame, "📤 Export",  self._export, bg=SURFACE).pack(side="left", padx=4)
        _btn(btn_frame, "🔒 Lock",    self._lock, bg=RED).pack(side="left", padx=4)

        # ── Search bar ────────────────────────────────────────────────── #
        search_frame = tk.Frame(self._root, bg=BG, pady=8)
        search_frame.pack(fill="x", padx=16)

        tk.Label(search_frame, text="🔍", font=FONT_BODY, bg=BG, fg=SUBTEXT
                 ).pack(side="left")
        self._search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self._search_var,
                                font=FONT_BODY, width=40)
        _style_entry(search_entry)
        search_entry.pack(side="left", padx=6)
        self._search_var.trace_add("write", lambda *_: self._filter())
        _btn(search_frame, "✕ Clear", self._clear_search, bg=SURFACE, pady=3
             ).pack(side="left")

        self._count_lbl = tk.Label(search_frame, text="", font=FONT_BODY,
                                   bg=BG, fg=SUBTEXT)
        self._count_lbl.pack(side="right", padx=10)

        # ── Treeview ──────────────────────────────────────────────────── #
        cols = ("ID", "Site", "Username", "Notes", "Updated")
        self._tree = ttk.Treeview(self._root, columns=cols, show="headings",
                                  selectmode="browse")

        widths = {"ID": 40, "Site": 200, "Username": 180, "Notes": 240, "Updated": 130}
        for col in cols:
            self._tree.heading(col, text=col,
                               command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=widths[col], anchor="w")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=SURFACE, fieldbackground=SURFACE,
                        foreground=TEXT, rowheight=28, font=FONT_BODY)
        style.configure("Treeview.Heading",
                        background=ACCENT, foreground=TEXT, font=FONT_BODY)
        style.map("Treeview", background=[("selected", ACCENT)])

        vsb = ttk.Scrollbar(self._root, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 4))
        self._tree.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Double-click → view password; right-click → context menu
        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<Button-3>", self._on_right_click)

        # ── Status bar ────────────────────────────────────────────────── #
        self._status = tk.Label(self._root, text="", font=FONT_BODY,
                                bg=SURFACE, fg=SUBTEXT, anchor="w")
        self._status.pack(fill="x", padx=16, pady=(0, 4))

        # Context menu
        self._ctx = tk.Menu(self._root, tearoff=0, bg=SURFACE, fg=TEXT,
                            activebackground=ACCENT)
        self._ctx.add_command(label="👁 View Password",  command=self._view_password)
        self._ctx.add_command(label="📋 Copy Password", command=self._copy_password)
        self._ctx.add_separator()
        self._ctx.add_command(label="✏️  Edit",          command=self._open_edit)
        self._ctx.add_command(label="🗑  Delete",        command=self._delete)

    # ------------------------------------------------------------------ #
    #  Data helpers                                                        #
    # ------------------------------------------------------------------ #

    def _refresh(self):
        self._all_creds = self._vault.get_all_credentials()
        self._filter()

    def _filter(self):
        query = self._search_var.get().strip().lower()
        if query:
            creds = [
                c for c in self._all_creds
                if query in c["site"].lower() or query in c["username"].lower()
            ]
        else:
            creds = self._all_creds

        self._tree.delete(*self._tree.get_children())
        for c in creds:
            notes_preview = (c["notes"][:30] + "…") if len(c["notes"]) > 30 else c["notes"]
            updated = c["updated_at"][:16] if c["updated_at"] else ""
            self._tree.insert("", "end", iid=str(c["id"]),
                              values=(c["id"], c["site"], c["username"],
                                      notes_preview, updated))

        self._count_lbl.config(text=f"{len(creds)} entr{'y' if len(creds)==1 else 'ies'}")

    def _clear_search(self):
        self._search_var.set("")

    def _sort_by(self, col: str):
        items = [(self._tree.set(k, col), k) for k in self._tree.get_children()]
        items.sort(key=lambda t: t[0].lower())
        for i, (_, k) in enumerate(items):
            self._tree.move(k, "", i)

    # ------------------------------------------------------------------ #
    #  Selected credential                                                 #
    # ------------------------------------------------------------------ #

    def _selected_id(self) -> int | None:
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _selected_cred(self) -> dict | None:
        cid = self._selected_id()
        if cid is None:
            messagebox.showwarning("No Selection", "Please select a credential first.")
            return None
        return next((c for c in self._all_creds if c["id"] == cid), None)

    # ------------------------------------------------------------------ #
    #  Actions                                                             #
    # ------------------------------------------------------------------ #

    def _on_double_click(self, _event):
        self._view_password()

    def _on_right_click(self, event):
        row = self._tree.identify_row(event.y)
        if row:
            self._tree.selection_set(row)
            self._ctx.tk_popup(event.x_root, event.y_root)

    def _view_password(self):
        cred = self._selected_cred()
        if not cred:
            return
        detail = (
            f"Site     : {cred['site']}\n"
            f"Username : {cred['username']}\n"
            f"Password : {cred['password']}\n"
            f"Notes    : {cred['notes'] or '—'}"
        )
        messagebox.showinfo(f"🔑 {cred['site']}", detail)

    def _copy_password(self):
        cred = self._selected_cred()
        if not cred:
            return
        try:
            pyperclip.copy(cred["password"])
            self._status.config(text=f"Password for '{cred['site']}' copied to clipboard.")
        except Exception:
            messagebox.showinfo("Password", cred["password"])

    def _open_add(self):
        AddEditDialog(self._root, self._vault, on_save=self._refresh)

    def _open_edit(self):
        cred = self._selected_cred()
        if cred:
            AddEditDialog(self._root, self._vault, credential=cred, on_save=self._refresh)

    def _delete(self):
        cred = self._selected_cred()
        if not cred:
            return
        if messagebox.askyesno("Confirm Delete",
                               f"Delete credentials for '{cred['site']}'?\n"
                               "This cannot be undone."):
            self._vault.delete_credential(cred["id"])
            self._refresh()
            self._status.config(text=f"Deleted credentials for '{cred['site']}'.")

    def _open_generator(self):
        GeneratorDialog(self._root, self._vault)

    def _export(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Export vault backup",
        )
        if not filepath:
            return
        try:
            count = self._vault.export_to_file(filepath)
            messagebox.showinfo("Export Complete",
                                f"Exported {count} credentials to:\n{filepath}\n\n"
                                "⚠️  This file contains plain-text passwords. "
                                "Store it securely!")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _lock(self):
        self._vault.lock()
        self._tree.delete(*self._tree.get_children())
        self._status.config(text="Vault locked.")
        self._restart_auth()

    def _restart_auth(self):
        for w in self._root.winfo_children():
            w.destroy()
        _launch_auth(self._root, self._vault)


# ======================================================================= #
#  Bootstrap helpers                                                       #
# ======================================================================= #

def _launch_auth(root: tk.Tk, vault: Vault):
    """Show master-password screen; on success rebuild the main screen."""
    def on_success():
        MainScreen(root, vault)

    root.withdraw()                     # Hide root while auth dialog is shown
    screen = MasterPasswordScreen(root, vault, on_success)
    screen.protocol("WM_DELETE_WINDOW", root.destroy)
    screen.wait_window()
    root.deiconify()


def launch():
    """Entry-point called by main.py."""
    vault = Vault()
    root = tk.Tk()
    root.withdraw()

    # Apply dark theme to root early so it doesn't flash white
    root.configure(bg=BG)

    _launch_auth(root, vault)

    try:
        root.mainloop()
    finally:
        vault.close()
