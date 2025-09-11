import os
import sys

exe_path = "./build/http-client"

if len(sys.argv) > 1:
    exe_path = sys.argv[1]

if not os.path.exists(exe_path):
    print(f"ERROR: file not exist: {exe_path}")
    sys.exit(1)

if not os.access(exe_path, os.X_OK):
    print(f"ERROR: file is not executable: {exe_path}")
    sys.exit(1)

print(f"INFO: start testing to {exe_path}...")
