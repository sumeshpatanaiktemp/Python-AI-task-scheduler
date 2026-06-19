import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from ai.schedule import generate_telegram_message
from reminders.telegram import send_telegram_message
import threading

# ── Theme colours (must match app.py) ────────────────────────────────────────
BG_DARK     = "#090E17"
BG_MID      = "#151E2E"
BG_CARD     = "#1F2937"
ACCENT      = "#8B5CF6"
ACCENT2     = "#10B981"
ACCENT3     = "#F43F5E"
TEXT_BRIGHT = "#F9FAFB"
TEXT_DIM    = "#9CA3AF"
BORDER      = "#334155"
ENTRY_BG    = "#0F172A"


class RoundedCard(tk.Canvas):
    def __init__(self, parent, bg=BG_CARD, border_color=BORDER, radius=12, **kwargs):
        super().__init__(parent, bg=parent["bg"], bd=0, highlightthickness=0, **kwargs)
        self.radius = radius
        self.bg_color = bg
        self.border_color = border_color
        
        self.inner_frame = tk.Frame(self, bg=bg)
        self.inner_id = self.create_window(0, 0, window=self.inner_frame, anchor="nw")
        self.bind("<Configure>", self._on_resize)
        
    def _on_resize(self, event):
        w, h = event.width, event.height
        self.delete("bg")
        r = self.radius
        
        # Rounded rectangle points
        points = [
            r, 0,
            w - r, 0,
            w, 0,
            w, r,
            w, h - r,
            w, h,
            w - r, h,
            r, h,
            0, h,
            0, h - r,
            0, r,
            0, 0
        ]
        
        self.create_polygon(points, smooth=True, fill=self.bg_color, tags="bg")
        if self.border_color:
            self.create_polygon(points, smooth=True, fill="", outline=self.border_color, width=1, tags="bg")
            
        pad = r // 2
        self.coords(self.inner_id, pad, pad)
        self.itemconfig(self.inner_id, width=w - 2 * pad, height=h - 2 * pad)


class TaskSummaryTab:
    def __init__(self, parent, db, calendar_tab):
        self.db = db
        self.calendar_tab = calendar_tab
        self.on_change = None

        self.frame = tk.Frame(parent, bg=BG_DARK)

        # ── Header row ────────────────────────────────────────────────────────
        header = tk.Frame(self.frame, bg=BG_DARK)
        header.pack(fill="x", padx=14, pady=(14, 8))

        tk.Label(header, text="📊  Daily Tasks Summary",
                 font=("Segoe UI", 14, "bold"),
                 fg=TEXT_BRIGHT, bg=BG_DARK).pack(side="left")

        # Daily limit control
        self.daily_limit_var = tk.DoubleVar(value=self.db.get_daily_limit())
        limit_frame = tk.Frame(header, bg=BG_DARK)
        limit_frame.pack(side="right")
        tk.Label(limit_frame, text="Daily limit (hrs):",
                 font=("Segoe UI", 10), fg=TEXT_DIM, bg=BG_DARK).pack(side="left")
        self.spin = ttk.Spinbox(
            limit_frame, from_=1.0, to=24.0, increment=0.5,
            textvariable=self.daily_limit_var, width=6,
            command=self.on_daily_limit_changed)
        self.spin.pack(side="left", padx=(6, 0))
        self.spin.bind("<FocusOut>", lambda e: self.on_daily_limit_changed())
        self.spin.bind("<Return>", lambda e: self.on_daily_limit_changed())

        # ── Date picker row ───────────────────────────────────────────────────
        date_row = tk.Frame(self.frame, bg=BG_DARK)
        date_row.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(date_row, text="Select Date:",
                 font=("Segoe UI", 10, "bold"),
                 fg=TEXT_DIM, bg=BG_DARK).pack(side="left", padx=(0, 6))
        
        self.date_picker = DateEntry(date_row, date_pattern="yyyy-mm-dd",
                                     background=BG_MID, foreground=TEXT_BRIGHT,
                                     bordercolor=BORDER, headersbackground=BG_MID,
                                     headersforeground=TEXT_BRIGHT, selectbackground=ACCENT,
                                     selectforeground=TEXT_BRIGHT, normalbackground="#FFFFFF",
                                     normalforeground="#111827", weekendbackground="#F9FAFB",
                                     weekendforeground="#EF4444", othermonthforeground="#9CA3AF",
                                     othermonthbackground="#F3F4F6", othermonthweforeground="#9CA3AF",
                                     othermonthwebackground="#F3F4F6", cursor="hand2")
        self.date_picker.pack(side="left")
        self.date_picker.bind("<<DateEntrySelected>>", lambda e: self.refresh_view())

        # ── Stats cards ───────────────────────────────────────────────────────
        stats_row = tk.Frame(self.frame, bg=BG_DARK)
        stats_row.pack(fill="x", padx=14, pady=(0, 8))

        CARD_PAD_X = 8
        CARD_PAD_Y = 4
        CARD_RADIUS = 8
        TITLE_FONT = ("Segoe UI", 7, "bold")
        VALUE_FONT = ("Segoe UI", 15, "bold")

        # ── Task count card ───────────────────────────────────────────────────
        c1 = RoundedCard(
            stats_row,
            bg=BG_CARD,
            border_color=ACCENT,
            radius=CARD_RADIUS,
            width=120,
            height=70
        )
        c1.pack(side="left", padx=(0, 8), ipadx=CARD_PAD_X, ipady=CARD_PAD_Y)

        tk.Label(
            c1.inner_frame,
            text="📝 TASKS",
            font=TITLE_FONT,
            fg=TEXT_DIM,
            bg=BG_CARD
        ).pack(anchor="w", pady=(0, 1))

        self.task_count_label = tk.Label(
            c1.inner_frame,
            text="0",
            font=VALUE_FONT,
            fg=ACCENT,
            bg=BG_CARD
        )
        self.task_count_label.pack(anchor="w")

        # ── Duration card ─────────────────────────────────────────────────────
        c2 = RoundedCard(
            stats_row,
            bg=BG_CARD,
            border_color=ACCENT2,
            radius=CARD_RADIUS,
            width=150,
            height=70
        )
        c2.pack(side="left", padx=(0, 8), ipadx=CARD_PAD_X, ipady=CARD_PAD_Y)

        tk.Label(
            c2.inner_frame,
            text="⏱ DURATION",
            font=TITLE_FONT,
            fg=TEXT_DIM,
            bg=BG_CARD
        ).pack(anchor="w", pady=(0, 1))

        self.duration_label = tk.Label(
            c2.inner_frame,
            text="0.0 / 6.0 hrs",
            font=VALUE_FONT,
            fg=ACCENT2,
            bg=BG_CARD
        )
        self.duration_label.pack(anchor="w")

        # ── Capacity card ─────────────────────────────────────────────────────
        c3 = RoundedCard(
            stats_row,
            bg=BG_CARD,
            border_color=ACCENT3,
            radius=CARD_RADIUS,
            width=150,
            height=70
        )
        c3.pack(side="left", padx=(0, 8), ipadx=CARD_PAD_X, ipady=CARD_PAD_Y)

        tk.Label(
            c3.inner_frame,
            text="🔋 CAPACITY",
            font=TITLE_FONT,
            fg=TEXT_DIM,
            bg=BG_CARD
        ).pack(anchor="w", pady=(0, 1))

        self.capacity_label = tk.Label(
            c3.inner_frame,
            text="Free",
            font=VALUE_FONT,
            fg=ACCENT3,
            bg=BG_CARD
        )
        self.capacity_label.pack(anchor="w")

        # ── Progress bar ──────────────────────────────────────────────────────
        bar_frame = tk.Frame(self.frame, bg=BG_DARK)
        bar_frame.pack(fill="x", padx=14, pady=(0, 10))
        self.progress_canvas = tk.Canvas(bar_frame, height=12,
                                          bg=BG_DARK, bd=0,
                                          highlightthickness=0)
        self.progress_canvas.pack(fill="x")
        self.progress_canvas.bind("<Configure>", lambda e: self.draw_progress_bar())

        # ── Treeview card ─────────────────────────────────────────────────────
        tree_card = RoundedCard(self.frame, bg=BG_CARD, border_color=BORDER, radius=16)
        tree_card.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        tk.Label(tree_card.inner_frame, text="📋  Tasks for Selected Date",
                 font=("Segoe UI", 11, "bold"),
                 fg=ACCENT, bg=BG_CARD).pack(anchor="w", padx=10, pady=(8, 4))

        self.tree = ttk.Treeview(
            tree_card.inner_frame,
            columns=("id", "title", "duration", "reminder", "chat_id"),
            show="headings", selectmode="none", height=5,
        )
        self.tree.heading("id",       text="ID")
        self.tree.heading("title",    text="Title")
        self.tree.heading("duration", text="Duration (hrs)")
        self.tree.heading("reminder", text="Reminder Time")
        self.tree.heading("chat_id",  text="Telegram Chat ID")
        self.tree.column("id",       width=50,  anchor="center")
        self.tree.column("title",    width=320)
        self.tree.column("duration", width=100, anchor="center")
        self.tree.column("reminder", width=120, anchor="center")
        self.tree.column("chat_id",  width=150, anchor="center")
        self.tree.tag_configure("even", background=BG_CARD)
        self.tree.tag_configure("odd",  background=ENTRY_BG)
        self.tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # ── Telegram message card ─────────────────────────────────────────────
        tg_card = RoundedCard(self.frame, bg=BG_CARD, border_color=BORDER, radius=16)
        tg_card.pack(fill="x", padx=14, pady=(0, 10))

        tk.Label(tg_card.inner_frame, text="💬  Plan Summary (Telegram Message)",
                 font=("Segoe UI", 11, "bold"),
                 fg=ACCENT, bg=BG_CARD).pack(anchor="w", padx=10, pady=(8, 4))

        self.summary_text = tk.Text(
            tg_card.inner_frame, height=5, wrap="word",
            bg=ENTRY_BG, fg=TEXT_BRIGHT,
            insertbackground=TEXT_BRIGHT,
            relief="flat", font=("Segoe UI", 10),
            highlightbackground=BORDER, highlightthickness=1)
        self.summary_text.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.summary_text.configure(state="disabled")

        def make_interactive_entry(entry):
            def on_focus_in(e):
                entry.config(highlightbackground=ACCENT)
            def on_focus_out(e):
                entry.config(highlightbackground=BORDER)
            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)
        make_interactive_entry(self.summary_text)

        btn_row = tk.Frame(tg_card.inner_frame, bg=BG_CARD)
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        self.btn_generate = ttk.Button(btn_row,
            text="⚡  Generate Message",
            command=self.generate_telegram_message_action)
        self.btn_generate.pack(side="left", padx=(0, 8))
        self.btn_send = ttk.Button(btn_row,
            text="📤  Send to Telegram", style="Accent2.TButton",
            command=self.send_telegram_messages)
        self.btn_send.pack(side="left")

        self.refresh_view()

    # ── Daily limit ───────────────────────────────────────────────────────────
    def on_daily_limit_changed(self):
        try:
            val = float(self.daily_limit_var.get())
            if val <= 0.0:
                raise ValueError()
            if val > 24.0:
                val = 24.0
                self.daily_limit_var.set(24.0)
            self.db.set_setting("daily_limit", val)
            self.refresh_view()
            if self.on_change:
                self.on_change()
        except ValueError:
            messagebox.showerror("Invalid Input",
                                 "Daily limit must be a number between 1 and 24.")
            self.daily_limit_var.set(self.db.get_daily_limit())

    # ── Refresh ───────────────────────────────────────────────────────────────
    def refresh_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            selected_date = self.date_picker.get_date().isoformat()
        except Exception:
            return

        tasks = self.db.get_tasks_for_date(selected_date)
        total_duration = self.db.get_total_duration_for_date(selected_date)
        daily_limit = self.db.get_daily_limit()

        # Stats
        self.task_count_label.config(text=str(len(tasks)))
        self.duration_label.config(text=f"{total_duration:.1f} / {daily_limit:.1f} hrs")

        remaining = max(0.0, daily_limit - total_duration)
        if remaining > 0:
            self.capacity_label.config(text=f"{remaining:.1f} hrs left", fg=ACCENT2)
        else:
            self.capacity_label.config(text="Fully Booked", fg=ACCENT3)

        # Draw progress bar
        self.draw_progress_bar()

        # Treeview
        for idx, task in enumerate(tasks):
            dur = task.get("estimated_duration") or 0.0
            rem = task.get("reminder_time") or "Not set"
            cid = task.get("chat_id") or ""
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end",
                values=(task["id"], task["title"], f"{dur:.1f}", rem, cid),
                tags=(tag,))

    # ── Draw Progress Bar ─────────────────────────────────────────────────────
    def draw_progress_bar(self):
        self.progress_canvas.delete("all")
        w = self.progress_canvas.winfo_width()
        if w <= 1:
            w = 400

        try:
            selected_date = self.date_picker.get_date().isoformat()
        except Exception:
            return

        total_duration = self.db.get_total_duration_for_date(selected_date)
        daily_limit = self.db.get_daily_limit()
        pct = min(total_duration / daily_limit, 1.0) if daily_limit > 0 else 0
        color = ACCENT2 if pct < 0.75 else ("#FFA000" if pct < 1.0 else ACCENT3)

        # Draw background track
        self.progress_canvas.create_line(6, 6, w - 6, 6, width=12, fill=BORDER, capstyle="round")
        # Draw fill indicator
        if pct > 0:
            fill_end = 6 + (w - 12) * pct
            if fill_end > 6:
                self.progress_canvas.create_line(6, 6, fill_end, 6, width=12, fill=color, capstyle="round")

    # ── Telegram generate ─────────────────────────────────────────────────────
    def generate_telegram_message_action(self):
        selected_date = self.date_picker.get_date().isoformat()
        tasks = self.db.get_tasks_for_date(selected_date)
        if not tasks:
            messagebox.showinfo("Generate Telegram Message",
                                f"No tasks on {selected_date}.")
            return
        daily_limit = self.db.get_daily_limit()
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "⏳ Generating Telegram message …")
        self.summary_text.configure(state="disabled")
        self.btn_generate.config(state="disabled")
        self.btn_send.config(state="disabled")

        def run():
            try:
                msg = generate_telegram_message(tasks, daily_limit=daily_limit)
                self.frame.after(0, lambda: self._show_msg(msg))
            except Exception as e:
                self.frame.after(0, lambda: self._show_msg(f"Error: {e}"))

        threading.Thread(target=run, daemon=True).start()

    def _show_msg(self, message):
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, message)
        self.summary_text.configure(state="disabled")
        self.btn_generate.config(state="normal")
        self.btn_send.config(state="normal")

    # ── Telegram send ─────────────────────────────────────────────────────────
    def send_telegram_messages(self):
        selected_date = self.date_picker.get_date().isoformat()
        tasks = self.db.get_tasks_for_date(selected_date)
        if not tasks:
            messagebox.showinfo("Send Telegram", "No tasks on this date to send.")
            return
        txt = self.summary_text.get("1.0", tk.END).strip()
        if not txt or txt.startswith("⏳") or txt.startswith("Error"):
            messagebox.showwarning("Send Telegram",
                                   "Please generate a valid message first.")
            return
        chat_ids = set(t.get("chat_id") for t in tasks if t.get("chat_id"))
        if not chat_ids:
            messagebox.showwarning("Send Telegram",
                                   "No tasks on this date have a Telegram chat ID.")
            return
        failed = []
        for cid in chat_ids:
            try:
                send_telegram_message(cid, txt)
            except Exception as exc:
                failed.append(f"{cid}: {exc}")
        if failed:
            messagebox.showerror("Send Telegram",
                                 f"Some messages failed:\n{'; '.join(failed)}")
        else:
            messagebox.showinfo("Send Telegram",
                                f"Sent reminders to chat IDs: {', '.join(chat_ids)}")
