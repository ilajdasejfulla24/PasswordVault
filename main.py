"""
main.py
-------
Entry point for the Password Vault application.
Run this file to start the application:

    python main.py
"""

import sys


def main():
    """Launch the Password Vault GUI."""
    try:
        from gui import launch
        launch()
    except ImportError as exc:
        print(f"[ERROR] Missing dependency: {exc}")
        print("Please install requirements first:")
        print("    pip install -r requirements.txt")
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] Unexpected error: {exc}")
        raise


if __name__ == "__main__":
    main()
