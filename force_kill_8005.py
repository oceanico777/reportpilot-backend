import os
import re

print("Searching for process on port 8005...")
# Run netstat and capture output
# 'findstr' is Windows specific
with os.popen('netstat -ano | findstr :8005') as f:
    lines = f.readlines()

pids = set()
for line in lines:
    parts = line.strip().split()
    # Output format: TCP 0.0.0.0:8005 0.0.0.0:0 LISTENING 1234
    if len(parts) > 4 and 'LISTENING' in line: 
        pid = parts[-1]
        pids.add(pid)

if not pids:
    print("No process found on port 8005.")
else:
    for pid in pids:
        print(f"Killing PID {pid}")
        os.system(f"taskkill /F /PID {pid}")
