"""Translation tables. English is the source language (identity); each other
language maps English source strings (templates keep their ``{placeholders}``)
to their translation."""

_FR = {
    # -- PDF: cover & overview --
    "Dates": "Dates",
    "Days": "Jours",
    "Day by day": "Jour par jour",
    "Jump to": "Aller à",
    "DAY": "JOUR",
    "DATE": "DATE",
    "HIGHLIGHTS": "TEMPS FORTS",
    "SLEEP": "NUIT",
    "DAY {index}": "JOUR {index}",
    "Itinerary": "Itinéraire",
    "Zoom — {area}": "Zoom — {area}",
    "Day {index} overview": "Aperçu du jour {index}",
    # the whole-trip map page's band (the viewer's Overview map says the same —
    # the `tripMapCaption` key in web/src/render/format.ts)
    "MAP": "CARTE",
    "Whole trip": "L'ensemble du voyage",
    # a hike's GPX block: the trail map's caption and the elevation profile's
    # header. The viewer fills the same three templates from its own table —
    # the `hikeMapCaption` / `hikeProfile` / `hikeAscent` / `hikeDescent` keys in
    # web/src/render/format.ts — so the two wordings must move together.
    "Trail — {name}": "Tracé — {name}",
    "Elevation profile": "Profil altimétrique",
    "↑ {m} m": "↑ {m} m",
    "↓ {m} m": "↓ {m} m",
    "Geocoded {filled} coordinate(s), {missed} not found → {path}":
        "{filled} coordonnée(s) géocodée(s), {missed} introuvable(s) → {path}",
    "this area has no 'coordinate' of its own — its map pin will be placed at "
    "the average position of its located sub-activities.":
        "cette zone n'a pas de 'coordinate' propre — son point sur la carte sera "
        "placé à la position moyenne de ses sous-activités localisées.",
    # -- PDF: activity badges & labels --
    "ROAD": "ROUTE",
    "POINT": "POINT",
    "PLACE": "LIEU",
    "HIKE": "RANDO",
    "MEAL": "REPAS",
    "TRANSPORT": "TRANSPORT",
    "OFF-ROAD SECTIONS": "SECTIONS HORS-ROUTE",
    # the same flag as a small pill on a single VIA leg's row
    "OFF-ROAD": "HORS-ROUTE",
    "VIA": "VIA",
    # the grey pill leading a detour's title — a stop kept for reference rather
    # than planned (the viewer mirrors it as the `detour` key in
    # render/format.ts, shown in the gutter; keep the two wordings in step)
    "OPTIONAL DETOUR": "DÉTOUR OPTIONNEL",
    # an activity's guidebook page reference, drawn in a lightened accent under
    # its description (the viewer mirrors this template in render/format.ts)
    "Guidebook p. {pages}": "Guide p. {pages}",
    "arrival": "arrivée",
    "OVERNIGHT": "DE NUIT",
    "INCLUDES": "COMPREND",
    "buffer": "pause",
    # meal types (from Meal.category) and the meal row head
    "breakfast": "petit-déjeuner",
    "lunch": "déjeuner",
    "dinner": "dîner",
    "brunch": "brunch",
    "snack": "collation",
    "picnic": "pique-nique",
    "meal": "repas",
    "{meal} at {restaurant}": "{meal} chez {restaurant}",
    "{meal} near {area}": "{meal} près de {area}",
    # route labels (from Hike.route_label)
    "Loop": "Boucle",
    "Back and forth": "Aller-retour",
    "One way": "Aller simple",
    # point-of-interest categories (badge + nested lists)
    "museum": "musée",
    "church": "église",
    "building": "bâtiment",
    "viewpoint": "point de vue",
    "ruins": "ruines",
    "castle": "château",
    "temple": "temple",
    "street": "rue",
    "natural park": "parc naturel",
    "mountain": "montagne",
    # The badge is uppercased and clipped to 14 characters, so "COL DE MONTAGNE"
    # would lose its last letter — "col" is what a map legend says anyway.
    "mountain pass": "col",
    "lake": "lac",
    "beach": "plage",
    "waterfall": "cascade",
    "canyon": "canyon",
    "spring": "source",
    "market": "marché",
    "other": "autre",
    # -- PDF: transport --
    "GETTING AROUND": "SE DÉPLACER",
    "Transport": "Transport",
    "Ref {ref}": "Réf {ref}",
    # the badge on each leg of a multi-leg booking (the viewer mirrors this
    # template in render/format.ts's `leg` key — keep the two wordings in step)
    "Leg {n}": "Trajet {n}",
    "Flight {number}": "Vol {number}",
    "Train {number}": "Train {number}",
    "Booked via {source}": "Réservé via {source}",
    "Website": "Site web",
    "Reservation": "Réservation",
    "(Navigate)": "(S'y rendre)",
    "BOOKED": "RÉSERVÉ",
    "CONFIRMED": "CONFIRMÉ",
    "PAID": "PAYÉ",
    "TO PAY": "À PAYER",
    # -- PDF: accommodation --
    "WHERE YOU'LL STAY": "OÙ VOUS DORMEZ",
    "Accommodation": "Hébergement",
    "✓  Breakfast included": "✓  Petit-déjeuner inclus",
    "TONIGHT'S STAY": "CETTE NUIT",
    "Night {night}/{total} here": "Nuit {night}/{total} ici",
    "on board": "à bord",
    # The day header band's sun times (show_sun_times). French keeps the labels
    # short — the full "Lever du soleil / Coucher du soleil" all but touches the
    # kicker on the longest day.
    "☀️ Sunrise: {sunrise}, Sunset: {sunset}": "☀️ Lever : {sunrise}, Coucher : {sunset}",
    # …and the same line closed by the night's moon phase, used when
    # show_moon_phase is on too. `{moon}` arrives already localized.
    "☀️ Sunrise: {sunrise}, Sunset: {sunset}, {emoji} {moon}":
        "☀️ Lever : {sunrise}, Coucher : {sunset}, {emoji} {moon}",
    # The bank-holiday call-out strip opening a day (day 'bank_holiday'). The
    # label is uppercase like the band's kicker; the ⚠️ is added by the renderer.
    "BANK HOLIDAY": "JOUR FÉRIÉ",
    "Expect closures and reduced opening hours.":
        "Attendez-vous à des fermetures et à des horaires réduits.",
    # A point of interest's opening days/hours (poi 'opening_days' /
    # 'opening_hours'): the label leading the row, and the same word as an ICS
    # detail line. The weekday names come localized from lang/dates.py, and the
    # hours are digits only — so this is the only string to translate.
    "Open": "Ouvert",
    # An activity's fee: what a zero price reads as (a stated free entry is
    # information, not an absent price) — the viewer's `free` key mirrors it.
    # "Contact" is further down, shared with the accommodation card's label.
    "Free": "Gratuit",
    # Moon phases (in that line, or in the "tonight" section when the sun times
    # are off or don't fit).
    "New moon": "Nouvelle lune",
    "Waxing crescent": "Premier croissant",
    "First quarter": "Premier quartier",
    "Waxing gibbous": "Lune gibbeuse croissante",
    "Full moon": "Pleine lune",
    "Waning gibbous": "Lune gibbeuse décroissante",
    "Last quarter": "Dernier quartier",
    "Waning crescent": "Dernier croissant",
    "Overnight {type}": "{type} de nuit",
    "Overnight travel": "Trajet de nuit",
    "Road": "Route",
    "{nights} night": "{nights} nuit",
    "{nights} nights": "{nights} nuits",
    # -- PDF: car rentals --
    "Car rentals": "Location de voiture",
    "Car rental": "Location de voiture",
    "Pick-up": "Pick-up",
    "Drop-off": "Drop-off",
    "Booked {start} → {end}": "Réservé {start} → {end}",
    "Booked from {start}": "Réservé à partir de {start}",
    "PICK-UP": "PICK-UP",
    "DROP-OFF": "DROP-OFF",
    "Pick up the rental car": "Retrait de la voiture de location",
    "Drop off the rental car": "Restitution de la voiture de location",
    "{n} additional driver": "{n} conducteur supplémentaire",
    "{n} additional drivers": "{n} conducteurs supplémentaires",
    "Regular": "Standard",
    "Small": "Petite",
    "SUV": "SUV",
    "4x4": "4x4",
    # -- PDF: emergency contacts (the `misc` group) --
    # The band's kicker and title on the book's last page, plus the cover's
    # "Jump to" shortcut to it — which is why that one is a single short word.
    "IN CASE OF EMERGENCY": "EN CAS D'URGENCE",
    "Emergency contacts": "Numéros d'urgence",
    "Emergency": "Urgences",
    # -- validation: message templates --
    "required field '{name}' is missing — {description}. Expected {expected}.":
        "champ obligatoire « {name} » manquant — {description}. Attendu : {expected}.",
    "optional field '{name}' is missing — {description}. Expected {expected}. "
    "Defaulting to {default}.":
        "champ optionnel « {name} » manquant — {description}. Attendu : "
        "{expected}. Valeur par défaut : {default}.",
    "field '{name}' is invalid ({value}) — {description}. Expected {expected} "
    "({error}).":
        "champ « {name} » invalide ({value}) — {description}. Attendu : "
        "{expected} ({error}).",
    "the top-level JSON must be an object":
        "le JSON de premier niveau doit être un objet",
    "required field 'days' is missing or empty — the list of days. Expected a "
    "non-empty array of day objects.":
        "champ obligatoire « days » manquant ou vide — la liste des jours. "
        "Attendu : un tableau non vide d'objets jour.",
    "optional field 'transport' is missing — the transport bookings. Expected "
    "an array of transport objects, each with its 'legs'. Defaulting to [] (no "
    "transport page).":
        "champ optionnel « transport » manquant — les réservations de transport. "
        "Attendu : un tableau d'objets transport, chacun avec ses « legs ». "
        "Valeur par défaut : [] (pas de page transport).",
    "optional field 'accommodations' is missing — the places you stay. Expected "
    "an array of accommodation objects. Defaulting to [] (no accommodation "
    "page).":
        "champ optionnel « accommodations » manquant — les hébergements. "
        "Attendu : un tableau d'objets hébergement. Valeur par défaut : [] "
        "(pas de page hébergement).",
    "each day must be an object": "chaque jour doit être un objet",
    "a day's 'activities' must not be empty — every day needs at least one "
    "activity.":
        "le champ « activities » d'un jour ne doit pas être vide — chaque jour "
        "a besoin d'au moins une activité.",
    "each activity must be an object with a 'type'":
        "chaque activité doit être un objet avec un « type »",
    "a nested activity must be an object with a 'type' of one of: {allowed}.":
        "une activité imbriquée doit être un objet avec un « type » parmi : "
        "{allowed}.",
    "a nested activity 'type' must be one of: {allowed} (got {kind}).":
        "le « type » d'une activité imbriquée doit être l'un de : {allowed} "
        "(reçu {kind}).",
    "a nested activity can't contain its own nested activities — nesting is "
    "only one level deep.":
        "une activité imbriquée ne peut pas contenir ses propres activités "
        "imbriquées — l'imbrication ne va que d'un niveau.",
    "required field 'type' is missing — the activity type. Expected one of: "
    "{kinds}.":
        "champ obligatoire « type » manquant — le type d'activité. Attendu : "
        "l'un de {kinds}.",
    "field 'type' is invalid ({kind}) — the activity type. Expected one of: "
    "{kinds}.":
        "champ « type » invalide ({kind}) — le type d'activité. Attendu : "
        "l'un de {kinds}.",
    "this is a zero-minute buffer — it only suppresses the trip's default "
    "buffer here and draws no line.":
        "pause de zéro minute — elle supprime seulement la pause par défaut "
        "ici et n'affiche aucune ligne.",
    "a '{route}' hike returns to its start, but 'end' ({end}) differs from "
    "'start' ({start}) — set 'end' to the start, or omit it.":
        "une randonnée « {route} » revient à son point de départ, mais « end » "
        "({end}) diffère de « start » ({start}) — mettez « end » égal au départ, "
        "ou omettez-le.",
    "a 'one_way' hike should have an 'end' that differs from its 'start'.":
        "une randonnée « one_way » devrait avoir un « end » différent de son "
        "« start ».",
    "both 'restaurant' and 'area' are set — 'area' is ignored when a restaurant "
    "is named.":
        "« restaurant » et « area » sont tous deux définis — « area » est ignoré "
        "lorsqu'un restaurant est nommé.",
    "field '{name}' is invalid ({value}) — {error}.":
        "champ « {name} » invalide ({value}) — {error}.",
    "'legs' must be an array of {start_location, end_location, duration, "
    "distance_km, off_road, waypoints} objects — one per hop of the drive.":
        "« legs » doit être un tableau d'objets {start_location, end_location, "
        "duration, distance_km, off_road, waypoints} — un par étape du trajet.",
    "a road needs at least one 'leg' — the hop from its departure to its "
    "arrival.":
        "une route a besoin d'au moins une étape dans « legs » — celle qui va "
        "de son départ à son arrivée.",
    "each road leg must be an object with a 'start_location' and an "
    "'end_location' (and their coordinates).":
        "chaque étape de route doit être un objet avec un « start_location » et "
        "un « end_location » (et leurs coordonnées).",
    "'waypoints' must be an array of {lat, long} coordinates, in order from the "
    "leg's start to its end.":
        "« waypoints » doit être un tableau de coordonnées {lat, long}, dans "
        "l'ordre du départ de l'étape vers son arrivée.",
    "each of a leg's 'waypoints' must be a coordinate with a 'lat' and a "
    "'long' ({error}).":
        "chaque « waypoints » d'une étape doit être une coordonnée avec un "
        "« lat » et un « long » ({error}).",
    "this leg departs from {here} but the previous one arrives at {there} — a "
    "drive can't jump between the two, and it is the previous leg's "
    "'end_location' that is used.":
        "cette étape part de {here} alors que la précédente arrive à {there} — "
        "un trajet ne peut pas sauter de l'un à l'autre, et c'est le "
        "« end_location » de l'étape précédente qui est utilisé.",
    "this leg's 'start_coordinate' is a kilometre or more from the previous "
    "leg's 'end_coordinate' — a drive can't jump between the two, and it is the "
    "previous leg's that is used.":
        "le « start_coordinate » de cette étape est à un kilomètre ou plus du "
        "« end_coordinate » de l'étape précédente — un trajet ne peut pas sauter "
        "de l'un à l'autre, et c'est celui de l'étape précédente qui est "
        "utilisé.",
    "'same_start_as_previous_activity' is set on the day's first activity — "
    "there is no previous activity to take the departure from.":
        "« same_start_as_previous_activity » est activé sur la première activité "
        "de la journée — il n'y a pas d'activité précédente d'où prendre le "
        "départ.",
    "'same_start_as_previous_activity' is set, but the previous activity "
    "({other}) names no place to depart from — give it a name, or the first leg "
    "a 'start_location'.":
        "« same_start_as_previous_activity » est activé, mais l'activité "
        "précédente ({other}) ne nomme aucun lieu de départ — donnez-lui un nom, "
        "ou donnez un « start_location » à la première étape.",
    "'display_start_on_maps' adds nothing here: "
    "'same_start_as_previous_activity' is on, so the departure wears the "
    "previous activity's own pin rather than a second number for the same "
    "place.":
        "« display_start_on_maps » n'ajoute rien ici : "
        "« same_start_as_previous_activity » est activé, donc le départ porte "
        "l'épingle de l'activité précédente plutôt qu'un second numéro pour le "
        "même lieu.",
    "'same_end_as_next_activity' is set on the day's last activity — there is "
    "no next activity to take the arrival from.":
        "« same_end_as_next_activity » est activé sur la dernière activité de la "
        "journée — il n'y a pas d'activité suivante d'où prendre l'arrivée.",
    "'same_end_as_next_activity' is set, but the next activity ({other}) names "
    "no place to arrive at — give it a name, or the last leg an 'end_location'.":
        "« same_end_as_next_activity » est activé, mais l'activité suivante "
        "({other}) ne nomme aucun lieu d'arrivée — donnez-lui un nom, ou donnez "
        "un « end_location » à la dernière étape.",
    "'same_end_as_next_activity' is set, but the next activity ({other}) has no "
    "'coordinate' — a drive's arrival is a point on its route, so it has to be "
    "located. Give that activity a coordinate, or the last leg an "
    "'end_coordinate'.":
        "« same_end_as_next_activity » est activé, mais l'activité suivante "
        "({other}) n'a pas de « coordinate » — l'arrivée d'un trajet est un "
        "point de son itinéraire, elle doit donc être localisée. Donnez une "
        "coordonnée à cette activité, ou un « end_coordinate » à la dernière "
        "étape.",
    "'display_end_on_maps' adds nothing here: 'same_end_as_next_activity' is "
    "on, so the arrival wears the next activity's own pin rather than a second "
    "number for the same place.":
        "« display_end_on_maps » n'ajoute rien ici : "
        "« same_end_as_next_activity » est activé, donc l'arrivée porte "
        "l'épingle de l'activité suivante plutôt qu'un second numéro pour le "
        "même lieu.",
    "field '{name}' is no longer read on a road — {where}.":
        "le champ « {name} » n'est plus lu sur une route — {where}.",
    "move it to the first leg's 'start_location'":
        "déplacez-le dans le « start_location » de la première étape",
    "move it to the first leg's 'start_coordinate'":
        "déplacez-le dans le « start_coordinate » de la première étape",
    "the drive's stops are its legs now: one leg per hop, its arrival in "
    "'end_location' / 'end_coordinate', and any route-shaping points in that "
    "leg's own 'waypoints'":
        "les arrêts du trajet sont désormais ses étapes : une étape par tronçon, "
        "son arrivée dans « end_location » / « end_coordinate », et les points "
        "qui dessinent l'itinéraire dans les « waypoints » de cette étape",
    "set it on each leg that runs off-road (the drive counts as off-road when "
    "every one of its legs does)":
        "indiquez-le sur chaque étape hors-route (le trajet n'est hors-route que "
        "si toutes ses étapes le sont)",
    "the legs last {total} in total, longer than the road's own {parent} — the "
    "leg times don't fit the drive.":
        "les étapes durent {total} au total, plus que la durée de la route "
        "({parent}) — les durées des étapes ne tiennent pas dans le trajet.",
    "the nested activities last {total} in total, longer than this activity's "
    "{parent} — they can't all fit inside it.":
        "les activités imbriquées durent {total} au total, plus que la durée de "
        "cette activité ({parent}) — elles ne peuvent pas toutes y tenir.",
    "a point of interest must be an object or a name string":
        "un point d'intérêt doit être un objet ou une chaîne de caractères",
    "each transport must be an object": "chaque transport doit être un objet",
    "leg end_date ({ed}) is before start_date ({sd}).":
        "la date d'arrivée du trajet ({ed}) est avant la date de départ ({sd}).",
    "each transport leg must be an object":
        "chaque trajet de transport doit être un objet",
    "'legs' must be an array of {start, end, start_date, start_time, …} objects "
    "— one per hop.":
        "« legs » doit être un tableau d'objets {start, end, start_date, "
        "start_time, …} — un par trajet.",
    "a transport needs at least one leg in 'legs' — a single-hop booking is a "
    "one-entry array.":
        "un transport nécessite au moins un trajet dans « legs » — une "
        "réservation directe est un tableau d'une entrée.",
    "field '{name}' belongs on a transport leg, not on the booking — move it "
    "into 'legs', where the model reads it.":
        "le champ « {name} » appartient à un trajet, pas à la réservation — "
        "déplacez-le dans « legs », où le modèle le lit.",
    "field '{name}' belongs on the transport booking, not on a leg — one "
    "reservation covers every leg, so move it up.":
        "le champ « {name} » appartient à la réservation, pas à un trajet — une "
        "seule réservation couvre tous les trajets, remontez-le.",
    "'flight_number' is set but the transport type is '{type}', not 'plane'.":
        "« flight_number » est défini mais le type de transport est « {type} », "
        "pas « plane ».",
    "'train_number' is set but the transport type is '{type}', not 'train'.":
        "« train_number » est défini mais le type de transport est « {type} », "
        "pas « train ».",
    "'status' is set but 'booking_number' is missing — a confirmed/booked leg "
    "usually has a reference.":
        "« status » est défini mais « booking_number » manque — un trajet "
        "réservé/confirmé a en général une référence.",
    "'paid' is set but 'price' is missing — the payment state is given without "
    "an amount.":
        "« paid » est défini mais « price » manque — l'état de paiement est "
        "donné sans montant.",
    "each accommodation must be an object":
        "chaque hébergement doit être un objet",
    "accommodation departure ({dep}) must be after arrival ({arr}).":
        "le départ de l'hébergement ({dep}) doit être après l'arrivée ({arr}).",
    "'status' is set but 'booking_source' is missing — a confirmed/booked stay "
    "usually has a reference.":
        "« status » est défini mais « booking_source » manque — un séjour "
        "réservé/confirmé a en général une référence.",
    # the `misc` group and its emergency contacts
    "'misc' must be an object holding 'emergency_contacts'.":
        "« misc » doit être un objet contenant « emergency_contacts ».",
    "'emergency_contacts' must be an array of objects, each with a 'name' and a "
    "'contact'.":
        "« emergency_contacts » doit être un tableau d'objets, chacun avec un "
        "« name » et un « contact ».",
    "each emergency contact must be an object with a 'name' and a 'contact'.":
        "chaque numéro d'urgence doit être un objet avec un « name » et un "
        "« contact ».",
    "this emergency contact is empty — give it a 'name', a 'contact', or both, "
    "or drop it.":
        "ce numéro d'urgence est vide — donnez-lui un « name », un « contact », "
        "ou les deux, ou supprimez-le.",
    "'secondary_currencies' must be an array of {currency, change_rate} "
    "objects.":
        "« secondary_currencies » doit être un tableau d'objets "
        "{currency, change_rate}.",
    "each secondary currency must be an object with a 'currency' and a "
    "'change_rate'.":
        "chaque devise secondaire doit être un objet avec « currency » et "
        "« change_rate ».",
    "a secondary currency needs a 'currency' (a 3-letter ISO code like 'USD').":
        "une devise secondaire a besoin d'un « currency » (un code ISO à 3 "
        "lettres comme « USD »).",
    "field 'currency' is invalid ({value}) — {error}.":
        "champ « currency » invalide ({value}) — {error}.",
    "a secondary currency needs a 'change_rate' (units of it per 1 unit of the "
    "default).":
        "une devise secondaire a besoin d'un « change_rate » (unités de cette "
        "devise pour 1 unité de la devise par défaut).",
    "field 'change_rate' is invalid ({value}) — must be a number.":
        "champ « change_rate » invalide ({value}) — doit être un nombre.",
    "change_rate must be a positive number (got {value}).":
        "change_rate doit être un nombre positif (reçu {value}).",
    "price currency '{cur}' is neither the default currency ({default}) nor a "
    "declared secondary currency — add it to defaults.secondary_currencies or "
    "use a known currency.":
        "la devise du prix « {cur} » n'est ni la devise par défaut ({default}) "
        "ni une devise secondaire déclarée — ajoutez-la à "
        "defaults.secondary_currencies ou utilisez une devise connue.",
    "optional field 'car_rentals' is missing — the rental-car bookings. "
    "Expected an array of car rental objects. Defaulting to [] (no car rental "
    "page).":
        "champ optionnel « car_rentals » manquant — les locations de voiture. "
        "Attendu : un tableau d'objets location de voiture. Valeur par défaut : "
        "[] (pas de page location).",
    "each car rental must be an object":
        "chaque location de voiture doit être un objet",
    "car rental booking end ({end}) must be after booking start ({start}).":
        "la fin de réservation de la location ({end}) doit être après le début "
        "de réservation ({start}).",
    "car rental pick-up ({pu}) is outside the booking period ({start} → {end}).":
        "le retrait de la location ({pu}) est hors de la période de réservation "
        "({start} → {end}).",
    "car rental drop-off ({do}) is outside the booking period "
    "({start} → {end}).":
        "la restitution de la location ({do}) est hors de la période de "
        "réservation ({start} → {end}).",
    "car rental drop-off ({do}) is before the pick-up ({pu}).":
        "la restitution de la location ({do}) est avant le retrait ({pu}).",
    "the car rental pick-up ({time}) overlaps an activity or transport on "
    "{date}.":
        "le retrait de la location ({time}) chevauche une activité ou un "
        "transport le {date}.",
    "the car rental drop-off ({time}) overlaps an activity or transport on "
    "{date}.":
        "la restitution de la location ({time}) chevauche une activité ou un "
        "transport le {date}.",
    "distance_km must be a positive number (got {value}).":
        "distance_km doit être un nombre positif (reçu {value}).",
    "duration must be a positive length (got {value}).":
        "la durée doit être positive (reçu {value}).",
    "start time, end time and duration are incompatible — the three don't "
    "agree. Provide only two of start_time / end_time / duration, or make them "
    "consistent.":
        "heure de début, heure de fin et durée incompatibles — les trois ne "
        "concordent pas. Ne renseignez que deux de start_time / end_time / "
        "duration, ou rendez-les cohérents.",
    "this activity ends at {end}, after the day's end_time ({day_end}).":
        "cette activité se termine à {end}, après l'heure de fin de journée "
        "({day_end}).",
    # A point of interest visited when it's shut (poi 'opening_days' /
    # 'opening_hours'). {weekday} and {days} arrive already localized; {hours} is
    # digits only.
    "this visit falls on a {weekday}, but '{name}' only opens {days} — it will "
    "be closed.":
        "cette visite tombe un {weekday}, alors que « {name} » n'ouvre que "
        "{days} — ce sera fermé.",
    "this visit ({visit}) falls outside the opening hours of '{name}' "
    "({hours}).":
        "cette visite ({visit}) est en dehors des horaires d'ouverture de "
        "« {name} » ({hours}).",
    "Invalid opening_days {value}, expected weekday names like 'tue-sun', "
    "'monday, thursday' or 'mon-fri, sun'":
        "opening_days invalide {value}, attendu des noms de jours comme "
        "« tue-sun », « monday, thursday » ou « mon-fri, sun »",
    "Invalid opening_hours {value}, expected time ranges like '09:30-18:00' "
    "or '09:30-12:30, 14:00-18:00', optionally per weekday as "
    "'mon-sat 09:00-17:00; sun 10:00-17:00'":
        "opening_hours invalide {value}, attendu des plages horaires comme "
        "« 09:30-18:00 » ou « 09:30-12:30, 14:00-18:00 », éventuellement par "
        "jour sous la forme « mon-sat 09:00-17:00; sun 10:00-17:00 »",
    "opening_hours {value} has two groups with no weekdays — only one can be "
    "the default for the days nothing else names":
        "opening_hours {value} a deux groupes sans jours — un seul peut servir "
        "de valeur par défaut pour les jours que rien d'autre ne nomme",
    "opening_hours {value} names {day} twice — a day can only have one set of "
    "hours":
        "opening_hours {value} nomme {day} deux fois — un jour ne peut avoir "
        "qu'une seule plage d'horaires",
    "opening_hours range {value} opens and closes at the same time — give the "
    "closing time, or drop the range":
        "la plage opening_hours {value} ouvre et ferme à la même heure — "
        "indiquez l'heure de fermeture, ou retirez la plage",
    "trip end_date ({ed}) is before start_date ({sd}).":
        "la date de fin du voyage ({ed}) est avant la date de début ({sd}).",
    "day date {d} is duplicated (also on day {other}).":
        "la date du jour {d} est en double (aussi au jour {other}).",
    "day date {d} is earlier than the previous day ({prev}) — days should be "
    "in chronological order.":
        "la date du jour {d} est antérieure au jour précédent ({prev}) — les "
        "jours doivent être dans l'ordre chronologique.",
    "trip start_date ({sd}) is after the first day ({first}) — the range "
    "doesn't cover the trip.":
        "la date de début ({sd}) est après le premier jour ({first}) — "
        "l'intervalle ne couvre pas le voyage.",
    "trip end_date ({ed}) is before the last day ({last}) — the range doesn't "
    "cover the trip.":
        "la date de fin ({ed}) est avant le dernier jour ({last}) — "
        "l'intervalle ne couvre pas le voyage.",
    "day date {d} is outside the trip range ({sd} → {ed}).":
        "la date du jour {d} est hors de l'intervalle du voyage ({sd} → {ed}).",
    "accommodation {key} {d} is outside the trip range ({sd} → {ed}).":
        "la date {key} de l'hébergement {d} est hors de l'intervalle du voyage "
        "({sd} → {ed}).",
    "transport {key} {d} is outside the trip range ({sd} → {ed}).":
        "la date {key} du transport {d} est hors de l'intervalle du voyage "
        "({sd} → {ed}).",
    "accommodations {n1} and {n2} overlap on the same night(s) — you can only "
    "sleep in one place.":
        "les hébergements {n1} et {n2} se chevauchent sur la ou les mêmes "
        "nuits — vous ne pouvez dormir qu'à un seul endroit.",
    "the night of {d} has both an accommodation and an overnight transport — "
    "using the accommodation.":
        "la nuit du {d} a à la fois un hébergement et un transport de nuit — "
        "l'hébergement est retenu.",
    "the night of {d} has no accommodation and no overnight transport — you "
    "have nowhere to sleep.":
        "la nuit du {d} n'a ni hébergement ni transport de nuit — vous n'avez "
        "nulle part où dormir.",
    "the day's city ({day_city}) doesn't match the accommodation city "
    "({acc_city}).":
        "la ville du jour ({day_city}) ne correspond pas à la ville de "
        "l'hébergement ({acc_city}).",
    "this overlaps an earlier item on the day's timeline — their start/end "
    "times collide.":
        "cet élément chevauche un élément précédent dans la journée — leurs "
        "heures de début/fin se croisent.",
    "the day's activities run past midnight — the schedule doesn't fit in a "
    "single day.":
        "les activités du jour dépassent minuit — le programme ne tient pas "
        "en une seule journée.",
    "this activity ({name}) has no duration and none can be inferred from its "
    "start/end times — add a 'duration', or a 'start_time' and 'end_time'.":
        "cette activité ({name}) n'a pas de durée et aucune ne peut être déduite "
        "de ses horaires — ajoutez « duration », ou « start_time » et « end_time ».",
    "this road ({route}) should give a duration and a 'distance_km' — "
    "missing: {missing}.":
        "cette route ({route}) devrait indiquer une durée et « distance_km » — "
        "manquant : {missing}.",
    "this road's leg ({route}) should give a duration and a 'distance_km' — "
    "missing: {missing}.":
        "l'étape de cette route ({route}) devrait indiquer une durée et "
        "« distance_km » — manquant : {missing}.",
    "this GPX carries no elevations — the trail map is drawn, but not the "
    "elevation profile.":
        "ce GPX ne contient pas d'altitudes — le tracé est dessiné, mais pas le "
        "profil altimétrique.",
    "'include_hike_maps' is off, so this GPX is parsed but neither the trail "
    "map nor the profile is drawn.":
        "« include_hike_maps » est désactivé : ce GPX est bien lu, mais ni le "
        "tracé ni le profil ne sont dessinés.",
    "'gpx' must be a base64 string holding a GPX file":
        "« gpx » doit être une chaîne base64 contenant un fichier GPX",
    "'gpx' is empty — expected a base64-encoded GPX file":
        "« gpx » est vide — un fichier GPX encodé en base64 est attendu",
    "'gpx' does not decode as UTF-8 text — is it really a GPX file?":
        "« gpx » ne se décode pas en texte UTF-8 — est-ce bien un fichier GPX ?",
    "'gpx' holds no track — expected at least two <trkpt>, <rtept> or <wpt> "
    "points with lat/lon":
        "« gpx » ne contient aucune trace — au moins deux points <trkpt>, "
        "<rtept> ou <wpt> avec lat/lon sont attendus",
    "'gpx' is not valid base64 ({detail}) — encode the .gpx file with base64":
        "« gpx » n'est pas du base64 valide ({detail}) — encodez le fichier .gpx "
        "en base64",
    "'gpx' is gzip data but won't inflate ({detail})":
        "« gpx » est un flux gzip mais ne se décompresse pas ({detail})",
    "'gpx' is not parseable XML ({detail})":
        "« gpx » n'est pas du XML analysable ({detail})",
    "this hike ({name}) should give a duration, a 'distance_km' and an "
    "'elevation_m' — missing: {missing}.":
        "cette randonnée ({name}) devrait indiquer une durée, « distance_km » et "
        "« elevation_m » — manquant : {missing}.",
    "this leg has no duration and none can be inferred from its start/end "
    "times — add a 'duration', or an 'end_time'.":
        "ce trajet n'a pas de durée et aucune ne peut être déduite de ses "
        "horaires — ajoutez « duration » ou « end_time ».",
    "invalid JSON — {error}": "JSON invalide — {error}",
    # -- validation: summary & CLI --
    "No problems found.": "Aucun problème trouvé.",
    "{errors} error(s), {warnings} warning(s), {infos} info":
        "{errors} erreur(s), {warnings} avertissement(s), {infos} info",
    "{count} warning(s)": "{count} avertissement(s)",
    "{count} info": "{count} info",
    " — {hidden} hidden (raise --verbose)":
        " — {hidden} masqué(s) (augmentez --verbose)",
    "Validation errors (building anyway):":
        "Erreurs de validation (génération quand même) :",
    "Validating {n} fragment file(s):":
        "Validation de {n} fichier(s) fragment :",
    "Validating the assembled itinerary:":
        "Validation de l'itinéraire assemblé :",
    "this fragment must be a JSON object.":
        "ce fragment doit être un objet JSON.",
    "Wrote {path}  ({days} days)": "Écrit {path}  ({days} jours)",
    # -- validation: field descriptions --
    "the trip title shown on the cover": "le titre du voyage sur la couverture",
    "the subtitle under the cover title": "le sous-titre sous le titre",
    "the trip start date (overrides inference)":
        "la date de début du voyage (remplace l'inférence)",
    "the trip end date (overrides inference)":
        "la date de fin du voyage (remplace l'inférence)",
    "the accent color for the whole document":
        "la couleur d'accent de tout le document",
    "a paragraph shown on the cover": "un paragraphe affiché sur la couverture",
    "the day's default start time (first activity)":
        "l'heure de début par défaut de la journée (première activité)",
    "the time each day's last activity should end at":
        "l'heure à laquelle la dernière activité de chaque journée doit finir",
    "whether to size the buffers between a day's activities so the day ends on "
    "'end_time'":
        "s'il faut dimensionner les pauses entre les activités d'une journée pour "
        "qu'elle finisse à « end_time »",
    "a fixed buffer inserted between consecutive activities (ignored when "
    "'auto_sized_buffer' is on)":
        "une pause fixe insérée entre deux activités consécutives (ignorée quand "
        "« auto_sized_buffer » est activé)",
    "the default UTC offset for all times":
        "le décalage UTC par défaut pour toutes les heures",
    "meals starting before this are categorized as breakfast":
        "les repas commençant avant cette heure sont classés petit-déjeuner",
    "meals starting up to this (after breakfast) are lunch, later ones dinner":
        "les repas jusqu'à cette heure (après le petit-déjeuner) sont le "
        "déjeuner, les suivants le dîner",
    "the default length of a meal that gives no duration or end time":
        "la durée par défaut d'un repas sans durée ni heure de fin",
    "the default currency all prices are given in":
        "la devise par défaut de tous les prix",
    "extra currencies to also show each price in, converted from the default":
        "des devises supplémentaires pour afficher aussi chaque prix, "
        "converties depuis la devise par défaut",
    "the currency this price is in": "la devise de ce prix",
    "the clock time the activity starts": "l'heure de début de l'activité",
    "the clock time the activity ends": "l'heure de fin de l'activité",
    "how long the activity lasts": "la durée de l'activité",
    "the start time zone": "le fuseau horaire de début",
    "the end time zone": "le fuseau horaire de fin",
    "whether this stop is a detour: one you probably won't make, kept for "
    "reference and left off the day's timeline":
        "si cette étape est un détour : une étape que vous ne ferez "
        "probablement pas, gardée pour référence et laissée hors du programme "
        "de la journée",
    "false (a normal stop, scheduled on the timeline)":
        "false (une étape normale, placée dans le programme)",
    # an activity's fee and contact (shared by every type, like `detour`)
    "what this stop costs (an entrance fee, a guided visit, a meal) — 0 prints "
    "as 'Free'":
        "ce que coûte cette étape (un droit d'entrée, une visite guidée, un "
        "repas) — 0 s'affiche « Gratuit »",
    "a number without a currency symbol, like 12 or 7.5":
        "un nombre sans symbole monétaire, comme 12 ou 7.5",
    "the currency of 'price'": "la devise de « price »",
    "a phone number, email or instructions for reaching this stop":
        "un numéro de téléphone, un e-mail ou la marche à suivre pour joindre "
        "cette étape",
    # a transport leg's distance
    "how far this leg covers, in km": "la distance couverte par ce trajet, en km",
    "a number like 200 or 30.5": "un nombre comme 200 ou 30.5",
    "none (no distance shown)": "aucune (pas de distance affichée)",
    "the day's title": "le titre du jour",
    "the city/region label": "le libellé de ville/région",
    "the day's date": "la date du jour",
    "an intro paragraph for the day": "un paragraphe d'intro pour le jour",
    "the day's items, in order (at least one)":
        "les éléments du jour, dans l'ordre (au moins un)",
    "a non-empty array of activity objects, each with a 'type'":
        "un tableau non vide d'objets activité, chacun avec un « type »",
    "the departure address": "l'adresse de départ",
    "the arrival address": "l'adresse d'arrivée",
    "intermediate stops the route passes through":
        "les arrêts intermédiaires que traverse l'itinéraire",
    # a road and its legs
    "the hops the drive is made of, in travel order":
        "les étapes qui composent le trajet, dans l'ordre du parcours",
    "a non-empty array of leg objects (see below), each with its endpoints and "
    "that hop's duration / distance_km / off_road":
        "un tableau non vide d'objets étape (voir ci-dessous), chacun avec ses "
        "extrémités et les « duration » / « distance_km » / « off_road » de "
        "cette étape",
    "the driving distance in km for the whole drive":
        "la distance de conduite en km pour tout le trajet",
    "whether the drive's departure gets a numbered map pin":
        "si le départ du trajet reçoit une épingle numérotée sur la carte",
    "whether the drive's final arrival gets a numbered map pin":
        "si l'arrivée finale du trajet reçoit une épingle numérotée sur la carte",
    "whether each junction between two legs gets a numbered map pin":
        "si chaque jonction entre deux étapes reçoit une épingle numérotée sur "
        "la carte",
    "false (the drive is drawn as a route only)":
        "false (le trajet n'est dessiné que comme un itinéraire)",
    "true (splitting the drive there is what says the junction matters — set it "
    "false to leave the junctions unpinned)":
        "true (découper le trajet à cet endroit est précisément ce qui dit que "
        "la jonction compte — mettez false pour laisser les jonctions sans "
        "épingle)",
    "whether the drive departs from the previous activity's place — the first "
    "leg may then leave out its 'start_location' / 'start_coordinate', and the "
    "departure shares that activity's map pin instead of taking a number of its "
    "own":
        "si le trajet part du lieu de l'activité précédente — la première étape "
        "peut alors omettre ses « start_location » / « start_coordinate », et le "
        "départ partage l'épingle de cette activité au lieu de prendre un numéro "
        "à lui",
    "false (the drive states its own departure)":
        "false (le trajet indique son propre départ)",
    "whether the drive arrives at the next activity's place — the last leg may "
    "then leave out its 'end_location' / 'end_coordinate', and the arrival "
    "shares that activity's map pin instead of taking a number of its own":
        "si le trajet arrive au lieu de l'activité suivante — la dernière étape "
        "peut alors omettre ses « end_location » / « end_coordinate », et "
        "l'arrivée partage l'épingle de cette activité au lieu de prendre un "
        "numéro à elle",
    "false (the drive states its own arrival)":
        "false (le trajet indique sa propre arrivée)",
    "the previous activity's place ('same_start_as_previous_activity' is on)":
        "le lieu de l'activité précédente (« same_start_as_previous_activity » "
        "est activé)",
    "the previous activity's coordinate, else geocoded from 'start_location' "
    "when maps are on":
        "la coordonnée de l'activité précédente, sinon géocodée depuis "
        "« start_location » si les cartes sont activées",
    "the next activity's place ('same_end_as_next_activity' is on)":
        "le lieu de l'activité suivante (« same_end_as_next_activity » est "
        "activé)",
    "the next activity's coordinate ('same_end_as_next_activity' is on) — which "
    "then has to have one":
        "la coordonnée de l'activité suivante (« same_end_as_next_activity » est "
        "activé) — qui doit donc en avoir une",
    "a GPX recording of this hop, drawn as its line on the day map (instead of "
    "the routed guess)":
        "un enregistrement GPX de cette étape, dessiné comme son tracé sur la "
        "carte du jour (à la place de l'itinéraire calculé)",
    "none (the hop's line is routed through its endpoints)":
        "aucun (le tracé de l'étape est calculé entre ses extrémités)",
    "'include_maps_in_render' is off, so this GPX is parsed but no map is drawn "
    "from it (the viewer still offers the file for download).":
        "« include_maps_in_render » est désactivé : ce GPX est analysé mais "
        "aucune carte n'en est dessinée (la visionneuse propose tout de même le "
        "fichier au téléchargement).",
    "where this hop departs from": "d'où part cette étape",
    "where the drive departs from (the first leg has no previous leg to inherit "
    "it from)":
        "d'où part le trajet (la première étape n'a pas d'étape précédente dont "
        "l'hériter)",
    "the previous leg's 'end_location'":
        "le « end_location » de l'étape précédente",
    "the departure point on the map": "le point de départ sur la carte",
    "an object with a 'lat' and a 'long'":
        "un objet avec un « lat » et un « long »",
    "the previous leg's 'end_coordinate' (geocoded from the name on the first "
    "leg)":
        "le « end_coordinate » de l'étape précédente (géocodé depuis le nom "
        "pour la première étape)",
    "geocoded from 'start_location' when maps are on":
        "géocodé depuis « start_location » si les cartes sont activées",
    "where this hop arrives": "où arrive cette étape",
    "where this hop arrives (the next leg could name it as its own "
    "'start_location' instead)":
        "où arrive cette étape (l'étape suivante peut le nommer dans son propre "
        "« start_location » à la place)",
    "where the drive arrives (the last leg has no next leg to inherit it from)":
        "où arrive le trajet (la dernière étape n'a pas d'étape suivante dont "
        "l'hériter)",
    "the next leg's 'start_location'":
        "le « start_location » de l'étape suivante",
    "the arrival point on the map": "le point d'arrivée sur la carte",
    "the arrival point on the map (the next leg could name it as its own "
    "'start_coordinate' instead)":
        "le point d'arrivée sur la carte (l'étape suivante peut le nommer dans "
        "son propre « start_coordinate » à la place)",
    "the arrival point on the map (the last leg has no next leg to inherit it "
    "from)":
        "le point d'arrivée sur la carte (la dernière étape n'a pas d'étape "
        "suivante dont l'hériter)",
    "the next leg's 'start_coordinate'":
        "le « start_coordinate » de l'étape suivante",
    "how long this hop takes to drive": "le temps de conduite de cette étape",
    "this hop's driving distance in km":
        "la distance de conduite de cette étape en km",
    "whether this hop runs off-road": "si cette étape est hors-route",
    "false (and the drive counts as off-road only when every leg is)":
        "false (et le trajet n'est hors-route que si toutes ses étapes le sont)",
    "intermediate points the hop's route bends through, in order from its start "
    "to its end":
        "les points intermédiaires par lesquels passe l'itinéraire de l'étape, "
        "dans l'ordre de son départ vers son arrivée",
    "an array of {lat, long} coordinates":
        "un tableau de coordonnées {lat, long}",
    "[] (the route runs straight between the hop's endpoints)":
        "[] (l'itinéraire va tout droit entre les extrémités de l'étape)",
    "the point-of-interest name": "le nom du point d'intérêt",
    "the kind of place, shown as the badge":
        "le type de lieu, affiché comme badge",
    "the address": "l'adresse",
    "a description": "une description",
    "the days it opens (the visit is checked against them)":
        "les jours d'ouverture (la visite est vérifiée par rapport à eux)",
    "weekday names like 'tue-sun', 'monday, thursday' or 'mon-fri, sun'":
        "des noms de jours comme « tue-sun », « monday, thursday » ou "
        "« mon-fri, sun »",
    "every day (no closed-day check)":
        "tous les jours (pas de vérification des jours de fermeture)",
    "the hours it opens (the visit is checked against them)":
        "les horaires d'ouverture (la visite est vérifiée par rapport à eux)",
    "time ranges like '09:30-18:00' or '09:30-12:30, 14:00-18:00', or per "
    "weekday as 'mon-sat 09:00-17:00; sun 10:00-17:00'":
        "des plages horaires comme « 09:30-18:00 » ou "
        "« 09:30-12:30, 14:00-18:00 », ou par jour sous la forme "
        "« mon-sat 09:00-17:00; sun 10:00-17:00 »",
    "all day (no opening-hours check)":
        "toute la journée (pas de vérification des horaires)",
    "the place name": "le nom du lieu",
    "a description of the place": "une description du lieu",
    "nested points of interest, hikes and meals":
        "les points d'intérêt, randonnées et repas imbriqués",
    "nested meals (a stop along the drive)":
        "les repas imbriqués (une halte pendant le trajet)",
    "nested meals (a stop along the hike)":
        "les repas imbriqués (une halte pendant la randonnée)",
    "the hike name": "le nom de la randonnée",
    "a description of the hike": "une description de la randonnée",
    "the hike distance in km": "la distance de la randonnée en km",
    "the elevation gain in m": "le dénivelé positif en m",
    "the trailhead address": "l'adresse du départ de rando",
    "the end address": "l'adresse d'arrivée",
    "the route shape": "la forme de l'itinéraire",
    "a GPX file of the trail, drawn as a map plus an elevation profile":
        "un fichier GPX du sentier, dessiné en carte et en profil altimétrique",
    "the .gpx file base64-encoded (gzip allowed)":
        "le fichier .gpx encodé en base64 (gzip accepté)",
    "none (no trail map or profile)": "aucun (ni tracé ni profil)",
    "which meal it is": "de quel repas il s'agit",
    "the restaurant name": "le nom du restaurant",
    "the town/region to eat in (used when no restaurant is named)":
        "la ville/région où manger (utilisée si aucun restaurant n'est nommé)",
    "the length of the free time": "la durée du temps libre",
    "the transport type (plane/train/bus…)":
        "le type de transport (avion/train/bus…)",
    "the departure date": "la date de départ",
    "the arrival date": "la date d'arrivée",
    "the departure time": "l'heure de départ",
    "the arrival time": "l'heure d'arrivée",
    "the departure time zone": "le fuseau horaire de départ",
    "the arrival time zone": "le fuseau horaire d'arrivée",
    "the travel time": "le temps de trajet",
    "the flight number of this leg (planes only)":
        "le numéro de vol de ce trajet (avions uniquement)",
    "the train number of this leg (trains only)":
        "le numéro de train de ce trajet (trains uniquement)",
    "the reservation reference": "la référence de réservation",
    "'status' is set but 'booking_number' is missing — a confirmed/booked "
    "booking usually has a reference.":
        "« status » est défini mais « booking_number » manque — une réservation "
        "confirmée/réservée a généralement une référence.",
    "where it was booked": "où cela a été réservé",
    "the reservation status": "l'état de la réservation",
    # the shared note on transport / accommodation / car rental (specs.NOTE_DESC)
    "a short note for whatever the other fields don't cover":
        "une note courte pour ce que les autres champs ne couvrent pas",
    "the price of the whole booking, every leg included":
        "le prix de la réservation entière, tous les trajets compris",
    "what to call the whole booking": "le nom de la réservation entière",
    "the route through its legs (A → B → C)":
        "l'itinéraire de ses trajets (A → B → C)",
    "a short note about the whole booking (a leg's own note goes on the leg)":
        "une note courte sur la réservation entière (la note d'un trajet se met "
        "sur le trajet)",
    "the hops this booking moves you over (a single-hop booking has one)":
        "les trajets que cette réservation couvre (une réservation directe en "
        "compte un)",
    "a non-empty array of {start, end, start_date, start_time, …} objects":
        "un tableau non vide d'objets {start, end, start_date, start_time, …}",
    "the payment state": "l'état du paiement",
    "the accommodation name": "le nom de l'hébergement",
    "the check-in date": "la date d'arrivée",
    "the check-out date": "la date de départ",
    "the town, for the cover overview":
        "la ville, pour le récapitulatif de couverture",
    "the street address": "l'adresse postale",
    "a phone or email": "un téléphone ou email",
    "the price": "le prix",
    "whether it is already paid": "si c'est déjà payé",
    "whether breakfast is included": "si le petit-déjeuner est inclus",
    "the booking start date": "la date de début de réservation",
    "the booking start time": "l'heure de début de réservation",
    "the booking end date": "la date de fin de réservation",
    "the booking end time": "l'heure de fin de réservation",
    "the pick-up date": "la date de retrait",
    "the pick-up time": "l'heure de retrait",
    "the drop-off date": "la date de restitution",
    "the drop-off time": "l'heure de restitution",
    "where you pick up the car": "où vous prenez la voiture",
    "where you drop off the car": "où vous rendez la voiture",
    "the booking start time zone": "le fuseau horaire de début de réservation",
    "the booking end time zone": "le fuseau horaire de fin de réservation",
    "the pick-up time zone": "le fuseau horaire de retrait",
    "the drop-off time zone": "le fuseau horaire de restitution",
    "the rental company": "la société de location",
    "the rental price": "le prix de la location",
    "the car category": "la catégorie de voiture",
    "the car make/model": "la marque/le modèle de la voiture",
    "a phone or email for the rental company":
        "un téléphone ou email de la société de location",
    "the number of additional drivers": "le nombre de conducteurs supplémentaires",
    "how long the pick-up takes": "la durée de la prise en charge",
    "how long the drop-off takes": "la durée de la restitution",
    # the `misc` group and its emergency contacts
    "who to call in an emergency where you're going":
        "qui appeler en cas d'urgence là où vous allez",
    "who this contact reaches": "qui ce numéro permet de joindre",
    "how to reach them — a phone number, an email or an address":
        "comment les joindre — un numéro, un email ou une adresse",
    # -- validation: expected values --
    "any text": "un texte",
    "a date YYYY-MM-DD": "une date AAAA-MM-JJ",
    "a hex color like '#2f6b4f'": "une couleur hex comme « #2f6b4f »",
    "a time HH:MM": "une heure HH:MM",
    "a duration like '15 min'": "une durée comme « 15 min »",
    "a duration like '1h30' or '45 min'": "une durée comme « 1h30 » ou « 45 min »",
    "a duration like '30 min'": "une durée comme « 30 min »",
    "a duration like '4h20'": "une durée comme « 4h20 »",
    "a duration like '1h'": "une durée comme « 1h »",
    "an offset like '+02:00', 'UTC-3' or 'Z'":
        "un décalage comme « +02:00 », « UTC-3 » ou « Z »",
    "a UTC offset like '+02:00'": "un décalage UTC comme « +02:00 »",
    "a UTC offset like '-04:00'": "un décalage UTC comme « -04:00 »",
    "a number": "un nombre",
    "a 3-letter ISO code like 'EUR'": "un code ISO à 3 lettres comme « EUR »",
    "a 3-letter ISO code like 'USD'": "un code ISO à 3 lettres comme « USD »",
    "an array of {currency, change_rate} objects":
        "un tableau d'objets {currency, change_rate}",
    "an array of objects with a 'name' and a 'contact', inside 'misc'":
        "un tableau d'objets avec un « name » et un « contact », dans « misc »",
    "true or false": "true ou false",
    "'loop', 'back_and_forth' or 'one_way'":
        "« loop », « back_and_forth » ou « one_way »",
    "an array of point_of_interest, hike or meal objects, each with a 'type'":
        "un tableau d'objets point_of_interest, hike ou meal, chacun avec un "
        "« type »",
    "an array of meal objects, each with a 'type'":
        "un tableau d'objets meal, chacun avec un « type »",
    "an array of {coordinate, location, duration, distance_km} objects":
        "un tableau d'objets {coordinate, location, duration, distance_km}",
    "'booked' or 'confirmed'": "« booked » ou « confirmed »",
    "'paid' or 'to pay'": "« paid » ou « to pay »",
    "text or a number": "un texte ou un nombre",
    "one of: regular, small, suv, 4x4": "l'un de : regular, small, suv, 4x4",
    "a whole number": "un nombre entier",
    # -- validation: default descriptions --
    '"" (no subtitle shown)': "« » (aucun sous-titre)",
    "inferred from the earliest date": "déduite de la date la plus tôt",
    "inferred from the latest date": "déduite de la date la plus tard",
    '"#1f4e5f" (teal)': "« #1f4e5f » (bleu-vert)",
    '"" (no summary shown)': "« » (aucun résumé)",
    '"08:00"': "« 08:00 »",
    '"18:00"': "« 18:00 »",
    "true (buffers are auto-sized)": "vrai (les pauses sont dimensionnées)",
    "0 (no fixed buffer)": "0 (aucune pause fixe)",
    "GMT (UTC+0)": "GMT (UTC+0)",
    '"10:00"': "« 10:00 »",
    '"16:00"': "« 16:00 »",
    "0 (instant)": "0 (instantané)",
    '"EUR"': "« EUR »",
    "[] (none shown)": "[] (aucune affichée)",
    "none (no price shown)": "aucun (pas de prix affiché)",
    "the trip's default currency": "la devise par défaut du voyage",
    "the previous activity's end, or the day's default start":
        "la fin de l'activité précédente, ou le début par défaut du jour",
    "start_time + duration": "start_time + duration",
    "inferred from end_time, else 0": "déduite de end_time, sinon 0",
    # a place's duration alone falls back to what it contains (specs.PLACE_SCHEDULE)
    "inferred from end_time, else the nested activities' total, else 0":
        "déduite de end_time, sinon le total des activités imbriquées, sinon 0",
    "the trip's default timezone": "le fuseau par défaut du voyage",
    '"" ': "« » ",
    "the trip start date + the day's index in 'days'":
        "la date de début du voyage + l'index du jour dans « days »",
    '""': "« »",
    "none (not shown)": "aucune (non affichée)",
    "[] (a direct start→end route)": "[] (un itinéraire direct départ→arrivée)",
    "false": "false",
    '"other"': "« other »",
    "[] (none listed)": "[] (aucun listé)",
    "[] (no emergency contacts section)": "[] (aucune page de numéros d'urgence)",
    '"" (the number is listed on its own)': "« » (le numéro est listé seul)",
    '"" (nothing to call — the entry is a label only)':
        "« » (rien à appeler — l'entrée n'est qu'un libellé)",
    "none": "aucune",
    '"back_and_forth"': "« back_and_forth »",
    '"" (badge shows TRANSPORT)': "« » (le badge affiche TRANSPORT)",
    "none (not woven into a day)": "aucune (non intégré à un jour)",
    "inferred (+1 day if it crosses midnight)":
        "déduite (+1 jour si passage à minuit)",
    "none / inferred from end_time − duration":
        "aucune / déduite de end_time − duration",
    "none / inferred from start_time + duration":
        "aucune / déduite de start_time + duration",
    "inferred from the two times": "déduite des deux heures",
    "none (no badge)": "aucune (pas de badge)",
    "none (not matched to a night)": "aucune (non rattachée à une nuit)",
    "the accommodation name": "le nom de l'hébergement",
    "false (shows a 'To pay' badge)": "false (affiche un badge « À payer »)",
    # -- type enums (added-later requirements) --
    "the transport type": "le type de transport",
    "the kind of accommodation": "le type d'hébergement",
    "one of: museum, church, building, viewpoint, ruins, castle, temple, street, "
    "natural park, mountain, lake, beach, waterfall, other":
        "l'un de : museum, church, building, viewpoint, ruins, castle, temple, street, "
        "natural park, mountain, lake, beach, waterfall, other",
    "one of: plane, train, bus, taxi, ferry, other":
        "l'un de : plane, train, bus, taxi, ferry, other",
    "one of: hotel, camping, b&b, other": "l'un de : hotel, camping, b&b, other",
    "one of: breakfast, lunch, dinner, brunch, snack, picnic, meal":
        "l'un de : breakfast, lunch, dinner, brunch, snack, picnic, meal",
    "inferred from the start time": "déduit de l'heure de début",
    '"hotel"': "« hotel »",
    # transport type badge words (uppercased for the badge)
    "plane": "avion",
    "train": "train",
    "bus": "bus",
    "taxi": "taxi",
    "ferry": "ferry",
    # accommodation type words
    "hotel": "hôtel",
    "camping": "camping",
    "b&b": "b&b",
    # car rental defaults
    "the pick-up location": "le lieu de retrait",
    '"regular"': "« regular »",
    "0": "0",
    # -- validation: field descriptions (maps + links) --
    "whether to draw a per-day OpenStreetMap with a pin for each activity":
        "s'il faut dessiner une carte OpenStreetMap par jour avec un point pour "
        "chaque activité",
    "whether to geocode activities that lack an explicit coordinate":
        "s'il faut géocoder les activités sans coordonnée explicite",
    "ISO country codes to restrict geocoding to (when inferring coordinates)":
        "les codes pays ISO auxquels limiter le géocodage (lors de l'inférence "
        "des coordonnées)",
    "a link to the venue's website": "un lien vers le site du lieu",
    "a link to the carrier's website": "un lien vers le site du transporteur",
    "a link to the property's website": "un lien vers le site de l'établissement",
    "a link to the rental company's website":
        "un lien vers le site de la société de location",
    "a direct link to this reservation": "un lien direct vers cette réservation",
    # -- validation: expected values (links + ISO list) --
    "a link like 'https://example.com'": "un lien comme « https://example.com »",
    "an array of 2-letter ISO codes like ['FR']":
        "un tableau de codes ISO à 2 lettres comme ['FR']",
    # -- validation: default descriptions (maps + links) --
    "none (no link shown)": "aucun (pas de lien affiché)",
    "false (no maps)": "false (aucune carte)",
    "whether to draw the trail map and elevation profile of a hike that embeds "
    "a 'gpx'":
        "s'il faut dessiner le tracé et le profil altimétrique d'une randonnée "
        "qui embarque un « gpx »",
    "true (drawn whenever a hike has a 'gpx')":
        "true (dessinés dès qu'une randonnée a un « gpx »)",
    "false (only activities with an explicit coordinate are mapped)":
        "false (seules les activités avec une coordonnée explicite sont "
        "cartographiées)",
    "[] (any country)": "[] (tous les pays)",
    "[] (none nested)": "[] (aucune imbriquée)",
    # -- validation: extra message templates --
    "field '{name}' is invalid — {error}.":
        "champ « {name} » invalide — {error}.",
    "inference country {value} is invalid — {error}.":
        "pays d'inférence {value} invalide — {error}.",
    "'inference_countries' must be an array of 2-letter ISO country codes like "
    "['FR'].":
        "« inference_countries » doit être un tableau de codes pays ISO à "
        "2 lettres comme ['FR'].",
    "'inference_countries' is set but 'infer_coordinates_from_address' is off — "
    "it is ignored.":
        "« inference_countries » est défini mais « infer_coordinates_from_address » "
        "est désactivé — il est ignoré.",
    "'buffer' is ignored — 'auto_sized_buffer' is on (it is by default) and "
    "sizes the buffers to fill the day instead. Drop one of the two.":
        "« buffer » est ignoré — « auto_sized_buffer » est activé (il l'est par "
        "défaut) et dimensionne les pauses pour remplir la journée. Supprimez "
        "l'un des deux.",
    "a detour is left off the day's timeline, so its 'start_time' and "
    "'end_time' are dropped — only the span between them is kept, as its "
    "duration. Write that as a 'duration' instead.":
        "un détour reste hors du programme de la journée : ses « start_time » "
        "et « end_time » sont donc abandonnés — seul l'écart entre les deux est "
        "conservé, comme sa durée. Écrivez-le plutôt en « duration ».",
    "'{key}' is ignored — a detour is left off the day's timeline, so it has "
    "no clock time (its duration is shown on its own).":
        "« {key} » est ignoré — un détour reste hors du programme de la "
        "journée, il n'a donc pas d'horaire (seule sa durée est affichée).",
    # -- validation: value-check messages (the parenthetical "(...)") --
    "must be a number": "doit être un nombre",
    "must be a number, not a boolean": "doit être un nombre, pas un booléen",
    "must be true or false": "doit être true ou false",
    "must be 'booked' or 'confirmed'": "doit être « booked » ou « confirmed »",
    "must be a whole number": "doit être un nombre entier",
    "must be zero or more": "doit être zéro ou plus",
    "must be a hex color like '#2f6b4f'":
        "doit être une couleur hex comme « #2f6b4f »",
    "must be a 3-letter currency code like 'EUR'":
        "doit être un code devise à 3 lettres comme « EUR »",
    "must be a link like 'https://example.com'":
        "doit être un lien comme « https://example.com »",
    "must be a 2-letter ISO country code like 'FR'":
        "doit être un code pays ISO à 2 lettres comme « FR »",
    "must be one of: museum, church, building, viewpoint, ruins, castle, temple, "
    "street, natural park, mountain, lake, beach, waterfall, other":
        "doit être l'un de : museum, church, building, viewpoint, ruins, castle, "
        "temple, street, natural park, mountain, lake, beach, waterfall, other",
    "must be one of: plane, train, bus, taxi, ferry, other":
        "doit être l'un de : plane, train, bus, taxi, ferry, other",
    "must be one of: hotel, camping, b&b, other":
        "doit être l'un de : hotel, camping, b&b, other",
    "must be one of: breakfast, lunch, dinner, brunch, snack, picnic, meal":
        "doit être l'un de : breakfast, lunch, dinner, brunch, snack, picnic, meal",
    "must be one of: regular, small, suv, 4x4":
        "doit être l'un de : regular, small, suv, 4x4",
    # -- validation: parser errors (templates re-formatted after translation) --
    "Invalid date {value}, expected YYYY-MM-DD":
        "date invalide {value}, format attendu AAAA-MM-JJ",
    "Invalid time {value}, expected HH:MM":
        "heure invalide {value}, format attendu HH:MM",
    "Invalid timezone {value}, expected e.g. '+02:00' or 'UTC-3'":
        "fuseau horaire invalide {value}, attendu par ex. « +02:00 » ou « UTC-3 »",
    "Could not parse duration {value}": "durée illisible {value}",
    "hike route must be 'loop', 'back_and_forth' or 'one_way', got {value}":
        "le parcours doit être « loop », « back_and_forth » ou « one_way », "
        "reçu {value}",
    "paid must be 'paid' or 'to pay', got {value}":
        "« paid » doit être « paid » ou « to pay », reçu {value}",
    "{name} must be an object with 'lat' and 'long'":
        "{name} doit être un objet avec « lat » et « long »",
    "{name} needs both 'lat' and 'long'":
        "{name} nécessite « lat » et « long »",
    "{name}.lat must be between -90 and 90 (got {value})":
        "{name}.lat doit être entre -90 et 90 (reçu {value})",
    "{name}.long must be between -180 and 180 (got {value})":
        "{name}.long doit être entre -180 et 180 (reçu {value})",
    "{name} must be a number, got {value}":
        "{name} doit être un nombre, reçu {value}",
    # -- ICS (calendar) export --
    "Validation errors (exporting anyway):":
        "Erreurs de validation (export quand même) :",
    "Day {n}": "Jour {n}",
    "Type": "Type",
    "Drive": "Route",
    "Yes": "Oui",
    "Off-road": "Hors-route",
    "Via": "Via",
    "Category": "Catégorie",
    "Address": "Adresse",
    "Description": "Description",
    # the .ics detail label; its value is the shared "p. {pages}" reference
    "Guidebook": "Guide",
    "p. {pages}": "p. {pages}",
    "Distance": "Distance",
    "Elevation": "Dénivelé",
    "Route": "Parcours",
    "Restaurant": "Restaurant",
    "Area": "Secteur",
    "Includes": "Comprend",
    "Duration": "Durée",
    "Departure": "Départ",
    "Arrival": "Arrivée",
    "Flight number": "Numéro de vol",
    "Train number": "Numéro de train",
    "Booking number": "Numéro de réservation",
    "Booking source": "Réservé via",
    "Status": "Statut",
    "Price": "Prix",
    # a multi-leg booking's fare covers every leg, so its label says so
    "Price (whole booking)": "Prix (réservation entière)",
    # the booking's own note, kept apart from a leg's "Description"
    "Booking note": "Note de réservation",
    "Booking": "Réservation",
    "Company": "Société",
    "Car model": "Modèle",
    "Car type": "Catégorie de véhicule",
    "Additional drivers": "Conducteurs supplémentaires",
    "Contact": "Contact",
    "Car pick-up": "Prise du véhicule",
    "Car drop-off": "Restitution du véhicule",
    "City": "Ville",
    "Nights": "Nuits",
    "Night": "Nuit",
    "Breakfast included": "Petit-déjeuner inclus",
    "paid": "payé",
    "to pay": "à payer",
    "Plane": "Avion",
    "Train": "Train",
    "Bus": "Bus",
    "Taxi": "Taxi",
    "Ferry": "Ferry",
    "Other": "Autre",
    "Small": "Petite",
    "4x4": "4x4",
    "booked": "réservé",
    "confirmed": "confirmé",
}

TRANSLATIONS = {"fr": _FR}
