# Changelog - waqt-timer

All notable changes to this project are tracked here.

## [1.5.2] - 2026-09-18
### Fixed
- Menu now labels both forbidden gaps: `Forbidden (Sunrise)` 05:46-06:01 and `Forbidden (Noon)` 11:48-11:53, each highlighted only in its own window.
- Fixed double highlight during `Asr (Makruh)` (both Asr rows lit up); now exactly one current and one next marker in all 10 day states.

## [1.5.1] - 2026-09-18
### Fixed
- Noon forbidden corrected 10 min to 5 min (window now 11:48-11:53 for Gazipur, matching mobile apps 11:47-11:52 within Dhuhr rounding). Triple-verified: Hanafi-Deobandi ihtiyat is 5 min (Mangera 3-5, Darul Ifta Birmingham 5), Islamic Foundation Bangladesh uses 5-6 min, and true solar noon Gazipur Sep 18 computes to 11:51:30 (Dhuhr 11:52/53 correct).
- Sunset row hidden from the menu list (Maghrib row already carries the time).
- Confirmed by test that switching method/school refetches every dependent time (cache is keyed by method+school; Dhuhr/Sunrise stay fixed across methods because they are astronomical, Asr moves with school: Hanafi 16:17 vs Shafi 15:20).

## [1.5.0] - 2026-09-18
### Added
- All 23 Aladhan calculation methods selectable (Karachi, MWL, Egypt, Makkah, ISNA, Tehran, Gulf, Kuwait, Qatar, Singapore, France, Turkey, Russia, Moonsighting, Dubai, Malaysia, Tunisia, Algeria, Indonesia, Morocco, Lisbon, Jordan, Shia) via new Calculation section in settings (Method + Asr school dropdowns) and the `--method` flag.
- Default stays Karachi 18/18 + Hanafi, the Islamic Foundation Bangladesh standard (verified via Niyat 2026 guides and LivePrayerTimes: IF Bangladesh and local mosques use 18/18 Hanafi).
- Offline fallback maps methods without angle sets to Karachi angles with a stderr note until network returns.

## [1.4.1] - 2026-09-18
### Added
- Sunset listed: new `Sunset` row (sun disappears = Maghrib begins) plus live `Asr (Makruh)` yellowing state and row (~15 min before Maghrib, no nafl; Asr fard still due till sunset per Bukhari/Muslim).
- `Isha (Makruh)` info row (delay past shar'i midnight ~11:14 PM is makruh; Isha fard valid till dawn).
- `Tahajjud (Nafl)` info row (Isha->Fajr is NOT forbidden; best from last third, e.g. 12:59 AM).
- `--test derived` now also prints `makruh_sunset`, `sunset`, `isha_makruh_after`, `tahajjud_best_from`.

## [1.4.0] - 2026-09-18
### Fixed
- Fajr no longer shows stale countdown till Dhuhr. Fajr ends at Sunrise; after that the app shows Forbidden (15 min sunrise gap) then Ishraq (Nafl) till zawal.
- Ishraq/Duha marked as Nafl: `Ishraq (Nafl)` from Sunrise+15 min till 10 min before Dhuhr. Majority view (one Nafl prayer) per Fiqh-us-Sunnah.
### Added
- Friday Dhuhr renamed to Jumuah (same time as Dhuhr, majority view).
- Noon forbidden window: `Forbidden 11:43-11:53 -X | Jumuah/Dhuhr HH:MM` for 10 min before Dhuhr (covers 7-10 min zawal per Tahtawi/SeekersGuidance). Top bar shows from-to instead of just next waqt.
- Compact top-bar label: minus sign before countdown (`Ishraq -2:02:03 | ...`), no `(Nafl)` in top bar (kept in menu + JSON), forbidden range shown when Forbidden is current or next.
- `--test` now prints `derived: {ishraq, forbidden_noon, dhuhr_label}`.

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
