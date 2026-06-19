import os
import tkinter as tk
from tkinter import ttk, messagebox
from ai.schedule import LOG_FILE, generate_schedule, generate_telegram_message
from export.csv_export import export_schedule_csv
from reminders.telegram import send_telegram_message


class ScheduleTab:
    def __init__(self, notebook, db, calendar_tab):
        self.db = db
        self.calendar_tab = calendar_tab
        self.on_schedule_change = None

        self.frame = ttk.Frame(notebook, padding=16)

        header_frame = ttk.Frame(self.frame)
        header_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(header_frame, text="Manage 1 day study tasks", font=("Segoe UI", 14, "bold")).pack(side="left")
        # Daily limit control
        self.daily_limit_var = tk.DoubleVar(value=6.0)
        limit_frame = ttk.Frame(header_frame)
        limit_frame.pack(side="right")
        ttk.Label(limit_frame, text="Daily limit (hrs):").pack(side="left")
        try:
            spin = ttk.Spinbox(limit_frame, from_=1, to=24, textvariable=self.daily_limit_var, width=5)
        except Exception:
            spin = ttk.Entry(limit_frame, textvariable=self.daily_limit_var, width=5)
        spin.pack(side="left", padx=(6, 0))

        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", pady=(0, 16))
        ttk.Button(button_frame, text="Generate 1 day tasks", command=self.generate_schedule).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Export CSV", command=self.export_csv).pack(side="left", padx=8)
        ttk.Button(button_frame, text="Get reminders", command=self.send_telegram_messages).pack(side="left", padx=8)

        schedule_frame = ttk.LabelFrame(self.frame, text="3-Day Time Blocks", style="Card.TLabelframe", padding=14)
        schedule_frame.pack(fill="both", expand=True, pady=(0, 12))

        self.schedule_tree = ttk.Treeview(
            schedule_frame,
            columns=("task", "start", "end"),
            show="headings",
            selectmode="none",
            height=12,
        )
        self.schedule_tree.heading("task", text="Task")
        self.schedule_tree.heading("start", text="Start")
        self.schedule_tree.heading("end", text="End")
        self.schedule_tree.column("task", width=420)
        self.schedule_tree.column("start", width=100, anchor="center")
        self.schedule_tree.column("end", width=100, anchor="center")
        self.schedule_tree.pack(fill="both", expand=True)

        summary_frame = ttk.LabelFrame(self.frame, text="Plan Summary", style="Card.TLabelframe", padding=14)
        summary_frame.pack(fill="x", pady=(0, 6))

        self.summary_text = tk.Text(summary_frame, height=7, wrap="word", bd=1, relief="solid")
        self.summary_text.pack(fill="both", expand=True)
        self.summary_text.configure(state="disabled")

        self.refresh_schedule_view()

    def refresh_schedule_view(self):
        for item in self.schedule_tree.get_children():
            self.schedule_tree.delete(item)
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)

        schedule_rows = self.db.get_schedule()
        if not schedule_rows:
            self.summary_text.insert(tk.END, "No schedule generated yet. Click 'Generate Schedule' to build your next day.")
            self.summary_text.configure(state="disabled")
            return

        for row in schedule_rows:
            self.schedule_tree.insert("", tk.END, values=(row["title"], row["start_time"], row["end_time"]))

        explanation = getattr(self, "schedule_explanation", None) or self.load_schedule_explanation()
        if explanation:
            self.summary_text.insert(tk.END, explanation)
        self.summary_text.configure(state="disabled")

    def load_schedule_explanation(self):
        tasks = self.db.get_all_tasks()
        if not tasks:
            return ""
        return "Plan your next day with clear study blocks and reminders. Export the schedule or generate Telegram text once ready."

    def generate_schedule(self):
        tasks = self.db.get_all_tasks()
        if not tasks:
            messagebox.showinfo("Generate Schedule", "Add tasks first then generate schedule.")
            return
        daily_limit = float(self.daily_limit_var.get() or 6.0)
        try:
            schedule_result = generate_schedule(tasks, daily_limit=daily_limit)
            self.db.clear_schedules()
            for block in schedule_result["schedule"]:
                for entry in block["blocks"]:
                    self.db.save_schedule(entry["task_id"], block["day"], entry["start"], entry["end"])
            self.schedule_explanation = schedule_result.get("explanation", "")
            self.refresh_schedule_view()
            if self.on_schedule_change:
                self.on_schedule_change()
        except Exception as exc:
            messagebox.showerror("Schedule Error", f"Unable to generate schedule: {exc}")

    def export_csv(self):
        schedule_rows = self.db.get_schedule()
        if not schedule_rows:
            messagebox.showinfo("Export CSV", "Generate a schedule first.")
            return
        export_schedule_csv(schedule_rows)
        messagebox.showinfo("Export CSV", "Schedule exported to CSV successfully.")

    def show_telegram_text(self):
        schedule_rows = self.db.get_schedule()
        if not schedule_rows:
            messagebox.showinfo("Telegram Text", "Generate a schedule first.")
            return
        text = get_telegram_message_text(schedule_rows)
        popup = tk.Toplevel(self.frame)
        popup.title("Telegram Reminder Text")
        popup.geometry("560x360")
        text_widget = tk.Text(popup, wrap="word", bd=1, relief="solid")
        text_widget.pack(fill="both", expand=True, padx=12, pady=12)
        text_widget.insert(tk.END, text)
        text_widget.config(state="disabled")

    def send_telegram_messages(self):
        tasks = self.db.get_all_tasks()
        if not tasks:
            messagebox.showinfo("Send Telegram", "Add tasks first then send reminders.")
            return
        daily_limit = float(self.daily_limit_var.get() or 6.0)
        try:
            message_text = generate_telegram_message(tasks, daily_limit=daily_limit)
        except Exception as exc:
            messagebox.showerror("Send Telegram", f"Unable to generate Telegram message: {exc}")
            return

        chat_ids = set(task.get("chat_id") for task in tasks if task.get("chat_id"))
        if not chat_ids:
            messagebox.showwarning("Send Telegram", "No tasks contain a Telegram chat ID.")
            return

        failed = []
        for chat_id in chat_ids:
            try:
                send_telegram_message(chat_id, message_text)
            except Exception as exc:
                failed.append(f"{chat_id}: {exc}")

        if failed:
            messagebox.showerror("Send Telegram", f"Some messages failed:\n{'; '.join(failed)}")
        else:
            messagebox.showinfo("Send Telegram", f"Sent reminders to chat IDs: {', '.join(chat_ids)}")

    def open_ai_log(self):
        if not os.path.exists(LOG_FILE):
            messagebox.showinfo("AI Log", "No AI log file exists yet.")
            return

        try:
            if os.name == "nt":
                os.startfile(LOG_FILE)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                os.system(f"{opener} \"{LOG_FILE}\"")
        except Exception as exc:
            messagebox.showerror("AI Log", f"Unable to open AI log: {exc}")
