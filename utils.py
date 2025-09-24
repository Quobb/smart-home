import os
from datetime import datetime
from config import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)

def log_event(msg):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} UTC | {msg}"
    print(line)
    with open(os.path.join(LOG_DIR, "events.log"), "a") as f:
        f.write(line + "\n")
