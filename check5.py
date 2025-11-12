#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import ipaddress

import argparse

parser = argparse.ArgumentParser(description="Run traceroute checker")
parser.add_argument("exe_path", nargs="?", default="./build/traceroute",
                    help="Path to the executable (default: ./build/traceroute)")
parser.add_argument("--bonus", action="store_true",
                    help="Enable bonus mode")

args = parser.parse_args()

exe_path = args.exe_path
bonus_enabled = args.bonus

# print("Executable path:", exe_path)
# print("Bonus enabled:", bonus_enabled)


if not os.path.exists(exe_path):
    print(f"file not exist: {exe_path}")
    sys.exit(1)

if not os.access(exe_path, os.X_OK):
    print(f"file is not executable: {exe_path}")
    sys.exit(1)

print(f"preparing tests for {exe_path}...")

def run(target, options, timeout=60):
    return subprocess.run(
        [exe_path, *options, target],
        capture_output=True,
        timeout=timeout,
        text=True,
    )

tests = []

def it(name, fn):
    tests.append((name, fn))


def first_hostname(output):
    lines = output.strip().splitlines()
    if len(lines) < 2:
        raise AssertionError(f"Invalid lines of output.")
    
    line = lines[1]
    parts = line.strip().split()
    host = parts[1].split('(')[0]
    return host

def assert_hostname(output, domain):
    host = first_hostname(output)
    if host != domain:
        raise AssertionError(f"expect `{domain}`, got `{host}`")
     

# === tests ===
def test_localhost_reverse():
    res = run("127.0.0.1", [])
    assert_hostname(res.stdout, "localhost")

def test_localhost_v6_reverse():
    res = run("::1", [])
    assert_hostname(res.stdout, "localhost")

def test_localhost_n_reverse():
    res = run("127.0.0.1", ["-n"])
    host = first_hostname(res.stdout)
    if host != "127.0.0.1":
        raise AssertionError(f"expect IP, got `{host}`")

def test_well_formed():
    res = run("127.0.0.1", [])
    lines = res.stdout.strip().splitlines()
    if len(lines) < 2:
        raise AssertionError(f"Invalid lines of output.")
    
    line = lines[1]
    parts = line.strip().split()
    assert parts[0] == "1"
    int(parts[3])
    int(parts[4])
    int(parts[5])

def test_broadcast():
    res = run("255.255.255.255", [])
    if res.returncode == 0:
        raise AssertionError("traceroute has failed to report error.")

def test_zero_ttl():
    res = run("127.0.0.0", ["-f", "0"])
    if res.returncode == 0:
        raise AssertionError("failed to reject invalid TTL.")

    res = run("127.0.0.0", ["-f", "1000"])
    if res.returncode == 0:
        raise AssertionError("failed to reject invalid TTL.")

it("localhost", test_localhost_reverse)
it("localhost v6", test_localhost_v6_reverse)
it("127.0.0.1", test_localhost_n_reverse)
it("broadcast address", test_broadcast)
it("ttl limit", test_zero_ttl)

# =============

count_pass = 0
count_test = 0

print("")
print(f"running {len(tests)} tests")
start = time.perf_counter()

for name, fn in tests:
    print(f"test {name} ... ", end="")
    try:
        fn()
        print("\033[32mok\033[0m")
        count_pass += 1
        count_test += 1
    except Exception as e:
        print(f"\033[31mfail ({e})\033[0m")
        count_test += 1

print("")
end = time.perf_counter()
elapsed = end - start
result = "\033[32mok\033[0m" if count_pass == count_test else "\033[31mfail\033[0m"
print(f"test result: {result}. {count_pass} passed; {count_test - count_pass} failed; finished in {elapsed:.2f}s")
