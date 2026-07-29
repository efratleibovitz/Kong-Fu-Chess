import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from server.auth.service import register, login


def main():
    while True:
        print("\n[1] Register  [2] Login  [q] Quit")
        choice = input("> ").strip().lower()

        if choice == "q":
            break

        if choice not in ("1", "2"):
            print("Invalid choice.")
            continue

        username = input("Username: ").strip()
        password = input("Password: ").strip()

        if choice == "1":
            try:
                user_id = register(username, password)
                print(f"Registered. user_id={user_id}")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "2":
            user_id = login(username, password)
            if user_id:
                print(f"Login successful. user_id={user_id}")
            else:
                print("Invalid username or password.")


if __name__ == "__main__":
    main()
