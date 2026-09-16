# Changelog - waqt-timer

All notable changes to this project are tracked here.

## [1.3.1] - 2026-09-16
### Fixed
- Fixed `ModuleNotFoundError: No module named 'gi'` under conda. Launcher and shebang now pin `/usr/bin/python3` so the system PyGObject is always used, even with a conda env active.

## [1.3.0] - 2026-09-16
### Changed - precision release for Bangladesh
- Default calculation switched from MWL (18/17, Shafi) to Karachi (18/18, Hanafi) to match Islamic Foundation Bangladesh. Research via Aladhan docs and Niyat 2026 guides confirmed Karachi + Hanafi Asr is the local mosque standard.
- Aladhan calls now send full precision params: `school=1` (Hanafi), `midnightMode=0`, `latitudeAdjustmentMethod=3`, 4 decimal coords.
- Offline fallback now respects Hanafi Asr (factor 2) when school is Hanafi.
- Geocoding upgraded for district precision: Nominatim first (thana level like Shahbag, Zindabazar), Open-Meteo fallback. Each result keeps source and full display name.
- New `--school Hanafi|Shafi` flag. Old MWL configs auto migrate to Karachi on next run.
- Verified: Shahbag Dhaka Fajr 04:29 Maghrib 18:01, Sylhet Fajr 04:23 Maghrib 17:56, Rajshahi Fajr 04:34 Maghrib 18:07. Asr moved from 15:21 (Shafi) to 16:19 (Hanafi) in Dhaka, matching jamaat times.

## [1.2.0] - 2026-09-16
### Fixed
- Fixed stale times after location change. Cache is now keyed by `date|lat|lon|method|school`, cleared on every location switch, with `force=True` refresh and `--refresh` flag. Midnight rollover uses stored day instead of broken compare.
### Changed
- Maintainer set to Ahmed Fahad <ahmedfahad3596@gmail.com>.
- Location dialog rebuilt: Location frame + Display frame, city Entry with search icon on the right, Enter key and icon click both trigger search, results dropdown, status line with active coords. No em dashes.
- Guide cleaned of em dashes.

## [1.1.0] - 2026-09-16
### Changed
- Label changed to `Maghrib (1:06:47 left) | Isha 19:13`. No minus sign. Countdown sits in braces right of current waqt.
- Added 12h/24h toggle (`7:13 PM` vs `19:13`), selectable in UI and via `--format`.
- Replaced manual lat/lon inputs with city search (Open-Meteo) plus auto IP toggle.
- Version bumped to 1.1.0.

## [1.0.0] - 2026-09-16
### Added
- Initial release. Python GTK AppIndicator top bar app.
- Auto IP geolocation with manual override, MWL method, Aladhan API with PrayTimes offline fallback.
- Top bar label, dropdown menu with 6 times, autostart desktop entry, SVG icon.
- Debian packaging: `DEBIAN/control`, `postinst`, `/opt/waqt-timer`, `/usr/bin/waqt-timer`, desktop files, `dpkg-deb --build`.
- Install docs and `/tmp` workaround for `_apt` sandbox warning.
