"""PrayTimes v2.3 offline port (MWL default) - public-domain algorithm by Hamid Zarrabi-Zadeh."""
import math
from datetime import date

class PrayTimes:
    METHODS = {
        'MWL': {'fajr': 18, 'isha': 17, 'maghrib': 0, 'midnight': 'Standard'},
        'ISNA': {'fajr': 15, 'isha': 15, 'maghrib': 0, 'midnight': 'Standard'},
        'Egypt': {'fajr': 19.5, 'isha': 17.5, 'maghrib': 0, 'midnight': 'Standard'},
        'Karachi': {'fajr': 18, 'isha': 18, 'maghrib': 0, 'midnight': 'Standard'},
    }
    def __init__(self, method='MWL', asr_factor=1):
        p = self.METHODS.get(method, self.METHODS['MWL'])
        self.fajr_angle = p['fajr']
        self.isha_angle = p['isha']
        self.maghrib_minutes = p['maghrib']
        self.asr_factor = asr_factor

    @staticmethod
    def _julian(y, m, d):
        if m <= 2:
            y -= 1; m += 12
        A = y // 100
        B = 2 - A + A // 4
        return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5

    @staticmethod
    def _sun(jd):
        D = jd - 2451545.0
        G = (357.529 + 0.98560028 * D) % 360
        Q = (280.459 + 0.98564736 * D) % 360
        L = (Q + 1.915 * math.sin(math.radians(G)) + 0.020 * math.sin(math.radians(2 * G))) % 360
        E = 23.439 - 0.00000036 * D
        RA = math.degrees(math.atan2(math.cos(math.radians(E)) * math.sin(math.radians(L)), math.cos(math.radians(L)))) / 15
        RA = (RA + 24) % 24
        decl = math.degrees(math.asin(math.sin(math.radians(E)) * math.sin(math.radians(L))))
        eqt = Q / 15 - RA
        return decl, eqt

    def _midday(self, jd, tz, lng):
        _, eqt = self._sun(jd)
        return 12 + tz - lng / 15 - eqt

    def _sun_angle_time(self, jd, tz, lng, lat, angle, direction, base=None):
        decl, eqt = self._sun(jd)
        noon = self._midday(jd, tz, lng) if base is None else base
        t = (1/15) * math.degrees(math.acos(
            max(-1, min(1, (math.sin(math.radians(angle)) - math.sin(math.radians(lat)) * math.sin(math.radians(decl))) /
            (math.cos(math.radians(lat)) * math.cos(math.radians(decl)))))))
        return noon - t if direction == 'ccw' else noon + t

    def _asr_time(self, jd, tz, lng, lat, base):
        decl, _ = self._sun(jd)
        angle = math.degrees(math.acot(self.asr_factor + math.tan(math.radians(abs(lat - decl)))))
        return self._sun_angle_time(jd, tz, lng, lat, angle, 'cw', base)

    def get_times(self, dt: date, lat: float, lng: float, tz: float):
        jd = self._julian(dt.year, dt.month, dt.day)
        # longitude correction
        jd_lon = jd - lng / (15 * 24)
        noon = self._midday(jd_lon, tz, lng)
        sunrise = self._sun_angle_time(jd_lon, tz, lng, lat, -0.833, 'ccw', noon)
        sunset = self._sun_angle_time(jd_lon, tz, lng, lat, -0.833, 'cw', noon)
        fajr = self._sun_angle_time(jd_lon, tz, lng, lat, -self.fajr_angle, 'ccw', noon)
        isha = self._sun_angle_time(jd_lon, tz, lng, lat, -self.isha_angle, 'cw', noon)
        dhuhr = noon
        asr = self._asr_time(jd_lon, tz, lng, lat, noon)
        maghrib = sunset + self.maghrib_minutes / 60.0
        return {'Fajr': fajr, 'Sunrise': sunrise, 'Dhuhr': dhuhr,
                'Asr': asr, 'Maghrib': maghrib, 'Isha': isha}

    @staticmethod
    def float_to_hm(f):
        f = f % 24
        h = int(f); m = int(round((f - h) * 60))
        if m == 60:
            h = (h + 1) % 24; m = 0
        return h, m

def _math_acot(x):
    return math.atan(1 / x) if x else math.pi / 2
math.acot = _math_acot
