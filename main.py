# Application's main module
# main.py
import cli_main
import gui_main

def main():
    print("=== Exam Scheduler ===")
    print("Select mode:")
    print("1. CLI Mode")
    print("2. GUI Mode")

    choice = input("Enter choice (1/2): ")

    if choice == "1":
        cli_main.main()        # runs the CLI entry point
    elif choice == "2":
        gui_main.start_gui()   # runs the GUI entry point
    else:
        print("Invalid choice. Exiting...")

if __name__ == "__main__":
    main()
