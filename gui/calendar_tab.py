import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
from datetime import date as _date_cls

# ── Theme colours (must match app.py) ────────────────────────────────────────
BG_DARK   = "#090E17"
BG_MID    = "#151E2E"
BG_CARD   = "#1F2937"
ACCENT    = "#8B5CF6"
ACCENT2   = "#10B981"
ACCENT3   = "#F43F5E"
TEXT_BRIGHT = "#F9FAFB"
TEXT_DIM    = "#9CA3AF"
BORDER    = "#334155"
SEL_BG    = "#8B5CF6"
SEL_FG    = "#FFFFFF"
ENTRY_BG  = "#0F172A"


class CustomCalendar(Calendar):
    """tkcalendar subclass that shows hours-used / hours-left under day numbers."""

    def __init__(self, master=None, db=None, **kw):
        self.db = db
        super().__init__(master, **kw)
        for row in self._calendar:
            for label in row:
                label.configure(justify="center", anchor="center", padding=(1, 2))

    def _display_days_without_othermonthdays(self):
        super()._display_days_without_othermonthdays()
        if not self.db:
            return
        year, month = self._date.year, self._date.month
        cal = self._cal.monthdays2calendar(year, month)
        while len(cal) < 6:
            cal.append([(0, i) for i in range(7)])
        for i_week in range(6):
            for i_day in range(7):
                day_number, _ = cal[i_week][i_day]
                if day_number:
                    try:
                        d = self.date(year, month, day_number)
                        used = self.db.get_total_duration_for_date(d.isoformat())
                        left = max(0.0, self.db.get_daily_limit() - used)
                        self._calendar[i_week][i_day].configure(
                            text=f"{day_number}\n{used:.1f}/{left:.1f}")
                    except Exception:
                        pass

    def _display_days_with_othermonthdays(self):
        super()._display_days_with_othermonthdays()
        if not self.db:
            return
        year, month = self._date.year, self._date.month
        cal = self._cal.monthdatescalendar(year, month)
        next_m, y = month + 1, year
        if next_m == 13:
            next_m, y = 1, year + 1
        while len(cal) < 6:
            extra = self._cal.monthdatescalendar(y, next_m)
            i = 0 if cal[-1][-1].month == month else 1
            cal.append(extra[i])
        for i_week in range(6):
            for i_day in range(7):
                try:
                    d = cal[i_week][i_day]
                    used = self.db.get_total_duration_for_date(d.isoformat())
                    left = max(0.0, self.db.get_daily_limit() - used)
                    self._calendar[i_week][i_day].configure(
                        text=f"{d.day}\n{used:.1f}/{left:.1f}")
                except Exception:
                    pass

    def _on_click(self, event):
        """Override so multi-line text ('20\\n1.5/4.5') doesn't crash int()."""
        if self._properties['state'] == 'normal':
            label = event.widget
            if "disabled" not in label.state():
                raw = label.cget("text")
                day = raw.split("\n")[0].strip()
                style = label.cget("style")
                if style in [
                    'normal_om.%s.TLabel' % self._style_prefixe,
                    'we_om.%s.TLabel' % self._style_prefixe,
                ]:
                    if label in self._calendar[0]:
                        self._prev_month()
                    else:
                        self._next_month()
                if day:
                    day = int(day)
                    year, month = self._date.year, self._date.month
                    self._remove_selection()
                    self._sel_date = self.date(year, month, day)
                    self._display_selection()
                    if self._textvariable is not None:
                        self._textvariable.set(self.format_date(self._sel_date))
                    self.event_generate("<<CalendarSelected>>")


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


class CalendarTab:
    def __init__(self, parent, db):
        self.db = db
        self.frame = tk.Frame(parent, bg=BG_DARK)

        # ── Main split ────────────────────────────────────────────────────────
        main = tk.Frame(self.frame, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=14, pady=12)

        # ── Left: calendar card ───────────────────────────────────────────────
        cal_card = RoundedCard(main, bg=BG_CARD, border_color=BORDER, radius=16)
        cal_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(cal_card.inner_frame, text="📅  Calendar",
                 font=("Segoe UI", 12, "bold"),
                 fg=ACCENT, bg=BG_CARD).pack(anchor="w", padx=14, pady=(12, 4))

        self.calendar = CustomCalendar(
            cal_card.inner_frame, db=self.db,
            selectmode="day", date_pattern="yyyy-mm-dd",
            background=BG_CARD, foreground=TEXT_BRIGHT,
            headersbackground=BG_MID, headersforeground=TEXT_BRIGHT,
            selectbackground=ACCENT, selectforeground=TEXT_BRIGHT,
            normalbackground="#FFFFFF", normalforeground="#111827",
            weekendbackground="#F9FAFB", weekendforeground="#EF4444",
            othermonthforeground="#9CA3AF", othermonthbackground="#F3F4F6",
            othermonthweforeground="#9CA3AF", othermonthwebackground="#F3F4F6",
            bordercolor=BORDER, borderwidth=0,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.calendar.pack(fill="both", expand=True, padx=10, pady=(0, 12))
        self.calendar.bind("<<CalendarSelected>>", self.on_date_selected)

        # ── Right: task list card ─────────────────────────────────────────────
        task_card = RoundedCard(main, bg=BG_CARD, border_color=BORDER, radius=16)
        task_card.pack(side="right", fill="both", expand=True, padx=(8, 0))

        tk.Label(task_card.inner_frame, text="📋  Tasks on Selected Date",
                 font=("Segoe UI", 12, "bold"),
                 fg=ACCENT, bg=BG_CARD).pack(anchor="w", padx=14, pady=(12, 6))

        list_frame = tk.Frame(task_card.inner_frame, bg=BG_CARD)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        scroll = tk.Scrollbar(list_frame, bg=BG_MID, troughcolor=BG_DARK,
                              activebackground=ACCENT)
        scroll.pack(side="right", fill="y")

        self.task_listbox = tk.Listbox(
            list_frame,
            bg=ENTRY_BG, fg=TEXT_BRIGHT,
            selectbackground=ACCENT, selectforeground=SEL_FG,
            activestyle="none",
            font=("Segoe UI", 10),
            borderwidth=0, highlightthickness=0,
            yscrollcommand=scroll.set,
            cursor="hand2",
        )
        self.task_listbox.pack(fill="both", expand=True)
        scroll.config(command=self.task_listbox.yview)

        # ── Footer note ───────────────────────────────────────────────────────
        tk.Label(self.frame,
                 text="  ℹ  Select a date to see tasks due on that day.",
                 font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG_DARK).pack(
            anchor="w", padx=14, pady=(0, 6))

        self.refresh_calendar()

    def refresh_calendar(self):
        self.calendar.calevent_remove("all")
        tasks = self.db.get_all_tasks()
        for task in tasks:
            if task.get("deadline_date"):
                try:
                    self.calendar.calevent_create(
                        task["deadline_date"], task["title"], "task")
                except Exception:
                    pass
        # Force calendar day cells to re-render so hours-used / hours-left update immediately
        try:
            # CustomCalendar implements both display methods; call whichever applies.
            self.calendar._display_days_without_othermonthdays()
        except Exception:
            pass
        try:
            self.calendar._display_days_with_othermonthdays()
        except Exception:
            pass
        self.on_date_selected(None)

    def on_date_selected(self, event):
        try:
            sel = self.calendar.selection_get()
            selected = sel.isoformat() if sel else self.calendar.get_date()
        except Exception:
            selected = self.calendar.get_date()
        self.task_listbox.delete(0, tk.END)
        tasks = self.db.get_all_tasks()
        for i, task in enumerate(t for t in tasks if t.get("deadline_date") == selected):
            duration = task.get("estimated_duration") or "?"
            reminder = task.get("reminder_time") or "No reminder"
            display = f"  #{task['id']}  {task['title']}  •  {duration}h  •  ⏰ {reminder}"
            self.task_listbox.insert(tk.END, display)
            self.task_listbox.itemconfig(i,
                bg=BG_CARD if i % 2 == 0 else ENTRY_BG,
                fg=TEXT_BRIGHT)
