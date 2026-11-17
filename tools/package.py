#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Package a built, branded phone app.

    python tools/package.py <source-tree> --build-root <microsip-build> [--iscc "C:\\...\\ISCC.exe"]

Produces in <kit>/dist/:
  <Exe>-<version>-portable.zip   unzip-and-run copy, server already filled in
  <Exe>-<version>-setup.exe      Windows installer (when Inno Setup is available)
  <Exe>-<version>-source.zip     the exact branded source (you must publish this: GPL v2)
  <Exe>-<version>-SHA256SUMS.txt
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import uuid
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
HELPER = "MicroSIPAudioGuard.exe"  # name is fixed in the app; keep it next to the main exe


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_verified(url: str, sha: str, dest: Path) -> Path:
    if not dest.is_file() or sha256(dest) != sha.lower():
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, dest)
    if sha256(dest) != sha.lower():
        fail(f"checksum mismatch for {dest}")
    return dest


def default_ini(b: dict) -> str:
    d = b["defaults"]
    lines = [
        "[Settings]",
        "accountId=1",
        "enableLocalAccount=0",
        "singleMode=1",
    ]
    if not b.get("update_url"):
        lines.append("updatesInterval=never")
    lines += [
        "",
        "[Account1]",
        f"label={d.get('label', 'Office')}",
        f"server={d['server']}",
        f"domain={d['server']}",
        f"transport={d.get('transport', 'udp')}",
        f"voicemailNumber={d.get('voicemail', '*97')}",
        "username=",
        "authID=",
        "password=",
        "displayName=",
        "",
    ]
    return "\r\n".join(lines)


def zip_dir(src: Path, dest: Path, prefix: str):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                z.write(f, f"{prefix}/{f.relative_to(src).as_posix()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path, help="branded and built source tree")
    ap.add_argument("--build-root", type=Path, required=True, help="folder holding pjproject and vcpkg")
    ap.add_argument("--brand", type=Path, default=KIT / "brand" / "brand.json")
    ap.add_argument("--iscc", default=os.environ.get("ISCC", ""), help="path to Inno Setup ISCC.exe")
    ap.add_argument("--no-installer", action="store_true")
    args = ap.parse_args()

    src = args.source.resolve()
    b = json.loads(args.brand.read_text(encoding="utf-8"))
    exe = b["exe_name"]
    ver = b["version"]
    if not (src / "BRANDED.txt").is_file():
        fail("this tree has not been branded: run tools/brand.py first")
    out = src / "out"
    for f in (f"{exe}.exe", HELPER):
        if not (out / f).is_file():
            fail(f"{out / f} not found: build first")

    dist = KIT / "dist"
    stage = KIT / "build" / "stage"
    app = stage / "app"
    shutil.rmtree(stage, ignore_errors=True)
    (app / "licenses").mkdir(parents=True)
    dist.mkdir(exist_ok=True)

    # 1. program files
    shutil.copy2(out / f"{exe}.exe", app)
    shutil.copy2(out / HELPER, app)

    # 2. ringtones and sounds (official MicroSIP WAV files, verified by checksum)
    pins = json.loads((src / "config" / "dependencies.json").read_text(encoding="utf-8"))
    snd = pins["portableSounds"]
    archive = fetch_verified(snd["url"], snd["sha256"], args.build_root / "downloads" / snd["filename"])
    with zipfile.ZipFile(archive) as z:
        wavs = [n for n in z.namelist() if n.lower().endswith(".wav")]
        if not wavs:
            fail("no WAV files in the sound archive")
        for n in wavs:
            (app / Path(n).name).write_bytes(z.read(n))

    # 3. licences and notices (GPL v2 requires these to travel with the program)
    for f in ("COPYING", "LICENSE", "THIRD-PARTY-NOTICES.md", "UPSTREAM-SOURCE.md"):
        if (src / f).is_file():
            shutil.copy2(src / f, app / "licenses" / f)
    if (src / "licenses").is_dir():
        shutil.copytree(src / "licenses", app / "licenses", dirs_exist_ok=True)
    pj = args.build_root / "pjproject"
    if (pj / "COPYING").is_file():
        shutil.copy2(pj / "COPYING", app / "licenses" / "PJSIP.txt")
    if (pj / "third_party").is_dir():
        for n in (pj / "third_party").rglob("*"):
            name = n.name.upper()
            if n.is_file() and (name.startswith(("COPYING", "LICENSE", "COPYRIGHT", "PATENTS")) or n.name == "PJSIP_NOTES") \
                    and "g7221" not in n.parts:
                d = app / "licenses" / "pjsip" / n.relative_to(pj)
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(n, d)
    vc = args.build_root / "vcpkg" / "installed" / "x86-windows-static" / "share"
    for dep in ("openssl", "opus", "sqlite3", "SQLiteCpp"):
        c = vc / dep / "copyright"
        if c.is_file():
            shutil.copy2(c, app / "licenses" / f"{dep}.txt")
    (app / "SOURCE.txt").write_text(
        f"{b['name']} {ver} is free software under the GNU General Public License v2.\r\n"
        f"It is based on MicroSIP (www.microsip.org) and the microsip-custom fork.\r\n"
        f"The complete source code of this version is available at:\r\n"
        f"  {b.get('source_url') or b['website']}\r\n"
        f"or on request from {b['company']} ({b.get('support_phone', b['support_url'])}).\r\n",
        encoding="utf-8")

    # 4. portable copy: settings file beside the exe makes the app run in portable mode
    portable = stage / "portable"
    shutil.copytree(app, portable)
    (portable / f"{exe}.ini").write_bytes(b"\xff\xfe" + default_ini(b).encode("utf-16-le"))
    pzip = dist / f"{exe}-{ver}-portable.zip"
    zip_dir(portable, pzip, f"{exe}-{ver}")

    # 5. branded source (GPL: publish this exact file wherever you publish the program)
    szip = dist / f"{exe}-{ver}-source.zip"
    with zipfile.ZipFile(szip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src.rglob("*")):
            rel = f.relative_to(src)
            if f.is_file() and rel.parts[0] not in (".git", "out", "build", "dist", ".vs"):
                z.write(f, f"{exe}-{ver}-source/{rel.as_posix()}")
        for f in sorted((KIT).rglob("*")):
            rel = f.relative_to(KIT)
            if f.is_file() and "__pycache__" not in rel.parts and (rel.parts[0] in ("brand", "tools", "installer", ".github")
                                or (f.parent == KIT and f.suffix in (".md", ".ps1", ".json") or f.name == ".gitignore")):
                z.write(f, f"{exe}-{ver}-source/brand-kit/{rel.as_posix()}")

    # 6. installer
    setup = None
    if not args.no_installer:
        iscc = args.iscc or shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if Path(iscc).is_file() or shutil.which(iscc):
            d = b["defaults"]
            app_guid = "{" + str(uuid.uuid5(uuid.NAMESPACE_DNS, b["app_id"].lower())).upper() + "}"
            defs = {
                "AppName": b["name"], "ExeName": exe, "AppVersion": ver, "Company": b["company"],
                "AppGuid": "{" + app_guid, "Website": b["website"], "SupportUrl": b["support_url"],
                "Server": d["server"], "Transport": d.get("transport", "udp"),
                "Voicemail": d.get("voicemail", "*97"), "Label": d.get("label", "Office"),
                "UpdatesNever": "0" if b.get("update_url") else "1",
                "SourceDir": str(app), "OutputDir": str(dist),
                "IconFile": str(KIT / "brand" / "icons" / "app.ico"),
                "LicenseFile": str(src / "COPYING") if (src / "COPYING").is_file() else str(src / "LICENSE"),
            }
            cmd = [iscc, "/Qp"] + [f"/D{k}={v}" for k, v in defs.items()] + [str(KIT / "installer" / "app.iss")]
            print("Building installer...")
            r = subprocess.run(cmd)
            if r.returncode:
                fail("Inno Setup failed")
            setup = dist / f"{exe}-{ver}-setup.exe"
        else:
            print("Inno Setup not found: skipping the installer (portable zip is ready). "
                  "Install Inno Setup 6 or pass --iscc.")

    files = [p for p in (pzip, szip, setup) if p and p.is_file()]
    sums = dist / f"{exe}-{ver}-SHA256SUMS.txt"
    sums.write_text("".join(f"{sha256(p)}  {p.name}\n" for p in files), encoding="ascii")
    print("Done:")
    for p in files + [sums]:
        print("  ", p)


if __name__ == "__main__":
    main()
