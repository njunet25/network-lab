#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import ipaddress

import argparse

parser = argparse.ArgumentParser(description="Run DNS checker")
parser.add_argument("exe_path", nargs="?", default="./build/dns",
                    help="Path to the executable (default: ./build/dns)")
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

def run(domain, type, timeout=20):
    return subprocess.run(
        [exe_path, domain, type],
        capture_output=True,
        timeout=timeout,
        text=True,
    )

tests = []

def it(name, fn):
    tests.append((name, fn))


def normalize_domain(d):
    return d.rstrip('.').lower()

def normalize_txt(t):
    if t.startswith('"') and t.endswith('"'):
        return t[1:-1]
    return t

def match_text(record, expected):
    return normalize_txt(record) == normalize_txt(expected)

def match_ipv4(record, expected):
    return ipaddress.IPv4Address(record) in ipaddress.IPv4Network(expected)

def match_ipv6(record, expected):
    return ipaddress.IPv6Address(record) in ipaddress.IPv6Network(expected)

def match_cname(record, expected):
    return normalize_domain(record) == normalize_domain(expected)

def assert_has_record(domain, type_, expected, output):
    domain = normalize_domain(domain)

    for line in output.strip().splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        d, t, r = parts[0], parts[1], " ".join(parts[2:])
        if normalize_domain(d) == domain and t.upper() == type_:
            if type_ == "A" and match_ipv4(r, expected):
                return
            if type_ == "AAAA" and match_ipv6(r, expected):
                return
            if type_ == "CNAME" and match_cname(r, expected):
                return
            if type_ == "TXT" and match_text(r, expected):
                return

    raise AssertionError(f"Record not found: {domain} {type_} {expected}")


# === tests ===

def test_ipv4_arpa_a():
    res = run("ipv4only.arpa", "A")
    assert_has_record("ipv4only.arpa", "A", "192.0.0.170", res.stdout)
    assert_has_record("ipv4only.arpa", "A", "192.0.0.171", res.stdout)

def test_www_example_com_aaaa():
    res = run("www.example.com", "AAAA")
    assert_has_record("www.example.com", "CNAME", "www.example.com-v4.edgesuite.net", res.stdout)
    assert_has_record("www.example.com-v4.edgesuite.net", "CNAME", "a1422.dscr.akamai.net", res.stdout)
    assert_has_record("a1422.dscr.akamai.net", "AAAA", "2000::/3", res.stdout)

def test_spf_google_txt():
    res = run("_spf.google.com", "TXT")
    assert_has_record("_spf.google.com", "TXT", "v=spf1 include:_netblocks.google.com include:_netblocks2.google.com ~all", res.stdout)

def test_www_nju_edu_cn_a():
    res = run("www.nju.edu.cn", "A")
    assert_has_record("www.nju.edu.cn", "A", "202.119.32.7", res.stdout)

def test_www_nju_edu_cn_aaaa():
    res = run("www.nju.edu.cn", "AAAA")
    assert_has_record("www.nju.edu.cn", "AAAA", "2001:da8:1007::9999", res.stdout)

def test_nxdomain_nju_edu_cn():
    res = run("nxdomain.nju.edu.cn", "AAAA")
    assert res.returncode != 0, "should error when NXDOMAIN"

def test_www_mi_com():
    res = run("小米科技有限责任公司.中国", "A")
    assert_has_record("xn--boq62d51cv6mulib5gtq9aboevs9begt.xn--fiqs8s", "A", "0.0.0.0/0", res.stdout)

def test_fake_apple_com():
    res = run("www.аррӏе.com", "A")
    assert_has_record("www.xn--80ak6aa92e.com", "CNAME", "xn--80ak6aa92e.com", res.stdout)
    assert_has_record("xn--80ak6aa92e.com", "A", "104.198.14.52", res.stdout)
    # assert_has_record("xn--80ak6aa92e.com", "A", "0.0.0.0/0", res.stdout)

it("ipv4only.arpa A", test_ipv4_arpa_a)
it("www.example.com AAAA", test_www_example_com_aaaa)
it("_spf.google.com TXT", test_spf_google_txt)
it("www.nju.edu.cn A", test_www_nju_edu_cn_a)
it("www.nju.edu.cn AAAA", test_www_nju_edu_cn_aaaa)
it("nxdomain.nju.edu.cn AAAA", test_nxdomain_nju_edu_cn)

if bonus_enabled:
    it("IDN: www.mi.com A", test_www_mi_com)
    it("IDN: fake apple A", test_fake_apple_com)

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
