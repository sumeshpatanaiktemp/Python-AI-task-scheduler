# 🤖 AI Task Scheduler

A powerful AI-driven task scheduling application with a beautiful Tkinter GUI. Manage your study tasks, generate intelligent 1-day schedules, and receive Telegram reminders automatically.

## ✨ Features

### 📅 Calendar & Task Management
- **Interactive Calendar**: Visual date picker for easy task scheduling
- **Task Management**: Create, edit, and delete tasks with custom deadlines and durations
- **Smart Categorization**: Organize tasks with status tracking (pending, in-progress, completed)

### 🤖 AI-Powered Scheduling
- **Intelligent Schedule Generation**: AI analyzes your tasks and creates optimized 1-day study blocks
- **Multi-Provider Support**: Works with multiple AI providers (Ollama, OpenAI, etc.)
- **Smart Load Balancing**: Automatically distributes tasks ensuring max 6 hours per day
- **Task Normalization**: Intelligent preprocessing of task data for better scheduling

### 📱 Telegram Integration
- **Auto Reminders**: Send study schedules directly to Telegram at any time
- **Flexible Scheduling**: Configure reminder times and preferences
- **Push Notifications**: Stay updated with task reminders

### 📊 Data Export & API
- **CSV Export**: Export tasks and schedules to CSV for external analysis
- **REST API**: Flask-based API server for n8n and other automation platforms
- **Database Management**: Persistent SQLite database with automatic schema initialization

### 🎨 User-Friendly UI
- **Tabbed Interface**: Organized sections for Calendar, Tasks, and Schedules
- **Modern Design**: Clean, responsive interface built with ttk widgets
- **Real-time Updates**: Instant feedback on task changes
## Demo

[![Watch the tutorial]](https://youtu.be/T9-RPNWJNyY)

## 📋 Project Structure

```
.
├── app.py                   # Main Tkinter application
├── main.py                  # Entry point with server initialization
├── requirements.txt         # Project dependencies
├── .env                     # api key and bot token
├── ai/
│   ├── normalize.py         # Task normalization logic
│   └── schedule.py          # AI schedule generation
├── api/
│   └── server.py            # Flask API server
├── database/
│   ├── db.py                # Database manager
│   └── schema.sql           # Database schema
├── export/
│   └── csv_export.py        # CSV export functionality
├── gui/
│   ├── calendar_tab.py      # Calendar interface
│   ├── task_summary_tab.py  # Schedule display and generation
│   └── tasks_tab.py         # Task management interface
├── logs/                    # Application logs directory
├── reminders/
│   ├── popup.py             # Desktop reminder notifications
│   └── telegram.py          # Telegram integration
└── utils/
    └── env.py               # Environment configuration loader
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone/Download the repository**
   ```bash
   cd "Python AI task scheduler"
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   - This is recommended on first use(This is also included in `startup.bat`)

4. **Configure environment variables** (optional)
   Create a `.env` file in the project root:
   ```env
   # AI Configuration
   AI_PROVIDER=ollama  # or openai, anthropic, etc.
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=llama2
   AI_API_KEY=your_api_key_here
   
   # Telegram Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```

5. **Run the application**
   ```bash
   python main.py
   ```
## Run on Windows startup

If you want this app to launch automatically when you log in, set up a short cut in start up:

1. press win+r.
2. write: 
     ```text
     shell:startup
     ```
3. Create a shortcut of the `startup.bat`

> Important: `main.py` opens a Tkinter GUI window, so the app will open visibly on startup. If you want it to start minimized or hidden, add that behavior inside the app or use a separate launcher.

## 📖 Usage Guide

### Creating Tasks
1. Open the **Tasks** tab
2. Click "Add Task" button
3. Enter task details:
   - **Title**: Task name
   - **Deadline**: Select date from calendar
   - **Duration**: Estimated study hours
   - **Priority**: Set task importance
4. Click "Save"

### Generating AI Schedule
1. Switch to the **Schedule** tab
2. Review your pending tasks
3. Click "Generate 1-Day Schedule"
4. AI will create an optimized study plan
5. View breakdown by day and time blocks

### Sending Reminders
- Click "Send to Telegram" to push the schedule to your Telegram
- Requires proper Telegram bot configuration in `.env`

### Exporting Data
- Use the **Export** option to save tasks and schedules as CSV
- Perfect for data analysis or external tool integration

### Using the REST API
The application runs a Flask API server on `http://127.0.0.1:5000`

- Note : This is not implemented yet fully please wait for future updates.

**Available Endpoints:**
- `GET /api/tasks` - Retrieve all tasks

## ⚙️ Configuration

### AI Provider Setup

#### Using Ollama (Local)
- Install [Ollama](https://ollama.ai)
- Pull a model: `ollama pull llama2`
- Set in `.env`:
  ```env
  AI_PROVIDER=ollama
  OLLAMA_HOST=http://localhost:11434
  OLLAMA_MODEL=llama2
  ```

#### Using OpenAI
- Get API key from [OpenAI](https://platform.openai.com)
- Set in `.env`:
  ```env
  AI_PROVIDER=openai
  AI_API_KEY=sk-...
  ```

### Telegram Setup
1. Create a bot via [BotFather](https://t.me/botfather)
2. Get your Chat ID from [@userinfobot](https://t.me/userinfobot)
3. Add to `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=987654321
   ```

## 🔧 Development

### Project Architecture
- **GUI Layer**: Tkinter-based UI with tabbed interface
- **Database Layer**: SQLite with managed schemas
- **AI Layer**: Modular provider support for flexible AI integration
- **API Layer**: Flask REST server for external integrations
- **Utility Layer**: Shared configuration and environment management

### Extending the Application
- **Add New AI Providers**: Modify `ai/normalize.py` and `ai/schedule.py`
- **Customize Schedule Logic**: Edit `ai/schedule.py`
- **Add API Endpoints**: Extend `api/server.py`
- **New UI Tabs**: Create new tab class in `gui/` and register in `app.py`

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| tkcalendar | Interactive calendar widget |
| requests | HTTP requests for API calls |
| Flask | REST API server |
| python-telegram-bot | Telegram integration |
| python-dotenv | Environment configuration |
| pyinstaller | Build executable binaries |

## 🐛 Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt --upgrade
```

### Telegram messages not sending
- Verify bot token is correct
- Check Chat ID matches
- Ensure internet connection is active

### AI scheduling not working
- Check AI provider is running (if using Ollama)
- Verify API credentials in `.env`
- Check network connectivity

### GUI not displaying properly
- Update tkinter: Usually pre-installed with Python
- On Linux: `sudo apt-get install python3-tk`

## 🤝 Contributing

Feel free to extend and customize this application for your needs:
- Add new scheduling algorithms
- Implement additional reminder methods
- Support more AI providers
- Enhance the UI with new features

## 📝 License

This project is provided as-is for educational and personal use.

## 🎯 Future Enhancements

- [ ] Cloud synchronization
- [ ] Mobile app companion
- [ ] Advanced analytics dashboard
- [ ] Integration with popular calendars (Google, Outlook)
- [ ] Machine learning for personalized scheduling
- [ ] Switchable UI theme
- [ ] Multi-language support

---

**Made with ❤️ for better task scheduling and productivity**
# Python-AI-task-scheduler
