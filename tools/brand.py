#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Apply your brand to a MicroSIP source tree (the pinned microsip-custom fork).

    python tools/brand.py <path-to-source-tree> [--brand brand/brand.json]

What it changes (and nothing else):
  - product name, company, version, settings-encryption key   (const.h)
  - window/tray name, menu and help links, default codecs      (define.h)
  - copyright line in the .exe properties, keeping MicroSIP's   (res/main.rc2)
  - update checks: off, or pointed at your own server          (mainDlg.cpp, settings.cpp)
  - crash reports to microsip.org: off                         (microsip.cpp)
  - Windows taskbar identity                                    (jumplist.h)
  - output file name  <exe_name>.exe                           (custom.vcxproj)
  - application icons                                           (res/microsip.ico, res/tray_inactive.ico)

Every change is checked: if an expected line is not found (for example after an
upstream update), the script stops and names the file and the change, so nothing
is half-branded. Running it twice on the same tree is safe.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
KIT = HERE.parent

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{1,38}$")
EXE_RE = re.compile(r"^[A-Za-z0-9_-]{2,40}$")
APPID_RE = re.compile(r"^[A-Za-z0-9]+(\.[A-Za-z0-9]+){1,3}$")
VER_RE = re.compile(r"^\d{1,4}\.\d{1,4}\.\d{1,4}$")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def c_str(s: str) -> str:
    """Escape for a C / resource-script string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def load_brand(path: Path) -> dict:
    b = json.loads(path.read_text(encoding="utf-8"))
    for key in ("name", "exe_name", "company", "app_id", "version", "website", "support_url", "defaults"):
        if key not in b:
            fail(f"{path}: missing '{key}'")
    if not NAME_RE.match(b["name"]):
        fail("name: 2-39 characters, English letters, digits, spaces, . _ - (it is also a folder name)")
    if not EXE_RE.match(b["exe_name"]):
        fail("exe_name: letters, digits, _ or - only, no spaces")
    if not APPID_RE.match(b["app_id"]):
        fail("app_id: like CompanyName.ProductName (letters and digits, dot separated)")
    if not VER_RE.match(b["version"]):
        fail("version: three numbers like 1.0.0")
    for key in ("website", "support_url"):
        if not re.match(r"^https?://", b[key]):
            fail(f"{key}: must start with http:// or https://")
    upd = b.get("update_url", "")
    if upd and urlparse(upd).scheme not in ("http", "https"):
        fail("update_url: leave empty to disable updates, or give an http(s) URL")
    if not b.get("company"):
        fail("company: required")
    return b


def lit(text: str):
    """Replacement that is inserted exactly as written."""
    return lambda m: text


def g1(text: str):
    """Keep the first captured group, then the literal text."""
    return lambda m: m.group(1) + text


class Tree:
    def __init__(self, root: Path):
        self.root = root
        self.changed = []

    def edit(self, rel: str, what: str, pattern: str, repl, count_min: int = 1, flags: int = 0, done_marker: str = None):
        """Regex replace in a file. Fails if the pattern matches fewer than count_min times,
        unless done_marker is already present (the change was applied before)."""
        p = self.root / rel
        if not p.is_file():
            fail(f"{rel} not found — is this the microsip-custom source tree?")
        text, enc, crlf = _read(p)
        new, n = re.subn(pattern, repl, text, flags=flags)
        if n < count_min:
            if done_marker and done_marker in text:
                return
            fail(f"{rel}: could not apply '{what}' (expected text not found). "
                 f"The upstream source has probably changed — update tools/brand.py for this version.")
        if new != text:
            _write(p, new, enc, crlf)
            self.changed.append(f"{rel}: {what}")

    def set_block(self, rel: str, what: str, header: str, block: str):
        """Replace (or append) a block that starts with `header` and runs to the end of the file."""
        p = self.root / rel
        if not p.is_file():
            fail(f"{rel} not found")
        text, enc, crlf = _read(p)
        i = text.find("\n" + header)
        base = text[:i] if i >= 0 else text.rstrip("\n") + "\n"
        new = base + block
        if new != text:
            _write(p, new, enc, crlf)
            self.changed.append(f"{rel}: {what}")


def _read(p: Path):
    """Read a source file; returns (text with \\n line ends, encoding, uses_crlf)."""
    raw = p.read_bytes()
    enc = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError:
        enc = "cp1252"
        text = raw.decode(enc)
    crlf = "\r\n" in text
    return text.replace("\r\n", "\n"), enc, crlf


def _write(p: Path, text: str, enc: str, crlf: bool):
    if crlf:
        text = text.replace("\n", "\r\n")
    p.write_bytes(text.encode(enc))


def apply(tree: Tree, b: dict) -> None:
    name = c_str(b["name"])
    company = c_str(b["company"])
    v4 = b["version"] + ".0"
    comma = v4.replace(".", ",")
    # A brand-specific key for the saved-password encryption in the settings file.
    # The source is public (GPL), so this stops cross-reading with other MicroSIP builds, nothing more.
    key = hashlib.sha256(("brand-key:" + b["app_id"]).encode()).hexdigest()[:24]
    website = c_str(b["website"])
    support = c_str(b["support_url"])
    upd = b.get("update_url", "")
    codecs = c_str(b["defaults"].get("codecs", "G722/16000/1 PCMA/8000/1 PCMU/8000/1"))

    # ---- const.h: identity ---------------------------------------------------------------
    tree.edit("const.h", "product name", r'#define _GLOBAL_NAME "[^"]*"', lit(f'#define _GLOBAL_NAME "{name}"'))
    tree.edit("const.h", "company", r'#define _GLOBAL_COMPANY "[^"]*"', lit(f'#define _GLOBAL_COMPANY "{company}"'))
    tree.edit("const.h", "settings key", r'#define _GLOBAL_KEY "[^"]*"', lit(f'#define _GLOBAL_KEY "{key}"'))
    tree.edit("const.h", "version", r'#define _GLOBAL_VERSION "[^"]*"', lit(f'#define _GLOBAL_VERSION "{v4}"'))
    tree.edit("const.h", "version (numeric)", r'#define _GLOBAL_VERSION_COMMA [0-9]+(?:,[0-9]+)+', lit(f'#define _GLOBAL_VERSION_COMMA {comma}'))

    # ---- define.h: visible name, links, codecs, switches ----------------------------------
    tree.edit("define.h", "visible name", r'(#define _GLOBAL_NAME_VISIBLE )"[^"]*"', g1(f'"{name}"'))
    for macro, url in (("_GLOBAL_MENU_WEBSITE", website), ("_GLOBAL_MENU_DOWNLOADS", website),
                       ("_GLOBAL_MENU_ISSUES", support), ("_GLOBAL_MENU_HELP", support),
                       ("_GLOBAL_HELP_WEBSITE", support), ("_GLOBAL_URL_CHECK_VERSION", website)):
        tree.edit("define.h", f"{macro} link", rf'(#define {macro} )"[^"]*"', g1(f'"{url}"'))
    tree.edit("define.h", "default codecs", r'(#define _GLOBAL_CODECS_ENABLED )"[^"]*"', g1(f'"{codecs}"'))
    switches = (
        "\n// ---- Brand switches (written by tools/brand.py) ----\n"
        "#define _GLOBAL_CRASH_REPORTS 0\n"
        f"#define _GLOBAL_UPDATE_ENABLED {1 if upd else 0}\n"
    )
    tree.set_block("define.h", "brand switches", "// ---- Brand switches (written by tools/brand.py) ----", switches)

    # ---- res/main.rc2: copyright in the .exe properties (MicroSIP credit kept, as GPL requires) ----
    year = "2026"
    copyright_line = (f"Copyright (c) {year} {company}. Based on MicroSIP, "
                      "Copyright (c) 2011-2025 MicroSIP (www.microsip.org). GPL v2.")
    tree.edit("res/main.rc2", "copyright line", r'(VALUE "LegalCopyright", )"[^"]*"', g1(f'"{c_str(copyright_line)}"'))

    # ---- mainDlg.cpp: update checks ----------------------------------------------------------
    tree.edit("mainDlg.cpp", "update switch",
              r'(void CmainDlg::CheckUpdates\(\)\s*\{)(?!\s*#if !_GLOBAL_UPDATE_ENABLED)',
              r'\1\n#if !_GLOBAL_UPDATE_ENABLED\n    return;\n#endif', done_marker="#if !_GLOBAL_UPDATE_ENABLED")
    if upd:
        host = urlparse(upd).hostname or ""
        tree.edit("mainDlg.cpp", "update URL", r'url = _T\("http://update\.microsip\.org/softphone-update\.txt"\);',
                  lit(f'url = _T("{c_str(upd)}");'), done_marker=f'url = _T("{c_str(upd)}");')
        tree.edit("mainDlg.cpp", "update download host",
                  r'strServer\.Right\(13\) == _T\("\.microsip\.org"\)',
                  lit(f'strServer.CompareNoCase(_T("{c_str(host)}")) == 0'),
                  done_marker=f'strServer.CompareNoCase(_T("{c_str(host)}")) == 0')
    else:
        tree.edit("settings.cpp", "updates default = never",
                  r'(_T\("updatesInterval"\), )NULL', r'\1_T("never")', done_marker='_T("updatesInterval"), _T("never")')

    # ---- microsip.cpp: no crash reports to microsip.org --------------------------------------
    tree.edit("microsip.cpp", "crash reports off",
              r'if \(!blockDump\) \{(\s*CInternetSession session;)',
              r'if (!blockDump && _GLOBAL_CRASH_REPORTS) {\1', done_marker="if (!blockDump && _GLOBAL_CRASH_REPORTS)")

    # ---- jumplist.h: taskbar identity (not grouped with real MicroSIP) ------------------------
    tree.edit("jumplist.h", "taskbar id", r'return L"AvrumFeldman\.MicroSIPCustom";',
              lit(f'return L"{c_str(b["app_id"])}";'), done_marker=f'return L"{c_str(b["app_id"])}";')

    # ---- custom.vcxproj: output file name ----------------------------------------------------
    tree.edit("custom.vcxproj", "exe name", r'<TargetName>[^<]*</TargetName>', lit(f'<TargetName>{b["exe_name"]}</TargetName>'))

    # ---- icons ----------------------------------------------------------------------------------
    icons = KIT / "brand" / "icons"
    for src, dst in (("app.ico", "res/microsip.ico"), ("app_inactive.ico", "res/tray_inactive.ico")):
        s = icons / src
        if not s.is_file():
            fail(f"{s} missing — run: python tools/make_icon.py")
        d = tree.root / dst
        if not d.parent.is_dir():
            fail(f"{dst}: folder not found in the source tree")
        if not d.is_file() or d.read_bytes() != s.read_bytes():
            shutil.copyfile(s, d)
            tree.changed.append(f"{dst}: brand icon")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="path to the microsip-custom source tree")
    ap.add_argument("--brand", type=Path, default=KIT / "brand" / "brand.json")
    args = ap.parse_args()

    if not (args.source / "custom.vcxproj").is_file():
        fail(f"{args.source} does not look like the microsip-custom source (custom.vcxproj missing)")
    b = load_brand(args.brand)
    tree = Tree(args.source.resolve())
    apply(tree, b)
    (tree.root / "BRANDED.txt").write_text(
        f"Branded as {b['name']} {b['version']} by tools/brand.py\n", encoding="utf-8")
    if tree.changed:
        print(f"Branded {b['name']} {b['version']}:")
        for c in tree.changed:
            print("  -", c)
    else:
        print(f"Already branded as {b['name']} {b['version']} — nothing to change.")


if __name__ == "__main__":
    main()
