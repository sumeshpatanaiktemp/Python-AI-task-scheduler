import threading
import tkinter as tk
from app import TaskSchedulerApp
from api.server import start_api_server


def main():
    # Start local HTTP server for n8n integration in a background thread
    server_thread = threading.Thread(target=start_api_server, daemon=True)
    server_thread.start()

    root = tk.Tk()
    app = TaskSchedulerApp(root)
    app.start()


if __name__ == "__main__":
    main()
