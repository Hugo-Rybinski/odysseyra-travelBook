"""Export a resolved :class:`~.models.Itinerary` as GPX files — one per day plus
one holding the whole trip — for Garmin, Komoot, OsmAnd and any other offline-GPS
app.

**One geometry, two granularities.** The per-day files are what you load the
night before; the trip file is every day's geometry in one document, for an app
that wants the shape of the whole thing. It is exactly the concatenation of the
day files (bar duplicate waypoints, collapsed), so the two can't disagree.

What a day contributes, and why each kind is what it is:

* a ``<wpt>`` per located **stop** — the day's points of interest, places (their
  nested activities included), hikes and meals, plus that night's
  accommodation and the endpoints of any transport leg in progress. Resolved by
  :func:`.maps.build.located_points`, i.e. exactly as the maps resolve them.
* a ``<rte>`` per **leg of a drive**, named for the two places it runs between.
  Per leg rather than per drive because a junction is then named as the end of
  one route and the start of the next — which is where a route's names belong,
  and why a drive's own map pins (``display_*_on_maps``) are not exported as
  waypoints. Computed geometry, hence a route: see :mod:`.models.gpx_export`.
* a ``<trk>`` per **recording** — a hike's ``gpx``, and a road leg's — with the
  hike's own named ``<wpt>``s alongside. Those really were walked or driven, so
  they are tracks; the same file drawn as a route would claim otherwise.

**A transport leg contributes its two endpoints and no line.** The maps draw one
as a dotted straight line precisely because its real path is unknown (a flight
has none on the ground), and the rule this repo already applies to a
crow-flight route holds here too: fine to draw, wrong to export. Same call as
``route(…, fallback=False)`` behind the viewer's *(Build GPX file)*.

Two switches deliberately do **not** apply. ``include_maps_in_render`` is a
*print* choice, and a day's or a place's ``show_map`` drops the map that object
draws — a GPX file is not a map, and asking for this export *is* the opt-in for
geometry. ``defaults.include_hike_maps`` doesn't gate it either, for the same
reason it doesn't gate a road leg's ``gpx``: it keeps hike *figures* out of the
book and their geometry out of the resolved document, whereas geometry is all
this file has. What still hides a point is ``coordinate.hide_on_map``: that says
"don't plot this", which is the nearest thing the format has to "leave it out",
and honouring it is also what keeps the export from drifting from the maps.

Routing and geocoding go through the usual :class:`.maps.Cache`, so a second
export of the same trip costs no network.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from pathlib import Path

from .lang import DEFAULT_LANGUAGE, fmt_date, tr
from .models import Itinerary
from .models.gpx_export import GpxLine, GpxPoint, gpx_document

__all__ = ["gpx_files", "gpx_zip", "write_gpx_files", "slug_for"]

# Everything a zip entry is stamped with. A fixed date keeps two exports of the
# same trip byte-identical, which is what makes the archive diffable and the
# tests able to assert on it; `zipfile` has no "no timestamp" option, and 1980 is
# the earliest the format can express.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def slug_for(title: str) -> str:
    """A filesystem-friendly base name from a trip title.

    Mirrors the viewer's ``file/saveExport.ts``'s ``slugify`` — the archive the
    browser downloads is named there while the files inside it are named here,
    and one trip should read as one name across the two.
    """
    plain = unicodedata.normalize("NFKD", title or "")
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    return slug or "odysseyra"


def _day_label(index: int, day, lang: str) -> str:
    """``Day 3 · Sep 06, 2026 · Renaissance châteaux`` — a waypoint's ``<desc>``
    and a day file's title, the one place the day is named."""
    parts = [tr("Day {n}", lang).format(n=index)]
    if day.date is not None:
        parts.append(fmt_date(day.date, "long", lang))
    if day.title:
        parts.append(day.title)
    return " · ".join(parts)


def _stop_points(day, itinerary, cache, desc: str) -> list[GpxPoint]:
    """A day's located stops, that night's stay and its transport endpoints."""
    # `_leg_coord` is private but is *the* "a transport endpoint honours
    # hide_on_map" rule; re-spelling it here would be the second copy of it.
    from .maps.build import _leg_coord, located_points

    out = [GpxPoint(lat, long, name, desc)
           for name, lat, long in located_points(day, itinerary, cache)]

    stay = itinerary.stay_for(day.date)
    if stay is not None and stay.coordinate is not None and not stay.coordinate.hide_on_map:
        out.append(GpxPoint(stay.coordinate.lat, stay.coordinate.long,
                            stay.name, desc))

    # A leg's endpoints, for every leg in progress on this day — the same window
    # `day_legs` draws its line over, so an overnight leg is named on both of
    # its days. Never geocoded (an endpoint's coordinate is written or absent),
    # and each end stands on its own: a *line* needs both, a waypoint doesn't.
    if day.date is not None:
        for leg in itinerary.legs:
            if leg.start_date is None:
                continue
            if not (leg.start_date <= day.date <= (leg.end_date or leg.start_date)):
                continue
            for coord, name in ((leg.start_coordinate, leg.start),
                                (leg.end_coordinate, leg.end)):
                here = _leg_coord(coord)
                if here and name:
                    out.append(GpxPoint(here[0], here[1], name, desc))
    return out


def _road_lines(day, itinerary, cache, desc: str) -> tuple[list[GpxLine], list[GpxLine]]:
    """``(routes, tracks)`` for the day's drives — one line per leg, a track when
    that leg carries a recording and a route when we computed it."""
    from .maps.build import road_departure, road_leg_lines

    routes: list[GpxLine] = []
    tracks: list[GpxLine] = []
    for act in day.activities:
        if act.kind != "road" or act.hide_on_map:
            continue
        previous = act.start
        for wp, line in road_leg_lines(act, road_departure(act, day, itinerary, cache),
                                       cache):
            if wp is None:  # trailing shaping points, with no arrival to name
                continue
            name = f"{previous} → {wp.location}" if previous else wp.location
            previous = wp.location
            if line and len(line) >= 2:
                recorded = getattr(wp, "track", None) is not None
                (tracks if recorded else routes).append(GpxLine(line, name, desc))
    return routes, tracks


def _hike_tracks(day, desc: str) -> tuple[list[GpxPoint], list[GpxLine]]:
    """A day's recorded trails, and the named points those files carry."""
    points: list[GpxPoint] = []
    tracks: list[GpxLine] = []
    for act in day.activities:
        for hike in [act] + list(getattr(act, "activities", []) or []):
            track = getattr(hike, "track", None) if hike.kind == "hike" else None
            if track is None or len(track.points) < 2:
                continue
            tracks.append(GpxLine(track.points, hike.title, desc))
            points.extend(GpxPoint(w.lat, w.long, w.name, hike.title)
                          for w in track.waypoints)
    return points, tracks


def _dedupe(points: list[GpxPoint]) -> list[GpxPoint]:
    """Drop repeats of the same named point at the same place, keeping the first.

    A day names one spot more than once as a matter of course (the map has
    ``fold_pins`` for the same reason), and across the trip file a hotel booked
    for four nights would otherwise appear four times. Keyed on the position as
    it is *written* — six decimals, the file's own precision.
    """
    seen: set[tuple[str, str, str]] = set()
    out: list[GpxPoint] = []
    for p in points:
        key = (p.name, f"{p.lat:.6f}", f"{p.long:.6f}")
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def gpx_files(itinerary: Itinerary, cache=None,
              lang: str = DEFAULT_LANGUAGE) -> list[tuple[str, str]]:
    """``[(filename, GPX text), …]`` for ``itinerary`` — the whole trip first,
    then one file per day that has any geometry at all.

    A day with nothing located contributes no file rather than an empty one, and
    the days keep their **position** in the numbering, so a missing ``day-03``
    says that day had nothing rather than shifting the rest. An itinerary with no
    geometry anywhere yields an empty list; the callers report that.

    ``cache`` is a :class:`.maps.Cache`; without one a fresh one is opened and
    saved around the call.
    """
    own_cache = cache is None
    if own_cache:
        from .maps import Cache
        cache = Cache.open()

    base = slug_for(itinerary.title)
    files: list[tuple[str, str]] = []
    all_points: list[GpxPoint] = []
    all_routes: list[GpxLine] = []
    all_tracks: list[GpxLine] = []

    for index, day in enumerate(itinerary.days, start=1):
        desc = _day_label(index, day, lang)
        points = _stop_points(day, itinerary, cache, desc)
        routes, tracks = _road_lines(day, itinerary, cache, desc)
        hike_points, hike_tracks = _hike_tracks(day, desc)
        points += hike_points
        tracks += hike_tracks

        points = _dedupe(points)
        all_points += points
        all_routes += routes
        all_tracks += tracks
        if not (points or routes or tracks):
            continue
        files.append((
            f"{base}-day-{index:02d}.gpx",
            gpx_document(f"{itinerary.title} — {desc}", waypoints=points,
                         routes=routes, tracks=tracks),
        ))

    if own_cache:
        try:
            cache.save()
        except OSError:
            pass

    if not files:
        return []
    trip = gpx_document(itinerary.title, waypoints=_dedupe(all_points),
                        routes=all_routes, tracks=all_tracks)
    return [(f"{base}.gpx", trip)] + files


def write_gpx_files(itinerary: Itinerary, directory: Path | str, cache=None,
                    lang: str = DEFAULT_LANGUAGE) -> list[Path]:
    """Write :func:`gpx_files` into ``directory`` (created if missing) and return
    the paths, in the order they were written."""
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in gpx_files(itinerary, cache, lang):
        path = out / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def gpx_zip(itinerary: Itinerary, cache=None,
            lang: str = DEFAULT_LANGUAGE) -> bytes:
    """:func:`gpx_files` as a flat ``.zip`` — the archive the viewer downloads.

    Flat, and named exactly as :func:`write_gpx_files` names them, so unzipping
    it gives the same set of files the CLI's ``gpx`` command produces. Raises
    :class:`ValueError` when the trip has no geometry to export: an empty archive
    looks like a broken download rather than an answer.
    """
    files = gpx_files(itinerary, cache, lang)
    if not files:
        raise ValueError("nothing to export: no coordinates on this trip")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in files:
            info = zipfile.ZipInfo(name, _ZIP_EPOCH)
            # A ZipInfo carries its own compression, and its default is STORED —
            # the archive's mode doesn't reach it.
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text)
    return buffer.getvalue()
