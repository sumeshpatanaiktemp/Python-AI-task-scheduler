import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from ai.normalize import normalize_task
from datetime import date as _today_cls

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


class TasksTab:
    def __init__(self, parent, db, calendar_tab):
        self.db = db
        self.calendar_tab = calendar_tab
        self.on_task_change = None

        self.frame = tk.Frame(parent, bg=BG_DARK)

        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self.frame, bg=BG_DARK)
        header.pack(fill="x", padx=14, pady=(14, 6))

        tk.Label(header, text="✅  Task Manager",
                 font=("Segoe UI", 14, "bold"),
                 fg=TEXT_BRIGHT, bg=BG_DARK).pack(side="left")

        # ── Button strip ──────────────────────────────────────────────────────
        btn_frame = tk.Frame(self.frame, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=14, pady=(0, 10))

        ttk.Button(btn_frame, text="➕  Add Task",
                   command=self.show_add_task_dialog).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="✏️  Edit Task", style="Accent2.TButton",
                   command=self.show_edit_task_dialog).pack(side="left", padx=8)
        ttk.Button(btn_frame, text="🗑  Delete Task", style="Danger.TButton",
                   command=self.delete_selected_task).pack(side="left", padx=8)

        # ── Treeview card ─────────────────────────────────────────────────────
        tree_card = RoundedCard(self.frame, bg=BG_CARD, border_color=BORDER, radius=16)
        tree_card.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.task_tree = ttk.Treeview(
            tree_card.inner_frame,
            columns=("id", "title", "due", "duration", "reminder", "chat_id"),
            show="headings",
            selectmode="browse",
            height=16,
        )
        self.task_tree.heading("id",       text="ID")
        self.task_tree.heading("title",    text="Title")
        self.task_tree.heading("due",      text="Deadline")
        self.task_tree.heading("duration", text="Hours")
        self.task_tree.heading("reminder", text="Reminder")
        self.task_tree.heading("chat_id",  text="Chat ID")

        self.task_tree.column("id",       width=45,  anchor="center")
        self.task_tree.column("title",    width=310)
        self.task_tree.column("due",      width=110, anchor="center")
        self.task_tree.column("duration", width=70,  anchor="center")
        self.task_tree.column("reminder", width=100, anchor="center")
        self.task_tree.column("chat_id",  width=140, anchor="center")

        # Alternating row colours via tags
        self.task_tree.tag_configure("even", background=BG_CARD)
        self.task_tree.tag_configure("odd",  background=ENTRY_BG)

        self.task_tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.load_tasks()

    # ── Load / refresh ────────────────────────────────────────────────────────
    def load_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        self.tasks = self.db.get_all_tasks()
        for idx, task in enumerate(self.tasks):
            deadline = task.get("deadline_date") or f"Week {task.get('deadline_week')}"
            duration = task.get("estimated_duration") or "?"
            reminder = task.get("reminder_time") or "Not set"
            chat_id  = task.get("chat_id") or ""
            tag = "even" if idx % 2 == 0 else "odd"
            self.task_tree.insert(
                "", "end",
                values=(task["id"], task["title"], deadline, duration, reminder, chat_id),
                tags=(tag,),
            )

    # ── Add / Edit dialogs ────────────────────────────────────────────────────
    def show_add_task_dialog(self):
        self.show_task_dialog()

    def show_edit_task_dialog(self):
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("Edit Task", "Please select a task first.")
            return
        item_id = selection[0]
        values = self.task_tree.item(item_id, "values")
        task_id = int(values[0])
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if task:
            self.show_task_dialog(task)

    def show_task_dialog(self, task=None):
        dialog = tk.Toplevel(self.frame)
        dialog.title("Add Task" if task is None else "Edit Task")
        dialog.geometry("560x540")
        dialog.configure(bg=BG_CARD)
        dialog.transient(self.frame)
        dialog.grab_set()

        # Accent bar at top
        tk.Frame(dialog, bg=ACCENT, height=4).pack(fill="x")

        header_text = "➕  New Task" if task is None else "✏️  Edit Task"
        tk.Label(dialog, text=header_text,
                 font=("Segoe UI", 14, "bold"),
                 fg=TEXT_BRIGHT, bg=BG_CARD).pack(anchor="w", padx=18, pady=(14, 8))

        container = tk.Frame(dialog, bg=BG_CARD, padx=18, pady=4)
        container.pack(fill="both", expand=True)

        def make_interactive_entry(entry):
            def on_focus_in(e):
                entry.config(highlightbackground=ACCENT)
            def on_focus_out(e):
                entry.config(highlightbackground=BORDER)
            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)

        def _label(parent, text, row, col=0):
            lbl = tk.Label(parent, text=text,
                           font=("Segoe UI", 10, "bold"),
                           fg=TEXT_DIM, bg=BG_CARD)
            lbl.grid(row=row, column=col, sticky="w", pady=(6, 3))
            return lbl

        def _entry(parent, row, width=48):
            e = tk.Entry(parent, width=width,
                         bg=ENTRY_BG, fg=TEXT_BRIGHT,
                         insertbackground=TEXT_BRIGHT,
                         relief="flat", font=("Segoe UI", 10),
                         highlightbackground=BORDER, highlightthickness=1)
            e.grid(row=row, column=1, sticky="ew", pady=(6, 3))
            make_interactive_entry(e)
            return e

        # Fields
        _label(container, "Title:", 0)
        title_entry = _entry(container, 0)

        _label(container, "Description:", 1)
        description_entry = tk.Text(container, width=48, height=6, wrap="word",
                                     bg=ENTRY_BG, fg=TEXT_BRIGHT,
                                     insertbackground=TEXT_BRIGHT,
                                     relief="flat", font=("Segoe UI", 10),
                                     highlightbackground=BORDER, highlightthickness=1)
        description_entry.grid(row=1, column=1, sticky="ew", pady=(6, 3))
        make_interactive_entry(description_entry)

        _label(container, "Deadline type:", 2)
        deadline_type = tk.StringVar(value="specific")
        type_frame = tk.Frame(container, bg=BG_CARD)
        type_frame.grid(row=2, column=1, sticky="w", pady=(6, 3))
        tk.Radiobutton(type_frame, text="Specific Date", variable=deadline_type,
                       value="specific", bg=BG_CARD, fg=TEXT_BRIGHT,
                       selectcolor=ENTRY_BG, activebackground=BG_CARD,
                       activeforeground=ACCENT, font=("Segoe UI", 10)).pack(side="left")
        tk.Radiobutton(type_frame, text="Week of Month", variable=deadline_type,
                       value="week", bg=BG_CARD, fg=TEXT_BRIGHT,
                       selectcolor=ENTRY_BG, activebackground=BG_CARD,
                       activeforeground=ACCENT, font=("Segoe UI", 10)).pack(side="left", padx=(16, 0))

        _label(container, "Select date:", 3)
        date_picker = DateEntry(container, date_pattern="yyyy-mm-dd",
                                mindate=_today_cls.today(),
                                background=BG_MID, foreground=TEXT_BRIGHT,
                                bordercolor=BORDER, headersbackground=BG_MID,
                                headersforeground=TEXT_BRIGHT, selectbackground=ACCENT,
                                selectforeground=TEXT_BRIGHT, normalbackground="#FFFFFF",
                                normalforeground="#111827", weekendbackground="#F9FAFB",
                                weekendforeground="#EF4444", othermonthforeground="#9CA3AF",
                                othermonthbackground="#F3F4F6", othermonthweforeground="#9CA3AF",
                                othermonthwebackground="#F3F4F6", cursor="hand2")
        date_picker.grid(row=3, column=1, sticky="w", pady=(6, 3))

        _label(container, "Week number:", 4)
        week_spin = ttk.Spinbox(container, from_=1, to=4, width=6)
        week_spin.grid(row=4, column=1, sticky="w", pady=(6, 3))

        _label(container, "Reminder time:", 5)
        reminder_entry = _entry(container, 5, 18)

        _label(container, "Telegram chat ID:", 6)
        chat_id_entry = _entry(container, 6, 30)

        _label(container, "Est. duration (hrs):", 7)
        duration_entry = _entry(container, 7, 18)

        if task:
            title_entry.insert(0, task["title"])
            description_entry.insert("1.0", task.get("description", ""))
            if task.get("deadline_date"):
                deadline_type.set("specific")
                date_picker.set_date(task["deadline_date"])
            else:
                deadline_type.set("week")
                week_spin.delete(0, tk.END)
                week_spin.insert(0, task.get("deadline_week", 1))
            reminder_entry.insert(0, task.get("reminder_time") or "")
            chat_id_entry.insert(0, task.get("chat_id") or "")
            duration_entry.insert(0, task.get("estimated_duration") or "")

        def save_task():
            title = title_entry.get().strip()
            description = description_entry.get("1.0", tk.END).strip()
            selected_type = deadline_type.get()
            deadline_date = date_picker.get_date().isoformat() if selected_type == "specific" else None
            deadline_week = int(week_spin.get()) if selected_type == "week" else None
            reminder_time = reminder_entry.get().strip() or None
            chat_id = chat_id_entry.get().strip() or None
            estimated_duration = duration_entry.get().strip()

            if not title:
                messagebox.showwarning("Validation", "Title cannot be blank.")
                return
            if not estimated_duration:
                estimated_duration = self.fetch_estimated_duration(description or title)

            try:
                estimated_duration = float(estimated_duration)
            except ValueError:
                messagebox.showwarning("Validation", "Estimated duration must be a number.")
                return

            if deadline_date:
                # Restrict past dates
                if deadline_date < _today_cls.today().isoformat():
                    messagebox.showerror(
                        "Invalid Date",
                        f"Deadline date {deadline_date} is in the past. Please choose today or a future date."
                    )
                    return

                exclude_id = task["id"] if task else None
                total_existing = self.db.get_total_duration_for_date(deadline_date, exclude_id)
                daily_limit = self.db.get_daily_limit()
                if total_existing + estimated_duration > daily_limit:
                    messagebox.showerror(
                        "Daily Limit Exceeded",
                        f"Cannot save task. Total estimated duration for {deadline_date} "
                        f"would be {total_existing + estimated_duration:.1f} hours, "
                        f"which exceeds the daily limit of {daily_limit:.1f} hours."
                    )
                    return

            if task:
                self.db.update_task(task["id"], title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration)
            else:
                self.db.add_task(title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration)

            dialog.destroy()
            self.load_tasks()
            if self.on_task_change:
                self.on_task_change()

        # Action buttons
        action_frame = tk.Frame(container, bg=BG_CARD)
        action_frame.grid(row=8, column=0, columnspan=2, pady=(18, 6))
        ttk.Button(action_frame, text="💾  Save Task",
                   command=save_task).pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="Cancel", style="Danger.TButton",
                   command=dialog.destroy).pack(side="left")

        container.columnconfigure(1, weight=1)

    def fetch_estimated_duration(self, description):
        try:
            return normalize_task(description)
        except Exception:
            return 1.0

    # ── Delete ────────────────────────────────────────────────────────────────
    def delete_selected_task(self):
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("Delete Task", "Please select a task first.")
            return
        item_id = selection[0]
        values = self.task_tree.item(item_id, "values")
        task_id = int(values[0])
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            return
        confirm = messagebox.askyesno("Delete Task", f"Delete task '{task['title']}'?")
        if not confirm:
            return
        self.db.delete_task(task["id"])
        self.load_tasks()
        if self.on_task_change:
            self.on_task_change()
