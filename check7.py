#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import ipaddress
import filecmp
import shutil
import signal

import argparse

parser = argparse.ArgumentParser(description="Run traceroute checker")
parser.add_argument("exe_path", nargs="?", default="./build/tftp",
                    help="Path to the executable (default: ./build/tftp)")
parser.add_argument("--bonus", action="store_true",
                    help="Test for Bonus")
parser.add_argument("--no-window", action="store_true",
                    help="Disable window")
parser.add_argument("--dump", nargs="?", const="dump.pcap",
                    help="Enable tcpdump, and dump to specific path, defaults to `dump.pcap`")

args = parser.parse_args()

exe_path = args.exe_path
bonus_enabled = args.bonus
dump_path = args.dump
disable_window = args.no_window
#nocapture = args.nocapture

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
        [exe_path, *options],
        timeout=timeout,
        text=True,
    )

def run_command(prog, *options):
    try:
        return subprocess.run(
            [prog, *options],
            capture_output=False,
            stderr=sys.stderr,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"{e.cmd} failed, code {e.returncode}")
        print(f"Reason: \n{e.stderr}")

tests = []

def it(name, fn):
    tests.append((name, fn))

def ns_create(ns):
    print(f"Creating netns: {ns}")
    ret = run_command("ip","netns","add", ns)
    if ret.returncode != 0:
        raise RuntimeError(f"failed to run {ret.args}:\n{ret.stderr}")
    
def ns_remove(ns):
    print(f"Deleting netns: {ns}")
    assert run_command("ip","netns","del", ns).returncode == 0

def ns_run(ns, prog, *options, timeout=600):
    return subprocess.run(
        ["ip", "netns", "exec", ns, prog, *options],
        capture_output=True,
        timeout=timeout,
        text=True,
    )

def ns_run_as(ns, prog, *options, timeout=600, user=1000):
    return ns_run(ns, "sudo", "-u", f"#{user}", prog, *options)

def run_server():
    return subprocess.Popen(
        ["ip", "netns", "exec", "tftpd", "sudo", "-u", "#1000", "atftpd", "--bind-address", "10.0.70.3", "--no-fork", "--daemon",
            "--port","6969","--prevent-sas","/tmp/tftpd"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        preexec_fn=os.setsid
    )

def run_tcpdump(path):
    return subprocess.Popen(
        ["ip", "netns", "exec", "tftp", "tcpdump", "-i", "veth0","-w", path]
    )

def run_cleanup():
    if dump_path:
        print("Waiting for packet")
        time.sleep(3)
        tcpdump.terminate()
    server.terminate()
    clean_network("tftp", "tftpd")

def signal_cleanup(signum, frame):
    print(f"Got signal {signum}. Cleaning up...")
    run_cleanup()
    sys.exit(1)

def run_tftp(file, window=1):
    if disable_window:
        window = 1
    shutil.rmtree("/tmp/tftp", ignore_errors=True)
    os.makedirs("/tmp/tftp", exist_ok=True)
    os.chown("/tmp/tftp", 1000, 1000)

    start = time.perf_counter()
    ret = ns_run_as("tftp", exe_path, "10.0.70.3", "6969", f"{file}", f"/tmp/tftp/{file}", f"{window}")
    end = time.perf_counter()

    if ret.returncode != 0:
        raise RuntimeError(f"tftp: return {ret.returncode}\nstderr:\n{ret.stderr}")

    if not compare_files(f"/tmp/tftpd/{file}", f"/tmp/tftp/{file}"):
        raise AssertionError(f"File mismatch, stderr: \n{ret.stderr}")
    elapsed = end - start
    size = os.path.getsize(f"/tmp/tftp/{file}")
    print(f"{size/1024:.1f} KB, window {window}, {size/elapsed/1024:.2f} KB/s")

def setup_network(ns1, ns2, veth0="veth0", veth1="veth1"):
    ns_create(ns1)
    ns_create(ns2)

    run_command("ip", "link", "add", veth0, "type", "veth", "peer", "name", veth1)
    run_command("ip", "link", "set", veth0, "netns", ns1)
    run_command("ip", "link", "set", veth1, "netns", ns2)

    ns_run(ns1, "ip", "link", "set", veth0, "up")
    ns_run(ns1, "ip", "addr", "add", "10.0.70.2", "dev", veth0)
    ns_run(ns1, "ip", "route", "add", "10.0.70.0/24", "dev", veth0)

    ns_run(ns2, "ip", "link", "set", veth1, "up")
    ns_run(ns2, "ip", "addr", "add", "10.0.70.3", "dev", veth1)
    ns_run(ns2, "ip", "route", "add", "10.0.70.0/24", "dev", veth1)

def display_network(ns1, ns2, veth0="veth0", veth1="veth1"):
    print(f"TFTP Client:\n{ns_run(ns1, "ip", "addr").stdout}")
    print(f"TFTP Client:\n{ns_run(ns1, "ip", "r").stdout}")
    print(f"TFTP Server:\n{ns_run(ns2, "ip", "addr").stdout}")
    print(f"TFTP Server:\n{ns_run(ns2, "ip", "r").stdout}")

def clean_network(ns1, ns2, veth0="veth0", veth1="veth1"):
    run_command("ip", "link", "del", veth0)
    run_command("ip", "link", "del", veth1)

    ns_remove(ns1)
    ns_remove(ns2)

def tc_set(ns, interface, /, latency=None, loss=None, rate=None, reorder_ratio=None, reorder_gap=None):
    tc_args = []
    if isinstance(latency, float) or isinstance(latency, int):
        tc_args.extend(["delay", f"{latency}ms", f"{latency / 10}ms"])
    if rate:
        tc_args.extend(["rate",f"{rate}"])
    if loss:
        tc_args.extend(["loss", "random", f"{loss}%"])
    if reorder_ratio:
        tc_args.extend(["reorder", f"{reorder_ratio}"])
    if reorder_gap:
        tc_args.extend([f"{reorder_gap}"])

    print(f"{interface}: {tc_args}")
    ret =  ns_run(ns, "tc", "qdisc", "add", "dev", interface, "root", "netem", *tc_args);
    if ret.returncode != 0:
        raise RuntimeError(f"failed to run {ret.args}:\n{ret.stderr}")
    return ret

def tc_clean(ns, interface):
    return ns_run(ns, "tc", "qdisc", "del", "dev", interface, "root")

def tc_clean_all():
    tc_clean("tftp", "veth0")
    tc_clean("tftpd", "veth1")

def compare_files(a, b):
    return filecmp.cmp(a, b, shallow=False)

def create_random_file(file, size):
    with open(file, "wb") as f:
        chunk = 4096
        bytes_left = size
        while bytes_left > 0:
            write_size = min(bytes_left, chunk)
            f.write(os.urandom(write_size))
            bytes_left -= write_size


signal.signal(signal.SIGTERM, signal_cleanup)
signal.signal(signal.SIGINT, signal_cleanup)


def fetch():
    run_tftp("test.386")
    run_tftp("test.512")
    run_tftp("test.513")
    run_tftp("test.4k", 1)

def fetch_with_window():
    run_tftp("test.4k", 1)
    run_tftp("test.128k", 16)
    run_tftp("test.16m", 128)
    run_tftp("test.24m", 16384)

def fetch_latency():
    try:
        # asymmetric latency.
        tc_set("tftpd", "veth1", latency=300)
        tc_set("tftp", "veth0", latency=300)
        run_tftp("test.4k", 1)
        run_tftp("test.16k", 1)
        run_tftp("test.16k", 8)
        run_tftp("test.64k", 16)
    finally:
        tc_clean("tftp", "veth0")
        tc_clean("tftpd", "veth1")

def fetch_lossy():
    try:
        tc_set("tftpd", "veth1", loss=20, latency=100)
        tc_set("tftp", "veth0", loss=20, latency=100)
        run_tftp("test.4k", 1)
        run_tftp("test.16k", 4)
        run_tftp("test.64k", 16)
        run_tftp("test.128k", 32)
        tc_clean("tftp", "veth0")
        tc_clean("tftpd", "veth1")


        tc_set("tftpd", "veth1", loss=10, latency=25)
        tc_set("tftp", "veth0", loss=10, latency=25)
        run_tftp("test.4k", 1)
        run_tftp("test.16k", 4)
        run_tftp("test.64k", 16)
        run_tftp("test.128k", 32)
        run_tftp("test.512k", 64)
        #run_tftp("test.16m", 32)
        #run_tftp("test.16m", 32)
        #run_tftp("test.24m", 128)
        tc_clean("tftp", "veth0")
        tc_clean("tftpd", "veth1")

        tc_set("tftpd", "veth1", loss=2, latency=25)
        tc_set("tftp", "veth0", loss=2, latency=25)
        run_tftp("test.4k", 1)
        run_tftp("test.16k", 4)
        run_tftp("test.64k", 16)
        run_tftp("test.128k", 32)
        run_tftp("test.512k", 64)
        #run_tftp("test.16m", 32)
        #run_tftp("test.16m", 32)
        #run_tftp("test.24m", 128)
        tc_clean("tftp", "veth0")
        tc_clean("tftpd", "veth1")
    finally:
        tc_clean_all()

def fetch_reorder():
    try:
        tc_set("tftpd", "veth1", reorder_ratio=5, reorder_gap=5, latency=25)
        tc_set("tftp", "veth0", reorder_ratio=5, reorder_gap=5, latency=25)
        run_tftp("test.4k", 1)
        run_tftp("test.4k", 4)
        run_tftp("test.128k", 16)
        run_tftp("test.1m", 32)
        #run_tftp("test.24m", 256)
        #run_tftp("test.24m", 512)
        #run_tftp("test.24m", 1024)
        tc_clean("tftp", "veth0")
        tc_clean("tftpd", "veth1")

        tc_set("tftpd", "veth1", reorder_ratio=2, reorder_gap=5, latency=25)
        tc_set("tftp", "veth0", reorder_ratio=2, reorder_gap=5, latency=25)
        run_tftp("test.4k", 16)
        run_tftp("test.128k", 16)
        run_tftp("test.1m", 32)
        #run_tftp("test.16m", 256)
        #run_tftp("test.16m", 512)
        #run_tftp("test.24m", 1024)
        tc_clean("tftp", "veth0")
        tc_clean("tftpd", "veth1")
    finally:
        tc_clean_all()

def fetch_lfn():
    try:
        tc_set("tftpd", "veth1", latency=50, reorder_ratio=0.01, reorder_gap=5, loss=0.05)
        tc_set("tftp", "veth0", latency=50, reorder_ratio=0.01, reorder_gap=5, loss=0.05)
        run_tftp("test.128k", 32)
        run_tftp("test.24m", 128)
        run_tftp("test.24m", 256)
        run_tftp("test.24m", 512)
        run_tftp("test.24m", 1024)
        tc_clean("tftp", "veth0")
        tc_clean("tftpd", "veth1")
        tc_set("tftpd", "veth1", latency=20, reorder_ratio=0.02, reorder_gap=1, loss=0.1)
        tc_set("tftp", "veth0", latency=20, reorder_ratio=0.02, reorder_gap=1, loss=0.1)
        run_tftp("test.24m", 512)
        run_tftp("test.24m", 1024)
    finally:
        tc_clean_all()

os.chown("/tmp/tftp", 1000, 1000)
os.makedirs("/tmp/tftpd", exist_ok=True)

create_random_file("/tmp/tftpd/test.386", 386)
create_random_file("/tmp/tftpd/test.512", 512)
create_random_file("/tmp/tftpd/test.513", 513)
create_random_file("/tmp/tftpd/test.4k", 1024*4)
create_random_file("/tmp/tftpd/test.16k", 1024*16)
create_random_file("/tmp/tftpd/test.64k", 1024*16)
create_random_file("/tmp/tftpd/test.128k", 1024*128)
create_random_file("/tmp/tftpd/test.512k", 1024*512)
create_random_file("/tmp/tftpd/test.1m", 1024*1024*1)
create_random_file("/tmp/tftpd/test.16m", 1024*1024*16)
create_random_file("/tmp/tftpd/test.24m", 1024*1024*24)

it("TFTP", fetch)

#it("TFTP, Larger File", fetch_large)
it("TFTP+Windowsize", fetch_with_window)
it("TFTP on high RTT", fetch_latency)
it("TFTP on Lossy Network", fetch_lossy)
it("TFTP with Packet Reordering", fetch_reorder)
it("TFTP on LFN", fetch_lfn)

# =============

count_pass = 0
count_test = 0

setup_network("tftp", "tftpd")
#display_network("tftp", "tftpd")
server = run_server()
if dump_path:
    tcpdump = run_tcpdump(dump_path)

print("Waiting for server (and tcpdump)")
time.sleep(3)
assert not server.poll()

print("")
print(f"running {len(tests)} tests")
start = time.perf_counter()

for name, fn in tests:
    print(f"running test {name} : ", end="\n")
    try:
        fn()
        print(f"{name}: \033[32mok\033[0m")
        count_pass += 1
        count_test += 1
    except Exception as e:
        print(f"{name}: \033[31mfail ({e})\033[0m")
        count_test += 1
    print("")

print("")
end = time.perf_counter()
elapsed = end - start
result = "\033[32mok\033[0m" if count_pass == count_test else "\033[31mfail\033[0m"
if disable_window:
    print("Test with window disabled.")

print(f"test result: {result}. {count_pass} passed; {count_test - count_pass} failed; finished in {elapsed:.2f}s")

run_cleanup()

if count_test == count_pass:
    ret = 0
else:
    ret = 1

sys.exit(ret)