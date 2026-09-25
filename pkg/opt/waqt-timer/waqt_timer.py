#!/usr/bin/python3
"""Waqt Timer v1.5.3 - top-bar prayer countdown. GNOME + Tray via AppIndicator."""
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, date, timedelta
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "waqt-timer"
CACHE_DIR = Path.home() / ".cache" / "waqt-timer"
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_FILE = CACHE_DIR / "timings.json"
METHOD_MAP = {"Shia": 0, "Karachi": 1, "ISNA": 2, "MWL": 3, "Makkah": 4,
              "Egypt": 5, "Tehran": 7, "Gulf": 8, "Kuwait": 9, "Qatar": 10,
              "Singapore": 11, "France": 12, "Turkey": 13, "Russia": 14,
              "Moonsighting": 15, "Dubai": 16, "Malaysia": 17, "Tunisia": 18,
              "Algeria": 19, "Indonesia": 20, "Morocco": 21, "Lisbon": 22,
              "Jordan": 23}
METHOD_KEYS = ["Karachi", "MWL", "Egypt", "Makkah", "ISNA", "Tehran", "Shia",
               "Gulf", "Kuwait", "Qatar", "Singapore", "France", "Turkey",
               "Russia", "Moonsighting", "Dubai", "Malaysia", "Tunisia",
               "Algeria", "Indonesia", "Morocco", "Lisbon", "Jordan"]
METHOD_LABELS = {"Karachi": "Karachi - Islamic Sciences (18/18) [Bangladesh]",
                 "MWL": "MWL - Muslim World League (18/17)",
                 "Egypt": "Egypt - General Authority (19.5/17.5)",
                 "Makkah": "Makkah - Umm al-Qura",
                 "ISNA": "ISNA - North America (15/15)"}
SCHOOL_MAP = {"Shafi": 0, "Hanafi": 1}
# Bangladesh default is Karachi 18/18 with Hanafi Asr per Islamic Foundation Bangladesh.
DEFAULT_CFG = {"lat": 23.8103, "lon": 90.4125, "city": "Dhaka", "country": "Bangladesh",
               "method": "Karachi", "school": "Hanafi",
               "location_mode": "auto", "time_format": "24h"}
UA = "waqt-timer/1.5.3"

PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
ALL = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]

# Makruh / forbidden gaps (verified via SeekersGuidance Hanafi, IslamQA, IslamicCalc,
# Sahih Muslim 612, Islamweb fatwa 84538):
# - Sunrise: no prayer from sunrise until spear's length, ~15-20 min after.
#   Dhaka sites (Islamuna) use 15 min (e.g. 05:36-05:51). We use 15 min.
# - Noon (istiwa/zawal): no prayer while sun is at zenith. The instant is
#   momentary; scholars add precaution (ihtiyat). Hanafi-Deobandi mashhur is
#   5 min before Dhuhr (Mangera 3-5, Darul Ifta Birmingham 5, Bahishti Zewar
#   practice 5); Islamic Foundation Bangladesh uses 5-6 min before listed Zuhr.
#   Triple-verified Sep 2026: fiqh texts + BD apps + solar-noon math for Gazipur
#   (true noon 11:51:30, Dhuhr 11:52/53). We use 5 min.
# - Sunset yellowing (isfirar): preferred Asr ends when sun turns yellow/pale
#   (Muslim 612); visual = sun low enough to look at (~5 deg, spear's length).
#   Practical value ~15 min before Maghrib. Asr FARD stays valid and due till
#   sunset (catch 1 rakah before sunset = caught Asr, Bukhari/Muslim), so the
#   app shows "Asr (Makruh)", never "Forbidden", in this stretch. Nafl banned
#   after Asr till sunset (Bukhari/Muslim).
# - Isha fard is valid till true dawn, but delaying past shar'i midnight
#   (Maghrib->Fajr midpoint) is makruh (Zahidi/Ibn Nujaym: tahriman; Ibn Abidin:
#   tanzihan). Preferred: delay till first third/half, not past half.
#   SeekersGuidance Hanafi; IslamQA. App shows an "Isha (Makruh)" info row.
# - Isha->Fajr night itself is NOT forbidden: night prayer (qiyam/Tahajjud)
#   Isha till Subh Sadiq is praised, best in last third (Muslim: best prayer
#   after fard is night prayer). App shows a Tahajjud info row.
# - Ishraq/Duha is Nafl (voluntary): starts after sunrise gap, ends at zawal start.
#   Majority view (IslamOnline, Fiqh-us-Sunnah): Ishraq and Duha are one prayer;
#   minority splits early Ishraq vs late Duha/Chasht. App shows one Nafl slot.
SUNRISE_FORBIDDEN_MIN = 15
NOON_FORBIDDEN_MIN = 5
SUNSET_FORBIDDEN_MIN = 15
ISHRAQ_LABEL = "Ishraq (Nafl)"
FORBIDDEN_LABEL = "Forbidden"
ASR_MAKRUH_LABEL = "Asr (Makruh)"
ISHA_MAKRUH_LABEL = "Isha (Makruh)"
SUNSET_LABEL = "Sunset"
TAHAJJUD_LABEL = "Tahajjud (Nafl)"

def load_cfg():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            c = json.loads(CONFIG_FILE.read_text())
            d = dict(DEFAULT_CFG); d.update(c)
            if c.get("manual") and "location_mode" not in c:
                d["location_mode"] = "city"
            return d
        except Exception:
            pass
    return dict(DEFAULT_CFG)

def save_cfg(c):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(c, indent=2))

def clear_cache():
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
    except Exception:
        pass

def _cache_key(cfg, dt: date):
    return (f"{dt.isoformat()}|{float(cfg['lat']):.4f}|{float(cfg['lon']):.4f}"
            f"|{cfg.get('method', 'Karachi')}|{cfg.get('school', 'Hanafi')}")

def _read_cache():
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text()).get("entries", {})
    except Exception:
        pass
    return {}

def _write_cache(entries):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({"entries": entries}))
    except Exception:
        pass

def geolocate_ip(cfg):
    req = urllib.request.Request("http://ip-api.com/json/?fields=lat,lon,city,country,status",
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=6) as r:
        j = json.loads(r.read().decode())
    if "lat" not in j:
        raise RuntimeError("IP geolocation failed")
    cfg["lat"] = float(j["lat"]); cfg["lon"] = float(j["lon"])
    cfg["city"] = j.get("city", cfg.get("city", ""))
    cfg["country"] = j.get("country", cfg.get("country", ""))
    cfg["location_mode"] = "auto"
    save_cfg(cfg)
    clear_cache()
    return cfg

def city_geocode(query, count=5):
    """District precise search. Tries Nominatim for thana level detail, falls back to Open-Meteo."""
    q = query.strip()
    results = []
    try:
        nq = urllib.parse.quote(q)
        url = (f"https://nominatim.openstreetmap.org/search?q={nq}&format=json"
               f"&addressdetails=1&limit={count}")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            j = json.loads(r.read().decode())
        for it in j:
            addr = it.get("address", {})
            city = (addr.get("suburb") or addr.get("neighbourhood") or addr.get("city")
                    or addr.get("town") or addr.get("village") or it.get("name", ""))
            state = addr.get("state", "")
            country = addr.get("country", "")
            label = it.get("display_name", "")[:80]
            results.append({"name": city or q, "country": country, "admin1": state,
                            "label": label, "lat": float(it["lat"]), "lon": float(it["lon"]),
                            "source": "nominatim"})
    except Exception as e:
        print(f"[waqt] nominatim failed ({e}), trying open-meteo", file=sys.stderr)
    if not results:
        oq = urllib.parse.quote(q)
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={oq}&count={count}&language=en&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            j = json.loads(r.read().decode())
        for it in j.get("results", []):
            results.append({"name": it.get("name", ""), "country": it.get("country", ""),
                            "admin1": it.get("admin1", ""), "label": it.get("name", ""),
                            "lat": it["latitude"], "lon": it["longitude"],
                            "source": "open-meteo"})
    return results

def set_city(cfg, name, country, lat, lon):
    cfg["city"] = name; cfg["country"] = country
    cfg["lat"] = float(lat); cfg["lon"] = float(lon)
    cfg["location_mode"] = "city"
    save_cfg(cfg)
    clear_cache()
    return cfg

def fetch_aladhan(lat, lon, method_num, dt: date, school_num=1):
    ds = dt.strftime("%d-%m-%Y")
    params = {"latitude": lat, "longitude": lon, "method": method_num,
              "school": school_num, "midnightMode": 0,
              "latitudeAdjustmentMethod": 3, "iso8601": "false"}
    qs = urllib.parse.urlencode(params)
    url = f"https://api.aladhan.com/v1/timings/{ds}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        j = json.loads(r.read().decode())
    t = j["data"]["timings"]
    return {k: t.get(k, "00:00")[:5] for k in ALL}

def fetch_offline(lat, lon, method, dt: date, school="Hanafi"):
    from praytimes import PrayTimes
    import time
    if time.daylight and time.localtime().tm_isdst > 0:
        tz = -time.altzone / 3600
    else:
        tz = -time.timezone / 3600
    asr_factor = 2 if school == "Hanafi" else 1
    # Offline port only knows 4 angle sets; other methods (Makkah fixed 90-min
    # Isha etc.) fall back to Karachi angles until network returns.
    pt_method = method if method in ("MWL", "ISNA", "Egypt", "Karachi") else "Karachi"
    if pt_method != method:
        print(f"[waqt] offline has no {method} angles, using Karachi approx", file=sys.stderr)
    pt = PrayTimes(method=pt_method, asr_factor=asr_factor)
    fl = pt.get_times(dt, lat, lon, tz)
    out = {}
    for k in ALL:
        h, m = PrayTimes.float_to_hm(fl[k])
        out[k] = f"{h:02d}:{m:02d}"
    return out

def get_timings(cfg, dt: date, force=False):
    key = _cache_key(cfg, dt)
    if not force:
        entries = _read_cache()
        if key in entries:
            return entries[key]["timings"]
    try:
        timings = fetch_aladhan(cfg["lat"], cfg["lon"],
                                METHOD_MAP.get(cfg.get("method", "Karachi"), 1), dt,
                                SCHOOL_MAP.get(cfg.get("school", "Hanafi"), 1))
        src = "aladhan"
    except Exception as e:
        print(f"[waqt] aladhan failed ({e}) for {cfg['lat']},{cfg['lon']}, offline fallback", file=sys.stderr)
        timings = fetch_offline(cfg["lat"], cfg["lon"], cfg.get("method", "Karachi"), dt,
                                cfg.get("school", "Hanafi"))
        src = "offline"
    entries = _read_cache()
    entries[key] = {"timings": timings, "src": src}
    _write_cache(entries)
    return timings

def to_dt(hm: str, base: date):
    h, m = map(int, hm.split(":")[:2])
    return datetime(base.year, base.month, base.day, h, m)

def dhuhr_name(day: date):
    """Friday Dhuhr is Jumuah. Same start time as Dhuhr (majority view, Islamweb)."""
    return "Jumuah" if day.weekday() == 4 else "Dhuhr"

def day_bounds(timings, day: date):
    """All waqt boundaries for one day. Keys use API names; display renames Dhuhr."""
    fajr = to_dt(timings["Fajr"], day)
    sunrise = to_dt(timings["Sunrise"], day)
    ishraq = sunrise + timedelta(minutes=SUNRISE_FORBIDDEN_MIN)
    dhuhr = to_dt(timings["Dhuhr"], day)
    zawal = dhuhr - timedelta(minutes=NOON_FORBIDDEN_MIN)
    asr = to_dt(timings["Asr"], day)
    maghrib = to_dt(timings["Maghrib"], day)
    makruh_sunset = maghrib - timedelta(minutes=SUNSET_FORBIDDEN_MIN)
    sunset = maghrib  # sun disappears = Maghrib begins (Karachi method, +0 min)
    isha = to_dt(timings["Isha"], day)
    return {"Fajr": fajr, "Sunrise": sunrise, "Ishraq": ishraq,
            "Zawal": zawal, "Dhuhr": dhuhr, "Asr": asr,
            "MakruhSunset": makruh_sunset, "Sunset": sunset,
            "Maghrib": maghrib, "Isha": isha}

def current_next(timings_today, timings_tomorrow, now: datetime):
    """Full-day sequence with correct Fajr end, Nafl Ishraq, and makruh gaps.

    Order: Isha(y) | Fajr [Fajr, Sunrise) | Forbidden(sunrise gap)
    | Ishraq(Nafl) [sunrise+15, zawal) | Forbidden(noon, 10 min)
    | Jumuah/Dhuhr | Asr | Asr(Makruh, yellowing ~15 min) | Maghrib(Sunset)
    | Isha | Fajr(tomorrow). Night Isha->Fajr is Tahajjud-permitted, not forbidden.
    Fajr ends at Sunrise (not Dhuhr). Ishraq/Duha is Nafl.
    """
    today = now.date()
    b = day_bounds(timings_today, today)
    dlabel = dhuhr_name(today)
    if now < b["Fajr"]:
        isha_y = to_dt(timings_today["Isha"], today) - timedelta(days=1)
        return ("Isha", isha_y, "Fajr", b["Fajr"])
    if now < b["Sunrise"]:
        return ("Fajr", b["Fajr"], FORBIDDEN_LABEL, b["Sunrise"])
    if now < b["Ishraq"]:
        return (FORBIDDEN_LABEL, b["Sunrise"], ISHRAQ_LABEL, b["Ishraq"])
    if now < b["Zawal"]:
        return (ISHRAQ_LABEL, b["Ishraq"], FORBIDDEN_LABEL, b["Zawal"])
    if now < b["Dhuhr"]:
        return (FORBIDDEN_LABEL, b["Zawal"], dlabel, b["Dhuhr"])
    if now < b["Asr"]:
        return (dlabel, b["Dhuhr"], "Asr", b["Asr"])
    if now < b["MakruhSunset"]:
        return ("Asr", b["Asr"], ASR_MAKRUH_LABEL, b["MakruhSunset"])
    if now < b["Maghrib"]:
        # Yellowing: Asr fard still due if missed (1 rakah before sunset = caught
        # Asr), delay is makruh, nafl banned. Never show Forbidden here.
        return (ASR_MAKRUH_LABEL, b["MakruhSunset"], "Maghrib", b["Maghrib"])
    if now < b["Isha"]:
        return ("Maghrib", b["Maghrib"], "Isha", b["Isha"])
    fajr_tm = to_dt(timings_tomorrow["Fajr"], today + timedelta(days=1))
    return ("Isha", b["Isha"], "Fajr", fajr_tm)

def fmt_remaining(delta: timedelta):
    s = max(0, int(delta.total_seconds()))
    h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}"

def fmt_hm(hm: str, fmt: str):
    h, m = map(int, hm.split(":")[:2])
    if fmt == "12h":
        ap = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {ap}"
    return f"{h:02d}:{m:02d}"

def fmt_dt(dt_: datetime, fmt: str):
    return fmt_hm(dt_.strftime("%H:%M"), fmt)

def label_text(cur, cdt, nxt, nxt_dt, now, time_format="24h", timings_today=None, today=None):
    rem = fmt_remaining(nxt_dt - now)
    cur_disp = cur.replace(" (Nafl)", "")
    nxt_disp = nxt.replace(" (Nafl)", "")
    if cur == FORBIDDEN_LABEL:
        return (f"{cur} {fmt_dt(cdt, time_format)}-{fmt_dt(nxt_dt, time_format)} "
                f"-{rem} | {nxt_disp} {fmt_dt(nxt_dt, time_format)}")
    if nxt == FORBIDDEN_LABEL:
        frange = fmt_dt(nxt_dt, time_format)
        if timings_today is not None and today is not None:
            try:
                b = day_bounds(timings_today, today)
                if nxt_dt == b["Sunrise"]:
                    frange = f"{fmt_dt(b['Sunrise'], time_format)}-{fmt_dt(b['Ishraq'], time_format)}"
                elif nxt_dt == b["Zawal"]:
                    frange = f"{fmt_dt(b['Zawal'], time_format)}-{fmt_dt(b['Dhuhr'], time_format)}"
            except Exception:
                pass
        return f"{cur_disp} -{rem} | {nxt_disp} {frange}"
    return f"{cur_disp} -{rem} | {nxt_disp} {fmt_dt(nxt_dt, time_format)}"

# ---------- GUI ----------
def run_gui(cfg):
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GLib
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as AI
        ai_mod = AI
    except Exception:
        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3 as AI
            ai_mod = AI
        except Exception:
            ai_mod = None

    state = {"cfg": cfg, "today": None, "tomorrow": None, "day": date.today()}

    def refresh_times(force=False):
        today = date.today()
        state["day"] = today
        state["today"] = get_timings(state["cfg"], today, force=force)
        state["tomorrow"] = get_timings(state["cfg"], today + timedelta(days=1), force=force)

    if state["cfg"].get("location_mode", "auto") == "auto":
        try:
            geolocate_ip(state["cfg"])
        except Exception as e:
            print(f"[waqt] auto locate failed: {e}", file=sys.stderr)
    refresh_times()

    if ai_mod:
        ind = ai_mod.Indicator.new("waqt-timer", "appointment-soon",
                                   ai_mod.IndicatorCategory.APPLICATION_STATUS)
        ind.set_status(ai_mod.IndicatorStatus.ACTIVE)
        try:
            ind.set_label("...", "...")
        except Exception:
            pass
        menu = Gtk.Menu()

        def rebuild_menu():
            for c in menu.get_children():
                menu.remove(c)
            now = datetime.now()
            cur, cdt, nxt, ndt = current_next(state["today"], state["tomorrow"], now)
            tf = state["cfg"].get("time_format", "24h")
            b = day_bounds(state["today"], date.today())
            dlabel = dhuhr_name(date.today())
            try:
                _fajr_tm = to_dt(state["tomorrow"]["Fajr"], date.today() + timedelta(days=1))
                _night = _fajr_tm - b["Maghrib"]
                _last_third = _fajr_tm - _night / 3
                _midnight = b["Maghrib"] + _night / 2
                _tj = f"{fmt_dt(_last_third, tf)} till Fajr (best last third)"
                _im = f"after {fmt_dt(_midnight, tf)} (pray before)"
            except Exception:
                _tj = "after Isha till Fajr (best last third)"
                _im = "after midnight (pray before)"
            rows = [
                ("Fajr", fmt_hm(state['today']["Fajr"], tf)),
                ("Sunrise", fmt_hm(state['today']["Sunrise"], tf)),
                ("Forbidden (Sunrise)", f"{fmt_dt(b['Sunrise'], tf)}-{fmt_dt(b['Ishraq'], tf)} (no prayer)"),
                (ISHRAQ_LABEL, f"{fmt_dt(b['Ishraq'], tf)} (till {fmt_dt(b['Zawal'], tf)})"),
                ("Forbidden (Noon)", f"{fmt_dt(b['Zawal'], tf)}-{fmt_dt(b['Dhuhr'], tf)} (no prayer)"),
                (dlabel, fmt_hm(state['today']["Dhuhr"], tf)),
                ("Asr", fmt_hm(state['today']["Asr"], tf)),
                (ASR_MAKRUH_LABEL, f"{fmt_dt(b['MakruhSunset'], tf)}-{fmt_dt(b['Maghrib'], tf)} (no nafl; Asr fard still due)"),
                ("Maghrib", fmt_hm(state['today']["Maghrib"], tf)),
                ("Isha", fmt_hm(state['today']["Isha"], tf)),
                (ISHA_MAKRUH_LABEL, _im),
                (TAHAJJUD_LABEL, _tj),
            ]
            for name, val in rows:
                is_cur = (name == cur)
                is_nxt = (name == nxt)
                if cur == FORBIDDEN_LABEL:
                    is_cur = ((name == "Forbidden (Sunrise)" and cdt == b["Sunrise"]) or
                              (name == "Forbidden (Noon)" and cdt == b["Zawal"]))
                if nxt == FORBIDDEN_LABEL:
                    is_nxt = ((name == "Forbidden (Sunrise)" and ndt == b["Sunrise"]) or
                              (name == "Forbidden (Noon)" and ndt == b["Zawal"]))
                mark = "> " if is_cur else "-> " if is_nxt else "   "
                item = Gtk.MenuItem(label=f"{mark}{name}: {val}")
                item.set_sensitive(False)
                menu.append(item)
            menu.append(Gtk.SeparatorMenuItem())
            mode = state["cfg"].get("location_mode", "auto")
            loc = Gtk.MenuItem(label=f"{state['cfg'].get('city','')}, {state['cfg'].get('country','')} [{mode}] [{tf}]")
            loc.set_sensitive(False); menu.append(loc)
            coords = Gtk.MenuItem(label=f"Coords {state['cfg']['lat']:.4f}, {state['cfg']['lon']:.4f}")
            coords.set_sensitive(False); menu.append(coords)
            for lbl, fn in [("Refresh times", lambda *_: (refresh_times(force=True), rebuild_menu())),
                            ("Location and display", lambda *_: location_dialog()),
                            ("Quit", Gtk.main_quit)]:
                it = Gtk.MenuItem(label=lbl)
                it.connect("activate", fn)
                menu.append(it)
            menu.show_all()

        def location_dialog():
            d = Gtk.Dialog(title="Waqt Timer - Location and Display", flags=0)
            d.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
            d.set_default_size(440, 420)
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            root.set_margin_top(12); root.set_margin_bottom(12)
            root.set_margin_start(12); root.set_margin_end(12)

            # Section 1: location mode
            fr_loc = Gtk.Frame(label="Location")
            box_loc = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box_loc.set_margin_top(8); box_loc.set_margin_bottom(8)
            box_loc.set_margin_start(8); box_loc.set_margin_end(8)
            chk_auto = Gtk.CheckButton(label="Track location automatically using internet")
            chk_auto.set_active(state["cfg"].get("location_mode", "auto") == "auto")
            box_loc.pack_start(chk_auto, False, False, 0)

            # Search row: entry with icon on right + button
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            e_city = Gtk.Entry()
            e_city.set_placeholder_text("City name, for example: Dhaka")
            e_city.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "system-search-symbolic")
            e_city.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Search")
            e_city.set_hexpand(True)
            btn_search = Gtk.Button(label="Search")
            row.pack_start(e_city, True, True, 0)
            row.pack_start(btn_search, False, False, 0)
            box_loc.pack_start(row, False, False, 0)

            cmb = Gtk.ComboBoxText()
            cmb.set_tooltip_text("Pick a search result")
            box_loc.pack_start(cmb, False, False, 0)
            fr_loc.add(box_loc)
            root.pack_start(fr_loc, False, False, 0)

            # Section 2: display
            fr_disp = Gtk.Frame(label="Display")
            box_disp = Gtk.Grid(column_spacing=8, row_spacing=8)
            box_disp.set_margin_top(8); box_disp.set_margin_bottom(8)
            box_disp.set_margin_start(8); box_disp.set_margin_end(8)
            box_disp.attach(Gtk.Label(label="Time format:"), 0, 0, 1, 1)
            cmb_fmt = Gtk.ComboBoxText()
            cmb_fmt.append_text("24h"); cmb_fmt.append_text("12h")
            cmb_fmt.set_active(0 if state["cfg"].get("time_format", "24h") == "24h" else 1)
            box_disp.attach(cmb_fmt, 1, 0, 1, 1)
            fr_disp.add(box_disp)
            root.pack_start(fr_disp, False, False, 0)

            # Section 3: calculation (default Karachi 18/18 Hanafi = Islamic
            # Foundation Bangladesh standard)
            fr_calc = Gtk.Frame(label="Calculation")
            box_calc = Gtk.Grid(column_spacing=8, row_spacing=8)
            box_calc.set_margin_top(8); box_calc.set_margin_bottom(8)
            box_calc.set_margin_start(8); box_calc.set_margin_end(8)
            box_calc.attach(Gtk.Label(label="Method:"), 0, 0, 1, 1)
            cmb_method = Gtk.ComboBoxText()
            for k in METHOD_KEYS:
                cmb_method.append_text(METHOD_LABELS.get(k, k))
            try:
                cmb_method.set_active(METHOD_KEYS.index(state["cfg"].get("method", "Karachi")))
            except ValueError:
                cmb_method.set_active(0)
            box_calc.attach(cmb_method, 1, 0, 1, 1)
            box_calc.attach(Gtk.Label(label="Asr school:"), 0, 1, 1, 1)
            cmb_school = Gtk.ComboBoxText()
            cmb_school.append_text("Hanafi"); cmb_school.append_text("Shafi")
            cmb_school.set_active(0 if state["cfg"].get("school", "Hanafi") == "Hanafi" else 1)
            box_calc.attach(cmb_school, 1, 1, 1, 1)
            fr_calc.add(box_calc)
            root.pack_start(fr_calc, False, False, 0)

            status = Gtk.Label()
            status.set_line_wrap(True)
            status.set_xalign(0)
            def set_status(msg):
                status.set_text(msg)
            set_status(f"Active: {state['cfg'].get('city','')}, {state['cfg'].get('country','')} "
                       f"at {state['cfg']['lat']:.4f}, {state['cfg']['lon']:.4f}")
            root.pack_start(status, False, False, 0)

            results = {"list": []}
            def on_search(*_args):
                q = e_city.get_text().strip()
                if not q:
                    set_status("Type a city name, then press Enter or Search.")
                    return
                set_status(f"Searching for '{q}'...")
                try:
                    results["list"] = city_geocode(q)
                except Exception as e:
                    set_status(f"Search failed: {e}")
                    return
                cmb.remove_all()
                if not results["list"]:
                    set_status("No matches. Check spelling and try again.")
                    return
                for r in results["list"]:
                    cmb.append_text(f"{r['name']}, {r['admin1']} {r['country']} ({r['lat']:.2f}, {r['lon']:.2f})")
                cmb.set_active(0)
                chk_auto.set_active(False)
                set_status(f"Found {len(results['list'])} match(es). Select one and press OK.")
            # Enter key and icon click both trigger search
            e_city.connect("activate", on_search)
            e_city.connect("icon-press", on_search)
            btn_search.connect("clicked", on_search)

            d.get_content_area().add(root)
            d.show_all()
            if d.run() == Gtk.ResponseType.OK:
                state["cfg"]["time_format"] = cmb_fmt.get_active_text() or "24h"
                mi = cmb_method.get_active()
                if mi is not None and mi >= 0:
                    state["cfg"]["method"] = METHOD_KEYS[mi]
                state["cfg"]["school"] = cmb_school.get_active_text() or "Hanafi"
                if chk_auto.get_active():
                    try:
                        geolocate_ip(state["cfg"])
                        set_status("Auto location updated.")
                    except Exception as e:
                        print(f"[waqt] auto locate failed: {e}", file=sys.stderr)
                else:
                    idx = cmb.get_active()
                    if results["list"] and idx >= 0:
                        r = results["list"][idx]
                        set_city(state["cfg"], r["name"], r["country"], r["lat"], r["lon"])
                    elif e_city.get_text().strip():
                        try:
                            lst = city_geocode(e_city.get_text().strip())
                            if lst:
                                r = lst[0]
                                set_city(state["cfg"], r["name"], r["country"], r["lat"], r["lon"])
                        except Exception as e:
                            print(f"[waqt] city apply failed: {e}", file=sys.stderr)
                save_cfg(state["cfg"])
                refresh_times(force=True)
                rebuild_menu()
            d.destroy()

        rebuild_menu()
        ind.set_menu(menu)

        def tick():
            now = datetime.now()
            if date.today() != state["day"]:
                refresh_times(force=True); rebuild_menu()
            cur, cdt, nxt, ndt = current_next(state["today"], state["tomorrow"], now)
            try:
                ind.set_label(label_text(cur, cdt, nxt, ndt, now, state["cfg"].get("time_format", "24h"), state["today"], now.date())[:64], "")
            except Exception:
                pass
            return True

        GLib.timeout_add_seconds(1, tick)
        tick()
        Gtk.main()
    else:
        win = Gtk.Window(title="Waqt Timer")
        lbl = Gtk.Label(label="...")
        win.add(lbl); win.set_default_size(460, 90)
        win.connect("destroy", Gtk.main_quit); win.show_all()
        def tick():
            now = datetime.now()
            cur, cdt, nxt, ndt = current_next(state["today"], state["tomorrow"], now)
            tf = state["cfg"].get("time_format", "24h")
            lbl.set_text(label_text(cur, cdt, nxt, ndt, now, tf, state["today"], now.date()) + "\n" +
                         "  ".join(f"{n} {fmt_hm(state['today'][n], tf)}" for n in ALL))
            return True
        GLib.timeout_add_seconds(1, tick); tick(); Gtk.main()

def main():
    cfg = load_cfg()
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", help="City name to use (disables auto)")
    ap.add_argument("--auto", action="store_true", help="Force auto IP location")
    ap.add_argument("--refresh", action="store_true", help="Ignore cache and refetch")
    ap.add_argument("--format", choices=["24h", "12h"], dest="fmt")
    ap.add_argument("--method", choices=list(METHOD_MAP))
    ap.add_argument("--school", choices=["Hanafi", "Shafi"])
    ap.add_argument("--no-gui", action="store_true"); ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    if a.fmt: cfg["time_format"] = a.fmt
    if a.method: cfg["method"] = a.method
    if a.school: cfg["school"] = a.school
    # migrate old installs that still default to MWL
    if cfg.get("method") == "MWL":
        cfg["method"] = "Karachi"
    if cfg.get("method") not in METHOD_MAP:
        cfg["method"] = "Karachi"
    if "school" not in cfg:
        cfg["school"] = "Hanafi"
    if a.auto:
        cfg["location_mode"] = "auto"
    if a.refresh:
        clear_cache()
    if a.city:
        try:
            lst = city_geocode(a.city)
            if lst:
                r = lst[0]
                set_city(cfg, r["name"], r["country"], r["lat"], r["lon"])
            else:
                print(f"No match for city '{a.city}'", file=sys.stderr)
        except Exception as e:
            print(f"City search failed: {e}", file=sys.stderr)
    save_cfg(cfg)
    if cfg.get("location_mode", "auto") == "auto" and not a.city:
        try:
            # refetch IP each run in auto mode so travel is picked up
            cfg = geolocate_ip(cfg)
        except Exception as e:
            print(f"[waqt] auto locate failed: {e}", file=sys.stderr)
    if a.test or a.no_gui:
        today = date.today()
        t = get_timings(cfg, today, force=a.refresh)
        tm = get_timings(cfg, today + timedelta(days=1), force=a.refresh)
        now = datetime.now()
        cur, cdt, nxt, ndt = current_next(t, tm, now)
        tf = cfg.get("time_format", "24h")
        b = day_bounds(t, today)
        _fajr_tm = to_dt(tm["Fajr"], today + timedelta(days=1))
        _night = _fajr_tm - b["Maghrib"]
        _tj_from = fmt_dt(_fajr_tm - _night / 3, tf)
        _mid = fmt_dt(b["Maghrib"] + _night / 2, tf)
        print(json.dumps({"loc": {k: cfg.get(k) for k in ("lat", "lon", "city", "country", "method", "school", "location_mode", "time_format")},
                          "today": {k: fmt_hm(v, tf) for k, v in t.items()},
                          "derived": {"ishraq": fmt_dt(b["Ishraq"], tf),
                                      "forbidden_noon": f"{fmt_dt(b['Zawal'], tf)}-{fmt_dt(b['Dhuhr'], tf)}",
                                      "makruh_sunset": f"{fmt_dt(b['MakruhSunset'], tf)}-{fmt_dt(b['Maghrib'], tf)}",
                                      "sunset": fmt_dt(b["Sunset"], tf),
                                      "isha_makruh_after": _mid,
                                      "tahajjud_best_from": _tj_from,
                                      "dhuhr_label": dhuhr_name(today)},
                          "now": now.isoformat(), "current": cur, "next": nxt,
                          "label": label_text(cur, cdt, nxt, ndt, now, tf, t, today)}, indent=2))
        return
    run_gui(cfg)

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
