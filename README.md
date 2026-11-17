# Selam Phone brand kit

Turns MicroSIP (the free Windows softphone) into **your own branded phone app** for the FreePBX systems you sell.
"Selam Phone" is a placeholder. Change it in one file and rebuild.

## What the customer gets

- `SelamPhone-1.0.0-setup.exe`: a normal Windows installer with your name, icon and company. It needs no admin rights.
  - It asks for the extension number, password and display name.
  - The server address is already filled in, so staff only type their extension.
  - Start menu and desktop shortcuts. Optionally starts with Windows, minimised to the tray.
- `SelamPhone-1.0.0-portable.zip`: the same app as unzip-and-run. Useful for testing.
- Inside the app: your name in the window title, tray, taskbar, About box and Windows "Apps" list. Your icon everywhere. Your website on the Help menu.
- **No calls home to microsip.org:** update checks and crash reports are switched off, unless you set your own update URL.

The basic features are all MicroSIP's: calls, hold, transfer, conference, call recording, voicemail button, contacts, call history, DND, auto-answer, G.722 HD audio, opus, BLF, TLS/SRTP.

## The 5 files you change

| File | What it is |
|---|---|
| `brand/brand.json` | Name, exe name, company, version, website, support phone, colours, **default server** |
| `brand/logo.png` | Optional. A square PNG, 512×512 or larger, transparent background. Without it, an icon is drawn from your initials. |
| `upstream.json` | The MicroSIP source version used. Leave it unless you are upgrading. |
| `installer/app.iss` | The installer. You rarely need to touch it. |
| `.github/workflows/build.yml` | The cloud build. You rarely need to touch it. |

`brand.json` fields:

| Field | Example | Notes |
|---|---|---|
| `name` | `Selam Phone` | Shown everywhere. It is also the settings folder name (`%APPDATA%\Selam Phone`). |
| `exe_name` | `SelamPhone` | Letters, digits, `-` or `_` only |
| `company` | `Selam Communications` | Copyright line, installer publisher |
| `app_id` | `SelamCommunications.SelamPhone` | Never change it after you ship, because Windows uses it to recognise upgrades |
| `version` | `1.0.0` | Raise it for every release |
| `website`, `support_url`, `support_phone` | | Help menu, installer, source notice |
| `update_url` | `""` | Leave empty to turn update checks off |
| `colour`, `accent` | `#0b6e4f` | Used only for the initials icon |
| `defaults.server` | `192.168.26.10` | The customer's PBX address. Build one installer per customer, or use a DNS name like `pbx.local`. |
| `defaults.transport`, `voicemail`, `label`, `codecs` | `udp`, `*97`, `Office` | |

## How to build

See **BUILD-GUIDE.md**. There are two routes:

1. **GitHub Actions (recommended):** upload this folder to GitHub, click *Run workflow*, and download the installer about 30–60 minutes later. You don't need Visual Studio on your PC.
2. **On your own Windows PC:** install Visual Studio 2022 and run `pwsh -File build.ps1`.

## The legal part (GPL v2): read this once

MicroSIP is free software under GPL v2. You **may** rebrand it, sell it and bundle it with your PBX service. In return:

1. **Ship the source with every release.** The build makes `SelamPhone-x.y.z-source.zip`. Put it next to the installer, for example on the GitHub release or your website, or give it to anyone who asks. A public GitHub repo for this kit is the easiest way to do this.
2. **Keep the licence files.** The installer includes them in the `licenses` folder, and the installer's licence page shows GPL v2. Don't remove them.
3. **Keep the "Based on MicroSIP" line.** It is in the About/copyright text. You can't claim the whole program as your own work, but your name, logo and company appear everywhere.
4. You can't make the app closed-source or add a licence key that stops copying.

You make money from the **PBX installation, support, phones and the portal**, not from the softphone itself. This is the same model the Kenyan and other African Asterisk resellers use.

The portal (v1.1) is your own code. It doesn't contain MicroSIP code, so the GPL does not apply to it.

## Limits to know

- Windows only (Windows 10 and 11). For mobile, use Linphone, Zoiper or Groundwire for now.
- The menus are in English. MicroSIP supports translation files, so an Amharic translation can be a later step.
- Video calls are off in this build (voice only).
