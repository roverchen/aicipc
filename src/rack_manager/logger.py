import os
import datetime

class TaskLogger:
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

    def log(self, task_id: str, message: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = os.path.join(self.logs_dir, f"{task_id}.log")
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
        print(f"[{task_id}] {message}")

# Global logger instance
logger = TaskLogger()
