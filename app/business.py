"""Everything that identifies this business, in one place.

Defaults describe the Tulsi Foods kitchen, so nothing changes until a value is
overridden. Each value can be set with an environment variable (BIZ_*) so a
deployment never needs a code edit. Templates read these as `biz.<name>`;
Python modules import `business` directly.

Phone numbers are stored once, in E.164 form, and every display variant
(spaced, local, digits-only) is derived from that single value.
"""
import os


def _env(name: str, default: str) -> str:
    return os.environ.get(f"BIZ_{name}", default)


def _spaced(e164: str) -> str:
    """'+919940621800' -> '+91 99406 21800' (Indian mobile grouping)."""
    d = e164.lstrip("+")
    if d.startswith("91") and len(d) == 12:
        return f"+91 {d[2:7]} {d[7:]}"
    return e164


class Business:
    name = _env("NAME", "Tulsi Foods")
    instagram = _env("INSTAGRAM", "tulsi.foods_chennai")
    email = _env("EMAIL", "tulsifoodsco@gmail.com")

    # Address parts
    street_no = _env("STREET_NO", "34")
    street = _env("STREET", "Murrays Gate Road")
    locality = _env("LOCALITY", "Alwarpet")
    city = _env("CITY", "Chennai")
    pincode = _env("PINCODE", "600018")
    state = _env("STATE", "Tamil Nadu")
    country = _env("COUNTRY", "India")

    # Kitchen phone (calls and WhatsApp) and a second WhatsApp contact
    phone_e164 = _env("PHONE", "+919940621800")
    contact_whatsapp_e164 = _env("CONTACT_WHATSAPP", "+919940062840")

    # Opening hours: (open, close) as shown to customers
    hours_mon_sat = (_env("HOURS_MON_SAT_OPEN", "9 AM"), _env("HOURS_MON_SAT_CLOSE", "9 PM"))
    hours_sunday = (_env("HOURS_SUN_OPEN", "11 AM"), _env("HOURS_SUN_CLOSE", "9 PM"))

    # ---- derived: phone
    @property
    def phone_display(self) -> str:
        return _spaced(self.phone_e164)

    @property
    def phone_digits(self) -> str:
        return self.phone_e164.lstrip("+")

    @property
    def phone_local(self) -> str:
        """Without the country code: '99406 21800'."""
        return self.phone_display.split(" ", 1)[1] if self.phone_display.startswith("+91 ") else self.phone_e164

    @property
    def phone_ten(self) -> str:
        """Ten digits, no spaces: '9940621800'."""
        return self.phone_digits[-10:]

    @property
    def contact_whatsapp_display(self) -> str:
        return _spaced(self.contact_whatsapp_e164)

    @property
    def contact_whatsapp_digits(self) -> str:
        return self.contact_whatsapp_e164.lstrip("+")

    # ---- derived: address
    @property
    def pickup_line(self) -> str:
        """'34 Murrays Gate Road, Alwarpet'"""
        return f"{self.street_no} {self.street}, {self.locality}"

    @property
    def address(self) -> str:
        """'34 Murrays Gate Road, Alwarpet, Chennai 600018'"""
        return f"{self.pickup_line}, {self.city} {self.pincode}"

    @property
    def address_commas(self) -> str:
        """'34, Murrays Gate Road, Alwarpet, Chennai 600018'"""
        return f"{self.street_no}, {self.street}, {self.locality}, {self.city} {self.pincode}"

    @property
    def address_commas_short(self) -> str:
        """'34, Murrays Gate Road, Alwarpet, Chennai'"""
        return f"{self.street_no}, {self.street}, {self.locality}, {self.city}"

    @property
    def street_address(self) -> str:
        """'34, Murrays Gate Road, Alwarpet' (schema.org streetAddress)"""
        return f"{self.street_no}, {self.street}, {self.locality}"

    @property
    def address_full(self) -> str:
        """Courier form: '34, Murrays Gate Road, Alwarpet, Chennai, 600018, Tamil Nadu, India'"""
        return f"{self.street_address}, {self.city}, {self.pincode}, {self.state}, {self.country}"

    # ---- derived: hours
    @property
    def hours(self) -> str:
        """Compact: 'Mon–Sat 9 AM–9 PM, Sun 11 AM–9 PM'"""
        return f"Mon–Sat {self.hours_mon_sat[0]}–{self.hours_mon_sat[1]}, Sun {self.hours_sunday[0]}–{self.hours_sunday[1]}"

    @property
    def hours_spaced(self) -> str:
        """Spaced: 'Mon–Sat 9 AM – 9 PM, Sun 11 AM – 9 PM'"""
        return f"Mon–Sat {self.hours_mon_sat[0]} – {self.hours_mon_sat[1]}, Sun {self.hours_sunday[0]} – {self.hours_sunday[1]}"


business = Business()
