import psutil
import sys

def kill_proc_on_port(port):
    found = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"Killing process {proc.info['name']} (PID: {proc.info['pid']}) on port {port}")
                    proc.kill()
                    found = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    if not found:
        print(f"No process found on port {port}")

if __name__ == "__main__":
    kill_proc_on_port(8005)
