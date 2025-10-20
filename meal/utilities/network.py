import socket

"""Network helper utilities for the Meal Planner.

This module contains a small helper that returns a usable local (LAN) IP
address when available. It's separated so `meal.main` can stay focused on
application startup while other modules can import the utility if needed.
"""


def get_local_ip() -> str:
    """Return a non-loopback local IP address if possible, otherwise '127.0.0.1'.

    The implementation uses a UDP socket to ask the OS which interface would
    be selected to reach a public IP; it does not send any data on the wire.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually send data but forces the OS to pick a source IP
        s.connect(("8.8.8.8", 80))
        # Ensure we return a str (some linters/typecheckers infer Any/Optional)
        ip = str(s.getsockname()[0])
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip
