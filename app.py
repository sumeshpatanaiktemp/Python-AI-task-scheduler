import tkinter as tk
from tkinter import ttk
from database.db import DatabaseManager
from gui.calendar_tab import CalendarTab
from gui.tasks_tab import TasksTab
from gui.task_summary_tab import TaskSummaryTab
from reminders.popup import ReminderManager
from datetime import datetime


# ── Palette ──────────────────────────────────────────────────────────────────
BG_DARK      = "#090E17"   # deep space dark background
BG_MID       = "#151E2E"   # sidebar / header background
BG_CARD      = "#1F2937"   # card / active tab background
ACCENT       = "#8B5CF6"   # primary electric violet
ACCENT2      = "#10B981"   # emerald green secondary accent
ACCENT3      = "#F43F5E"   # rose / danger accent
TEXT_BRIGHT  = "#F9FAFB"   # primary bright text
TEXT_DIM     = "#9CA3AF"   # secondary dim text
BORDER       = "#334155"   # slate border
SEL_BG       = "#8B5CF6"   # treeview row selection bg
SEL_FG       = "#FFFFFF"
ROW_ALT      = "#111827"   # alternating treeview row (darker slate)
HEADER_BG    = "#8B5CF6"
HEADER_FG    = "#FFFFFF"
TAB_BG       = "#151E2E"
TAB_SEL      = "#8B5CF6"
TAB_FG       = "#9CA3AF"
TAB_SEL_FG   = "#FFFFFF"
ENTRY_BG     = "#0F172A"
ENTRY_FG     = TEXT_BRIGHT
SPIN_BG      = "#0F172A"
BTN_BG       = ACCENT
BTN_FG       = "#FFFFFF"
BTN_HOV      = "#A78BFA"   # lighter purple hover
BTN2_BG      = ACCENT2
BTN2_FG      = "#090E17"
BTN3_BG      = ACCENT3
BTN3_FG      = "#FFFFFF"
SEPARATOR    = "#334155"


class SidebarButton(tk.Canvas):
    def __init__(self, parent, text, icon, command, active_bg, active_fg, inactive_bg, inactive_fg, hover_bg):
        super().__init__(parent, height=38, bg=parent["bg"], bd=0, highlightthickness=0, cursor="hand2")
        self.text = text
        self.icon = icon
        self.command = command
        self.active_bg = active_bg
        self.active_fg = active_fg
        self.inactive_bg = inactive_bg
        self.inactive_fg = inactive_fg
        self.hover_bg = hover_bg
        self.selected = False
        self.hovering = False
        
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return
        
        if self.selected:
            bg = self.active_bg
            icon_fg = ACCENT
            text_fg = TEXT_BRIGHT
        elif self.hovering:
            bg = self.hover_bg
            icon_fg = TEXT_BRIGHT
            text_fg = TEXT_BRIGHT
        else:
            bg = self.inactive_bg
            icon_fg = TEXT_DIM
            text_fg = TEXT_DIM
            
        # Draw rounded rectangle (radius 10)
        r = 10
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
        self.create_polygon(points, smooth=True, fill=bg)
        
        if self.selected:
            self.create_line(6, 11, 6, h - 11, width=3, fill=ACCENT, capstyle="round")
            
        self.create_text(24, h // 2, text=self.icon, font=("Segoe UI Emoji", 11), fill=icon_fg, anchor="w")
        self.create_text(52, h // 2, text=self.text, font=("Segoe UI", 10, "bold"), fill=text_fg, anchor="w")

    def on_enter(self, e):
        self.hovering = True
        self.draw()

    def on_leave(self, e):
        self.hovering = False
        self.draw()

    def on_click(self, e):
        if self.command:
            self.command()
            
    def select(self):
        self.selected = True
        self.draw()
        
    def deselect(self):
        self.selected = False
        self.draw()


class TaskSchedulerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Task Scheduler")
        self.root.geometry("1180x800")
        self.root.minsize(1080, 720)
        self.root.configure(bg=BG_DARK)

        self._build_styles()

        self.db = DatabaseManager()
        self.reminder_manager = ReminderManager(self.db)

        self.sidebar_buttons = {}
        self.active_tab = None

        # Build main layout
        self.main_layout = tk.Frame(self.root, bg=BG_DARK)
        self.main_layout.pack(fill="both", expand=True)

        # Left Sidebar
        self.sidebar = tk.Frame(self.main_layout, bg=BG_MID, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Right Content Area
        self.content_area = tk.Frame(self.main_layout, bg=BG_DARK)
        self.content_area.pack(side="right", fill="both", expand=True)

        self._build_sidebar()
        self._build_header()
        self._build_footer()
        self._build_content()

        self.tasks_tab.on_task_change = self.refresh_views
        self.task_summary_tab.on_change = self.refresh_views

        self.reminder_manager.set_root(self.root)
        self.root.after(1000, self.reminder_manager.check_reminders)

    # ── Style setup ──────────────────────────────────────────────────────────
    def _build_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # Root / Frame
        style.configure(".", background=BG_DARK, foreground=TEXT_BRIGHT,
                        font=("Segoe UI", 10))
        style.configure("TFrame", background=BG_DARK)

        # Header labels
        style.configure("Header.TLabel",
                        font=("Segoe UI", 20, "bold"),
                        foreground=TEXT_BRIGHT,
                        background=BG_DARK)
        style.configure("SubHeader.TLabel",
                        font=("Segoe UI", 10),
                        foreground=TEXT_DIM,
                        background=BG_DARK)
        style.configure("Status.TLabel",
                        font=("Segoe UI", 9),
                        foreground=TEXT_DIM,
                        background=BG_DARK)

        # Accent labels for stats
        style.configure("Stat.TLabel",
                        font=("Segoe UI", 11, "bold"),
                        foreground=ACCENT2,
                        background=BG_MID)
        style.configure("StatCard.TFrame", background=BG_MID)

        # Section header inside tabs
        style.configure("SectionTitle.TLabel",
                        font=("Segoe UI", 14, "bold"),
                        foreground=TEXT_BRIGHT,
                        background=BG_MID)
        style.configure("FieldLabel.TLabel",
                        font=("Segoe UI", 10, "bold"),
                        foreground=TEXT_DIM,
                        background=BG_CARD)
        style.configure("DimLabel.TLabel",
                        font=("Segoe UI", 9),
                        foreground=TEXT_DIM,
                        background=BG_MID)

        # Tab frame (inner)
        style.configure("Tab.TFrame", background=BG_MID)

        # Card LabelFrame
        style.configure("Card.TLabelframe",
                        background=BG_CARD,
                        bordercolor=BORDER,
                        relief="flat",
                        borderwidth=1)
        style.configure("Card.TLabelframe.Label",
                        font=("Segoe UI", 11, "bold"),
                        foreground=ACCENT,
                        background=BG_CARD)

        # Buttons — base
        style.configure("TButton",
                        font=("Segoe UI", 10, "bold"),
                        padding=[14, 7],
                        relief="flat",
                        borderwidth=0,
                        background=BTN_BG,
                        foreground=BTN_FG)
        style.map("TButton",
                  background=[("active", BTN_HOV), ("disabled", "#3A3D55")],
                  foreground=[("disabled", TEXT_DIM)],
                  relief=[("active", "flat")])

        # Accent2 button (green)
        style.configure("Accent2.TButton",
                        font=("Segoe UI", 10, "bold"),
                        padding=[14, 7],
                        relief="flat",
                        borderwidth=0,
                        background=BTN2_BG,
                        foreground=BTN2_FG)
        style.map("Accent2.TButton",
                  background=[("active", "#059669"), ("disabled", "#3A3D55")],
                  foreground=[("disabled", TEXT_DIM)])

        # Danger button (red/pink)
        style.configure("Danger.TButton",
                        font=("Segoe UI", 10, "bold"),
                        padding=[14, 7],
                        relief="flat",
                        borderwidth=0,
                        background=BTN3_BG,
                        foreground=BTN3_FG)
        style.map("Danger.TButton",
                  background=[("active", "#E11D48"), ("disabled", "#3A3D55")],
                  foreground=[("disabled", TEXT_DIM)])

        # Treeview
        style.configure("Treeview",
                        background=BG_CARD,
                        foreground=TEXT_BRIGHT,
                        fieldbackground=BG_CARD,
                        rowheight=32,
                        font=("Segoe UI", 10),
                        borderwidth=0,
                        relief="flat")
        style.configure("Treeview.Heading",
                        background=HEADER_BG,
                        foreground=HEADER_FG,
                        font=("Segoe UI", 10, "bold"),
                        relief="flat",
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", SEL_FG)])
        style.map("Treeview.Heading",
                  background=[("active", BTN_HOV)])

        # Entry & Combobox styling (used by tkcalendar.DateEntry)
        style.configure("TEntry",
                        fieldbackground=ENTRY_BG,
                        foreground=TEXT_BRIGHT,
                        insertcolor=TEXT_BRIGHT,
                        bordercolor=BORDER,
                        lightcolor=BORDER,
                        darkcolor=BORDER,
                        relief="flat")
        
        style.configure("TCombobox",
                        fieldbackground=ENTRY_BG,
                        foreground=TEXT_BRIGHT,
                        insertcolor=TEXT_BRIGHT,
                        bordercolor=BORDER,
                        arrowcolor=ACCENT,
                        background=BG_MID,
                        relief="flat")
        style.map("TCombobox",
                  fieldbackground=[("readonly", ENTRY_BG)],
                  foreground=[("readonly", TEXT_BRIGHT)])

        # Spinbox
        style.configure("TSpinbox",
                        background=SPIN_BG,
                        foreground=TEXT_BRIGHT,
                        fieldbackground=SPIN_BG,
                        bordercolor=BORDER,
                        arrowcolor=ACCENT,
                        insertcolor=TEXT_BRIGHT,
                        relief="flat")

        # Separator
        style.configure("TSeparator", background=BORDER)

        # Radiobutton
        style.configure("TRadiobutton",
                        background=BG_CARD,
                        foreground=TEXT_BRIGHT,
                        font=("Segoe UI", 10))
        style.map("TRadiobutton",
                  background=[("active", BG_CARD)],
                  foreground=[("active", ACCENT)])

        self.style = style

    # ── Sidebar Navigation ───────────────────────────────────────────────────
    def _build_sidebar(self):
        # Logo frame
        logo_frame = tk.Frame(self.sidebar, bg=BG_MID, pady=24)
        logo_frame.pack(fill="x")

        logo_lbl = tk.Label(logo_frame, text="🎯  TaskAI",
                            font=("Segoe UI", 16, "bold"),
                            fg=ACCENT2, bg=BG_MID)
        logo_lbl.pack(anchor="w", padx=20)

        subtitle_lbl = tk.Label(logo_frame, text="AI-Powered Scheduler",
                                font=("Segoe UI", 8, "bold"),
                                fg=TEXT_DIM, bg=BG_MID)
        subtitle_lbl.pack(anchor="w", padx=20, pady=(4, 0))

        sep = tk.Frame(self.sidebar, bg=BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=(0, 20))

        # Add buttons
        self.sidebar_buttons["calendar"] = SidebarButton(
            self.sidebar, "Calendar", "📅", lambda: self.select_tab("calendar"),
            active_bg=BG_CARD, active_fg=ACCENT,
            inactive_bg=BG_MID, inactive_fg=TEXT_DIM,
            hover_bg=BG_CARD
        )
        self.sidebar_buttons["calendar"].pack(fill="x", pady=4, padx=14)

        self.sidebar_buttons["tasks"] = SidebarButton(
            self.sidebar, "Tasks", "✅", lambda: self.select_tab("tasks"),
            active_bg=BG_CARD, active_fg=ACCENT,
            inactive_bg=BG_MID, inactive_fg=TEXT_DIM,
            hover_bg=BG_CARD
        )
        self.sidebar_buttons["tasks"].pack(fill="x", pady=4, padx=14)

        self.sidebar_buttons["summary"] = SidebarButton(
            self.sidebar, "Analytics", "📊", lambda: self.select_tab("summary"),
            active_bg=BG_CARD, active_fg=ACCENT,
            inactive_bg=BG_MID, inactive_fg=TEXT_DIM,
            hover_bg=BG_CARD
        )
        self.sidebar_buttons["summary"].pack(fill="x", pady=4, padx=14)

    def select_tab(self, tab_name):
        self.active_tab = tab_name

        # Hide all tab frames
        self.calendar_tab.frame.pack_forget()
        self.tasks_tab.frame.pack_forget()
        self.task_summary_tab.frame.pack_forget()

        # Update buttons styling
        for name, btn in self.sidebar_buttons.items():
            if name == tab_name:
                btn.select()
            else:
                btn.deselect()

        # Show selected tab frame
        if tab_name == "calendar":
            self.calendar_tab.frame.pack(fill="both", expand=True)
            self.header_title.config(text="📅  Calendar Dashboard")
        elif tab_name == "tasks":
            self.tasks_tab.frame.pack(fill="both", expand=True)
            self.header_title.config(text="✅  Task Manager")
        elif tab_name == "summary":
            self.task_summary_tab.frame.pack(fill="both", expand=True)
            self.header_title.config(text="📊  Daily Analytics")

    # ── Header ───────────────────────────────────────────────────────────────
    def _build_header(self):
        header = tk.Frame(self.content_area, bg=BG_MID)
        header.pack(fill="x", side="top")

        inner = tk.Frame(header, bg=BG_MID, padx=22, pady=16)
        inner.pack(fill="x")

        self.header_title = tk.Label(inner,
                                     text="📅  Calendar Dashboard",
                                     font=("Segoe UI", 16, "bold"),
                                     fg=TEXT_BRIGHT, bg=BG_MID)
        self.header_title.pack(side="left", anchor="center")

        # Live clock on the right
        self.clock_label = tk.Label(inner,
                                    font=("Segoe UI", 12, "bold"),
                                    fg=ACCENT2, bg=BG_MID)
        self.clock_label.pack(side="right", anchor="center")
        self._tick_clock()

        # Separator line under header
        tk.Frame(self.content_area, bg=BORDER, height=1).pack(fill="x", side="top")

    def _tick_clock(self):
        now = datetime.now().strftime("%H:%M:%S  %a, %d %b %Y")
        self.clock_label.config(text=now)
        self.root.after(1000, self._tick_clock)

    # ── Content Container ────────────────────────────────────────────────────
    def _build_content(self):
        self.content_container = tk.Frame(self.content_area, bg=BG_DARK, padx=14, pady=10)
        self.content_container.pack(fill="both", expand=True)

        self.calendar_tab = CalendarTab(self.content_container, self.db)
        self.tasks_tab = TasksTab(self.content_container, self.db, self.calendar_tab)
        self.task_summary_tab = TaskSummaryTab(self.content_container, self.db, self.calendar_tab)

        # Start by showing the calendar tab
        self.select_tab("calendar")

    # ── Footer ───────────────────────────────────────────────────────────────
    def _build_footer(self):
        tk.Frame(self.content_area, bg=BORDER, height=1).pack(fill="x", side="bottom")
        footer = tk.Frame(self.content_area, bg=BG_MID, padx=18, pady=8)
        footer.pack(fill="x", side="bottom")

        self.status_dot = tk.Label(footer, text="●", fg=ACCENT2, bg=BG_MID,
                                   font=("Segoe UI", 10))
        self.status_dot.pack(side="left")
        self.status_label = tk.Label(footer, text="  Ready",
                                     fg=TEXT_DIM, bg=BG_MID,
                                     font=("Segoe UI", 9))
        self.status_label.pack(side="left")

        tk.Label(footer, text="AI Task Scheduler  v1.1",
                 fg=TEXT_DIM, bg=BG_MID,
                 font=("Segoe UI", 9)).pack(side="right")

    # ── Refresh ───────────────────────────────────────────────────────────────
    def refresh_views(self):
        self.calendar_tab.refresh_calendar()
        self.tasks_tab.load_tasks()
        self.task_summary_tab.refresh_view()

    def start(self):
        self.refresh_views()
        self.root.mainloop()
