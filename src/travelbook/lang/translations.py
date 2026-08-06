"""Translation tables. English is the source language (identity); each other
language maps English source strings (templates keep their ``{placeholders}``)
to their translation."""

_FR = {
    # -- PDF: cover & overview --
    "Dates": "Dates",
    "Days": "Jours",
    "Day by day": "Jour par jour",
    "DAY": "JOUR",
    "DATE": "DATE",
    "HIGHLIGHTS": "TEMPS FORTS",
    "SLEEP": "NUIT",
    "DAY {index}": "JOUR {index}",
    "Itinerary": "Itinéraire",
    # -- PDF: activity badges & labels --
    "ROAD": "ROUTE",
    "POINT": "POINT",
    "PLACE": "LIEU",
    "HIKE": "RANDO",
    "TRANSPORT": "TRANSPORT",
    "OFF-ROAD SECTIONS": "SECTIONS HORS-ROUTE",
    "OVERNIGHT": "DE NUIT",
    "POINTS OF INTEREST": "POINTS D'INTÉRÊT",
    "buffer": "pause",
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
    "other": "autre",
    # -- PDF: transport --
    "GETTING AROUND": "SE DÉPLACER",
    "Transport": "Transport",
    "Ref {ref}": "Réf {ref}",
    "Booked via {source}": "Réservé via {source}",
    "BOOKED": "RÉSERVÉ",
    "CONFIRMED": "CONFIRMÉ",
    "PAID": "PAYÉ",
    "TO PAY": "À PAYER",
    # -- PDF: accommodation --
    "WHERE YOU'LL STAY": "OÙ VOUS DORMEZ",
    "Accommodation": "Hébergement",
    "PAID ONLINE": "PAYÉ EN LIGNE",
    "✓  Breakfast included": "✓  Petit-déjeuner inclus",
    "TONIGHT'S STAY": "CETTE NUIT",
    "Night {night}/{total} here": "Nuit {night}/{total} ici",
    "on board": "à bord",
    "Overnight {type}": "{type} de nuit",
    "Overnight travel": "Trajet de nuit",
    "{nights} night": "{nights} nuit",
    "{nights} nights": "{nights} nuits",
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
    "optional field 'transport' is missing — the transport legs. Expected an "
    "array of transport objects. Defaulting to [] (no transport page).":
        "champ optionnel « transport » manquant — les trajets. Attendu : un "
        "tableau d'objets transport. Valeur par défaut : [] (pas de page "
        "transport).",
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
    "a point of interest must be an object or a name string":
        "un point d'intérêt doit être un objet ou une chaîne de caractères",
    "each transport must be an object": "chaque transport doit être un objet",
    "transport end_date ({ed}) is before start_date ({sd}).":
        "la date d'arrivée du transport ({ed}) est avant la date de départ ({sd}).",
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
    "'paid_online' is true but 'price' is missing — marked paid without an "
    "amount.":
        "« paid_online » est vrai mais « price » manque — marqué payé sans "
        "montant.",
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
    "you can't sleep in two places.":
        "la nuit du {d} a à la fois un hébergement et un transport de nuit — "
        "vous ne pouvez pas dormir à deux endroits.",
    "the night of {d} has no accommodation and no overnight transport — you "
    "have nowhere to sleep.":
        "la nuit du {d} n'a ni hébergement ni transport de nuit — vous n'avez "
        "nulle part où dormir.",
    "the day's city ({day_city}) doesn't match the accommodation city "
    "({acc_city}).":
        "la ville du jour ({day_city}) ne correspond pas à la ville de "
        "l'hébergement ({acc_city}).",
    "this overlaps the previous item on the day's timeline — their start/end "
    "times collide.":
        "cet élément chevauche le précédent dans la journée — leurs heures de "
        "début/fin se croisent.",
    "the day's activities run past midnight — the schedule doesn't fit in a "
    "single day.":
        "les activités du jour dépassent minuit — le programme ne tient pas "
        "en une seule journée.",
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
    "the latest an activity should end each day":
        "l'heure la plus tardive à laquelle une activité doit finir",
    "a buffer inserted between consecutive activities":
        "une pause insérée entre deux activités consécutives",
    "the default UTC offset for all times":
        "le décalage UTC par défaut pour toutes les heures",
    "the clock time the activity starts": "l'heure de début de l'activité",
    "the clock time the activity ends": "l'heure de fin de l'activité",
    "how long the activity lasts": "la durée de l'activité",
    "the start time zone": "le fuseau horaire de début",
    "the end time zone": "le fuseau horaire de fin",
    "the day's title": "le titre du jour",
    "the city/region label": "le libellé de ville/région",
    "the day's date": "la date du jour",
    "an intro paragraph for the day": "un paragraphe d'intro pour le jour",
    "the departure address": "l'adresse de départ",
    "the arrival address": "l'adresse d'arrivée",
    "the driving distance in km": "la distance de conduite en km",
    "whether part of the drive is off-road":
        "si une partie du trajet est hors-route",
    "the point-of-interest name": "le nom du point d'intérêt",
    "the kind of place, shown as the badge":
        "le type de lieu, affiché comme badge",
    "the address": "l'adresse",
    "a description": "une description",
    "the place name": "le nom du lieu",
    "a description of the place": "une description du lieu",
    "points of interest grouped here": "les points d'intérêt regroupés ici",
    "the hike name": "le nom de la randonnée",
    "a description of the hike": "une description de la randonnée",
    "the hike distance in km": "la distance de la randonnée en km",
    "the elevation gain in m": "le dénivelé positif en m",
    "the trailhead address": "l'adresse du départ de rando",
    "the end address": "l'adresse d'arrivée",
    "the route shape": "la forme de l'itinéraire",
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
    "the reservation reference": "la référence de réservation",
    "where it was booked": "où cela a été réservé",
    "the reservation status": "l'état de la réservation",
    "the ticket price": "le prix du billet",
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
    # -- validation: expected values --
    "any text": "un texte",
    "a date YYYY-MM-DD": "une date AAAA-MM-JJ",
    "a hex color like '#2f6b4f'": "une couleur hex comme « #2f6b4f »",
    "a time HH:MM": "une heure HH:MM",
    "a duration like '15 min'": "une durée comme « 15 min »",
    "a duration like '1h30' or '45 min'": "une durée comme « 1h30 » ou « 45 min »",
    "a duration like '30 min'": "une durée comme « 30 min »",
    "a duration like '4h20'": "une durée comme « 4h20 »",
    "an offset like '+02:00', 'UTC-3' or 'Z'":
        "un décalage comme « +02:00 », « UTC-3 » ou « Z »",
    "a UTC offset like '+02:00'": "un décalage UTC comme « +02:00 »",
    "a UTC offset like '-04:00'": "un décalage UTC comme « -04:00 »",
    "a number": "un nombre",
    "true or false": "true ou false",
    "'loop', 'back_and_forth' or 'one_way'":
        "« loop », « back_and_forth » ou « one_way »",
    "an array of point-of-interest objects or name strings":
        "un tableau d'objets point d'intérêt ou de noms",
    "'booked' or 'confirmed'": "« booked » ou « confirmed »",
    "'paid' or 'to pay'": "« paid » ou « to pay »",
    "text or a number": "un texte ou un nombre",
    # -- validation: default descriptions --
    '"" (no subtitle shown)': "« » (aucun sous-titre)",
    "inferred from the earliest date": "déduite de la date la plus tôt",
    "inferred from the latest date": "déduite de la date la plus tard",
    '"#1f4e5f" (teal)': "« #1f4e5f » (bleu-vert)",
    '"" (no summary shown)': "« » (aucun résumé)",
    '"08:00"': "« 08:00 »",
    "none (no end-of-day check)": "aucune (pas de contrôle de fin de journée)",
    "0 (no buffer)": "0 (aucune pause)",
    "GMT (UTC+0)": "GMT (UTC+0)",
    "the previous activity's end, or the day's default start":
        "la fin de l'activité précédente, ou le début par défaut du jour",
    "start_time + duration": "start_time + duration",
    "inferred from end_time, else 0": "déduite de end_time, sinon 0",
    "the trip's default timezone": "le fuseau par défaut du voyage",
    '"" ': "« » ",
    "the trip start date + the day's index in 'days'":
        "la date de début du voyage + l'index du jour dans « days »",
    '""': "« »",
    "none (not shown)": "aucune (non affichée)",
    "false": "false",
    '"other"': "« other »",
    "[] (none listed)": "[] (aucun listé)",
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
    "one of: museum, church, building, viewpoint, ruins, castle, temple, street, other":
        "l'un de : museum, church, building, viewpoint, ruins, castle, temple, street, other",
    "one of: plane, train, bus, taxi, other":
        "l'un de : plane, train, bus, taxi, other",
    "one of: hotel, camping, b&b, other": "l'un de : hotel, camping, b&b, other",
    '"hotel"': "« hotel »",
    # transport type badge words (uppercased for the badge)
    "plane": "avion",
    "train": "train",
    "bus": "bus",
    "taxi": "taxi",
    # accommodation type words
    "hotel": "hôtel",
    "camping": "camping",
    "b&b": "b&b",
}

TRANSLATIONS = {"fr": _FR}
