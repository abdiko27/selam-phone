# Build guide

> **Status:** the branding script has been tested against the real MicroSIP source, and the packaging has been tested with stand-in files. The Windows compile and installer have **not** been run yet. Your first build is that test. If a step fails, send me the red error text.

## Step 0: set your brand (5 minutes)

1. Open `brand/brand.json` in Notepad and change `name`, `exe_name`, `company`, `app_id`, `website`, `support_phone` and `defaults.server`.
2. Optional: put your logo at `brand/logo.png` (square, 512 px or larger).
3. Save.

---

## Route A: GitHub Actions (recommended, no Visual Studio needed)

GitHub builds the app on its own Windows machines. This is free for public repositories, and the GPL needs the source to be public anyway.

1. Create a free account at github.com, if you don't have one.
2. Click **New repository** and name it, for example `selam-phone`. Choose **Public**, then **Create**.
3. On the new repo page, click **uploading an existing file**. Drag in **everything inside** the `selam-phone-kit` folder, including the `.github` folder.
   - Windows hides folders that start with a dot. In Explorer, choose View → Show → Hidden items.
   - If the drag-and-drop skips `.github`, create the file on GitHub instead: **Add file → Create new file**, name it `.github/workflows/build.yml`, and paste in the contents.
4. Click **Commit changes**.
5. Open the **Actions** tab, choose **Build branded phone app**, then **Run workflow**.
6. Wait. The first run takes about 45–90 minutes because it compiles PJSIP and OpenSSL. Later runs are faster thanks to the cache.
7. When the run shows a green tick, open it and scroll to **Artifacts**. Download **phone-app**, which contains the setup.exe, the portable zip, the source zip and the checksums.

**To publish a release:** on the repo page, create a tag such as `v1.0.0` (Releases → Draft a new release → choose a tag → Publish). The workflow builds it and attaches the installer *and* the source zip to the release, which covers your GPL obligation.

---

## Route B: build on your own PC

You need about 15 GB of free disk space and a good connection for the first build.

1. **Visual Studio 2022 Community** (free). In the installer, tick **Desktop development with C++**. Under *Individual components*, add:
   - **C++ MFC for latest v143 build tools (x86 & x64)**
   - **C++ ATL for latest v143 build tools (x86 & x64)**
   - a **Windows 11 SDK** (any recent version)
2. **PowerShell 7:** `winget install Microsoft.PowerShell`
3. **Git:** `winget install Git.Git`
4. **Python 3:** `winget install Python.Python.3.12` (tick "Add to PATH" if you are asked)
5. Optional, for the installer: **Inno Setup 6:** `winget install JRSoftware.InnoSetup`
6. Open **PowerShell 7** in the kit folder and run:

   ```powershell
   pwsh -File build.ps1
   ```

7. The results are in the `dist` folder.

**After you change `brand.json`, run `pwsh -File build.ps1 -Clean`.** This takes a fresh copy of the source before re-branding. The libraries in `microsip-build` are kept, so the rebuild is quick.

---

## Step 1: test it against the lab PBX

1. Run `SelamPhone-1.0.0-setup.exe` on your PC.
2. On the **Phone account** page, enter extension `1005`, its secret from FreePBX (Applications → Extensions → 1005 → Secret) and a name.
3. Finish. The app opens and the tray icon should turn from grey to coloured within a few seconds.
4. Test calls:
   - Call 1006 (your mobile).
   - Dial `*97` for voicemail.
   - Dial `800` for the IVR.
   - Transfer a call.
5. Check what the customer sees:
   - The title bar, the tray tooltip and Help → About show your name.
   - Settings → Apps in Windows lists it with your company name.
6. If it doesn't register, check the FreePBX firewall first (`fwconsole firewall trust 192.168.26.0/24`), then the secret.

## Installing at a customer site

| Situation | How |
|---|---|
| A few PCs | Run setup.exe on each one and type the extension |
| Many PCs | Use a silent install from a script or USB stick: `SelamPhone-1.0.0-setup.exe /SILENT /EXT=1005 /SIPPASS=secret /NAME="Front Desk"` |
| A different PBX address per customer | Change `defaults.server` and `version` (for example `1.0.0` → `1.0.1`) and rebuild. Or keep one build that uses a DNS name like `pbx.office.local`, which you add to each customer's router. |
| Upgrade | Run the newer setup.exe. Settings, contacts and history are kept, and the account page is skipped. |
| Uninstall | Windows Settings → Apps. It asks whether to also delete settings. |

Settings live in `%APPDATA%\<name>\<exe>.ini`. The password is encrypted the first time the app starts.

## Where each brand item ends up (for reference)

| Item | Done by | Where |
|---|---|---|
| Name, company, version | `tools/brand.py` | `const.h`, `define.h`, `res/main.rc2` |
| Exe file name | `brand.py` | `custom.vcxproj` (TargetName) |
| Icons | `tools/make_icon.py` and `brand.py` | `res/microsip.ico`, `res/tray_inactive.ico` |
| Help and website links | `brand.py` | `define.h` |
| Update check off | `brand.py` | `mainDlg.cpp`, `settings.cpp` |
| Crash reports off | `brand.py` | `microsip.cpp` |
| Taskbar grouping ID | `brand.py` | `jumplist.h` |
| Default server and account | `package.py` and `installer/app.iss` | settings file written at install |

`brand.py` checks every change. If a future MicroSIP version moves the code, the script stops with a message naming the file. It never builds a half-branded app.

## Common errors

| Message | Fix |
|---|---|
| `Install Visual Studio 2022 C++ tools, MFC/ATL…` | Add the MFC and ATL components (Route B step 1) |
| `brand.py: … could not apply …` | The upstream source changed. Keep the commit in `upstream.json`, or send me the message. |
| `exe_name: letters, digits…` | Remove spaces from `exe_name` |
| `checksum mismatch` | The sound download was corrupted or blocked. Delete `microsip-build\downloads` and run again. |
| `Inno Setup not found` | Install Inno Setup 6, or use the portable zip |
| Windows SmartScreen warns "unknown publisher" | This is normal for new apps. Later, buy a code-signing certificate (about US$200–400 a year) and sign the setup.exe. |
