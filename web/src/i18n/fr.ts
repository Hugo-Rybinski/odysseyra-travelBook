// French translations for the app *chrome* (top bar, Options, Edit tab, findings
// panel, PWA toasts, and the Edit-tab field registry: labels, help tooltips and
// placeholders). English is the source string and the key; a missing key falls
// back to English. Templates keep {placeholders} — see i18n/index.tsx.
//
// The travel-book renderer's own labels live in render/format.ts, not here.
// Validator findings are translated by the Python engine (validate(text, lang)).

export const FR: Record<string, string> = {
  // ---------------------------------------------------------------- App shell
  "Odysseyra TravelBook": "Odysseyra TravelBook",
  View: "Vue",
  "⚙️ Options": "⚙️ Options",
  "🧭 Travel": "🧭 Voyage",
  "✈️ Transports": "✈️ Transports",
  "🏠 Accommodations": "🏠 Hébergements",
  "🔎 Findings": "🔎 Diagnostics",
  "✏️ Edit": "✏️ Édition",
  "Open an itinerary first": "Ouvrez d'abord un itinéraire",
  "unapplied edits": "modifications non appliquées",
  "Unapplied edits": "Modifications non appliquées",
  "● Engine ready": "● Moteur prêt",
  "● Online": "● En ligne",
  "⚡ Offline — the app still works.": "⚡ Hors ligne — l'application fonctionne quand même.",
  "⚡ Offline": "⚡ Hors ligne",
  " · working…": " · en cours…",

  // Boot stages
  "Starting…": "Démarrage…",
  "Loading Python runtime…": "Chargement de l'environnement Python…",
  "Installing packages…": "Installation des paquets…",
  "Installing Odysseyra TravelBook…": "Installation d'Odysseyra TravelBook…",
  Ready: "Prêt",
  "Engine failed to start": "Échec du démarrage du moteur",

  // Empty / error states
  "Can't render this itinerary yet": "Impossible d'afficher cet itinéraire pour l'instant",
  "The itinerary couldn't be built.": "L'itinéraire n'a pas pu être construit.",
  "Fix the errors in {findings} or {edit}, then {apply} to render it here.":
    "Corrigez les erreurs dans {findings} ou {edit}, puis {apply} pour l'afficher ici.",
  "Apply changes": "Appliquer les modifications",
  "Open an itinerary": "Ouvrir un itinéraire",
  "Choose an Odysseyra TravelBook JSON file to render the travel book and see its validation findings. Everything stays on your device.":
    "Choisissez un fichier JSON Odysseyra TravelBook pour afficher le carnet de voyage et voir ses diagnostics de validation. Tout reste sur votre appareil.",
  "Unsaved edits from a previous session{name} were found.":
    "Des modifications non enregistrées d'une session précédente{name} ont été trouvées.",
  Restore: "Restaurer",
  Discard: "Ignorer",
  "The engine is still warming up…": "Le moteur est encore en train de démarrer…",

  // ------------------------------------------------------------------ Options
  Options: "Options",
  File: "Fichier",
  Language: "Langue",
  Maps: "Cartes",
  "PDF export": "Export PDF",
  App: "Application",
  Display: "Affichage",
  "How the on-screen travel book collapses sections and shows long text.":
    "Comment le carnet de voyage à l'écran replie les sections et affiche les textes longs.",
  Days: "Jours",
  Transports: "Transports",
  Accommodations: "Hébergements",
  "Collapse past": "Replier les passés",
  "Collapse all": "Tout replier",
  "Collapse all but the current": "Tout replier sauf l'actuel",
  "Expand all": "Tout déplier",
  "Truncate long descriptions": "Tronquer les descriptions longues",
  "Truncate long descriptions to a few lines with a 'Show more' link; off shows them in full":
    "Tronquer les descriptions longues à quelques lignes avec un lien « Voir plus » ; désactivé pour tout afficher",
  "Show more": "Voir plus",
  "Show less": "Voir moins",
  "Open an itinerary, reopen the last one, or load a bundled sample.":
    "Ouvrez un itinéraire, rouvrez le dernier, ou chargez un exemple fourni.",
  "Current file opened:": "Fichier actuellement ouvert :",
  "Set the language of the viewer and PDF exports.":
    "Choisissez la langue de la visionneuse et des exports PDF.",
  "Turn on interactive maps and rebuild this file's cached map images.":
    "Activez les cartes interactives et reconstruisez les images de carte en cache de ce fichier.",
  "Choose the navigation app, turn on interactive maps, and rebuild this file's cached map images.":
    "Choisissez l'application de navigation, activez les cartes interactives et reconstruisez les images de carte en cache de ce fichier.",
  "Navigate links open in": "Les liens « Naviguer » s'ouvrent dans",
  "Choose print options, then export the print-ready PDF.":
    "Choisissez les options d'impression, puis exportez le PDF prêt à imprimer.",
  "Install Odysseyra on this device and check for updates.":
    "Installez Odysseyra sur cet appareil et vérifiez les mises à jour.",
  "The engine is still starting…": "Le moteur est encore en cours de démarrage…",
  "No previously opened file to reopen": "Aucun fichier récemment ouvert à rouvrir",
  "This itinerary doesn't enable maps (include_maps_in_render is off)":
    "Cet itinéraire n'active pas les cartes (include_maps_in_render est désactivé)",
  "Your browser hasn't offered to install the app (it may already be installed, or your browser doesn't support this)":
    "Votre navigateur n'a pas proposé d'installer l'application (elle est peut-être déjà installée, ou votre navigateur ne le prend pas en charge)",
  "Open an Odysseyra TravelBook JSON file from your device":
    "Ouvrir un fichier JSON Odysseyra TravelBook depuis votre appareil",
  "Open JSON…": "Ouvrir un JSON…",
  "Reopen the last opened file": "Rouvrir le dernier fichier ouvert",
  "Reopen last": "Rouvrir le dernier",
  "Load the bundled Pyrenees sample itinerary": "Charger l'itinéraire d'exemple des Pyrénées",
  Sample: "Exemple",
  "Interactive (pan/zoom) maps; each day's area is prefetched for offline use, and falls back to the static image if it can't load":
    "Cartes interactives (déplacement/zoom) ; la zone de chaque jour est préchargée pour un usage hors ligne, avec repli sur l'image statique en cas d'échec du chargement",
  "Interactive maps": "Cartes interactives",
  "Discard this file's cached map images and rebuild them":
    "Supprimer les images de carte en cache de ce fichier et les régénérer",
  "Redrawing…": "Régénération…",
  "Redraw maps": "Régénérer les cartes",
  "Outlines instead of solid accent fills — less colored ink when printing":
    "Contours plutôt que des aplats de couleur — moins d'encre couleur à l'impression",
  "Ink-saver": "Économie d'encre",
  "Embed the per-day maps in the exported PDF (fetches map tiles; slower)":
    "Intégrer les cartes journalières dans le PDF exporté (télécharge les tuiles ; plus lent)",
  "Include maps": "Inclure les cartes",
  "Maps are embedded in the PDF": "Les cartes sont intégrées au PDF",
  "Maps are omitted from the PDF": "Les cartes sont exclues du PDF",
  "Exporting…": "Export…",
  "Export PDF": "Exporter en PDF",
  "Install Odysseyra TravelBook as an app on this device":
    "Installer Odysseyra TravelBook comme application sur cet appareil",
  "Install as an app": "Installer comme application",
  "Odysseyra is already installed on this device. ✓":
    "Odysseyra est déjà installé sur cet appareil. ✓",
  "On iPhone/iPad you must use Safari: tap the Share button, then “Add to Home Screen” to install.":
    "Sur iPhone/iPad, vous devez utiliser Safari : appuyez sur le bouton Partager, puis « Sur l'écran d'accueil » pour installer.",
  "Open in Safari": "Ouvrir dans Safari",
  "Check for a new version and update to it": "Rechercher une nouvelle version et l'installer",
  "Updating…": "Mise à jour…",
  "Checking…": "Vérification…",
  "Check for updates": "Rechercher des mises à jour",
  "🔄 Update": "🔄 Mettre à jour",
  "🔄 Checking…": "🔄 Vérification…",
  "🔄 Updating…": "🔄 Mise à jour…",

  // ------------------------------------------------------------ FindingsPanel
  Validation: "Validation",
  "Validation findings": "Diagnostics de validation",
  "Filter by level": "Filtrer par niveau",
  "line {line}": "ligne {line}",
  "No findings — this itinerary validates clean 🎉":
    "Aucun problème — cet itinéraire est valide 🎉",
  "Select a level above to show findings.":
    "Sélectionnez un niveau ci-dessus pour afficher les diagnostics.",
  "Nothing at the selected levels.": "Rien aux niveaux sélectionnés.",
  "Other findings": "Autres diagnostics",

  // -------------------------------------------------------------- PWA toasts
  "⚡ You’re offline — the app still works.":
    "⚡ Vous êtes hors ligne — l'application fonctionne toujours.",
  "Updating to the latest version…": "Mise à jour vers la dernière version…",
  "Checking for updates…": "Recherche de mises à jour…",
  "✓ Ready to work offline.": "✓ Prêt à fonctionner hors ligne.",
  Dismiss: "Fermer",

  // -------------------------------------------------------------- Edit panel
  "Edit itinerary": "Modifier l'itinéraire",
  "Applying…": "Application…",
  "Applied ✓": "Appliqué ✓",
  "Apply & redraw maps": "Appliquer et régénérer les cartes",
  "Apply the draft and rebuild this itinerary's maps":
    "Appliquer le brouillon et régénérer les cartes de cet itinéraire",
  "↶ Undo": "↶ Annuler",
  "Undo the last edit": "Annuler la dernière modification",
  "↷ Redo": "↷ Rétablir",
  Redo: "Rétablir",
  Revert: "Réinitialiser",
  "Discard changes since the last save/open":
    "Annuler les modifications depuis la dernière sauvegarde/ouverture",
  "Overwrite the opened file": "Écraser le fichier ouvert",
  "Saving…": "Enregistrement…",
  Save: "Enregistrer",
  "Saved ✓": "Enregistré ✓",
  "Save to a new file": "Enregistrer dans un nouveau fichier",
  "Save as…": "Enregistrer sous…",
  "Download the itinerary as a .json file": "Télécharger l'itinéraire au format .json",
  "Download JSON": "Télécharger le JSON",
  "Unapplied edits — the viewer and export still show the last applied version.":
    "Modifications non appliquées — la visionneuse et l'export affichent encore la dernière version appliquée.",
  "Unsaved changes.": "Modifications non enregistrées.",
  "◌ Validating…": "◌ Validation…",
  Trip: "Voyage",
  Defaults: "Valeurs par défaut",
  "Days ({n})": "Jours ({n})",
  "Transport ({n})": "Transport ({n})",
  "Accommodations ({n})": "Hébergements ({n})",
  "Car rentals ({n})": "Locations de voiture ({n})",
  "Day {n}": "Jour {n}",
  "Transport {n}": "Transport {n}",
  "Accommodation {n}": "Hébergement {n}",
  "Car rental {n}": "Location de voiture {n}",
  day: "jour",
  transport: "transport",
  accommodation: "hébergement",
  "car rental": "location de voiture",
  "No days yet — an itinerary needs at least one.":
    "Aucun jour — un itinéraire en nécessite au moins un.",
  "No transport legs.": "Aucun trajet.",
  "No accommodations.": "Aucun hébergement.",
  "No car rentals.": "Aucune location de voiture.",

  // -------------------------------------------------------------- ArrayEditor
  "None yet.": "Aucun pour l'instant.",
  "{n} error": "{n} erreur",
  "{n} errors": "{n} erreurs",
  "{n} warning": "{n} avertissement",
  "{n} warnings": "{n} avertissements",
  "Move up": "Monter",
  "Move down": "Descendre",
  Remove: "Supprimer",

  // -------------------------------------------------------- FieldRow controls
  "— unset —": "— non défini —",
  paid: "payé",
  "to pay": "à payer",
  "{value} (from defaults.{key})": "{value} (d'après defaults.{key})",
  "{label} swatch": "nuancier {label}",

  // ----------------------------------------------------------- CoordinateField
  Coordinate: "Coordonnée",
  "{label}: paste latitude, longitude": "{label} : coller latitude, longitude",
  "paste: 43.0974, -0.0583": "coller : 43.0974, -0.0583",
  "Look up “{query}” and fill the coordinate": "Rechercher « {query} » et remplir la coordonnée",
  "Geocoding needs the engine ready and a network connection":
    "Le géocodage nécessite un moteur prêt et une connexion réseau",
  "Geocoding…": "Géocodage…",
  "Geocode from address": "Géocoder depuis l'adresse",
  "No match for “{query}”.": "Aucun résultat pour « {query} ».",
  Lat: "Lat",
  "Latitude, −90 to 90. Leave both lat & long empty to omit the coordinate.":
    "Latitude, −90 à 90. Laissez lat et long vides pour omettre la coordonnée.",
  "Latitude, −90 to 90.": "Latitude, −90 à 90.",
  Long: "Long",
  "Longitude, −180 to 180. Leave both lat & long empty to omit the coordinate.":
    "Longitude, −180 à 180. Laissez lat et long vides pour omettre la coordonnée.",
  "Longitude, −180 to 180.": "Longitude, −180 à 180.",
  "Hide on map": "Masquer sur la carte",
  "Plot this point on the map. Shown by default when a coordinate is set; tick to hide it while keeping the coordinate.":
    "Affiche ce point sur la carte. Affiché par défaut lorsqu'une coordonnée est définie ; cochez pour le masquer tout en gardant la coordonnée.",
  "Hide this point on the map.": "Masquer ce point sur la carte.",
  "Start coordinate": "Coordonnée de départ",
  "End coordinate": "Coordonnée d'arrivée",
  "Pick-up coordinate": "Coordonnée de prise en charge",
  "Drop-off coordinate": "Coordonnée de restitution",

  // ------------------------------------------------------------ Form sections
  Type: "Type",
  Waypoints: "Points de passage",
  "Nested activities": "Activités imbriquées",
  Activities: "Activités",
  "Secondary currencies": "Devises secondaires",
  "Activity {n}": "Activité {n}",
  "Waypoint {n}": "Point de passage {n}",
  "Currency {n}": "Devise {n}",
  waypoint: "point de passage",
  currency: "devise",
  "No waypoints — a road needs at least one (the arrival).":
    "Aucun point de passage — une route en nécessite au moins un (l'arrivée).",
  "Travel time is missing.": "Le temps de trajet est manquant.",
  "Distance is missing.": "La distance est manquante.",
  "Travel time and distance are missing.": "Le temps de trajet et la distance sont manquants.",
  "Check online to fill it.": "Vérifier en ligne pour le compléter.",
  "No nested activities.": "Aucune activité imbriquée.",
  "No activities — a day needs at least one.":
    "Aucune activité — un jour en nécessite au moins une.",
  "No secondary currencies.": "Aucune devise secondaire.",

  // ------------------------------------------------------ Activity type labels
  "Road / drive": "Route / trajet",
  "Point of interest": "Point d'intérêt",
  Place: "Lieu",
  Hike: "Randonnée",
  Meal: "Repas",
  Buffer: "Pause",

  // ------------------------------------------------------------- Enum options
  // POI categories
  museum: "musée",
  church: "église",
  building: "bâtiment",
  viewpoint: "point de vue",
  ruins: "ruines",
  castle: "château",
  temple: "temple",
  street: "rue",
  "natural park": "parc naturel",
  mountain: "montagne",
  lake: "lac",
  beach: "plage",
  waterfall: "cascade",
  other: "autre",
  // Hike routes
  loop: "boucle",
  back_and_forth: "aller-retour",
  one_way: "aller simple",
  // Transport types
  plane: "avion",
  train: "train",
  bus: "bus",
  taxi: "taxi",
  ferry: "ferry",
  // Accommodation types
  hotel: "hôtel",
  camping: "camping",
  "b&b": "chambre d'hôtes",
  // Car types
  regular: "standard",
  small: "petite",
  SUV: "SUV",
  "4x4": "4x4",
  // Meal types
  breakfast: "petit-déjeuner",
  lunch: "déjeuner",
  dinner: "dîner",
  brunch: "brunch",
  snack: "en-cas",
  picnic: "pique-nique",
  meal: "repas",
  // Statuses
  booked: "réservé",
  confirmed: "confirmé",

  // ------------------------------------------------------- Field labels/help
  // Travel description
  Title: "Titre",
  "Trip title (shown on the cover)": "Titre du voyage (affiché sur la couverture)",
  "The trip title shown on the cover. Required.":
    "Le titre du voyage affiché sur la couverture. Obligatoire.",
  Subtitle: "Sous-titre",
  "Line under the title": "Ligne sous le titre",
  "A line shown under the title on the cover. Optional — hidden when empty.":
    "Une ligne affichée sous le titre sur la couverture. Facultatif — masqué si vide.",
  "Start date": "Date de début",
  "inferred (earliest date)": "déduite (date la plus ancienne)",
  "Trip start date. Defaults to the earliest date across days, transport and accommodation.":
    "Date de début du voyage. Par défaut, la date la plus ancienne parmi les jours, transports et hébergements.",
  "End date": "Date de fin",
  "inferred (latest date)": "déduite (date la plus récente)",
  "Trip end date. Defaults to the latest date across days, transport and accommodation.":
    "Date de fin du voyage. Par défaut, la date la plus récente parmi les jours, transports et hébergements.",
  "Cover color": "Couleur de couverture",
  "Accent colour driving the whole palette. Defaults to #1f4e5f.":
    "Couleur d'accent qui définit toute la palette. Par défaut #1f4e5f.",
  Summary: "Résumé",
  "Paragraph shown on the cover": "Paragraphe affiché sur la couverture",
  "A paragraph shown on the cover. Optional — hidden when empty.":
    "Un paragraphe affiché sur la couverture. Facultatif — masqué si vide.",

  // Defaults
  "Start time": "Heure de début",
  "The first activity's start time each day. Defaults to 08:00.":
    "Heure de début de la première activité chaque jour. Par défaut 08:00.",
  "End time": "Heure de fin",
  "none (no check)": "aucune (pas de contrôle)",
  "The latest an activity should end; validation warns past it. No check when unset.":
    "L'heure limite à laquelle une activité devrait se terminer ; la validation avertit au-delà. Aucun contrôle si non défini.",
  // "Buffer" is defined once in the activity-type labels above (→ "Pause").
  "0 (no buffer)": "0 (aucune pause)",
  "Buffer auto-inserted between consecutive activities. Defaults to 0 (none).":
    "Pause insérée automatiquement entre activités consécutives. Par défaut 0 (aucune).",
  "Time zone": "Fuseau horaire",
  "Default UTC offset for all times (e.g. +02:00, UTC-3, Z). Defaults to GMT (UTC+0).":
    "Décalage UTC par défaut pour toutes les heures (ex. +02:00, UTC-3, Z). Par défaut GMT (UTC+0).",
  "Breakfast until": "Petit-déjeuner jusqu'à",
  "A meal starting before this is inferred as breakfast. Defaults to 10:00.":
    "Un repas commençant avant cette heure est déduit comme petit-déjeuner. Par défaut 10:00.",
  "Lunch until": "Déjeuner jusqu'à",
  "A meal up to this (after breakfast) is lunch; later is dinner. Defaults to 16:00.":
    "Un repas jusqu'à cette heure (après le petit-déjeuner) est un déjeuner ; plus tard, un dîner. Par défaut 16:00.",
  "Meal duration": "Durée du repas",
  "0 (instant)": "0 (instantané)",
  "Default length of a meal with no duration/end time. Defaults to 0 (instant).":
    "Durée par défaut d'un repas sans durée/heure de fin. Par défaut 0 (instantané).",
  Currency: "Devise",
  "The currency every price is in unless it sets its own. 3-letter ISO code. Defaults to EUR.":
    "La devise de tous les prix, sauf mention contraire. Code ISO à 3 lettres. Par défaut EUR.",
  "Include maps in render": "Inclure les cartes au rendu",
  "Draw a per-day map with a pin for each located activity. Defaults to off.":
    "Dessiner une carte par jour avec une épingle pour chaque activité localisée. Désactivé par défaut.",
  "Infer coordinates from address": "Déduire les coordonnées depuis l'adresse",
  "Geocode activities that lack an explicit coordinate. Defaults to off (only explicit coordinates are mapped).":
    "Géocoder les activités sans coordonnée explicite. Désactivé par défaut (seules les coordonnées explicites sont cartographiées).",
  "Inference countries": "Pays d'inférence",
  "Restrict geocoding to these 2-letter ISO codes (e.g. FR, ES). Defaults to any country.":
    "Limiter le géocodage à ces codes ISO à 2 lettres (ex. FR, ES). Par défaut, tous les pays.",

  // Secondary currency
  USD: "USD",
  "The secondary currency's 3-letter ISO code. Required.":
    "Le code ISO à 3 lettres de la devise secondaire. Obligatoire.",
  Rate: "Taux",
  "units per 1 default (1 € = 1.09 $ → 1.09)": "unités pour 1 par défaut (1 € = 1,09 $ → 1,09)",
  "Units of this currency per one unit of the default currency (e.g. 1 € = 1.09 $ → 1.09). Required.":
    "Unités de cette devise pour une unité de la devise par défaut (ex. 1 € = 1,09 $ → 1,09). Obligatoire.",

  // Day
  "The day's title": "Le titre du jour",
  "The day's title. Required.": "Le titre du jour. Obligatoire.",
  City: "Ville",
  "City/region label": "Libellé ville/région",
  "City/region label for the day. Optional.": "Libellé ville/région pour le jour. Facultatif.",
  Date: "Date",
  "trip start + the day's index": "début du voyage + l'indice du jour",
  "The day's date, matched to stays & transport. Defaults to the trip start date plus the day's index.":
    "La date du jour, alignée sur les séjours et transports. Par défaut, la date de début du voyage plus l'indice du jour.",
  Description: "Description",
  "Intro paragraph for the day": "Paragraphe d'introduction du jour",
  "Intro paragraph for the day. Optional.": "Paragraphe d'introduction du jour. Facultatif.",

  // Scheduled (shared)
  "previous item's end / defaults.start_time":
    "fin de l'élément précédent / defaults.start_time",
  "Clock time this activity starts. Defaults to the previous item's end (or defaults.start_time for the first).":
    "Heure de début de cette activité. Par défaut, la fin de l'élément précédent (ou defaults.start_time pour le premier).",
  "start + duration": "début + durée",
  "Clock time this activity ends. Inferred from start + duration when unset.":
    "Heure de fin de cette activité. Déduite de début + durée si non définie.",
  Duration: "Durée",
  "1h30 / 45 min": "1h30 / 45 min",
  "How long it lasts (e.g. 1h30, 45 min). Inferred from start/end when unset, else 0.":
    "Durée (ex. 1h30, 45 min). Déduite de début/fin si non définie, sinon 0.",
  "Start tz": "Fuseau de début",
  "Start time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire de début (décalage UTC). Par défaut defaults.timezone (GMT).",
  "End tz": "Fuseau de fin",
  "End time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire de fin (décalage UTC). Par défaut defaults.timezone (GMT).",

  // Road
  "Start (departure)": "Départ",
  "Departure address": "Adresse de départ",
  "Departure address/name; also the map route's start. Required.":
    "Adresse/nom de départ ; aussi le début de l'itinéraire sur la carte. Obligatoire.",
  "Distance (km)": "Distance (km)",
  "driving distance": "distance routière",
  "Total driving distance in km. Optional.": "Distance routière totale en km. Facultatif.",
  "Off-road": "Hors-piste",
  "Highlight off-road sections. Defaults to off.":
    "Mettre en évidence les sections hors-piste. Désactivé par défaut.",

  // POI
  Name: "Nom",
  "Point-of-interest name": "Nom du point d'intérêt",
  "Point-of-interest name. Required.": "Nom du point d'intérêt. Obligatoire.",
  Category: "Catégorie",
  "The kind of place, shown as a badge. Defaults to 'other'.":
    "Le type de lieu, affiché comme badge. Par défaut « other ».",
  Address: "Adresse",
  "Street address. Optional.": "Adresse postale. Facultatif.",
  "A description. Optional.": "Une description. Facultatif.",
  Website: "Site web",
  "Link to the venue's website, shown as a clickable link. Optional.":
    "Lien vers le site du lieu, affiché comme lien cliquable. Facultatif.",

  // Place
  "Place name": "Nom du lieu",
  "Place name (e.g. a town) grouping the nested activities. Required.":
    "Nom du lieu (ex. une ville) regroupant les activités imbriquées. Obligatoire.",

  // Hike
  "Hike name": "Nom de la randonnée",
  "Hike name. Required.": "Nom de la randonnée. Obligatoire.",
  "Distance in km. Optional.": "Distance en km. Facultatif.",
  "Elevation (m)": "Dénivelé (m)",
  "Elevation gain in m. Optional.": "Dénivelé positif en m. Facultatif.",
  "Start (trailhead)": "Départ (point de départ)",
  "Trailhead address. Optional.": "Adresse du point de départ. Facultatif.",
  End: "Fin",
  "End address. For a loop/back-and-forth it should equal (or omit) start; for one-way it should differ. Optional.":
    "Adresse d'arrivée. Pour une boucle/un aller-retour, elle devrait être identique au départ (ou omise) ; pour un aller simple, elle devrait différer. Facultatif.",
  Route: "Parcours",
  "Route shape. Defaults to back_and_forth.":
    "Forme du parcours. Par défaut back_and_forth.",

  // Meal
  "Meal type": "Type de repas",
  "inferred from start_time": "déduit de start_time",
  "Which meal it is. Inferred from the start time when unset (breakfast/lunch/dinner); the others are explicit-only.":
    "De quel repas il s'agit. Déduit de l'heure de début si non défini (petit-déjeuner/déjeuner/dîner) ; les autres sont explicites uniquement.",
  Restaurant: "Restaurant",
  "Restaurant name; shown in the head and the cover highlights. Optional.":
    "Nom du restaurant ; affiché dans l'en-tête et les temps forts de la couverture. Facultatif.",
  Area: "Zone",
  "Town/region to eat in, used when no restaurant is named. Optional.":
    "Ville/région où manger, utilisée quand aucun restaurant n'est nommé. Facultatif.",

  // Buffer
  "Length of the free time": "Durée du temps libre",
  "Length of the free time (e.g. 30 min). A 0 min buffer just suppresses the default buffer here. Required.":
    "Durée du temps libre (ex. 30 min). Une pause de 0 min supprime simplement la pause par défaut ici. Obligatoire.",

  // Waypoint
  Location: "Lieu",
  "The waypoint's name": "Le nom du point de passage",
  "The waypoint's name. Optional — an unnamed waypoint still draws a map pin but merges into the next named leg.":
    "Le nom du point de passage. Facultatif — un point de passage sans nom pose quand même une épingle mais fusionne avec le tronçon nommé suivant.",
  "Leg duration": "Durée du tronçon",
  "Driving time for the leg reaching this waypoint. Optional.":
    "Temps de conduite du tronçon menant à ce point de passage. Facultatif.",
  "Leg distance (km)": "Distance du tronçon (km)",
  "Driving distance for the leg reaching this waypoint. Optional.":
    "Distance routière du tronçon menant à ce point de passage. Facultatif.",

  // Transport
  "Transport kind, shown as a badge. Defaults to 'other'.":
    "Type de transport, affiché comme badge. Par défaut « other ».",
  "Departure address. Required.": "Adresse de départ. Obligatoire.",
  "End (arrival)": "Arrivée",
  "Arrival address": "Adresse d'arrivée",
  "Arrival address. Required.": "Adresse d'arrivée. Obligatoire.",
  "Departure date; slots the leg into that day. Required.":
    "Date de départ ; place le trajet dans ce jour. Obligatoire.",
  "inferred (+1 day if crosses midnight)": "déduite (+1 jour si passage à minuit)",
  "Arrival date. Inferred (+1 day if the leg crosses midnight).":
    "Date d'arrivée. Déduite (+1 jour si le trajet passe minuit).",
  "Departure time. Required.": "Heure de départ. Obligatoire.",
  "Arrival time. Inferred from start + duration when unset.":
    "Heure d'arrivée. Déduite de début + durée si non définie.",
  "inferred from the two times": "déduite des deux heures",
  "Travel time. Inferred from the two times when unset.":
    "Temps de trajet. Déduit des deux heures si non défini.",
  "Departure time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire de départ (décalage UTC). Par défaut defaults.timezone (GMT).",
  "Arrival time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire d'arrivée (décalage UTC). Par défaut defaults.timezone (GMT).",
  "Flight number": "Numéro de vol",
  "Flight number (planes only), shown on the card. Optional.":
    "Numéro de vol (avions uniquement), affiché sur la carte. Facultatif.",
  "Train number": "Numéro de train",
  "Train number (trains only), shown on the card. Optional.":
    "Numéro de train (trains uniquement), affiché sur la carte. Facultatif.",
  "Booking number": "Numéro de réservation",
  "Reservation reference / PNR. Optional.": "Référence de réservation / PNR. Facultatif.",
  "Booking source": "Source de réservation",
  "Where it was booked. Optional.": "Où la réservation a été faite. Facultatif.",
  "Link to the carrier's website. Optional.":
    "Lien vers le site du transporteur. Facultatif.",
  "Booking link": "Lien de réservation",
  "Direct link to this reservation. Optional.":
    "Lien direct vers cette réservation. Facultatif.",
  Status: "Statut",
  "none (no badge)": "aucun (pas de badge)",
  "Reservation status, shown as a badge. No badge when unset.":
    "Statut de la réservation, affiché comme badge. Aucun badge si non défini.",
  Price: "Prix",
  "amount only, no symbol": "montant seul, sans symbole",
  "Ticket price (amount only, no symbol). Optional.":
    "Prix du billet (montant seul, sans symbole). Facultatif.",
  "Currency this price is in (3-letter ISO). Defaults to defaults.currency.":
    "Devise de ce prix (ISO à 3 lettres). Par défaut defaults.currency.",
  Paid: "Payé",
  "Payment state, shown as a badge. No badge when unset.":
    "État du paiement, affiché comme badge. Aucun badge si non défini.",

  // Accommodation
  "Accommodation name. Required.": "Nom de l'hébergement. Obligatoire.",
  "Arrival (check-in)": "Arrivée (check-in)",
  "Check-in date; the stay covers nights from here up to (not including) departure. Required.":
    "Date d'arrivée ; le séjour couvre les nuits d'ici jusqu'au départ (exclu). Obligatoire.",
  "Departure (check-out)": "Départ (check-out)",
  "Check-out date; the checkout day shows no stay bar. Required.":
    "Date de départ ; le jour du départ n'affiche pas de barre de séjour. Obligatoire.",
  "Town shown in the cover overview. Required.":
    "Ville affichée dans le récapitulatif de couverture. Obligatoire.",
  "Kind of accommodation, shown as a badge. Defaults to 'hotel'.":
    "Type d'hébergement, affiché comme badge. Par défaut « hotel ».",
  Contact: "Contact",
  "phone or email": "téléphone ou e-mail",
  "Phone or email. Optional.": "Téléphone ou e-mail. Facultatif.",
  "Link to the property's website. Optional.":
    "Lien vers le site de l'établissement. Facultatif.",
  "whole-stay amount, no symbol": "montant du séjour complet, sans symbole",
  "Price for the whole stay (amount only, no symbol). Optional.":
    "Prix pour l'ensemble du séjour (montant seul, sans symbole). Facultatif.",
  "Breakfast included": "Petit-déjeuner inclus",
  "Show a 'Breakfast included' line. Defaults to off.":
    "Afficher une ligne « Petit-déjeuner inclus ». Désactivé par défaut.",

  // Car rental
  "Booking start date": "Date de début de réservation",
  "Start of the booking window. The pick-up/drop-off must fall inside it. Required.":
    "Début de la période de réservation. La prise en charge/restitution doit s'y situer. Obligatoire.",
  "Booking start time": "Heure de début de réservation",
  "Booking-window start time. Required.":
    "Heure de début de la période de réservation. Obligatoire.",
  "Booking start tz": "Fuseau de début de réservation",
  "Booking-start time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire du début de réservation (décalage UTC). Par défaut defaults.timezone (GMT).",
  "Booking end date": "Date de fin de réservation",
  "End of the booking window. Required.":
    "Fin de la période de réservation. Obligatoire.",
  "Booking end time": "Heure de fin de réservation",
  "Booking-window end time. Required.":
    "Heure de fin de la période de réservation. Obligatoire.",
  "Booking end tz": "Fuseau de fin de réservation",
  "Booking-end time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire de la fin de réservation (décalage UTC). Par défaut defaults.timezone (GMT).",
  "Pick-up date": "Date de prise en charge",
  "Pick-up date; must be within the booking window. Woven into that day. Required.":
    "Date de prise en charge ; doit être dans la période de réservation. Intégrée à ce jour. Obligatoire.",
  "Pick-up time": "Heure de prise en charge",
  "Pick-up time. Required.": "Heure de prise en charge. Obligatoire.",
  "Pick-up tz": "Fuseau de prise en charge",
  "Pick-up time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire de prise en charge (décalage UTC). Par défaut defaults.timezone (GMT).",
  "Pick-up location": "Lieu de prise en charge",
  "Where you pick up the car. Required.": "Où récupérer la voiture. Obligatoire.",
  "Pick-up duration": "Durée de prise en charge",
  "How long the pick-up takes. Optional (not shown when unset).":
    "Durée de la prise en charge. Facultatif (non affiché si non défini).",
  "Drop-off date": "Date de restitution",
  "Drop-off date; must be within the booking window and not before pick-up. Required.":
    "Date de restitution ; doit être dans la période de réservation et pas avant la prise en charge. Obligatoire.",
  "Drop-off time": "Heure de restitution",
  "Drop-off time. Required.": "Heure de restitution. Obligatoire.",
  "Drop-off tz": "Fuseau de restitution",
  "Drop-off time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire de restitution (décalage UTC). Par défaut defaults.timezone (GMT).",
  "Drop-off location": "Lieu de restitution",
  "the pick-up location": "le lieu de prise en charge",
  "Where you drop off the car. Defaults to the pick-up location.":
    "Où restituer la voiture. Par défaut, le lieu de prise en charge.",
  "Drop-off duration": "Durée de restitution",
  "How long the drop-off takes. Optional (not shown when unset).":
    "Durée de la restitution. Facultatif (non affiché si non défini).",
  Company: "Société",
  "Rental company. Optional.": "Société de location. Facultatif.",
  "Reservation reference. Optional.": "Référence de réservation. Facultatif.",
  "Link to the rental company's website. Optional.":
    "Lien vers le site de la société de location. Facultatif.",
  "Rental price (amount only, no symbol). Optional.":
    "Prix de la location (montant seul, sans symbole). Facultatif.",
  "Car type": "Type de voiture",
  "Car category, shown as a badge. Defaults to 'regular'.":
    "Catégorie de voiture, affichée comme badge. Par défaut « regular ».",
  "Car model": "Modèle de voiture",
  "Car make/model. Optional.": "Marque/modèle de la voiture. Facultatif.",
  "Phone or email for the rental company. Optional.":
    "Téléphone ou e-mail de la société de location. Facultatif.",
  "Additional drivers": "Conducteurs supplémentaires",
  "Number of additional drivers. Defaults to 0.":
    "Nombre de conducteurs supplémentaires. Par défaut 0.",

  // ---------------------------------------------------------- 🤖 LLM prompts
  "🤖 LLM prompts": "🤖 Prompts IA",
  "LLM prompts": "Prompts IA",
  "Ready-made prompts that turn your raw trip material into itinerary JSON — or help you fill its gaps. Copy one, paste it into your favourite LLM (Claude, ChatGPT…), and add your own documents.":
    "Des prompts prêts à l'emploi qui transforment vos documents de voyage en JSON d'itinéraire — ou vous aident à en combler les manques. Copiez-en un, collez-le dans votre IA préférée (Claude, ChatGPT…), puis ajoutez vos propres documents.",
  "Give it": "À fournir",
  "You get": "Résultat",
  "📋 Copy prompt": "📋 Copier le prompt",
  "✓ Copied": "✓ Copié",
  "Couldn't load this prompt.": "Impossible de charger ce prompt.",
  "Paste it into an LLM chat, then add your material.":
    "Collez-le dans une IA, puis ajoutez vos documents.",

  "Build the full itinerary JSON": "Construire le JSON complet de l'itinéraire",
  "Turns raw trip material into one complete, ready-to-render itinerary JSON file. The prompt is self-contained: it carries every field, value format and rule the LLM needs to get the JSON right on the first pass.":
    "Transforme vos documents de voyage en un fichier JSON d'itinéraire complet, prêt à être rendu. Le prompt est autonome : il contient tous les champs, formats de valeurs et règles dont l'IA a besoin pour produire un JSON correct du premier coup.",
  "Your trip material — a brief, a day-by-day plan, booking-confirmation emails, hotel/rental vouchers, screenshots, a guidebook PDF, links to blog posts, or a KML/KMZ track (e.g. exported from a custom Google Map).":
    "Vos documents de voyage — un brief, un programme jour par jour, des e-mails de confirmation, des bons d'hôtel/location, des captures d'écran, un PDF de guide, des liens vers des articles de blog, ou une trace KML/KMZ (par ex. exportée depuis une carte Google personnalisée).",
  "The more concrete the sources, the fewer gaps the LLM has to leave blank.":
    "Plus les sources sont concrètes, moins l'IA laisse de champs vides.",
  "A single <title>.json you can open here (Options → Open JSON…), plus a report of the gaps and any conflicts it found between your sources.":
    "Un seul fichier <titre>.json que vous pouvez ouvrir ici (Options → Ouvrir JSON…), ainsi qu'un rapport des manques et des éventuels conflits entre vos sources.",

  "Build a Google My Maps KML from a guidebook PDF":
    "Créer un KML Google My Maps à partir d'un PDF de guide",
  "Turns a guidebook PDF into an importable KML map: one placemark per place, grouped into folders by region, color-coded by category, with page references, descriptions and hike stats. The result is a custom Google Map you can then export as KML/KMZ and feed to the itinerary-JSON prompt above.":
    "Transforme un PDF de guide en une carte KML importable : un repère par lieu, regroupés en dossiers par région, avec un code couleur par catégorie, des références de pages, des descriptions et des données de randonnée. Le résultat est une carte Google personnalisée que vous pouvez ensuite exporter en KML/KMZ et fournir au prompt de JSON d'itinéraire ci-dessus.",
  "A guidebook PDF — even a scanned, image-only one (the prompt reads pages visually rather than assuming selectable text).":
    "Un PDF de guide — même scanné, en images seules (le prompt lit les pages visuellement plutôt que de supposer un texte sélectionnable).",
  "Optionally, a list of nearby-city road distances / driving times to attach to city placemarks.":
    "Éventuellement, une liste de distances routières / temps de trajet vers les villes voisines à joindre aux repères de villes.",
  "A grouped, color-coded guidebook_places_grouped_colored.kml, ready to import into Google My Maps — plus the source CSVs and scripts to rebuild it.":
    "Un fichier guidebook_places_grouped_colored.kml regroupé et coloré, prêt à importer dans Google My Maps — avec les CSV sources et les scripts pour le régénérer.",

  "Fix missing durations & distances": "Compléter les durées et distances manquantes",
  "Builds a fill-in-the-blank Markdown worksheet for the roads, hikes and activities that are missing a duration, distance or elevation — one entry per missing value, with Google Maps links for road distances and web-sourced estimates (tagged “to be checked”) for hikes.":
    "Construit une fiche Markdown à compléter pour les routes, randonnées et activités auxquelles il manque une durée, une distance ou un dénivelé — une entrée par valeur manquante, avec des liens Google Maps pour les distances routières et des estimations issues du web (marquées « à vérifier ») pour les randonnées.",
  "Your itinerary JSON.": "Votre JSON d'itinéraire.",
  "The ⚠️ warnings about missing duration/distance/elevation — copy them from the 🔎 Findings tab (or the validator output).":
    "Les avertissements ⚠️ concernant les durées/distances/dénivelés manquants — copiez-les depuis l'onglet 🔎 Diagnostics (ou la sortie du validateur).",
  "A <title>-missing.md worksheet to complete by hand, then merge the figures back into your JSON.":
    "Une fiche <titre>-missing.md à compléter à la main, puis à réintégrer dans votre JSON.",
};
