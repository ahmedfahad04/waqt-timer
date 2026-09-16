# Waqt Timer - Complete .deb Build Guide (v1.3.0)

## 1. The story: why a PC timer is tricky

Checking how much prayer time is left sounds simple. On a phone you open an app and it tells you. On a Linux PC the problem is different: there is no single place that shows live info all day, prayer times shift every day and every few kilometers, and most web timers go stale the moment you travel from Shahbag to Sylhet.

So we needed a clever little resident for the PC: something that lives in the top bar, knows where the machine actually is, fetches the correct times for those exact coordinates every day, counts down each second, and survives reboots. That is what waqt-timer is. A Python app that sits in the GNOME top bar and tray, auto locates over the internet or by city name, pulls Karachi 18/18 Hanafi times for Bangladesh with district precision, and shows `Maghrib (1:06:47 left) | Isha 19:13`. Packaged once as a `.deb`, it installs on any Debian based distro with one command.

## 2. Core components of ANY Linux desktop solution

Every well behaved Linux GUI tool, prayer timer or not, is made of the same core parts. Here is the generic set, how waqt-timer uses each, and what extra parts this app adds.

| # | Core component (any app) | What it is | How waqt-timer uses it |
|---|---|---|---|
| 1 | Executable code | The program itself | `opt/waqt-timer/waqt_timer.py` + `praytimes.py` (Python, stdlib + GTK only) |
| 2 | PATH launcher | A short shim so the shell finds it | `usr/bin/waqt-timer`: `exec /opt/waqt-timer/waqt_timer.py "$@"` |
| 3 | Desktop entry | Makes the app appear in the app grid | `usr/share/applications/waqt-timer.desktop` with `Exec` and `Icon` |
| 4 | Icon | Hicolor themed artwork | `usr/share/icons/hicolor/scalable/apps/waqt-timer.svg` |
| 5 | Autostart | Launch on login | Copy of the desktop file in `etc/xdg/autostart/` |
| 6 | Config and cache | Per user state, never in the package | `~/.config/waqt-timer/config.json`, `~/.cache/waqt-timer/timings.json` |
| 7 | Package metadata | Name, version, deps | `DEBIAN/control` with `Depends` on `python3, python3-gi, gir1.2-gtk-3.0, appindicator` |
| 8 | Install hooks | One time setup after copy | `DEBIAN/postinst`: refresh desktop DB and icon cache |

Additional components specific to this app:

- Location providers: IP lookup (`ip-api.com`) for auto mode, Nominatim first then Open-Meteo for thana level city search (Shahbag, Sylhet, Rajshahi resolve to distinct coords).
- Time providers: Aladhan API with `method=Karachi, school=Hanafi, midnightMode=Standard, latitudeAdjustmentMethod=AngleBased`, plus a bundled PrayTimes offline fallback.
- Keyed cache: entries stored as `date|lat|lon|method|school` so a location switch can never reuse old times. Cleared on every location change, with `--refresh` for manual refetch.
- Docs in the package: `usr/share/doc/waqt-timer/changelog`, `BUILD-GUIDE.md`, `README.md`.

## 3. Folder structure in `~/waqt-timer/`

```
waqt-timer/
  pkg/                                    # staging root, becomes /
    DEBIAN/control                        # metadata
    DEBIAN/postinst                       # post install hook, chmod 755
    opt/waqt-timer/waqt_timer.py          # main app
    opt/waqt-timer/praytimes.py           # offline fallback
    usr/bin/waqt-timer                    # launcher shim
    usr/share/applications/waqt-timer.desktop
    etc/xdg/autostart/waqt-timer.desktop  # autostart copy
    usr/share/icons/hicolor/scalable/apps/waqt-timer.svg
    usr/share/doc/waqt-timer/changelog    # copy of CHANGELOG.md
    usr/share/doc/waqt-timer/README.md
    usr/share/doc/waqt-timer/BUILD-GUIDE.md
  waqt-timer_1.3.0_all.deb                # built artifact
  BUILD-GUIDE.md                          # this file (source)
  README.md                               # open source front page (source)
  CHANGELOG.md                            # v1.0.0 to v1.3.0 history
```

Create the staging dirs with:

```bash
mkdir -p pkg/DEBIAN pkg/opt/waqt-timer pkg/usr/bin \
  pkg/usr/share/applications pkg/etc/xdg/autostart \
  pkg/usr/share/icons/hicolor/scalable/apps \
  pkg/usr/share/doc/waqt-timer
```

## 4. Build from zero

1. Place code, desktop files, icon, control and postinst into the paths above.
2. Set bits:
```bash
chmod +x pkg/opt/waqt-timer/waqt_timer.py pkg/usr/bin/waqt-timer
chmod 755 pkg/DEBIAN/postinst
```
3. Test logic before packing (about 30 sec):
```bash
python3 -m py_compile pkg/opt/waqt-timer/*.py
python3 pkg/opt/waqt-timer/waqt_timer.py --test --refresh
python3 pkg/opt/waqt-timer/waqt_timer.py --test --city "Shahbag, Dhaka" --refresh
python3 pkg/opt/waqt-timer/waqt_timer.py --test --city "Sylhet" --refresh
python3 pkg/opt/waqt-timer/waqt_timer.py --test --city "Rajshahi" --refresh
```
4. Pack (about 10 sec):
```bash
rm -rf pkg/opt/waqt-timer/__pycache__
dpkg-deb --build pkg waqt-timer_1.3.0_all.deb
dpkg-deb -c waqt-timer_1.3.0_all.deb
dpkg-deb -f waqt-timer_1.3.0_all.deb Package Version Maintainer Depends
```
5. Install (about 1 min):
```bash
cp waqt-timer_1.3.0_all.deb /tmp/
sudo apt install /tmp/waqt-timer_1.3.0_all.deb
waqt-timer --test
waqt-timer &
```
6. Bump version later by editing `DEBIAN/control` (`1.3.0` to `1.3.1`), adding a `CHANGELOG.md` entry, and rebuilding with the new filename.

## 5. Probable issues, fixes, and what we actually hit here

General issues anyone packing a Linux tool will meet, with the fix that works:

1. `E: Unable to locate package x.deb` after `apt install x.deb`. Cause: apt reads a bare name as a repo package. Fix: use a path: `sudo apt install ./x.deb` or an absolute path.
2. `N: Download is performed unsandboxed ... _apt ... Permission denied`. Cause: apt drops to the `_apt` user to read the file, but home dirs are not readable by it. Fix: copy the deb to `/tmp/` (mode 1777) and install from there. Warning only, install still succeeds.
3. Tray icon missing on GNOME. Cause: stock GNOME hides AppIndicators. Fix: depend on `gir1.2-appindicator3-0.1 | gir1.2-ayatanaappindicator3-0.1` and suggest the AppIndicator extension. The app also has a plain window fallback.
4. `postinst: permission denied`. Cause: hook not executable. Fix: `chmod 755 pkg/DEBIAN/postinst`.
5. `__pycache__` shipped in the deb. Cause: test runs create it. Fix: `rm -rf pkg/opt/waqt-timer/__pycache__` before every build.
6. Icon or app grid entry missing. Cause: caches not refreshed. Fix: `update-desktop-database` and `gtk-update-icon-cache` in `postinst`.
7. Times look right but never change after moving cities. Cause: single slot cache keyed without coords. Fix: key by `date|lat|lon|method|school`, clear on location change, add `--refresh`.
8. Times off by 45 to 60 min at Asr or a few min at Isha in South Asia. Cause: wrong fiqh defaults (MWL + Shafi instead of Karachi + Hanafi). Fix: default to Karachi 18/18 with `school=Hanafi`, expose `--school`.
9. City search too coarse (whole city, no thana). Cause: city DB returns center only. Fix: Nominatim first for suburb level detail, Open-Meteo fallback.
10. API blocks headless tests. Cause: missing User-Agent or no timeout. Fix: set `User-Agent: waqt-timer/x.y` and 6 to 10 sec timeouts, always keep offline fallback.

What we actually faced in this build, in order:

- v1.0.0 installed but `apt install -f waqt-timer_1.0.0_all.deb` failed with `Unable to locate package`. Fixed with `./` prefix.
- Then the `_apt Permission denied` notice appeared. Confirmed `dpkg -l` showed `ii` (installed), documented as warning only, moved installs to `/tmp/`.
- v1.1.0 label used a minus elapsed format. Reworked to `Cur (H:MM:SS left) | Next HH:MM` with 12h/24h toggle.
- v1.2.0 times stuck after city switch. Root cause was the single slot cache plus a midnight check that could never fire. Rebuilt cache as a keyed dict with force refresh.
- v1.3.0 precision review (web research) showed MWL/Shafi mismatches Bangladesh mosques. Switched defaults to Karachi/Hanafi with full Aladhan params and district geocoding. Verified Shahbag 04:29/18:01, Sylhet 04:23/17:56, Rajshahi 04:34/18:07.

## 6. Reuse checklist for your next tool

1. Put code in `/opt/myapp/`, add a 2 line `/usr/bin/myapp` shim.
2. Write `DEBIAN/control` with exact `Depends`, check with `dpkg-deb -f`.
3. Add desktop file, icon, autostart copy, executable `postinst`.
4. Keep config in `~/.config/myapp`, cache in `~/.cache/myapp`, never in the package.
5. Add `--test` or `--no-gui` headless mode and run it before every build.
6. Delete `__pycache__`, build with `dpkg-deb --build`, inspect with `dpkg-deb -c`.
7. Install from `/tmp/` to avoid the `_apt` warning, verify with `dpkg -l myapp`.
8. Ship `changelog`, `README.md` and this guide under `/usr/share/doc/myapp/`.
