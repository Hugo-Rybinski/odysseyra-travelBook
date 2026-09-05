"""Serialize a *resolved* :class:`~.itinerary.Itinerary` into a plain, JSON-ready
dict — the single contract the PWA (and any other non-Python consumer) renders
from.

The point is that all of the model's inference has already run by the time this
is called (``Itinerary.from_dict`` chains activity times, infers dates, resolves
meal categories, lays out the day timelines and converts prices), so the dict
this emits carries the *resolved* values, not the raw input. Consumers never
re-implement any of that logic; they just render what is here.

Beyond the per-object fields, each day also carries the associations the day
renderer needs — the night's ``stay``, the transport **legs** departing that day
(``transports``), the ``car_events`` (pick-up / drop-off) falling on it, and any
``night_transport`` — computed through the same :class:`Itinerary` helpers the
PDF uses, so the per-day weaving isn't duplicated downstream either.

Transport is emitted at both levels: the top-level ``transports`` are *bookings*,
each holding its ``legs``, while a day's ``transports`` are the legs themselves,
each enriched with its booking's shared reservation fields (see
:func:`_transport_leg`) so nothing has to look its parent up.

Times are ``"HH:MM"`` strings, dates ISO ``"YYYY-MM-DD"``, UTC offsets integer
minutes (with a formatted ``*_tz_label`` alongside). Money is emitted structured
— the raw ``amount``/``currency`` plus the amount converted into the trip's
default currency and into each secondary currency — leaving only symbol/position
formatting to the consumer.
"""

from __future__ import annotations

from datetime import date, time

from .itinerary import Itinerary
from .moon import moon_phase
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


def _track(itin: Itinerary, act) -> dict | None:
    """A hike's embedded GPX: the simplified trail line, the resampled elevation
    profile and the figures measured off the full-resolution recording — plus the
    original base64 ``gpx`` itself.

    ``None`` when the hike carries no ``gpx`` — or when the trip switched the
    hike maps off (``defaults.include_hike_maps``), the way ``moon`` and ``sun``
    go absent for theirs. The point is that the (kilobytes of) geometry doesn't
    ride into a consumer that isn't going to draw it.

    ``gpx`` is carried verbatim so the viewer can offer the file for **download**
    (its "(Get GPX track)" link) — the bytes you attached, not a re-export of the
    simplified line. It rides along rather than being matched back to the source
    JSON: the resolved timeline has buffers woven into it, so a resolved hike has
    no index into the input to look itself up by.
    """
    track = getattr(act, "track", None)
    if track is None or not itin.include_hike_maps:
        return None
    (min_lat, min_long), (max_lat, max_long) = track.bounds
    return {
        "gpx": act.gpx,
        "points": [[lat, long] for lat, long in track.points],
        "profile": [[km, m] for km, m in track.profile],
        "distance_km": round(track.distance_km, 3),
        "ascent_m": None if track.ascent_m is None else round(track.ascent_m),
        "descent_m": None if track.descent_m is None else round(track.descent_m),
        "min_elevation_m": (None if track.min_elevation_m is None
                            else round(track.min_elevation_m)),
        "max_elevation_m": (None if track.max_elevation_m is None
                            else round(track.max_elevation_m)),
        "point_count": track.point_count,
        "bounds": [[min_lat, min_long], [max_lat, max_long]],
    }


def _opening(op) -> dict | None:
    """A point of interest's opening days/hours (``None`` when it states
    neither). ``day_runs`` is the *folded* form — consecutive days already
    grouped into ``(first, last)`` pairs — so the viewer only has to name the
    weekdays, not work out the runs; ``hours_display`` is digits only, hence
    language-neutral and precomputed once here.

    ``rules`` is the same thing per weekday group, and ``per_day`` says whether
    any group names days — which is what picks between the viewer's two line
    shapes, exactly as it does in the PDF. The flat ``hours``/``hours_display``
    stay the union of every group, so a reader that ignores ``rules`` still sees
    that hours are stated."""
    if op is None:
        return None
    return {
        "days": list(op.days),
        "day_runs": [list(run) for run in op.day_runs],
        "hours": [[f"{o:%H:%M}", f"{c:%H:%M}"] for o, c in op.hours],
        "hours_display": op.hours_display,
        "per_day": op.per_day,
        "rules": [
            {
                "days": list(rule.days),
                "day_runs": [list(run) for run in rule.day_runs],
                "hours": [[f"{o:%H:%M}", f"{c:%H:%M}"] for o, c in rule.hours],
                "hours_display": rule.hours_display,
            }
            for rule in op.rules
        ],
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
        # whether the leg *reaching* this waypoint runs off-road
        "off_road": wp.off_road,
        # The map pin label of this point, when the road asked for pins on its
        # points (Road.display_*_on_maps) and maps were rendered for this build;
        # ``None`` otherwise. Stamped onto the waypoint object by the caller, the
        # same way an activity's is (see the PWA bridge).
        "map_pin": getattr(wp, "_map_pin", None),
        # The leg's recorded track, base64, exactly as it was attached — the one
        # thing the browser needs it for is handing the file back ("(Get GPX
        # track)"). Deliberately *not* wrapped in a `track` object like a hike's:
        # a leg's recording is drawn as the route on the day map, which the map
        # render already carries, so there is no geometry or profile to ship.
        "gpx": wp.gpx or None,
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
        # A stop kept for reference rather than planned: it carries a duration
        # but no clock time (the timeline pass left it out), and both renderers
        # mark it and draw it a step down in emphasis.
        "detour": act.detour,
        # What the stop costs (an entrance fee, a guided visit, a meal) in the
        # same structured shape as a booking's, and who to call about it. Every
        # type carries both, so they sit on the common dict. ``paid`` is always
        # None here: an activity has no payment state (see models/activities.py).
        "price": _price(itin, act.price, act.currency, None),
        "contact": act.contact,
        # Whether this activity draws its **own** map — a place's zoom map, a
        # hike's trail map. On the common dict like ``detour``, so the viewer
        # reads one field wherever it draws one of those; inert on the types
        # that have no map of their own. Not to be confused with
        # ``coordinate.show_on_map``, which hides a *pin* on somebody else's map.
        "show_map": act.show_map,
        **_sched(act, itin.default_timezone),
    }

    if act.kind == "buffer":
        out["auto"] = act.auto

    elif act.kind == "road":
        out.update({
            "start": act.start,
            "destination": act.destination,
            "description": act.description,
            "guidebook_pages": act.guidebook_pages,
            "distance_km": act.distance_km,
            "off_road": act.off_road,
            # which of the drive's own points asked for a numbered pin
            "display_start_on_maps": act.display_start_on_maps,
            "display_end_on_maps": act.display_end_on_maps,
            "display_intermediate_point_on_maps": act.display_intermediate_point_on_maps,
            "waypoints": [_waypoint(w) for w in act.waypoints],
        })

    elif act.kind == "point_of_interest":
        out.update({
            "name": act.name,
            "address": act.address,
            "description": act.description,
            "guidebook_pages": act.guidebook_pages,
            "category": act.category,
            "website": act.website,
            "opening": _opening(act.opening),
        })

    elif act.kind == "place":
        out.update({
            "name": act.name,
            "description": act.description,
            "guidebook_pages": act.guidebook_pages,
        })

    elif act.kind == "hike":
        out.update({
            "name": act.name,
            "description": act.description,
            "guidebook_pages": act.guidebook_pages,
            "distance_km": act.distance_km,
            "elevation_m": act.elevation_m,
            "start": act.start,
            "end": act.end,
            "route": act.route,
            "route_label": act.route_label,
            "track": _track(itin, act),
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

def _transport_leg(itin: Itinerary, leg) -> dict:
    """One leg, **enriched with its booking's shared fields** (type, reference,
    source, links, status, price) so it stands alone wherever a leg is shown
    without its booking around it — a day's itinerary, the night's stay bar, the
    calendar export. The leg-level values come first; everything from
    ``booking_number`` on is the parent's, identical across its legs.

    ``price`` is the **whole booking's**: a renderer that draws it once per leg
    would print a two-leg round trip's fare twice. The day pages don't draw it;
    the transport page draws it once on the booking."""
    return {
        "type": leg.type,
        "title": leg.title,
        "start": leg.start,
        "end": leg.end,
        "start_date": _date(leg.start_date),
        "end_date": _date(leg.end_date),
        "overnight": leg.overnight,
        "end_day_offset": leg.end_day_offset,
        "flight_number": leg.flight_number,
        "train_number": leg.train_number,
        "distance_km": leg.distance_km,
        "description": leg.description,
        "coordinate": _coord(leg.coordinate),
        "start_coordinate": _coord(leg.start_coordinate),
        "end_coordinate": _coord(leg.end_coordinate),
        "leg_index": leg.leg_index,
        "leg_count": leg.leg_count,
        "booking_number": leg.booking_number,
        "booking_source": leg.booking_source,
        "website": leg.website,
        "booking_link": leg.booking_link,
        "status": leg.status,
        "price": _price(itin, leg.price, leg.currency, leg.paid),
        **_sched(leg, itin.default_timezone),
    }


def _transport(itin: Itinerary, t) -> dict:
    """A booking: what was reserved once, plus its legs (always at least one).

    ``name``/``description`` are *not* copied onto the legs (unlike the other
    shared fields): they describe the reservation, and the renderers show them
    where the reservation itself is — the transport section — rather than on a
    day's row, which is about one hop. ``title`` resolves the name for a
    consumer that just wants a heading (the route chain when none is set)."""
    return {
        "type": t.type,
        "name": t.name,
        "title": t.title,
        "route_chain": t.route_chain,
        "description": t.description,
        "start_date": _date(t.start_date),
        "end_date": _date(t.end_date),
        "booking_number": t.booking_number,
        "booking_source": t.booking_source,
        "website": t.website,
        "booking_link": t.booking_link,
        "status": t.status,
        "price": _price(itin, t.price, t.currency, t.paid),
        "legs": [_transport_leg(itin, leg) for leg in t.legs],
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
        "description": a.description,
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
        "description": c.description,
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
        # The rental's note, carried onto both of its events: the day's row is
        # where you read it, and the event has no back-reference to look it up.
        "description": rental.description if rental else "",
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
    # The night's moon phase, unless opted out (defaults.show_moon_phase). The
    # ``key`` is localized by the viewer; ``name`` is the English fallback.
    moon = moon_phase(day.date) if itin.show_moon_phase and day.date else None
    # The day's sunrise/sunset at the night's accommodation, unless switched off
    # (defaults.show_sun_times) or there's no coordinate to compute them for.
    sun = itin.sun_for(day)
    return {
        "day_number": index + 1,
        "title": day.title,
        "date": _date(day.date),
        "city": day.city,
        "description": day.description,
        "bank_holiday": day.bank_holiday,
        # Whether the day draws its overview map. The renderers still receive
        # whatever the map pass produced (its areas, a hike's trail), so this is
        # what tells the viewer the empty main slot is a choice rather than a
        # render still in flight.
        "show_map": day.show_map,
        "activities": [_activity(itin, a) for a in day.activities],
        # Legs, not bookings: a day is moved by hops. Each carries its
        # booking's shared fields (see _transport_leg).
        "transports": [_transport_leg(itin, leg)
                       for leg in itin.transports_on(day.date)],
        "car_events": [_car_event(itin, e) for e in itin.car_events_on(day.date)],
        "stay": _accommodation(itin, stay) if stay else None,
        # 1-based index of this night within the stay (for "Night x/total").
        "stay_night": stay.night_of(day.date) if stay else None,
        "night_transport": _transport_leg(itin, night) if night else None,
        "sleep_city": (stay.city if stay else "") or day.city,
        "moon": {"key": moon.key, "emoji": moon.emoji, "name": moon.name} if moon else None,
        # Just the two clock times: the viewer builds the display string from
        # its own localized template (render/format.ts), as the PDF does.
        "sun": ({"sunrise": sun.sunrise.strftime("%H:%M"),
                 "sunset": sun.sunset.strftime("%H:%M")} if sun else None),
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
        "accommodation_start_time": _time(itinerary.default_accommodation_start_time),
        "accommodation_end_time": _time(itinerary.default_accommodation_end_time),
        "maps": {
            "include_in_render": itinerary.include_maps_in_render,
            # Independent of `include_in_render`: a hike's map comes from the GPX
            # the hike itself carries, not from the trip-wide map inference.
            "include_hike_maps": itinerary.include_hike_maps,
            "infer_from_address": itinerary.infer_coordinates_from_address,
            "inference_countries": list(itinerary.inference_countries),
        },
        # The `misc` group is flattened here the same way `defaults` is: the
        # resolved doc has no use for the grouping, only for the values.
        "emergency_contacts": [
            {"name": c.name, "contact": c.contact}
            for c in itinerary.emergency_contacts
        ],
        "days": [_day(itinerary, i, d) for i, d in enumerate(itinerary.days)],
        "transports": [_transport(itinerary, t) for t in itinerary.transports],
        "accommodations": [
            _accommodation(itinerary, a) for a in itinerary.accommodations
        ],
        "car_rentals": [_car_rental(itinerary, c) for c in itinerary.car_rentals],
    }
