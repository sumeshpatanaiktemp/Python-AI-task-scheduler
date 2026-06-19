import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from ai.normalize import normalize_task


class TasksTab:
    def __init__(self, notebook, db, calendar_tab):
        self.db = db
        self.calendar_tab = calendar_tab
        self.on_task_change = None

        self.frame = ttk.Frame(notebook, padding=16)

        header_frame = ttk.Frame(self.frame)
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(header_frame, text="Task Manager", font=("Segoe UI", 14, "bold")).pack(side="left")

        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", pady=(0, 12))
        ttk.Button(button_frame, text="Add Task", command=self.show_add_task_dialog).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Edit Task", command=self.show_edit_task_dialog).pack(side="left", padx=8)
        ttk.Button(button_frame, text="Delete Task", command=self.delete_selected_task).pack(side="left", padx=8)

        self.task_tree = ttk.Treeview(
            self.frame,
            columns=("id", "title", "due", "duration", "reminder", "chat_id"),
            show="headings",
            selectmode="browse",
            height=16,
        )
        self.task_tree.heading("id", text="ID")
        self.task_tree.heading("title", text="Title")
        self.task_tree.heading("due", text="Deadline")
        self.task_tree.heading("duration", text="Hours")
        self.task_tree.heading("reminder", text="Reminder")
        self.task_tree.heading("chat_id", text="Chat ID")
        self.task_tree.column("id", width=40, anchor="center")
        self.task_tree.column("title", width=300)
        self.task_tree.column("due", width=110, anchor="center")
        self.task_tree.column("duration", width=70, anchor="center")
        self.task_tree.column("reminder", width=100, anchor="center")
        self.task_tree.column("chat_id", width=140, anchor="center")
        self.task_tree.pack(fill="both", expand=True)

        self.load_tasks()

    def load_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        self.tasks = self.db.get_all_tasks()
        for task in self.tasks:
            deadline = task.get("deadline_date") or f"Week {task.get('deadline_week')}"
            duration = task.get("estimated_duration") or "?"
            reminder = task.get("reminder_time") or "Not set"
            chat_id = task.get("chat_id") or ""
            self.task_tree.insert(
                "",
                "end",
                values=(task["id"], task["title"], deadline, duration, reminder, chat_id),
            )

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
        dialog.geometry("520x500")
        dialog.transient(self.frame)
        dialog.grab_set()

        container = ttk.Frame(dialog, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Title:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        title_entry = ttk.Entry(container, width=56)
        title_entry.grid(row=0, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(container, text="Description:", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="nw", pady=(8, 6))
        description_entry = tk.Text(container, width=55, height=8, wrap="word", bd=1, relief="solid")
        description_entry.grid(row=1, column=1, sticky="ew", pady=(8, 6))

        ttk.Label(container, text="Deadline type:", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(8, 6))
        deadline_type = tk.StringVar(value="specific")
        type_frame = ttk.Frame(container)
        type_frame.grid(row=2, column=1, sticky="w", pady=(8, 6))
        ttk.Radiobutton(type_frame, text="Specific Date", variable=deadline_type, value="specific").pack(side="left")
        ttk.Radiobutton(type_frame, text="Week of Month", variable=deadline_type, value="week").pack(side="left", padx=(16, 0))

        ttk.Label(container, text="Select date:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(8, 6))
        date_picker = DateEntry(container, date_pattern="yyyy-mm-dd")
        date_picker.grid(row=3, column=1, sticky="w", pady=(8, 6))

        ttk.Label(container, text="Week number:", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(8, 6))
        week_spin = ttk.Spinbox(container, from_=1, to=4, width=6)
        week_spin.grid(row=4, column=1, sticky="w", pady=(8, 6))

        ttk.Label(container, text="Reminder time:", font=("Segoe UI", 10, "bold")).grid(row=5, column=0, sticky="w", pady=(8, 6))
        reminder_entry = ttk.Entry(container, width=18)
        reminder_entry.grid(row=5, column=1, sticky="w", pady=(8, 6))

        ttk.Label(container, text="Telegram chat ID:", font=("Segoe UI", 10, "bold")).grid(row=6, column=0, sticky="w", pady=(8, 6))
        chat_id_entry = ttk.Entry(container, width=30)
        chat_id_entry.grid(row=6, column=1, sticky="w", pady=(8, 6))

        ttk.Label(container, text="Estimated duration:", font=("Segoe UI", 10, "bold")).grid(row=7, column=0, sticky="w", pady=(8, 6))
        duration_entry = ttk.Entry(container, width=18)
        duration_entry.grid(row=7, column=1, sticky="w", pady=(8, 6))

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

            if task:
                self.db.update_task(task["id"], title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration)
            else:
                self.db.add_task(title, description, deadline_date, deadline_week, reminder_time, chat_id, estimated_duration)

            dialog.destroy()
            self.load_tasks()
            if self.on_task_change:
                self.on_task_change()

        action_frame = ttk.Frame(container)
        action_frame.grid(row=7, column=0, columnspan=2, pady=(16, 0))
        ttk.Button(action_frame, text="Save Task", command=save_task).pack(side="left")

        container.columnconfigure(1, weight=1)

    def fetch_estimated_duration(self, description):
        try:
            return normalize_task(description)
        except Exception:
            return 1.0

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
