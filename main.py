import json
import os
from threading import Thread
from sensors import start_motion_monitor, start_environment_monitor
from rfid_module import handle_rfid, rfid_reader, RFID_WHITELIST, normalize_uid
from utils import log_event

RFID_FILE = "rfid_whitelist.json"

def load_rfid_whitelist():
    """Load RFID whitelist from file if available"""
    if os.path.exists(RFID_FILE):
        try:
            with open(RFID_FILE, "r") as f:
                data = json.load(f)
                RFID_WHITELIST.update(data)
                log_event(f"Loaded {len(data)} RFID cards from {RFID_FILE}")
        except Exception as e:
            log_event(f"Error loading RFID whitelist: {e}")

def save_rfid_whitelist():
    """Save RFID whitelist to file"""
    try:
        with open(RFID_FILE, "w") as f:
            json.dump(RFID_WHITELIST, f, indent=4)
        log_event(f"Saved {len(RFID_WHITELIST)} RFID cards to {RFID_FILE}")
    except Exception as e:
        log_event(f"Error saving RFID whitelist: {e}")

def main():
    log_event("Smart Home Master Starting")

    # Load saved RFID cards
    load_rfid_whitelist()

    # Start motion sensor monitoring
    start_motion_monitor()

    # Start environment monitoring
    start_environment_monitor()

    # Start RFID monitoring
    t_rfid = Thread(target=handle_rfid, daemon=True)
    t_rfid.start()

    # CLI loop
    try:
        while True:
            cmd = input("Command> ").strip().lower()

            if cmd in ["quit", "exit", "q"]:
                log_event("Shutting down Smart Home Master")
                save_rfid_whitelist()
                break

            elif cmd == "list_rfid":
                if RFID_WHITELIST:
                    for uid, name in RFID_WHITELIST.items():
                        print(f"{uid} -> {name}")
                else:
                    print("No RFID tags registered")

            elif cmd == "register_rfid":
                if rfid_reader:
                    print("Place new card...")
                    try:
                        card_id, _ = rfid_reader.read()  # blocking
                        uid_str = normalize_uid(card_id)
                        name = input("Enter name: ").strip()

                        if name:
                            RFID_WHITELIST[uid_str] = name
                            save_rfid_whitelist()  # persist immediately
                            log_event(f"New RFID registered: {name} -> {uid_str}")
                            print(f"Registered {uid_str} as {name}")
                        else:
                            print("Registration cancelled (empty name)")
                    except Exception as e:
                        log_event(f"RFID registration error: {e}")
                        print("Failed to register RFID card")
                else:
                    print("RFID reader not available")

            elif cmd == "":
                continue  # ignore empty input

            else:
                print("Unknown command. Options: list_rfid, register_rfid, quit")

    except KeyboardInterrupt:
        log_event("Interrupted by user, shutting down...")
        save_rfid_whitelist()

if __name__ == "__main__":
    main()
