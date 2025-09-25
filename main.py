# main.py - Updated with authorized user handling
import json
import os
from threading import Thread
from sensors import start_motion_monitor, start_environment_monitor
from rfid_module import handle_rfid, rfid_reader, RFID_WHITELIST, normalize_uid
from utils import log_event
from gsm_module import send_sms, send_image_mms
from camera_module import capture_image, get_frame
import time

RFID_FILE = "rfid_whitelist.json"

# Global dictionary to track multiple authorized users
authorized_users = {}  # {uid: {"name": str, "entry_time": timestamp, "timer": Timer}}
authorized_users_count = 0

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

def add_authorized_user(uid, user_name):
    """Add an authorized user to the tracking system"""
    global authorized_users, authorized_users_count
    
    if uid not in authorized_users:
        entry_time = time.time()
        
        # Create auto-logout timer for this user (8 hours = 28800 seconds)
        def auto_logout():
            remove_authorized_user(uid, "session expired")
        
        logout_timer = Timer(28800, auto_logout)
        logout_timer.start()
        
        authorized_users[uid] = {
            "name": user_name,
            "entry_time": entry_time,
            "timer": logout_timer
        }
        authorized_users_count += 1
        
        log_event(f"Authorized user added: {user_name} (UID: {uid}) - Total users: {authorized_users_count}")
        
        # Send SMS notification
        send_sms(f"User '{user_name}' entered the house at {time.strftime('%Y-%m-%d %H:%M:%S')}. Active users: {authorized_users_count}")
        
        # Send live camera feed
        image_path = capture_image(f"entry_{user_name.replace(' ', '_')}")
        if image_path:
            send_image_mms(image_path, f"Entry: {user_name} - {authorized_users_count} users active")
    else:
        log_event(f"User {user_name} already registered as present")

def remove_authorized_user(uid, reason="manual logout"):
    """Remove an authorized user from the tracking system"""
    global authorized_users, authorized_users_count
    
    if uid in authorized_users:
        user_info = authorized_users[uid]
        user_name = user_info["name"]
        
        # Cancel the auto-logout timer
        if user_info["timer"]:
            user_info["timer"].cancel()
        
        # Calculate session duration
        duration = time.time() - user_info["entry_time"]
        duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
        
        del authorized_users[uid]
        authorized_users_count -= 1
        
        log_event(f"Authorized user removed: {user_name} ({reason}) - Session: {duration_str} - Remaining users: {authorized_users_count}")
        
        # Send SMS notification
        send_sms(f"User '{user_name}' left the house ({reason}). Session duration: {duration_str}. Remaining users: {authorized_users_count}")
        
        return user_name
    else:
        log_event(f"Attempted to remove non-existent user with UID: {uid}")
        return None

def remove_user_by_name(user_name):
    """Remove a user by name (for CLI usage)"""
    for uid, user_info in authorized_users.items():
        if user_info["name"].lower() == user_name.lower():
            return remove_authorized_user(uid, "manual logout")
    return None

def clear_all_authorized_users():
    """Clear all authorized users"""
    global authorized_users, authorized_users_count
    
    if authorized_users:
        user_names = [info["name"] for info in authorized_users.values()]
        
        # Cancel all timers
        for user_info in authorized_users.values():
            if user_info["timer"]:
                user_info["timer"].cancel()
        
        authorized_users.clear()
        authorized_users_count = 0
        
        log_event(f"All authorized users cleared: {', '.join(user_names)}")
        send_sms(f"All users logged out: {', '.join(user_names)}")

def is_any_authorized_user_present():
    """Check if any authorized user is present"""
    return authorized_users_count > 0

def get_authorized_users_list():
    """Get list of all authorized users currently present"""
    return [(uid, info["name"], info["entry_time"]) for uid, info in authorized_users.items()]

def get_authorized_users_summary():
    """Get summary string of authorized users"""
    if not authorized_users:
        return "No authorized users present"
    
    user_list = []
    for uid, info in authorized_users.items():
        duration = time.time() - info["entry_time"]
        duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
        user_list.append(f"{info['name']} ({duration_str})")
    
    return f"{authorized_users_count} user(s): {', '.join(user_list)}"

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
                        
                        if uid_str in RFID_WHITELIST:
                            print(f"Card already registered to: {RFID_WHITELIST[uid_str]}")
                            continue
                        
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
                if rfid_reader:
                    print("Registering multiple RFID cards for one user...")
                    user_name = input("Enter user name for all cards: ").strip()
                    if not user_name:
                        print("Registration cancelled (empty name)")
                        continue
                    
                    card_count = 0
                    print("Place cards one by one (type 'done' when finished):")
                    
                    while True:
                        try:
                            user_input = input(f"Place card #{card_count + 1} (or type 'done'): ").strip()
                            if user_input.lower() == 'done':
                                break
                            
                            print("Reading card...")
                            card_id, _ = rfid_reader.read()  # blocking
                            uid_str = normalize_uid(card_id)
                            
                            if uid_str in RFID_WHITELIST:
                                print(f"Card {uid_str} already registered to {RFID_WHITELIST[uid_str]}")
                                continue
                            
                            RFID_WHITELIST[uid_str] = user_name
                            card_count += 1
                            print(f"Card #{card_count} registered: {uid_str}")
                            
                        except Exception as e:
                            log_event(f"RFID registration error: {e}")
                            print("Failed to read card, try again")
                    
                    if card_count > 0:
                        save_rfid_whitelist()
                        log_event(f"Registered {card_count} cards for user: {user_name}")
                        print(f"Successfully registered {card_count} cards for {user_name}")
                    else:
                        print("No cards were registered")
                else:
                    print("RFID reader not available")

            elif cmd == "user_cards":
                if RFID_WHITELIST:
                    # Group cards by user name
                    users_cards = {}
                    for uid, name in RFID_WHITELIST.items():
                        if name not in users_cards:
                            users_cards[name] = []
                        users_cards[name].append(uid)
                    
                    print("Users and their RFID cards:")
                    for user, cards in users_cards.items():
                        print(f"  {user}: {len(cards)} card(s)")
                        for i, card in enumerate(cards, 1):
                            print(f"    {i}. {card}")
                else:
                    print("No RFID tags registered")

            elif cmd == "remove_user_cards":
                user_name = input("Enter user name to remove all their cards: ").strip()
                if user_name:
                    removed_cards = []
                    for uid, name in list(RFID_WHITELIST.items()):
                        if name.lower() == user_name.lower():
                            removed_cards.append(uid)
                            del RFID_WHITELIST[uid]
                    
                    if removed_cards:
                        save_rfid_whitelist()
                        log_event(f"Removed {len(removed_cards)} cards for user: {user_name}")
                        print(f"Removed {len(removed_cards)} cards for {user_name}")
                        for card in removed_cards:
                            print(f"  - {card}")
                    else:
                        print(f"No cards found for user: {user_name}")
                else:
                    print("User name cannot be empty")

            elif cmd == "status":
                if authorized_users_count > 0:
                    print(f"Authorized users present ({authorized_users_count}):")
                    for uid, info in authorized_users.items():
                        duration = time.time() - info["entry_time"]
                        duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
                        print(f"  - {info['name']} (UID: {uid[-8:]}...) - {duration_str}")
                else:
                    print("No authorized users present")

            elif cmd == "logout":
                if authorized_users_count == 0:
                    print("No users to logout")
                elif authorized_users_count == 1:
                    # Single user - logout directly
                    uid = list(authorized_users.keys())[0]
                    user_name = remove_authorized_user(uid, "manual logout")
                    print(f"Logged out: {user_name}")
                else:
                    # Multiple users - show selection
                    print("Multiple users present:")
                    user_list = list(authorized_users.items())
                    for i, (uid, info) in enumerate(user_list, 1):
                        print(f"  {i}. {info['name']} (UID: {uid[-8:]}...)")
                    print(f"  {len(user_list) + 1}. Logout ALL users")
                    
                    try:
                        choice = int(input("Select user to logout (number): "))
                        if 1 <= choice <= len(user_list):
                            uid, info = user_list[choice - 1]
                            user_name = remove_authorized_user(uid, "manual logout")
                            print(f"Logged out: {user_name}")
                        elif choice == len(user_list) + 1:
                            clear_all_authorized_users()
                            print("All users logged out")
                        else:
                            print("Invalid selection")
                    except ValueError:
                        print("Invalid input. Please enter a number.")

            elif cmd == "logout_all":
                clear_all_authorized_users()
                print("All users logged out")

            elif cmd.startswith("logout_user "):
                user_name = cmd.split("logout_user ", 1)[1].strip()
                if remove_user_by_name(user_name):
                    print(f"Logged out user: {user_name}")
                else:
                    print(f"User '{user_name}' not found or not currently present")

            elif cmd == "":
                continue  # ignore empty input

            else:
                print("Unknown command. Options: list_rfid, register_rfid, status, logout, logout_all, logout_user <name>, quit")

    except KeyboardInterrupt:
        log_event("Interrupted by user, shutting down...")
        save_rfid_whitelist()

if __name__ == "__main__":
    main()
