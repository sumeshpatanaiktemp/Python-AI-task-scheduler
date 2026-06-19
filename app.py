import tkinter as tk
from tkinter import ttk
from database.db import DatabaseManager
from gui.calendar_tab import CalendarTab
from gui.tasks_tab import TasksTab
from gui.schedule_tab import ScheduleTab
from reminders.popup import ReminderManager


class TaskSchedulerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Task Scheduler")
        self.root.geometry("1024x760")
        self.root.minsize(960, 700)

        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground="#222")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 10), foreground="#555")
        self.style.configure("Card.TLabelframe", background="#ffffff")
        self.style.configure("Card.TLabelframe.Label", font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=8)
        self.style.configure("Status.TLabel", font=("Segoe UI", 9), foreground="#666")
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))

        self.db = DatabaseManager()
        self.reminder_manager = ReminderManager(self.db)

        header_frame = ttk.Frame(self.root, padding=(18, 16, 18, 8))
        header_frame.pack(fill="x")
        title_label = ttk.Label(header_frame, text="AI Task Scheduler", style="Header.TLabel")
        title_label.pack(anchor="w")
        subtitle_label = ttk.Label(
            header_frame,
            text="Manage study tasks, generate 1-day block, and send schedule to telegram at any time.",
            style="SubHeader.TLabel",
        )
        subtitle_label.pack(anchor="w", pady=(4, 0))

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=18, pady=(0, 8))

        content_frame = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        content_frame.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(content_frame)
        self.calendar_tab = CalendarTab(self.notebook, self.db)
        self.tasks_tab = TasksTab(self.notebook, self.db, self.calendar_tab)
        self.schedule_tab = ScheduleTab(self.notebook, self.db, self.calendar_tab)

        self.notebook.add(self.calendar_tab.frame, text="Calendar")
        self.notebook.add(self.tasks_tab.frame, text="Tasks")
        self.notebook.add(self.schedule_tab.frame, text="Schedule")
        self.notebook.pack(fill="both", expand=True)

        footer_frame = ttk.Frame(self.root, padding=(18, 0, 18, 12))
        footer_frame.pack(fill="x")
        self.status_label = ttk.Label(footer_frame, text="Ready", style="Status.TLabel")
        self.status_label.pack(side="left")

        self.tasks_tab.on_task_change = self.refresh_views
        self.schedule_tab.on_schedule_change = self.refresh_views

        # Start automatic reminder checking
        self.reminder_manager.set_root(self.root)
        self.root.after(1000, self.reminder_manager.check_reminders)

    def refresh_views(self):
        self.calendar_tab.refresh_calendar()
        self.tasks_tab.load_tasks()
        self.schedule_tab.refresh_schedule_view()

    def start(self):
        self.refresh_views()
        self.root.mainloop()
