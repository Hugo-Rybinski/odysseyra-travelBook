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
    "MEAL": "REPAS",
    "TRANSPORT": "TRANSPORT",
    "OFF-ROAD SECTIONS": "SECTIONS HORS-ROUTE",
    "OVERNIGHT": "DE NUIT",
    "INCLUDES": "COMPREND",
    "buffer": "pause",
    # meal types (from Meal.type) and the meal row head
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
    "lake": "lac",
    "beach": "plage",
    "waterfall": "cascade",
    "other": "autre",
    # -- PDF: transport --
    "GETTING AROUND": "SE DÉPLACER",
    "Transport": "Transport",
    "Ref {ref}": "Réf {ref}",
    "Flight {number}": "Vol {number}",
    "Train {number}": "Train {number}",
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
    "the nested activities last {total} in total, longer than this activity's "
    "{parent} — they can't all fit inside it.":
        "les activités imbriquées durent {total} au total, plus que la durée de "
        "cette activité ({parent}) — elles ne peuvent pas toutes y tenir.",
    "a point of interest must be an object or a name string":
        "un point d'intérêt doit être un objet ou une chaîne de caractères",
    "each transport must be an object": "chaque transport doit être un objet",
    "transport end_date ({ed}) is before start_date ({sd}).":
        "la date d'arrivée du transport ({ed}) est avant la date de départ ({sd}).",
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
    "'paid_online' is true but 'price' is missing — marked paid without an "
    "amount.":
        "« paid_online » est vrai mais « price » manque — marqué payé sans "
        "montant.",
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
    "the flight number (planes only)": "le numéro de vol (avions uniquement)",
    "the train number (trains only)": "le numéro de train (trains uniquement)",
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
    "true or false": "true ou false",
    "'loop', 'back_and_forth' or 'one_way'":
        "« loop », « back_and_forth » ou « one_way »",
    "an array of point_of_interest, hike or meal objects, each with a 'type'":
        "un tableau d'objets point_of_interest, hike ou meal, chacun avec un "
        "« type »",
    "an array of meal objects, each with a 'type'":
        "un tableau d'objets meal, chacun avec un « type »",
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
    "none (no end-of-day check)": "aucune (pas de contrôle de fin de journée)",
    "0 (no buffer)": "0 (aucune pause)",
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
}

TRANSLATIONS = {"fr": _FR}
