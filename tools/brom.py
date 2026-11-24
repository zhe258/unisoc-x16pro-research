#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brom.py - Unisoc UMS9230 (T616) BootROM client

Flow:
  CHECK_BAUD(CRC16) -> CONNECT -> load FDL1 -> write ROP payload -> END_DATA
  -> FDL1 handshake (sum) -> load FDL2 -> EXEC -> read partition table / dump

Usage:
  python brom.py --wait 600 --dump uboot_a,misc
"""
import os, sys, time, struct, argparse

DLL_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(DLL_DIR):
    try:
        os.add_dll_directory(DLL_DIR)
    except Exception:
        pass
    os.environ["PATH"] = DLL_DIR + ";" + os.environ.get("PATH", "")
    try:
        import ctypes
        ctypes.WinDLL(os.path.join(DLL_DIR, "libusb-1.0.dll"))
    except Exception as _e:
        print("libusb preload failed: %s" % _e)

import usb.core
import usb.util

VID, PID = 0x1782, 0x4D00
T0 = time.time()
HDLC_HEADER = 0x7E
HDLC_ESCAPE = 0x7D

BSL_CMD_CONNECT        = 0x00
BSL_CMD_START_DATA     = 0x01
BSL_CMD_MIDST_DATA     = 0x02
BSL_CMD_END_DATA       = 0x03
BSL_CMD_EXEC_DATA      = 0x04
BSL_CMD_READ_START     = 0x10
BSL_CMD_READ_MIDST     = 0x11
BSL_CMD_READ_END       = 0x12
BSL_CMD_CHECK_BAUD     = 0x1A
BSL_CMD_READ_PARTITION = 0x2D

BSL_REP_ACK            = 0x80
BSL_REP_VER            = 0x81
BSL_REP_READ_FLASH     = 0x93
BSL_REP_INCOMPATIBLE_PARTITION = 0x96
BSL_REP_READ_PARTITION = 0xBA


def log(msg):
    print("[%6.2fs] %s" % (time.time() - T0, msg), flush=True)


def crc16(data, crc=0):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x11021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def spd_sum(data, send_side):
    crc = 0
    i, n = 0, len(data)
    while n - i > 1:
        crc += (data[i + 1] << 8) | data[i]
        i += 2
    if n - i:
        crc += data[i]
    crc = (crc >> 16) + (crc & 0xFFFF)
    crc += crc >> 16
    crc = ~crc & 0xFFFF
    tail = n - i
    if tail < (1 if send_side else 2):
        crc = ((crc >> 8) | ((crc & 0xFF) << 8)) & 0xFFFF
    return crc


def transcode(data):
    out = bytearray()
    for a in data:
        if a == HDLC_HEADER or a == HDLC_ESCAPE:
            out.append(HDLC_ESCAPE)
            a ^= 0x20
        out.append(a)
    return bytes(out)


def untranscode(data):
    out = bytearray()
    i = 0
    while i < len(data):
        a = data[i]
        if a == HDLC_ESCAPE and i + 1 < len(data):
            out.append(data[i + 1] ^ 0x20)
            i += 2
        else:
            out.append(a)
            i += 1
    return bytes(out)


class Brom:
    def __init__(self, dev, crc=True, verbose=True):
        self.dev = dev
        self.crc_mode = crc
        self.verbose = verbose
        self.ep_in = None
        self.ep_out = None
        self.buf = bytearray()
        self._find_endpoints()

    def _find_endpoints(self):
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]
        for ep in intf:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                if self.ep_in is None:
                    self.ep_in = ep.bEndpointAddress
            else:
                if self.ep_out is None:
                    self.ep_out = ep.bEndpointAddress
        log("endpoints: IN=0x%02X OUT=0x%02X" % (self.ep_in, self.ep_out))

    def _frame(self, msg_type, data=b""):
        body = struct.pack(">HH", msg_type, len(data)) + data
        chk = crc16(body) if self.crc_mode else spd_sum(body, True)
        body += struct.pack(">H", chk)
        return bytes([HDLC_HEADER]) + transcode(body) + bytes([HDLC_HEADER])

    def send(self, msg_type, data=b""):
        f = self._frame(msg_type, data)
        if self.verbose and len(f) < 40:
            log("  > " + " ".join("%02X" % x for x in f))
        self.dev.write(self.ep_out, f, timeout=5000)

    def send_raw(self, raw):
        self.dev.write(self.ep_out, raw, timeout=5000)

    def recv(self, timeout_ms=5000):
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            start = self.buf.find(HDLC_HEADER)
            if start >= 0:
                end = self.buf.find(HDLC_HEADER, start + 1)
                if end > start + 1:
                    frame = bytes(self.buf[start + 1:end])
                    del self.buf[:end + 1]
                    body = untranscode(frame)
                    if len(body) >= 6:
                        mtype, mlen = struct.unpack(">HH", body[:4])
                        payload = body[4:4 + mlen]
                        got = struct.unpack(">H", body[4 + mlen:6 + mlen])[0]
                        want = crc16(body[:4 + mlen]) if self.crc_mode else spd_sum(body[:4 + mlen], False)
                        if self.verbose:
                            log("  < type=0x%02X len=%d chk=0x%04X (expect 0x%04X)" % (mtype, mlen, got, want))
                        if got != want:
                            log("  [!] checksum mismatch")
                            continue
                        return mtype, payload
            try:
                chunk = self.dev.read(self.ep_in, 65536, timeout=100)
                if chunk:
                    self.buf.extend(bytes(chunk))
            except usb.core.USBTimeoutError:
                pass
            except usb.core.USBError as e:
                s = str(e)
                if "Timeout" in s:
                    continue
                if "Pipe" in s or "stall" in s.lower():
                    log("  [!] endpoint stall, clearing")
                    try:
                        self.dev.clear_halt(self.ep_in)
                    except Exception:
                        pass
                    time.sleep(0.1)
                    continue
                log("  [!!] USB error: %s" % s)
                raise
        return None, None

    def check_baud(self, n=1, tries=1):
        self.send_raw(bytes([HDLC_HEADER]) * n)
        for _ in range(tries):
            t, p = self.recv(5000)
            if t is not None:
                return t, p
        return None, None

    def send_file(self, data, addr, chunk=528, end=True):
        self.send(BSL_CMD_START_DATA, struct.pack(">II", addr, len(data)))
        t, _ = self.expect({BSL_REP_ACK}, 8000)
        if t != BSL_REP_ACK:
            raise RuntimeError("START_DATA failed: 0x%02X" % (t or 0))
        for off in range(0, len(data), chunk):
            self.send(BSL_CMD_MIDST_DATA, data[off:off + chunk])
            t, _ = self.expect({BSL_REP_ACK}, 10000)
            if t != BSL_REP_ACK:
                raise RuntimeError("MIDST_DATA failed @%d: 0x%02X" % (off, t or 0))
        if not end:
            return
        self.send(BSL_CMD_END_DATA)
        t, _ = self.expect({BSL_REP_ACK}, 10000)
        if t != BSL_REP_ACK:
            raise RuntimeError("END_DATA failed: 0x%02X" % (t or 0))

    def exec_data(self, timeout=15000):
        self.send(BSL_CMD_EXEC_DATA)
        return self.recv(timeout)

    # ---- FDL2 read/write ----
    def read_part(self, name, size, chunk=2112, retries=2):
        last = None
        for attempt in range(retries + 1):
            try:
                return self._read_part_once(name, size, chunk)
            except Exception as e:
                last = e
                log("    retry %d/%d (%s)" % (attempt + 1, retries, e))
                time.sleep(0.3)
        raise last

    def _read_part_once(self, name, size, chunk):
        nm = name.encode("utf-16-le")[:72].ljust(72, b"\x00")
        self.buf = bytearray()
        self.send(BSL_CMD_READ_START, nm + struct.pack("<I", size))
        t, _ = self.recv(6000)
        if t != BSL_REP_ACK:
            raise RuntimeError("READ_START failed: 0x%02X" % (t or 0))
        out = bytearray()
        self.last_stats = {"chunks": 0, "lens": []}
        while len(out) < size:
            n = min(chunk, size - len(out))
            self.send(BSL_CMD_READ_MIDST, struct.pack("<II", n, len(out) & 0xFFFFFFFF))
            t, p = self.recv(15000)
            if t == BSL_REP_READ_FLASH and p:
                self.last_stats["chunks"] += 1
                self.last_stats["lens"].append(len(p))
                out += p
            elif t == BSL_REP_ACK:
                raise RuntimeError("got ACK instead of data @%d" % len(out))
            else:
                raise RuntimeError("READ_MIDST failed @%d: 0x%02X" % (len(out), t or 0))
        self.send(BSL_CMD_READ_END)
        try:
            self.recv(6000)
        except Exception:
            pass
        return bytes(out)

    def expect(self, want, timeout_ms=8000):
        """segmented read + incremental write"""
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            left = int((deadline - time.time()) * 1000)
            if left <= 0:
                break
            t, p = self.recv(min(left, 4000))
            if t is None:
                continue
            if t in want:
                return t, p
        return None, None

    def read_part_to_file(self, name, size, path, chunk=32768, segment=4 * 1024 * 1024):
        """segmented read + incremental write"""
        nm = name.encode("utf-16-le")[:72].ljust(72, b"\x00")
        off = 0
        self.last_stats = {"chunks": 0, "lens": []}
        with open(path, "wb") as f:
            while off < size:
                seg_end = min(size, off + segment)
                self.buf = bytearray()
                self.send(BSL_CMD_READ_START, nm + struct.pack("<I", seg_end))
                t, _ = self.expect({BSL_REP_ACK}, 8000)
                if t != BSL_REP_ACK:
                    raise RuntimeError("READ_START failed @%d: 0x%02X" % (off, t or 0))
                while off < seg_end:
                    n = min(chunk, seg_end - off)
                    self.send(BSL_CMD_READ_MIDST, struct.pack("<II", n, off & 0xFFFFFFFF))
                    t, p = self.expect({BSL_REP_READ_FLASH}, 20000)
                    if t != BSL_REP_READ_FLASH or not p:
                        raise RuntimeError("READ_MIDST failed @%d: 0x%02X" % (off, t or 0))
                    f.write(p)
                    f.flush()
                    self.last_stats["chunks"] += 1
                    self.last_stats["lens"].append(len(p))
                    off += len(p)
                self.send(BSL_CMD_READ_END)
                # ascii note
        return off

    def write_part(self, name, data, chunk=2112):
        nm = name.encode("utf-16-le")[:72].ljust(72, b"\x00")
        self.send(BSL_CMD_START_DATA, nm + struct.pack("<I", len(data)))
        t, _ = self.recv(6000)
        if t != BSL_REP_ACK:
            raise RuntimeError("WRITE_START failed: 0x%02X" % (t or 0))
        for off in range(0, len(data), chunk):
            self.send(BSL_CMD_MIDST_DATA, data[off:off + chunk])
            t, _ = self.recv(15000)
            if t != BSL_REP_ACK:
                raise RuntimeError("WRITE_MIDST failed @%d: 0x%02X" % (off, t or 0))
        self.send(BSL_CMD_END_DATA)
        t, _ = self.recv(15000)
        if t != BSL_REP_ACK:
            raise RuntimeError("WRITE_END failed: 0x%02X" % (t or 0))


def load(path):
    with open(path, "rb") as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=int, default=120)
    ap.add_argument("--fdl1", default="fdl1-9230.bin")
    ap.add_argument("--fdl2", default="fdl2-9230-ufs.bin")
    ap.add_argument("--payload", default="custom_exec_no_verify_65015f08.bin")
    ap.add_argument("--addr1", default="0x65000800")
    ap.add_argument("--addr2", default="0x9efffe00")
    ap.add_argument("--exec-addr", default="0x65015f08")
    ap.add_argument("--no-cve", action="store_true")
    ap.add_argument("--order", default="fdl1-first", choices=["fdl1-first", "payload-first"])
    ap.add_argument("--dump", default="", help="comma separated partition names")
    ap.add_argument("--blk", type=int, default=2112, help="chunk size for read (max 65535)")
    ap.add_argument("--quiet", action="store_true", help="no per-frame logging (faster)")
    ap.add_argument("--bench", default="", help="partition name for block-size sweep")
    ap.add_argument("--run-spl", action="store_true", help="execute spl-unlock.bin as FDL1 and stop")
    ap.add_argument("--write", default="", help="name=file : write file to partition")
    ap.add_argument("--verify-write", action="store_true", help="after write, read back and compare")
    args = ap.parse_args()

    addr1 = int(args.addr1, 16)
    addr2 = int(args.addr2, 16)
    exec_addr = int(args.exec_addr, 16)

    log("waiting for 1782:4D00 (%d s)..." % args.wait)
    try:
        log("script: %s | order: %s | blk: %d" % (
            time.strftime("%m-%d %H:%M:%S", time.localtime(os.path.getmtime(os.path.abspath(__file__)))),
            args.order, args.blk))
    except Exception:
        pass

    dev = None
    deadline = time.time() + args.wait
    while time.time() < deadline:
        d = usb.core.find(idVendor=VID, idProduct=PID)
        if d is not None:
            try:
                try:
                    d.set_configuration()
                except Exception:
                    pass
                usb.util.claim_interface(d, 0)
                dev = d
                break
            except usb.core.USBError as e:
                log("  device present but busy (%s), retrying..." % e)
                time.sleep(0.1)
                continue
        time.sleep(0.05)
    if dev is None:
        log("[X] no device")
        return 2

    log("[OK] device connected")
    b = Brom(dev, crc=True, verbose=not args.quiet)

    log("\n=== 1. CHECK_BAUD (CRC16) ===")
    t, p = b.check_baud(1)
    if t != BSL_REP_VER:
        log("[X] no version (0x%02X)" % (t or 0))
        return 3
    log("[OK] BROM version: %r" % (p[:16],))

    log("\n=== 2. CONNECT ===")
    b.send(BSL_CMD_CONNECT)
    t, _ = b.recv(5000)
    log("[%s] CONNECT -> 0x%02X" % ("OK" if t == BSL_REP_ACK else "X", t or 0))

    if args.order == "fdl1-first":
        f1name = "spl-unlock.bin" if args.run_spl else args.fdl1
        fdl1 = load(os.path.join(DLL_DIR, f1name))
        log("\n=== 3. load %s %d bytes -> 0x%08X ===" % (f1name, len(fdl1), addr1))
        b.send_file(fdl1, addr1, chunk=528, end=True)
        log("[OK] %s in place" % f1name)

        if not args.no_cve:
            payload = load(os.path.join(DLL_DIR, args.payload))
            log("\n=== 4. write CVE payload %d bytes -> 0x%08X (no END) ===" % (len(payload), exec_addr))
            b.send_file(payload, exec_addr, end=False)
            log("[OK] payload written, stack armed")

            log("\n=== 5. send END_DATA to trigger ROP ===")
            b.send(BSL_CMD_END_DATA)
            t, _ = b.recv(3000)
            log("END -> %s" % (("0x%02X" % t) if t is not None else "no reply (expected)"))

        if args.run_spl:
            log("\n*** spl-unlock.bin 正在芯片里执行，等 10 秒 ***")
            time.sleep(10)
            log("*** 结束。如果设备卡住/黑屏，拔线断电重启即可 ***")
            return 0
    else:
        if not args.no_cve:
            payload = load(os.path.join(DLL_DIR, args.payload))
            log("\n=== 3. write CVE payload %d bytes -> 0x%08X (no END) ===" % (len(payload), exec_addr))
            b.send_file(payload, exec_addr, end=False)
            log("[OK] payload written")
        fdl1 = load(os.path.join(DLL_DIR, args.fdl1))
        log("\n=== 4. load FDL1 %d bytes -> 0x%08X ===" % (len(fdl1), addr1))
        b.send_file(fdl1, addr1)
        log("[OK] FDL1 written")
        log("\n=== 5. EXEC ===")
        t, _ = b.exec_data(15000)
        log("EXEC -> 0x%02X" % (t or 0))

    log("\n=== 6. FDL1 handshake (sum) ===")
    b.crc_mode = False
    ok = False
    for i in range(10):
        t, p = b.check_baud(4, tries=1)
        if t == BSL_REP_VER:
            log("[OK] FDL1 version: %r" % (p[:32],))
            ok = True
            break
        log("  checkbaud %d -> %s" % (i + 1, t))
    if not ok:
        log("[X] no FDL1 response")
        return 4

    log("\n=== 7. CONNECT (FDL1) ===")
    b.send(BSL_CMD_CONNECT)
    t, _ = b.recv(5000)
    log("CONNECT -> 0x%02X" % (t or 0))

    fdl2 = load(os.path.join(DLL_DIR, args.fdl2))
    log("\n=== 8. load FDL2 %d bytes -> 0x%08X ===" % (len(fdl2), addr2))
    b.send_file(fdl2, addr2, chunk=528)
    log("[OK] FDL2 written")

    log("\n=== 9. EXEC FDL2 ===")
    t, _ = b.exec_data(20000)
    log("EXEC -> 0x%02X %s" % (t or 0, "(ok)" if t in (BSL_REP_ACK, BSL_REP_INCOMPATIBLE_PARTITION) else ""))
    if t not in (BSL_REP_ACK, BSL_REP_INCOMPATIBLE_PARTITION):
        log("[X] FDL2 did not start")
        return 5
    log("*** FDL2 running ***")

    if args.write:
        nm, path = args.write.split("=", 1)
        fp = path if os.path.isabs(path) else os.path.join(DLL_DIR, path)
        data = load(fp)
        log("\n=== WRITE %s <- %s (%d bytes) ===" % (nm, os.path.basename(fp), len(data)))
        b.write_part(nm, data, chunk=528)
        log("[OK] write finished")
        if args.verify_write:
            log("=== verify: read back ===")
            back = b.read_part(nm, len(data), chunk=32768)
            same = (back == data)
            log("[%s] verify: read %d bytes, identical=%s" % ("OK" if same else "X", len(back), same))
            if not same:
                bad = [i for i in range(min(len(back), len(data))) if back[i] != data[i]][:8]
                log("  first diffs: %s" % ", ".join("0x%X" % i for i in bad))
        return 0

    log("\n=== 10. read partition table (0x2D) ===")
    b.send(BSL_CMD_READ_PARTITION)
    t, p = b.recv(15000)
    if t != BSL_REP_READ_PARTITION:
        log("  direct read failed (0x%02X), retry after CONNECT" % (t or 0))
        b.send(BSL_CMD_CONNECT)
        b.recv(3000)
        b.send(BSL_CMD_READ_PARTITION)
        t, p = b.recv(15000)
    if t != BSL_REP_READ_PARTITION or not p:
        log("[X] no partition table (0x%02X)" % (t or 0))
        return 6

    n = len(p) // 0x4C
    log("[OK] %d partitions (%d bytes)" % (n, len(p)))
    log("")
    log("  %-3s %-24s %12s  %s" % ("#", "name", "size(KB)", "human"))
    rows = []
    for i in range(n):
        e = p[i * 0x4C:(i + 1) * 0x4C]
        try:
            name = e[:72].decode("utf-16-le", "ignore").split("\x00")[0]
        except Exception:
            name = "?"
        kb = struct.unpack("<I", e[72:76])[0]
        if kb * 1024 >= 1 << 30:
            hr = "%.2f GB" % (kb * 1024.0 / (1 << 30))
        elif kb >= 1024:
            hr = "%.1f MB" % (kb / 1024.0)
        else:
            hr = "%d KB" % kb
        log("  %-3d %-24s %12d  %s" % (i, name, kb, hr))
        rows.append((i, name, kb))

    out = os.path.join(DLL_DIR, "partitions.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# %s (unit: KB)\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        for i, name, kb in rows:
            f.write("%d\t%s\t%d\n" % (i, name, kb))
    log("\n[OK] partition table saved: %s" % out)

    if args.bench:
        bt = {name: kb for _, name, kb in rows}
        nm = args.bench if args.bench in bt else "misc"
        total = bt.get(nm, 1024) * 1024
        log("\n=== BENCH: %s (%d bytes) ===" % (nm, total))
        best = None
        for blk in [2112, 4096, 8192, 16384, 32768, 65535]:
            t0 = time.time()
            try:
                data = b.read_part(nm, total, chunk=blk, retries=0)
            except Exception as e:
                log("  blk %-6d FAILED: %s" % (blk, e))
                continue
            dt = time.time() - t0
            stats = getattr(b, "last_stats", {}) or {}
            lens = stats.get("lens") or [0]
            typical = max(set(lens), key=lens.count)
            mbs = (len(data) / 1048576.0) / dt if dt > 0 else 0
            log("  blk %-6d -> %6.2f MB/s  (%d chunks, typical %d bytes)" % (blk, mbs, stats.get("chunks", 0), typical))
            if best is None or mbs > best[1]:
                best = (blk, mbs)
        if best:
            log("\n[BEST] blk=%d  %.2f MB/s" % best)
            log("  : boot_a(64MB) %s / super(6.4GB) %s" % (
                "%.1f min" % (64 / best[1] / 60) if best[1] else "?",
                "%.1f min" % (6444 / best[1] / 60) if best[1] else "?"))

    if args.dump:
        dump_dir = os.path.join(DLL_DIR, "dump")
        os.makedirs(dump_dir, exist_ok=True)
        table = {name: kb for _, name, kb in rows}
        for spec in [x.strip() for x in args.dump.split(",") if x.strip()]:
            if ":" in spec:
                nm, sz = spec.split(":", 1)
                total = int(sz, 0)
            elif spec in table:
                nm, total = spec, table[spec] * 1024
            else:
                nm, total = spec, 512 * 1024
                log("[!] %s not in table, trying %d bytes" % (nm, total))
            log("\n=== dump %s (%d bytes / %.1f MB) ===" % (nm, total, total / 1048576.0))
            t0 = time.time()
            fp = os.path.join(dump_dir, "%s.bin" % nm)
            got = None
            for blk in ([args.blk] if args.blk == 2112 else [args.blk, 2112]):
                try:
                    got = b.read_part_to_file(nm, total, fp, chunk=blk)
                    if blk != args.blk:
                        log("  (blk %d unsupported, fell back to 2112)" % args.blk)
                    break
                except Exception as e:
                    log("[!] blk %d failed: %s" % (blk, e))
            if got is None:
                log("[X] %s read failed" % nm)
                continue
            dt = time.time() - t0
            log("[OK] %s -> %s (%d bytes, %.1fs, %.2f MB/s)" % (
                nm, os.path.basename(fp), got, dt,
                (got / 1048576.0) / dt if dt > 0 else 0))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except usb.core.USBError as e:
        log("[!!] USB error: %s" % e)
        sys.exit(9)
    except Exception as e:
        log("[!!] error: %r" % e)
        sys.exit(9)
