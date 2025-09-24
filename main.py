from threading import Thread
from sensors import start_motion_monitor
from rfid_module import handle_rfid,rfid_reader, RFID_WHITELIST
from utils import log_event

def main():
    log_event("Smart Home Master Starting")

    # Start motion sensor monitoring
    t_motion = Thread(target=start_motion_monitor, daemon=True)
    t_motion.start()

    # Start RFID monitoring
    t_rfid = Thread(target=handle_rfid, daemon=True)
    t_rfid.start()

    # CLI loop
    while True:
        cmd = input("Command> ").strip()
        if cmd in ["quit", "exit", "q"]:
            break
        elif cmd == "list_rfid":
            print(RFID_WHITELIST)
        elif cmd == "register_rfid":
            if rfid_reader:
                print("Place new card...")
                rfid_reader.wait_for_tag()
                _, _ = rfid_reader.request()
                _, uid = rfid_reader.anticoll()
                uid_str = ":".join(map(str, uid))
                name = input("Enter name: ")
                RFID_WHITELIST[uid_str] = name
                log_event(f"New RFID registered: {name} -> {uid_str}")

if __name__ == "__main__":
    main()
