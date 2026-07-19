#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read_doc.py — 정훈이 주는 자료(PDF·문서) 텍스트 추출기 (자기치유).

Read 툴은 PDF 렌더에 poppler(pdftoppm)가 필요한데 웹 컨테이너엔 없을 때가 많다.
이 스크립트는 poppler 없이 **텍스트 레이어를 직접 추출**한다 → 노션 PDF·리서치
리포트·증권사 자료를 바로 소화. 스캔본(이미지 PDF)은 텍스트가 없으니 Read 툴의
시각 인식으로 넘겨야 한다(그 경우 안내 출력).

자기치유: 웹 컨테이너의 cryptography 백엔드(_cffi_backend)가 깨져 pdfminer/pypdf가
임포트조차 안 되는 사례가 있다(2026-07-19 실측) → cffi 재설치·라이브러리 자동 설치
후 재시도한다. 라이브러리 임포트는 전부 함수 안(지연) — selfcheck import 게이트 무해.

사용:
  python3 read_doc.py <파일>                    # 텍스트 → stdout
  python3 read_doc.py <파일> --save             # docs/research/inbox/<이름>.txt 로 저장
  python3 read_doc.py <파일> --save --out DIR
  python3 read_doc.py <파일.pdf> --pages 1-5     # PDF 특정 페이지만

지원: .pdf(텍스트 레이어) · .txt/.md/.json/.csv(그대로) · 그 외는 UTF-8 시도.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
INBOX = os.path.join(REPO, "docs", "research", "inbox")


def _pip(*pkgs: str) -> None:
    """조용히 pip 설치(웹 컨테이너는 pip 가용·ephemeral). 실패해도 예외 안 냄."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *pkgs],
                       capture_output=True, timeout=180)
    except Exception:
        pass


def _repair_crypto() -> None:
    """cryptography 백엔드 깨짐(_cffi_backend 없음) 자동복구."""
    try:
        import _cffi_backend  # noqa: F401
        return
    except Exception:
        _pip("--force-reinstall", "cffi")


def _parse_pages(spec: str | None):
    if not spec:
        return None
    if "-" in spec:
        a, b = spec.split("-", 1)
        return set(range(int(a) - 1, int(b)))  # 1-indexed → 0-indexed
    return {int(spec) - 1}


def extract_pdf(path: str, pages=None) -> str:
    """pdfminer.six 우선, 실패 시 cffi 복구·설치 후 재시도, 그래도 안 되면 pypdf."""
    # 1) pdfminer 시도 (필요시 설치·복구)
    for attempt in range(2):
        try:
            from pdfminer.high_level import extract_text
            if pages is None:
                return extract_text(path)
            return extract_text(path, page_numbers=pages)
        except Exception:
            if attempt == 0:
                _repair_crypto()
                _pip("pdfminer.six")
            else:
                break
    # 2) pypdf 폴백
    for attempt in range(2):
        try:
            import pypdf
            r = pypdf.PdfReader(path)
            idx = range(len(r.pages)) if pages is None else sorted(pages)
            return "\n".join((r.pages[i].extract_text() or "")
                             for i in idx if 0 <= i < len(r.pages))
        except Exception:
            if attempt == 0:
                _repair_crypto()
                _pip("pypdf")
            else:
                break
    raise RuntimeError(
        "PDF 텍스트 추출 실패. 스캔본(이미지 PDF)이면 텍스트 레이어가 없으니 "
        "Read 툴의 시각 인식(pages 인자)으로 읽어야 함. "
        "라이브러리 문제면: pip install --force-reinstall cffi pdfminer.six")


def extract(path: str, pages=None) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return extract_pdf(path, pages)
    # 텍스트류는 그대로
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def main() -> int:
    ap = argparse.ArgumentParser(description="PDF·문서 텍스트 추출기 (자기치유)")
    ap.add_argument("path", help="읽을 파일 (.pdf/.txt/.md/.json/.csv …)")
    ap.add_argument("--save", action="store_true", help="docs/research/inbox/에 .txt 저장")
    ap.add_argument("--out", help="저장 디렉토리 (기본 docs/research/inbox)")
    ap.add_argument("--pages", help="PDF 페이지 범위 (예: 1-5 또는 3)")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        print(f"파일 없음: {args.path}", file=sys.stderr)
        return 2

    try:
        text = extract(args.path, _parse_pages(args.pages))
    except Exception as e:
        print(f"⚠️ {e}", file=sys.stderr)
        return 1

    text = text.strip()
    if not text:
        print("⚠️ 추출된 텍스트 없음 — 스캔본(이미지)일 가능성. Read 툴 시각인식으로.",
              file=sys.stderr)
        return 1

    if args.save:
        outdir = args.out or INBOX
        os.makedirs(outdir, exist_ok=True)
        base = os.path.splitext(os.path.basename(args.path))[0] + ".txt"
        outp = os.path.join(outdir, base)
        with open(outp, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"saved {os.path.relpath(outp, REPO)}  ({len(text):,} chars)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
