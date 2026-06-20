#!/usr/bin/env python3
"""
make_icons.py — 의존성 0(stdlib zlib/struct만)으로 PWA 아이콘 PNG를 그린다.

PIL/matplotlib 없이도 동작. 다크 네이비 배경 + 상승 막대차트 + 업애로우 모티프.
정훈 증권 앱 홈화면 아이콘. 출력: app/icons/icon-{180,192,512}.png

사용법: python3 app/make_icons.py
"""
import os
import struct
import zlib

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


def png_bytes(px, w, h):
    """px: bytearray RGBA (w*h*4) → PNG bytes."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter: none
        raw.extend(px[y * w * 4:(y + 1) * w * 4])

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def render(size):
    s = size
    px = bytearray(s * s * 4)
    top = (0x16, 0x20, 0x38)     # 위쪽 네이비
    bot = (0x0a, 0x0d, 0x14)     # 아래쪽 더 어두운
    gold = (0xff, 0xcc, 0x4d)
    green = (0x34, 0xd3, 0x99)
    blue = (0x6d, 0x8b, 0xff)

    def setpx(x, y, rgb, a=255):
        if 0 <= x < s and 0 <= y < s:
            i = (y * s + x) * 4
            px[i], px[i + 1], px[i + 2], px[i + 3] = rgb[0], rgb[1], rgb[2], a

    # 배경 세로 그라데이션
    for y in range(s):
        col = lerp(top, bot, y / s)
        for x in range(s):
            setpx(x, y, col)

    # 막대 3개 (상승) — 비율 좌표
    bars = [(0.22, 0.62, blue), (0.42, 0.48, green), (0.62, 0.30, gold)]
    bw = int(s * 0.13)
    base = int(s * 0.78)
    for bx, topf, col in bars:
        x0 = int(s * bx)
        y0 = int(s * topf)
        for x in range(x0, x0 + bw):
            for y in range(y0, base):
                setpx(x, y, col)

    # 상승 화살표 (우상향 대각선 + 화살촉) — gold
    aw = max(2, int(s * 0.022))
    p0 = (int(s * 0.24), int(s * 0.60))
    p1 = (int(s * 0.78), int(s * 0.24))
    steps = s * 2
    for k in range(steps + 1):
        t = k / steps
        cx = int(p0[0] + (p1[0] - p0[0]) * t)
        cy = int(p0[1] + (p1[1] - p0[1]) * t)
        for dx in range(-aw, aw + 1):
            for dy in range(-aw, aw + 1):
                if dx * dx + dy * dy <= aw * aw:
                    setpx(cx + dx, cy + dy, gold)
    # 화살촉
    hx, hy = p1
    hl = int(s * 0.10)
    for dx in range(0, hl):
        for dy in range(0, dx + 1):
            setpx(hx - dx, hy + dy, gold)        # 아래쪽 날
            setpx(hx - dy, hy + dx, gold)        # 왼쪽 날
    return png_bytes(px, s, s)


def main():
    os.makedirs(OUT, exist_ok=True)
    for sz in (180, 192, 512):
        with open(os.path.join(OUT, f"icon-{sz}.png"), "wb") as f:
            f.write(render(sz))
        print(f"✅ icons/icon-{sz}.png")


if __name__ == "__main__":
    main()
