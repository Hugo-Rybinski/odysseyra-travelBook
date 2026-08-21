"""Serialize a *resolved* :class:`~.itinerary.Itinerary` into a plain, JSON-ready
dict — the single contract the PWA (and any other non-Python consumer) renders
from.

The point is that all of the model's inference has already run by the time this
is called (``Itinerary.from_dict`` chains activity times, infers dates, resolves
meal categories, lays out the day timelines and converts prices), so the dict
this emits carries the *resolved* values, not the raw input. Consumers never
re-implement any of that logic; they just render what is here.

Beyond the per-object fields, each day also carries the associations the day
renderer needs — the night's ``stay``, the ``transports`` departing that day,
the ``car_events`` (pick-up / drop-off) falling on it, and any ``night_transport``
— computed through the same :class:`Itinerary` helpers the PDF uses, so the
per-day weaving isn't duplicated downstream either.

Times are ``"HH:MM"`` strings, dates ISO ``"YYYY-MM-DD"``, UTC offsets integer
minutes (with a formatted ``*_tz_label`` alongside). Money is emitted structured
— the raw ``amount``/``currency`` plus the amount converted into the trip's
default currency and into each secondary currency — leaving only symbol/position
formatting to the consumer.
"""

from __future__ import annotations

from datetime import date, time

from .itinerary import Itinerary
from .parsers import _format_tz

__all__ = ["to_dict"]


# --- scalar helpers ---------------------------------------------------------

def _time(t: time | None) -> str | None:
    return None if t is None else f"{t:%H:%M}"


def _date(d: date | None) -> str | None:
    return None if d is None else d.isoformat()


def _coord(c) -> dict | None:
    if c is None:
        return None
    return {"lat": c.lat, "long": c.long, "show_on_map": c.show_on_map}


def _tz_label(offset: int | None, default_tz: int | None) -> str:
    """A UTC-offset display label, blank when the offset is unset or matches the
    trip's default timezone (so only meaningful, differing offsets are shown)."""
    if offset is None or offset == default_tz:
        return ""
    return _format_tz(offset)


def _tz(offset: int | None, default_tz: int | None) -> dict:
    """A UTC offset as both integer minutes and a display label (blank when it
    equals the default). Used for the car-rental stamps."""
    return {"tz": offset, "tz_label": _tz_label(offset, default_tz)}


def _price(itin: Itinerary, amount: float | None, currency: str,
           paid: bool | None) -> dict | None:
    """Structured money: the raw amount and its currency (resolved to the trip
    default when blank), the amount converted into the default currency, and the
    equivalent in each secondary currency. ``in_default`` is ``None`` when the
    currency has no known rate. ``paid`` is the tri-state flag (True/False/None).
    Returns ``None`` when there is no price."""
    if amount is None:
        return None
    code = (currency or itin.default_currency).strip().upper()
    in_default = itin.in_default(amount, code)
    secondaries = []
    if in_default is not None:
        for sec in itin.secondary_currencies:
            secondaries.append({
                "currency": sec.currency,
                "amount": in_default * sec.change_rate,
            })
    return {
        "amount": amount,
        "currency": code,
        "default_currency": itin.default_currency,
        "in_default": in_default,
        "secondaries": secondaries,
        "paid": paid,
    }


def _sched(obj, default_tz: int | None) -> dict:
    """The shared timeline fields carried by every scheduled object. The UTC
    offsets are emitted as ``start_tz``/``end_tz`` (integer minutes) with a
    ``*_tz_label`` display string — deliberately *not* ``start``/``end``, which
    are the semantic place names on roads, transports and hikes. A label is blank
    when the offset matches the trip default (so only differing offsets show)."""
    return {
        "start_time": _time(obj.start_time),
        "end_time": _time(obj.end_time),
        "duration_min": obj.duration_min,
        "duration_display": obj.duration_display,
        "time_range": obj.time_range,
        "start_tz": obj.start_tz,
        "start_tz_label": _tz_label(obj.start_tz, default_tz),
        "end_tz": obj.end_tz,
        "end_tz_label": _tz_label(obj.end_tz, default_tz),
    }


# --- activities -------------------------------------------------------------

def _waypoint(wp) -> dict:
    return {
        "coordinate": _coord(wp.coordinate),
        "location": wp.location,
        "duration_min": wp.duration_min,
        "duration_display": wp.duration_display,
        "distance_km": wp.distance_km,
    }


def _activity(itin: Itinerary, act) -> dict:
    """Serialize one timeline activity (recursing into any nested activities).
    ``type`` is the activity ``kind``; ``title`` is the model's computed title."""
    out = {
        "type": act.kind,
        "title": act.title,
        "coordinate": _coord(getattr(act, "coordinate", None)),
        # The map pin label (number / area letter / ★ stay) when maps were rendered
        # for this build; ``None`` otherwise. Stamped onto the model object by the
        # caller (see the PWA bridge) from the rendered day maps.
        "map_pin": getattr(act, "_map_pin", None),
        **_sched(act, itin.default_timezone),
    }

    if act.kind == "buffer":
        out["auto"] = act.auto

    elif act.kind == "road":
        out.update({
            "start": act.start,
            "destination": act.destination,
            "distance_km": act.distance_km,
            "off_road": act.off_road,
            "waypoints": [_waypoint(w) for w in act.waypoints],
        })

    elif act.kind == "point_of_interest":
        out.update({
            "name": act.name,
            "address": act.address,
            "description": act.description,
            "category": act.category,
            "website": act.website,
        })

    elif act.kind == "place":
        out.update({"name": act.name, "description": act.description})

    elif act.kind == "hike":
        out.update({
            "name": act.name,
            "description": act.description,
            "distance_km": act.distance_km,
            "elevation_m": act.elevation_m,
            "start": act.start,
            "end": act.end,
            "route": act.route,
            "route_label": act.route_label,
        })

    elif act.kind == "meal":
        out.update({
            "restaurant": act.restaurant,
            "address": act.address,
            "area": act.area,
            "meal_type": act.meal_type,
            "category": act.category,
        })

    nested = getattr(act, "activities", None)
    if nested:
        out["activities"] = [_activity(itin, a) for a in nested]
    return out


# --- top-level sections -----------------------------------------------------

def _transport(itin: Itinerary, t) -> dict:
    return {
        "type": t.type,
        "title": t.title,
        "start": t.start,
        "end": t.end,
        "start_date": _date(t.start_date),
        "end_date": _date(t.end_date),
        "overnight": t.overnight,
        "end_day_offset": t.end_day_offset,
        "flight_number": t.flight_number,
        "train_number": t.train_number,
        "booking_number": t.booking_number,
        "booking_source": t.booking_source,
        "website": t.website,
        "booking_link": t.booking_link,
        "status": t.status,
        "price": _price(itin, t.price, t.currency, t.paid),
        "coordinate": _coord(t.coordinate),
        "start_coordinate": _coord(t.start_coordinate),
        "end_coordinate": _coord(t.end_coordinate),
        **_sched(t, itin.default_timezone),
    }


def _accommodation(itin: Itinerary, a) -> dict:
    return {
        "name": a.name,
        "arrival": _date(a.arrival),
        "departure": _date(a.departure),
        "nights": a.nights,
        "date_range": a.date_range,
        "city": a.city,
        "type": a.type,
        "address": a.address,
        "contact": a.contact,
        "booking_source": a.booking_source,
        "website": a.website,
        "booking_link": a.booking_link,
        "status": a.status,
        "price": _price(itin, a.price, a.currency, a.paid),
        "breakfast_included": a.breakfast_included,
        "coordinate": _coord(a.coordinate),
        "map_pin": getattr(a, "_map_pin", None),
    }


def _stamp(s, default_tz: int | None) -> dict:
    return {"date": _date(s.date), "time": _time(s.time), **_tz(s.tz, default_tz)}


def _car_rental(itin: Itinerary, c) -> dict:
    dtz = itin.default_timezone
    return {
        "title": c.title,
        "company": c.company,
        "booking_start": _stamp(c.booking_start, dtz),
        "booking_end": _stamp(c.booking_end, dtz),
        "pickup": _stamp(c.pickup, dtz),
        "dropoff": _stamp(c.dropoff, dtz),
        "pickup_location": c.pickup_location,
        "dropoff_location": c.dropoff_location,
        "booking_number": c.booking_number,
        "website": c.website,
        "booking_link": c.booking_link,
        "status": c.status,
        "price": _price(itin, c.price, c.currency, c.paid),
        "car_type": c.car_type,
        "car_type_label": c.car_type_label,
        "car_model": c.car_model,
        "contact": c.contact,
        "additional_drivers": c.additional_drivers,
        "pickup_duration_min": c.pickup_duration_min,
        "pickup_duration_display": c.pickup_duration_display,
        "dropoff_duration_min": c.dropoff_duration_min,
        "dropoff_duration_display": c.dropoff_duration_display,
        "coordinate": _coord(c.coordinate),
        "pickup_coordinate": _coord(c.pickup_coordinate),
        "dropoff_coordinate": _coord(c.dropoff_coordinate),
    }


def _car_event(itin: Itinerary, ev) -> dict:
    """A car pick-up / drop-off woven into a day's timeline. Carries the timeline
    fields plus the identifying bits of its owning rental."""
    rental = ev.rental
    # The event's own coordinate: pick-up / drop-off point, else the rental's
    # fallback — mirrors the PDF's inline "(Navigate)" target (pdf/days.py).
    coord = None
    if rental is not None:
        coord = (rental.pickup_coordinate if ev.kind == "car_pickup"
                 else rental.dropoff_coordinate) or rental.coordinate
    return {
        "kind": ev.kind,  # "car_pickup" | "car_dropoff"
        "date": _date(ev.date),
        "location": ev.location,
        "rental_title": rental.title if rental else "",
        "company": rental.company if rental else "",
        "car_model": rental.car_model if rental else "",
        "car_type_label": rental.car_type_label if rental else "",
        "booking_number": rental.booking_number if rental else "",
        "coordinate": _coord(coord),
        **_sched(ev, itin.default_timezone),
    }


def _day(itin: Itinerary, index: int, day) -> dict:
    """One day, with its resolved timeline and the associations the renderer
    needs (the night's stay, that day's transports / car events / overnight leg).
    ``sleep_city`` is a convenience for the cover overview: the town you sleep in
    that night — the stay's city, else the day's own city."""
    stay = itin.stay_for(day.date)
    night = itin.night_transport(day.date)
    return {
        "day_number": index + 1,
        "title": day.title,
        "date": _date(day.date),
        "city": day.city,
        "description": day.description,
        "activities": [_activity(itin, a) for a in day.activities],
        "transports": [_transport(itin, t) for t in itin.transports_on(day.date)],
        "car_events": [_car_event(itin, e) for e in itin.car_events_on(day.date)],
        "stay": _accommodation(itin, stay) if stay else None,
        # 1-based index of this night within the stay (for "Night x/total").
        "stay_night": stay.night_of(day.date) if stay else None,
        "night_transport": _transport(itin, night) if night else None,
        "sleep_city": (stay.city if stay else "") or day.city,
    }


def to_dict(itinerary: Itinerary) -> dict:
    """Serialize a resolved :class:`Itinerary` into a plain, JSON-ready dict.

    Every value is already resolved (inferred times/dates, meal categories,
    converted prices) and every container carries its per-day associations, so a
    consumer can render the whole travel book without any further computation."""
    return {
        "title": itinerary.title,
        "subtitle": itinerary.subtitle,
        "summary": itinerary.summary,
        "cover_color": itinerary.cover_color,
        "start_date": _date(itinerary.start_date),
        "end_date": _date(itinerary.end_date),
        "date_range": itinerary.date_range,
        "day_count": len(itinerary.days),
        "default_currency": itinerary.default_currency,
        "secondary_currencies": [
            {"currency": s.currency, "change_rate": s.change_rate}
            for s in itinerary.secondary_currencies
        ],
        "timezone": itinerary.default_timezone,
        "timezone_label": _format_tz(itinerary.default_timezone),
        "maps": {
            "include_in_render": itinerary.include_maps_in_render,
            "infer_from_address": itinerary.infer_coordinates_from_address,
            "inference_countries": list(itinerary.inference_countries),
        },
        "days": [_day(itinerary, i, d) for i, d in enumerate(itinerary.days)],
        "transports": [_transport(itinerary, t) for t in itinerary.transports],
        "accommodations": [
            _accommodation(itinerary, a) for a in itinerary.accommodations
        ],
        "car_rentals": [_car_rental(itinerary, c) for c in itinerary.car_rentals],
    }
