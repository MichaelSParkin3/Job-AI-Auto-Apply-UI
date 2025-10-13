#!/usr/bin/env python3
"""
Generate a de-identified PDF resume from a profile TOML without external deps.

This script reads profiles/<profile_id>.toml and writes a simple 1-page PDF
containing only generic, non-personal info derived from the profile fields.

Usage:
  python scripts/build_pdf_resume.py --profile front_end \
      --output resumes/Front_End_Specialist_Resume_2025.pdf
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

try:
    import tomllib  # Python 3.11+
except Exception as exc:  # pragma: no cover
    print("Python 3.11+ is required (tomllib)", file=sys.stderr)
    raise


def _read_profile(profile_id: str, base: Path) -> dict:
    profile_path = base / f"{profile_id}.toml"
    if not profile_path.exists():
        raise SystemExit(f"Profile not found: {profile_path}")
    return tomllib.loads(profile_path.read_text(encoding="utf-8"))


def _wrap(text: str, width: int = 84) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        add = (1 if cur else 0) + len(w)
        if cur_len + add > width:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len += add
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]


def _escape_pdf_text(s: str) -> str:
    # Escape parentheses and backslashes for PDF string literals
    return s.replace("\\", r"\\\\").replace("(", r"\(").replace(")", r"\)")


def _build_content_lines(profile: dict) -> list[str]:
    name = str(profile.get("name") or profile.get("id") or "Front End Specialist")
    defaults = {k: str(v) for k, v in (profile.get("defaults") or {}).items() if v is not None}
    keywords = {k: [str(x) for x in v] for k, v in (profile.get("keywords") or {}).items()}
    prompts = {k: str(v) for k, v in (profile.get("prompts") or {}).items() if v is not None}

    # Build sections
    lines: list[str] = []
    # Header
    lines.append(f"== {name} ==")
    if defaults.get("location"):
        lines.append(defaults["location"])  # e.g., "Remote (US)"
    # Links (generic)
    link_fields = [
        ("Portfolio", defaults.get("portfolio_url")),
        ("GitHub", defaults.get("github_url")),
        ("LinkedIn", defaults.get("linkedin_url")),
        ("Email", defaults.get("email")),
    ]
    link_line = ", ".join([f"{k}: {v}" for k, v in link_fields if v])
    if link_line:
        lines.append(link_line)
    lines.append("")

    # Summary
    summary = prompts.get("resume_summary") or "Front-end specialist focused on accessible, performant web apps."
    lines.append("SUMMARY")
    lines.extend(_wrap(summary))
    lines.append("")

    # Skills
    skills = keywords.get("tech_stack", [])
    if skills:
        lines.append("SKILLS")
        wrapped = _wrap(", ".join(skills))
        lines.extend(wrapped)
        lines.append("")

    # Domains
    domains = keywords.get("domains", [])
    if domains:
        lines.append("DOMAINS")
        lines.extend(_wrap(", ".join(domains)))
        lines.append("")

    # Target Roles
    roles = keywords.get("roles", [])
    if roles:
        lines.append("TARGET ROLES")
        lines.extend(_wrap(", ".join(roles)))
        lines.append("")

    # Achievements
    achievements = prompts.get("key_accomplishments", "").splitlines()
    achievements = [re.sub(r"^[-\s]+", "- ", a).strip() for a in achievements if a.strip()]
    if achievements:
        lines.append("SELECTED ACHIEVEMENTS")
        for a in achievements:
            for wl in _wrap(a, width=82):
                lines.append(wl)
        lines.append("")

    # Work Authorization (as a note)
    if defaults.get("work_authorization"):
        lines.append("NOTES")
        lines.append(defaults["work_authorization"])  # keep generic

    # Ensure no personal phone/zip appears, even if present
    redacted = []
    for ln in lines:
        ln = re.sub(r"\b\+?1?[-.\s]?(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})\b", "[redacted]", ln)
        ln = re.sub(r"\b\d{5}(?:-\d{4})?\b", "[redacted]", ln)
        redacted.append(ln)
    return redacted


def _make_simple_pdf(lines: list[str], out_path: Path) -> None:
    # Very small PDF writer: 1 page, Helvetica, 12pt, letter size
    # Coordinates: start at (72, 760) and step down by 14 per line
    # Title line (first) will be 18pt; we just include a separate text object for it.

    def to_bytes(s: str) -> bytes:
        return s.encode("latin-1", errors="replace")

    # Build content stream
    y_start = 760
    leading = 14
    content: list[str] = []

    # Title
    if lines:
        title = _escape_pdf_text(lines[0])
        content.append("BT /F1 18 Tf 72 {} Td ({} ) Tj ET".format(y_start, title))
        cur_y = y_start - 24
        body = lines[1:]
    else:
        cur_y = y_start
        body = []

    # Body lines
    for ln in body:
        ln = _escape_pdf_text(ln)
        if cur_y < 72:  # crude bottom margin check; stop overflow
            break
        content.append(f"BT /F1 12 Tf 72 {cur_y} Td ({ln}) Tj ET")
        cur_y -= leading

    stream_text = "\n".join(content)
    stream_bytes = to_bytes(stream_text)

    # Prepare objects
    objects: list[bytes] = []
    # 1: Catalog
    objects.append(to_bytes("<< /Type /Catalog /Pages 2 0 R >>"))
    # 2: Pages
    objects.append(to_bytes("<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    # 3: Page
    page_dict = (
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
    )
    objects.append(to_bytes(page_dict))
    # 4: Contents stream
    stream_obj = b"<< /Length %d >>\nstream\n" % len(stream_bytes) + stream_bytes + b"\nendstream"
    objects.append(stream_obj)
    # 5: Font
    objects.append(to_bytes("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))

    # Build PDF file
    xref_positions: list[int] = []
    out = bytearray()
    out.extend(b"%PDF-1.4\n")
    for i, obj in enumerate(objects, start=1):
        xref_positions.append(len(out))
        out.extend(to_bytes(f"{i} 0 obj\n"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    # xref
    xref_start = len(out)
    out.extend(to_bytes(f"xref\n0 {len(objects)+1}\n"))
    out.extend(b"0000000000 65535 f \n")  # object 0
    for pos in xref_positions:
        out.extend(to_bytes(f"{pos:010d} 00000 n \n"))
    # trailer
    out.extend(
        to_bytes(
            "trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".format(
                size=len(objects) + 1, start=xref_start
            )
        )
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="front_end")
    ap.add_argument("--profiles-dir", default="profiles")
    ap.add_argument("--output", default="resumes/Front_End_Specialist_Resume_2025.pdf")
    args = ap.parse_args()

    profile = _read_profile(args.profile, Path(args.profiles_dir))
    lines = _build_content_lines(profile)
    _make_simple_pdf(lines, Path(args.output))
    print(f"Wrote {args.output} with {len(lines)} lines.")


if __name__ == "__main__":
    main()

