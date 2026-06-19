import csv
import os
from datetime import datetime


def export_schedule_csv(schedule_rows):
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    filename = f"ai_task_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    path = os.path.join(downloads, filename)
    with open(path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["day", "task", "start", "end"])
        writer.writeheader()
        for row in schedule_rows:
            writer.writerow({
                "day": row["day_number"],
                "task": row["title"],
                "start": row["start_time"],
                "end": row["end_time"],
            })
    return path
