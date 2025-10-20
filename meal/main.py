import uvicorn
from meal.api.api_run import app
from meal.utilities.network import get_local_ip


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8000
    local_url = f"http://localhost:{port}"
    local_ip = get_local_ip()
    lan_url = f"http://{local_ip}:{port}"
    # Print a friendly message that points to the URL you can open in a browser
    print(f"Uvicorn running on {local_url} (Press CTRL+C to quit)")
    # Also show the LAN-accessible URL for other devices on the same network
    if local_ip not in ("127.0.0.1", "localhost"):
        print(f"Accessible from other devices at: {lan_url}")
    uvicorn.run(app, host=host, port=port)
