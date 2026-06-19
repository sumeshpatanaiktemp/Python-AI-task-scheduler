import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar


class CalendarTab:
    def __init__(self, notebook, db):
        self.db = db
        self.frame = ttk.Frame(notebook, padding=16)

        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True)

        calendar_frame = ttk.LabelFrame(main_frame, text="Calendar", style="Card.TLabelframe", padding=14)
        calendar_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=4)

        self.calendar = Calendar(calendar_frame, selectmode="day", date_pattern="yyyy-mm-dd")
        self.calendar.pack(fill="both", expand=True)
        self.calendar.bind("<<CalendarSelected>>", self.on_date_selected)

        task_frame = ttk.LabelFrame(main_frame, text="Tasks on Selected Date", style="Card.TLabelframe", padding=14)
        task_frame.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=4)

        self.task_listbox = tk.Listbox(task_frame, height=13, borderwidth=0, highlightthickness=0)
        self.task_listbox.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(task_frame, orient="vertical", command=self.task_listbox.yview)
        scroll.pack(side="right", fill="y")
        self.task_listbox.config(yscrollcommand=scroll.set)

        note_label = ttk.Label(self.frame, text="Select a date to review task due dates and reminders.", font=("Segoe UI", 9), foreground="#555")
        note_label.pack(anchor="w", pady=(10, 0), padx=4)

        self.refresh_calendar()

    def refresh_calendar(self):
        self.calendar.calevent_remove("all")
        tasks = self.db.get_all_tasks()
        for task in tasks:
            if task.get("deadline_date"):
                try:
                    self.calendar.calevent_create(task["deadline_date"], task["title"], "task")
                except Exception:
                    pass
        self.on_date_selected(None)

    def on_date_selected(self, event):
        selected = self.calendar.get_date()
        self.task_listbox.delete(0, tk.END)
        tasks = self.db.get_all_tasks()
        for task in tasks:
            if task.get("deadline_date") == selected:
                display = f"{task['title']} • {task.get('reminder_time', 'No reminder')}"
                self.task_listbox.insert(tk.END, display)
