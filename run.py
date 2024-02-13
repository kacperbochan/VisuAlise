import socket
import uvicorn

def find_available_port(start_port):
    port = start_port
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except socket.error:
            port += 1

if __name__ == "__main__":
    port = find_available_port(8000)
    uvicorn.run("myapi:app", host="127.0.0.1", port=port, reload=True)
