<div align="center">

<img src="pkg/usr/share/icons/hicolor/scalable/apps/waqt-timer.svg" width="96" alt="Waqt Timer icon" />

# Waqt Timer

**Prayer countdown in your Linux top bar. Auto located, district precise, always on time.**

[![version](https://img.shields.io/badge/version-1.3.0-green)](CHANGELOG.md)
[![platform](https://img.shields.io/badge/platform-Ubuntu%2022.04%2B-blue)](https://ubuntu.com)
[![desktop](https://img.shields.io/badge/desktop-GNOME%20%7C%20KDE%20%7C%20XFCE%20%7C%20MATE-lightgrey)](#)
[![python](https://img.shields.io/badge/python-3.8%2B-yellow)](https://www.python.org)
[![method](https://img.shields.io/badge/method-Karachi%2018%2F18%20Hanafi-orange)](#configuration)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

`Maghrib (1:06:47 left) | Isha 19:13`

</div>

## Why this exists

Phone apps know where you are. Linux panel clocks do not. Waqt Timer closes that gap: it lives in the top bar, finds your location over the internet or by city name, fetches the correct times for those exact coordinates, and counts down every second. Built for Bangladesh first (Karachi 18/18, Hanafi Asr), usable anywhere by switching method and school.

## Features

- Top bar countdown: current waqt with time left plus next waqt start.
- Auto location over internet, or district search (Shahbag, Sylhet, Rajshahi resolve separately).
- 12h / 24h toggle, Hanafi / Shafi Asr, MWL / Karachi / ISNA / Egypt methods.
- Offline fallback when the API is down.
- Autostart on login, one codebase for GNOME, KDE, XFCE and MATE.

## Install

### Option A: git clone and run from source (recommended)

```bash
git clone https://github.com/<you>/waqt-timer.git
cd waqt-timer
sudo apt install python3 python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1
python3 pkg/opt/waqt-timer/waqt_timer.py --test
python3 pkg/opt/waqt-timer/waqt_timer.py &
```

Replace `<you>` with your GitHub username. To update later: `git pull` and rerun.

### Option B: install from GitHub Releases

Each release ships the `.deb` plus its changelog notes.

1. Open the Releases page of this repo and download `waqt-timer_1.3.0_all.deb` (pick the newest version).
2. Read the release notes there before installing, they mirror `CHANGELOG.md`.
3. Install:

```bash
cp ~/Downloads/waqt-timer_1.3.0_all.deb /tmp/
sudo apt install /tmp/waqt-timer_1.3.0_all.deb
waqt-timer --test
waqt-timer &
```

Or in one line with the GitHub CLI:

```bash
gh release download v1.3.0 -p '*.deb' -D /tmp && sudo apt install /tmp/waqt-timer_1.3.0_all.deb
```

### Option C: build your own .deb from the clone

```bash
git clone https://github.com/<you>/waqt-timer.git
cd waqt-timer
dpkg-deb --build pkg waqt-timer_1.3.0_all.deb
cp waqt-timer_1.3.0_all.deb /tmp/
sudo apt install /tmp/waqt-timer_1.3.0_all.deb
waqt-timer &
```

Use `/tmp/` to avoid the apt `_apt` sandbox warning for home dir files. See `BUILD-GUIDE.md` for the full packaging walkthrough.

## Usage

1. Launch `waqt-timer` from the app grid or terminal.
2. Open `Location and display` from the indicator menu.
3. Either keep `Track location automatically` checked, or type a city and press Enter, pick a result, press OK.
4. Switch `Time format` between `24h` and `12h` as needed.

Handy commands:

```bash
waqt-timer --test --refresh
waqt-timer --test --city "Shahbag, Dhaka" --refresh
waqt-timer --test --city "Sylhet" --refresh --format 12h
waqt-timer --test --school Hanafi --format 24h
```

## Configuration

| Setting     | Default         | Where                                |
| ----------- | --------------- | ------------------------------------ |
| Method      | Karachi (18/18) | Menu,`--method`, config            |
| School      | Hanafi          | Menu,`--school`                    |
| Format      | 24h             | Menu,`--format`                    |
| Config file | -               | `~/.config/waqt-timer/config.json` |
| Cache       | -               | `~/.cache/waqt-timer/timings.json` |

Times come from Aladhan with `school=Hanafi, midnightMode=Standard, latitudeAdjustmentMethod=AngleBased`. City search uses Nominatim with Open-Meteo fallback.

## Roadmap

- [ ] macOS menu bar port: same Aladhan plus Karachi and Hanafi core, native menu bar countdown via rumps.
- [ ] Adhan audio plus desktop notification at each waqt start, with quiet hours toggle.
- [ ] Qibla compass and monthly timetable export for the active location.

## Contributing

1. Fork and create a branch: `git checkout -b fix/my-fix`.
2. Test headless first: `python3 pkg/opt/waqt-timer/waqt_timer.py --test --refresh`.
3. Rebuild the deb: `dpkg-deb --build pkg waqt-timer_1.3.x_all.deb`.
4. Open a pull request with the city you tested and before/after times.

## Issues

Found wrong times for your area? Open an issue with:

1. Your city and thana (example: `Shahbag, Dhaka`).
2. Output of `waqt-timer --test --city "Your Area" --refresh`.
3. Your local mosque method if known (Karachi, MWL, other) and Hanafi or Shafi Asr.

## License

MIT. Contact: Istiaq Ahmed Fahad <ahmedfahad3596@gmail.com>. See `CHANGELOG.md` for release history and `BUILD-GUIDE.md` to build any Linux tool this way.
