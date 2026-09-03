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
  "🗺️ Overview": "🗺️ Aperçu",
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
  "Current version: {hash} ({date})": "Version actuelle : {hash} ({date})",
  "Current version: {hash}": "Version actuelle : {hash}",
  "View this commit on GitHub": "Voir ce commit sur GitHub",

  // Boot stages
  "Starting…": "Démarrage…",
  "Loading Python runtime…": "Chargement de l'environnement Python…",
  "Installing packages…": "Installation des paquets…",
  "Installing Odysseyra TravelBook…": "Installation d'Odysseyra TravelBook…",
  Ready: "Prêt",
  "Engine failed to start": "Échec du démarrage du moteur",

  // The loader (ActivityIndicator) — what the engine is busy with
  "Reading the itinerary…": "Lecture de l'itinéraire…",
  "Applying changes…": "Application des modifications…",
  "Building the PDF…": "Génération du PDF…",
  "Building the calendar…": "Génération du calendrier…",
  "Drawing maps — day {day} of {total}": "Tracé des cartes — jour {day} sur {total}",
  "Redrawing the maps…": "Régénération des cartes…",

  // Empty / error states
  "Can't render this itinerary yet": "Impossible d'afficher cet itinéraire pour l'instant",
  "The itinerary couldn't be built.": "L'itinéraire n'a pas pu être construit.",
  "Fix the errors in {findings} or {edit}, then {apply} to render it here.":
    "Corrigez les erreurs dans {findings} ou {edit}, puis {apply} pour l'afficher ici.",
  "Apply changes": "Appliquer les modifications",
  "Open an itinerary": "Ouvrir un itinéraire",
  "Render your travel book and see its validation findings. Everything stays on your device.":
    "Affichez votre carnet de voyage et consultez ses diagnostics de validation. Tout reste sur votre appareil.",
  "Create a blank itinerary, open an existing JSON file, or just try the app with our demo — and if you're new, check the usage guide.":
    "Créez un itinéraire vierge, ouvrez un fichier JSON existant, ou essayez simplement l'application avec notre démo — et si vous débutez, consultez le guide d'utilisation.",
  "➕ Create blank": "➕ Créer un vierge",
  "🚀 Demo": "🚀 Démo",
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
  "Show weather forecast": "Afficher la météo",
  "Fetch a weather forecast (from Open-Meteo) for each located activity in the next 7 days, shown as a small chip on its title; needs a connection":
    "Récupérer la météo (via Open-Meteo) pour chaque activité localisée dans les 7 prochains jours, affichée en petite pastille sur son titre ; nécessite une connexion",
  "Show more": "Voir plus",
  "Show less": "Voir moins",
  "Open an itinerary, reopen the last one, or load a bundled sample.":
    "Ouvrez un itinéraire, rouvrez le dernier, ou chargez un exemple fourni.",
  "Create a new itinerary, open one, reopen the last one, or load a bundled sample.":
    "Créez un nouvel itinéraire, ouvrez-en un, rouvrez le dernier, ou chargez un exemple fourni.",
  "Start a new blank itinerary and edit it from scratch":
    "Démarrer un nouvel itinéraire vierge et le composer de zéro",
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
  "📂 Open JSON…": "📂 Ouvrir un JSON…",
  "Reopen the last opened file": "Rouvrir le dernier fichier ouvert",
  "Reopen last": "Rouvrir le dernier",
  "Load the bundled France sample itinerary": "Charger l'itinéraire d'exemple de France",
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
  "Calendar export": "Export calendrier",
  "Export the trip as an .ics calendar file you can import into Google Calendar (activities, transport, car rentals and accommodation — timezone-aware).":
    "Exportez le voyage en fichier calendrier .ics importable dans Google Agenda (activités, transports, locations de voiture et hébergements — avec fuseaux horaires).",
  "Download an .ics file with one event per activity, transport leg, car pick-up/drop-off and accommodation booking":
    "Télécharger un fichier .ics avec un événement par activité, trajet, prise/restitution de voiture et réservation d'hébergement",
  "Export ICS (calendar)": "Exporter en ICS (calendrier)",
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
  "🔄 Update app": "🔄 Mettre à jour l'appli",
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
  Legs: "Trajets",
  "Leg {n}": "Trajet {n}",
  "No legs — a transport needs at least one (a single-hop booking has one).":
    "Aucun trajet — un transport en nécessite au moins un (une réservation directe en compte un).",
  "Accommodation {n}": "Hébergement {n}",
  "Car rental {n}": "Location de voiture {n}",
  day: "jour",
  transport: "transport",
  leg: "trajet",
  accommodation: "hébergement",
  "car rental": "location de voiture",
  "No days yet — an itinerary needs at least one.":
    "Aucun jour — un itinéraire en nécessite au moins un.",
  "No transport bookings.": "Aucune réservation de transport.",
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
  "Plot this point on the map. Shown by default when a coordinate is set; switch this on to hide it while keeping the coordinate.":
    "Affiche ce point sur la carte. Affiché par défaut lorsqu'une coordonnée est définie ; activez pour le masquer tout en gardant la coordonnée.",
  "Hide this point on the map.": "Masquer ce point sur la carte.",
  "Start coordinate": "Coordonnée de départ",
  "End coordinate": "Coordonnée d'arrivée",
  "Pick-up coordinate": "Coordonnée de prise en charge",
  "Drop-off coordinate": "Coordonnée de restitution",

  // ------------------------------------------------------------ Form sections
  Type: "Type",
  // A road's legs are "étapes"; a transport booking's are "trajets" (below).
  "Drive legs": "Étapes du trajet",
  "Drive leg {n}": "Étape {n}",
  "drive leg": "étape",
  "Route waypoints": "Points de passage de l'itinéraire",
  "Nested activities": "Activités imbriquées",
  Activities: "Activités",
  // The `defaults` box's group titles
  "Day timing": "Horaires de la journée",
  Meals: "Repas",
  "Accommodation nights": "Nuits d'hébergement",
  Money: "Argent",
  // "Maps" is already keyed in the Options section above.
  "Sun & moon": "Soleil et lune",
  "Secondary currencies": "Devises secondaires",
  "1 {new} = {x} {main} and 1 {main} = {y} {new}":
    "1 {new} = {x} {main} et 1 {main} = {y} {new}",
  "Activity {n}": "Activité {n}",
  "Waypoint {n}": "Point de passage {n}",
  "Currency {n}": "Devise {n}",
  waypoint: "point de passage",
  currency: "devise",
  "No legs — a road needs at least one (its departure to its arrival).":
    "Aucune étape — une route en nécessite au moins une (de son départ à son arrivée).",
  "One leg per hop of the drive. Leave a leg's From blank to reuse the previous leg's To.":
    "Une étape par tronçon du trajet. Laissez le « De » d'une étape vide pour reprendre le « À » de la précédente.",
  "Points the route bends through between this leg's two ends — coordinates only, in travel order.":
    "Les points par lesquels passe l'itinéraire entre les deux extrémités de cette étape — des coordonnées seulement, dans l'ordre du parcours.",
  "No waypoints — the route runs straight between the leg's two ends.":
    "Aucun point de passage — l'itinéraire va tout droit entre les deux extrémités de l'étape.",
  "Travel time is missing.": "Le temps de trajet est manquant.",
  "Distance is missing.": "La distance est manquante.",
  "Travel time and distance are missing.": "Le temps de trajet et la distance sont manquants.",
  "Check online to fill it.": "Vérifier en ligne pour le compléter.",
  "No nested activities.": "Aucune activité imbriquée.",
  "No activities — a day needs at least one.":
    "Aucune activité — un jour en nécessite au moins une.",
  "No secondary currencies.": "Aucune devise secondaire.",
  // The `misc` group and its emergency contacts
  Misc: "Divers",
  "Emergency contacts ({n})": "Numéros d'urgence ({n})",
  "Who to call where you're going. Shown in the 🗺️ Overview tab and on the book's last page. Leave a number out rather than guessing it.":
    "Qui appeler là où vous allez. Affichés dans l'onglet 🗺️ Aperçu et sur la dernière page du livre. Mieux vaut omettre un numéro que de le deviner.",
  "Contact {n}": "Contact {n}",
  contact: "contact",
  "No emergency contacts.": "Aucun numéro d'urgence.",

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
  "Where each day's last activity should land: auto-sized buffers spread the day out to it, and validation warns past it. Defaults to 18:00.":
    "L'heure où devrait tomber la dernière activité de chaque journée : les pauses dimensionnées étalent la journée jusque-là, et la validation avertit au-delà. Par défaut 18:00.",
  "Auto-sized buffer": "Pause dimensionnée",
  "Size the buffers between a day's activities so the day spreads out and ends on “End time”, in steps of 5 min. Defaults to on — switch it off to fall back to the fixed “Buffer” below.":
    "Dimensionne les pauses entre les activités d'une journée pour l'étaler jusqu'à « Heure de fin », par pas de 5 min. Activé par défaut — désactivez pour revenir à la « Pause » fixe ci-dessous.",
  // "Buffer" is defined once in the activity-type labels above (→ "Pause").
  "0 (no fixed buffer)": "0 (aucune pause fixe)",
  "A fixed buffer inserted between consecutive activities. Ignored while “Auto-sized buffer” is on. Defaults to 0 (none).":
    "Pause fixe insérée entre activités consécutives. Ignorée tant que « Pause dimensionnée » est activée. Par défaut 0 (aucune).",
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
  "Accommodation start time": "Heure de début d'hébergement",
  "Clock time an accommodation booking starts on the calendar (ICS export). Defaults to 22:00.":
    "Heure à laquelle une réservation d'hébergement commence dans le calendrier (export ICS). Par défaut 22:00.",
  "Accommodation end time": "Heure de fin d'hébergement",
  "Clock time each accommodation night ends on the calendar (ICS export). Defaults to 00:00 (midnight).":
    "Heure à laquelle chaque nuit d'hébergement se termine dans le calendrier (export ICS). Par défaut 00:00 (minuit).",
  Currency: "Devise",
  "The currency every price is in unless it sets its own. 3-letter ISO code. Defaults to EUR.":
    "La devise de tous les prix, sauf mention contraire. Code ISO à 3 lettres. Par défaut EUR.",
  "Include maps in render": "Inclure les cartes au rendu",
  "Draw a per-day map with a pin for each located activity. Defaults to off.":
    "Dessiner une carte par jour avec une épingle pour chaque activité localisée. Désactivé par défaut.",
  "Include hike maps": "Inclure les cartes de randonnée",
  "Draw the trail map and elevation profile of any hike that attaches a GPX file. Independent of “Include maps in render”, since the track comes with the hike. Defaults to on — switch it off to hide them.":
    "Dessiner le tracé et le profil altimétrique de toute randonnée à laquelle un fichier GPX est joint. Indépendant de « Inclure les cartes au rendu », puisque la trace accompagne la randonnée. Activé par défaut — désactivez pour les masquer.",
  "Infer coordinates from address": "Déduire les coordonnées depuis l'adresse",
  "Geocode activities that lack an explicit coordinate. Defaults to off (only explicit coordinates are mapped).":
    "Géocoder les activités sans coordonnée explicite. Désactivé par défaut (seules les coordonnées explicites sont cartographiées).",
  "Inference countries": "Pays d'inférence",
  "Restrict geocoding to these 2-letter ISO codes (e.g. FR, ES). Defaults to any country.":
    "Limiter le géocodage à ces codes ISO à 2 lettres (ex. FR, ES). Par défaut, tous les pays.",
  "Show moon phase": "Afficher la phase de lune",
  "Show the night's moon phase — closing the sunrise/sunset line when that is shown too, otherwise in the day's “tonight” section. Defaults to on — switch it off to hide it.":
    "Afficher la phase de lune de la nuit — à la fin de la ligne lever/coucher du soleil quand celle-ci est affichée, sinon dans la section « cette nuit » du jour. Activé par défaut — désactivez pour la masquer.",
  "Show sunrise/sunset": "Afficher lever/coucher du soleil",
  "Show each day's sunrise and sunset in its header, computed at that night's accommodation. Defaults to on — switch it off to hide them.":
    "Afficher le lever et le coucher du soleil de chaque jour dans son en-tête, calculés à l'hébergement de la nuit. Activé par défaut — désactivez pour les masquer.",

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
  "Bank holiday": "Jour férié",
  "Switch on if the day is a public holiday where you are — the day then opens with a banner warning about closures and reduced hours. Defaults to off.":
    "Activez si le jour est un jour férié là où vous êtes — le jour s'ouvre alors sur une bannière signalant fermetures et horaires réduits. Désactivé par défaut.",

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
  // a place alone falls back to what it contains (PLACE_SCHEDULED_FIELDS)
  "the nested activities' total": "le total des activités imbriquées",
  "How long it lasts (e.g. 1h30, 45 min). Defaults to the nested activities' total — a place is what you do there. Inferred from start/end when those are given.":
    "Durée (ex. 1h30, 45 min). Par défaut, le total des activités imbriquées — un lieu, c'est ce qu'on y fait. Déduite de début/fin si les deux sont donnés.",
  "Start tz": "Fuseau de début",
  "Start time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire de début (décalage UTC). Par défaut defaults.timezone (GMT).",
  "End tz": "Fuseau de fin",
  "End time zone (UTC offset). Defaults to defaults.timezone (GMT).":
    "Fuseau horaire de fin (décalage UTC). Par défaut defaults.timezone (GMT).",
  Detour: "Détour",
  "A stop you probably won't make but want the book to carry anyway. It's left off the day's timeline — it takes no time and gets no buffer before it — and it's shown a step down in emphasis, with its duration but no start/end time (a time written here is dropped). Defaults to off.":
    "Une étape que vous ne ferez probablement pas mais que vous voulez garder dans le carnet. Elle reste hors du programme de la journée — elle ne prend pas de temps et n'a pas de pause avant elle — et s'affiche en retrait, avec sa durée mais sans horaire (un horaire saisi ici est ignoré). Désactivé par défaut.",

  // An activity's fee and contact — offered on every type, like Detour above.
  "12 / 7.5": "12 / 7,5",
  'What this stop costs — an entrance fee, a guided visit, a meal. A bare number with no currency symbol. 0 is meaningful and prints as "Free". There\'s no paid/to-pay flag: a fee at the gate has nothing to settle in advance.':
    "Ce que coûte cette étape — un droit d'entrée, une visite guidée, un repas. Un nombre seul, sans symbole monétaire. 0 est une information et s'affiche « Gratuit ». Pas d'indicateur payé/à payer : un droit d'entrée sur place n'a rien à régler à l'avance.",
  "The 3-letter ISO code of this price. Defaults to defaults.currency, and must be that or one of defaults.secondary_currencies so there's a rate to convert it with.":
    "Le code ISO à 3 lettres de ce prix. Par défaut defaults.currency ; il doit être celui-ci ou l'une des defaults.secondary_currencies pour qu'un taux de conversion existe.",
  "+996 700 732 984": "+996 700 732 984",
  'A phone number, an email, or how to get in ("call the guardian to open the museum"). Free text, never parsed. Shown as its own labelled row; the viewer links a phone number or email.':
    "Un numéro de téléphone, un e-mail, ou comment entrer (« appeler le gardien pour ouvrir le musée »). Texte libre, jamais analysé. Affiché sur sa propre ligne intitulée ; la visionneuse transforme un numéro ou un e-mail en lien.",

  // Guidebook pages — one wording shared by road / POI / place / hike
  "Guidebook pages": "Pages du guide",
  "14 / 15-18 / 16, 23, 25-30": "14 / 15-18 / 16, 23, 25-30",
  "The guidebook page(s) covering this activity — a single page, a range, or a comma-separated list (e.g. 14, 15-18, 16, 23, 25-30). Shown as a light-accent pill at the end of the description. Optional.":
    "La ou les pages du guide qui traitent de cette activité — une page, une plage, ou une liste séparée par des virgules (ex. 14, 15-18, 16, 23, 25-30). Affichées dans une pastille d'accent clair à la fin de la description. Facultatif.",

  // Road
  "Distance (km)": "Distance (km)",
  "driving distance": "distance routière",
  "Total driving distance in km for the whole drive (each leg carries its own too). Optional.":
    "Distance routière totale en km pour tout le trajet (chaque étape porte aussi la sienne). Facultatif.",
  "Pin the departure": "Épingler le départ",
  "Give the drive's departure a numbered pin on the day map. Defaults to off — a drive is drawn as a route, and its pins are opt-in.":
    "Donner au départ du trajet une épingle numérotée sur la carte du jour. Désactivé par défaut — un trajet est dessiné comme un itinéraire, ses épingles s'activent au cas par cas.",
  "Pin the arrival": "Épingler l'arrivée",
  "Give the drive's final arrival a numbered pin on the day map. Defaults to off.":
    "Donner à l'arrivée finale du trajet une épingle numérotée sur la carte du jour. Désactivé par défaut.",
  "Pin the junctions": "Épingler les jonctions",
  "Give every junction between two legs a numbered pin on the day map — splitting the drive there is what says the junction matters. Defaults to on, unlike the two ends: switch it off to leave the junctions marked only by the route's own small disc.":
    "Donner à chaque jonction entre deux étapes une épingle numérotée sur la carte du jour — découper le trajet à cet endroit est précisément ce qui dit que la jonction compte. Activé par défaut, contrairement aux deux extrémités : désactivez-le pour ne laisser les jonctions marquées que par le petit disque de l'itinéraire.",
  "Starts at the previous activity": "Part de l'activité précédente",
  "The drive departs from wherever the previous activity is. You can then leave the first leg's From and its coordinate blank — they're filled in from that activity — and the departure shares its map pin instead of taking a second number for the same place. Errors if there is no previous activity. Defaults to off.":
    "Le trajet part de là où se trouve l'activité précédente. Vous pouvez alors laisser vides le « De » de la première étape et sa coordonnée — ils sont repris de cette activité — et le départ partage son épingle plutôt que de prendre un second numéro pour le même lieu. Erreur s'il n'y a pas d'activité précédente. Désactivé par défaut.",
  "Ends at the next activity": "Arrive à l'activité suivante",
  "The drive arrives at wherever the next activity is. You can then leave the last leg's To and its coordinate blank — they're filled in from that activity, which must have a coordinate — and the arrival shares its map pin instead of taking a second number for the same place. Errors if there is no next activity. Defaults to off.":
    "Le trajet arrive là où se trouve l'activité suivante. Vous pouvez alors laisser vides le « À » de la dernière étape et sa coordonnée — ils sont repris de cette activité, qui doit donc avoir une coordonnée — et l'arrivée partage son épingle plutôt que de prendre un second numéro pour le même lieu. Erreur s'il n'y a pas d'activité suivante. Désactivé par défaut.",
  "Anything about the drive the other fields don't cover — road conditions, a scenic stretch, a toll or ferry. Optional.":
    "Tout ce que les autres champs ne couvrent pas — l'état de la route, un tronçon panoramique, un péage ou un ferry. Facultatif.",

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
  "Opening days": "Jours d'ouverture",
  "The days it opens — weekday names, single days and/or ranges (e.g. tue-sun, mon-fri, sun). Shown under the address, and you get a warning if the visit falls on another day. Defaults to every day.":
    "Les jours d'ouverture — des noms de jours en anglais, jours seuls et/ou plages (ex. tue-sun, mon-fri, sun). Affichés sous l'adresse, avec un avertissement si la visite tombe un autre jour. Tous les jours par défaut.",
  "Opening hours": "Horaires d'ouverture",
  'The hours it opens — one or more HH:MM-HH:MM ranges, so a midday closure stays two ranges (e.g. 09:30-12:30, 14:00-18:00). Hours that differ by weekday go in ";"-separated groups, each prefixed with its days (e.g. mon-sat 09:00-17:00; sun 10:00-17:00); a group with no days is the default for the rest. Shown under the address, and you get a warning if the visit falls outside them. Defaults to all day.':
    "Les horaires d'ouverture — une ou plusieurs plages HH:MM-HH:MM, pour qu'une fermeture le midi reste deux plages (ex. 09:30-12:30, 14:00-18:00). Des horaires qui changent selon le jour s'écrivent en groupes séparés par « ; », chacun précédé de ses jours (ex. mon-sat 09:00-17:00; sun 10:00-17:00) ; un groupe sans jours sert de valeur par défaut pour les autres. Affichés sous l'adresse, avec un avertissement si la visite tombe en dehors. Toute la journée par défaut.",

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
  "GPX track": "Trace GPX",
  "A .gpx file of the trail, stored in the itinerary itself. Drawn as a trail map plus an elevation profile, and it fills in the distance and elevation gain when you leave those blank. Optional.":
    "Un fichier .gpx du sentier, enregistré dans l'itinéraire lui-même. Dessiné sous forme de tracé et de profil altimétrique, et il complète la distance et le dénivelé si vous les laissez vides. Facultatif.",
  "GPX attached ({kb} KB encoded)": "GPX joint ({kb} Ko encodés)",
  "No GPX attached": "Aucun GPX joint",
  Clear: "Retirer",
  "That file is too large (over {mb} MB).": "Ce fichier est trop volumineux (plus de {mb} Mo).",
  "That file could not be read.": "Ce fichier n'a pas pu être lu.",

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

  // Road leg
  Location: "Lieu",
  From: "De",
  To: "À",
  "the previous leg's arrival": "l'arrivée de l'étape précédente",
  "Where this hop departs from. Leave it blank on any leg but the first: it then reuses the previous leg's arrival. The first leg may leave it blank too when the drive starts at the previous activity.":
    "D'où part cette étape. Laissez vide sur toute étape sauf la première : elle reprend alors l'arrivée de l'étape précédente. La première étape peut aussi le laisser vide si le trajet part de l'activité précédente.",
  "the next leg's departure": "le départ de l'étape suivante",
  "Where this hop arrives. Required on the last leg — unless the drive ends at the next activity; on an earlier one the next leg's departure can name it instead.":
    "Où arrive cette étape. Obligatoire sur la dernière étape — sauf si le trajet arrive à l'activité suivante ; sur une étape antérieure, le départ de l'étape suivante peut le nommer à la place.",
  "Driving time": "Temps de conduite",
  "Driving time for this hop. Optional, but validation warns when it's missing.":
    "Temps de conduite de cette étape. Facultatif, mais la validation avertit s'il manque.",
  "Driving distance for this hop. Optional, but validation warns when it's missing.":
    "Distance routière de cette étape. Facultatif, mais la validation avertit si elle manque.",
  "Off-road": "Hors-piste",
  "Mark just this hop as off-road. The drive as a whole counts as off-road only when every leg is. Defaults to off.":
    "Marquer cette seule étape comme hors-piste. Le trajet entier n'est hors-piste que si toutes ses étapes le sont. Désactivé par défaut.",
  "GPX recording": "Enregistrement GPX",
  "A .gpx recording of this hop, stored in the itinerary itself. It becomes this leg's line on the day map instead of the routed guess — there's no separate trail map or elevation profile, unlike a hike's. Optional.":
    "Un enregistrement .gpx de cette étape, stocké dans l'itinéraire lui-même. Il devient le tracé de cette étape sur la carte du jour à la place de l'itinéraire calculé — sans carte ni profil altimétrique dédiés, contrairement à une randonnée. Facultatif.",
  "From coordinate": "Coordonnée de départ",
  "To coordinate": "Coordonnée d'arrivée",
  Waypoint: "Point de passage",

  // Transport
  "Transport kind, shown as a badge on the booking and on each of its legs. Defaults to 'other'.":
    "Type de transport, affiché comme badge sur la réservation et sur chacun de ses trajets. Par défaut « other ».",
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
  "Flight number of this leg (planes only), shown under its route. Optional.":
    "Numéro de vol de ce trajet (avions uniquement), affiché sous son itinéraire. Facultatif.",
  "Train number": "Numéro de train",
  "Train number of this leg (trains only), shown under its route. Optional.":
    "Numéro de train de ce trajet (trains uniquement), affiché sous son itinéraire. Facultatif.",
  'How far this hop covers — an airport transfer is "30 km / 35 min". Shown beside its date and times. Optional.':
    "La distance couverte par ce trajet — un transfert d'aéroport fait « 30 km / 35 min ». Affichée à côté de sa date et de ses horaires. Facultatif.",
  "Booking number": "Numéro de réservation",
  "Reservation reference / PNR, covering every leg. Optional.":
    "Référence de réservation / PNR, valable pour tous les trajets. Facultatif.",
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
  // The short `description` note — one shared placeholder, one help string per
  // section (each names the examples that fit that section).
  "Short note": "Note courte",
  "the route through its legs": "l'itinéraire de ses trajets",
  "What to call the whole booking (“Round trip New York ↔ France”), shown as the card's heading. Defaults to the route through its legs (A → B → C).":
    "Le nom de la réservation entière (« Aller-retour New York ↔ France »), affiché en titre de la carte. Par défaut, l'itinéraire de ses trajets (A → B → C).",
  "Short note about the whole booking": "Note courte sur la réservation entière",
  "A short note about the whole reservation — a baggage allowance, a fare condition, a check-in window. A note about one hop goes on that leg instead. Optional.":
    "Une note courte sur la réservation entière — une franchise bagages, une condition tarifaire, une fenêtre d'enregistrement. Une note sur un seul trajet se met sur ce trajet. Facultatif.",
  "A short note about this leg — a seat, a terminal, a coach number. A note about the whole reservation goes on the booking instead. Optional.":
    "Une note courte sur ce trajet — un siège, un terminal, un numéro de voiture. Une note sur la réservation entière se met sur la réservation. Facultatif.",
  Price: "Prix",
  "amount only, no symbol": "montant seul, sans symbole",
  "Price of the whole booking, every leg included (amount only, no symbol). Optional.":
    "Prix de la réservation entière, tous trajets compris (montant seul, sans symbole). Facultatif.",
  "Currency this price is in (3-letter ISO). Defaults to defaults.currency.":
    "Devise de ce prix (ISO à 3 lettres). Par défaut defaults.currency.",
  Paid: "Payé",
  "Payment state, shown as a badge. No badge when unset.":
    "État du paiement, affiché comme badge. Aucun badge si non défini.",

  // Emergency contact (`misc.emergency_contacts`) — "Name" / "Contact" are keyed
  // elsewhere already, so only the hints and help text are new here.
  "e.g. SAMU (medical emergencies)": "ex. SAMU (urgences médicales)",
  "Who this contact reaches — the service, the embassy, the person. Optional: a number on its own is still listed.":
    "Qui ce contact permet de joindre — le service, l'ambassade, la personne. Facultatif : un numéro seul est tout de même affiché.",
  "e.g. 112, +33 1 43 12 22 22": "ex. 112, +33 1 43 12 22 22",
  "How to reach them: a phone number, an email or an address. Free text, so a country's own conventions survive. Optional — but an entry with neither half is dropped.":
    "Comment les joindre : un numéro, un e-mail ou une adresse. Texte libre, pour respecter les conventions locales. Facultatif — mais une entrée sans aucun des deux est ignorée.",

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
  "A short note for whatever the other fields don't cover — a door code, where to park, which bell to ring. Optional.":
    "Une note courte pour ce que les autres champs ne couvrent pas — un code d'entrée, où se garer, quelle sonnette. Facultatif.",
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
  "A short note for whatever the other fields don't cover — the insurance excess, a fuel policy, where the desk is. Optional.":
    "Une note courte pour ce que les autres champs ne couvrent pas — la franchise d'assurance, la politique carburant, où se trouve le comptoir. Facultatif.",
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
  "New to this? Start with the": "Nouveau ici ? Commencez par le",
  "📘 Usage guide": "📘 Guide d'utilisation",
  "Usage guide": "Guide d'utilisation",
  "From a pile of trip material to a finished, printable travel book — the steps, what each one takes in and produces, and how to do the manual parts.":
    "D'un tas de documents de voyage à un carnet imprimable — les étapes, ce que chacune prend en entrée et produit, et comment réaliser les parties manuelles.",
  "Open this prompt →": "Ouvrir ce prompt →",
  "How the pieces fit together": "Comment les pièces s'assemblent",
  "The pipeline that turns your raw trip material into an itinerary JSON — then a PDF. Each step spells out what to do (and how, for the manual parts); every prompt links to its full text in the 🤖 LLM prompts tab.":
    "Le pipeline qui transforme vos documents de voyage en JSON d'itinéraire — puis en PDF. Chaque étape détaille quoi faire (et comment, pour les parties manuelles) ; chaque prompt renvoie à son texte complet dans l'onglet 🤖 Prompts IA.",
  // stage headings
  "Prepare your source material": "Préparez vos documents sources",
  "First, gather the raw documents the prompts will read. Collect only what fits your trip — you don't need everything.":
    "D'abord, réunissez les documents bruts que les prompts vont lire. Ne rassemblez que ce qui correspond à votre voyage — inutile de tout avoir.",
  "Preprocess your source material": "Prétraitez vos documents sources",
  "Now run these prompts to turn the raw documents into a few clean files. They're independent — do only the ones you need.":
    "Lancez maintenant ces prompts pour transformer les documents bruts en quelques fichiers propres. Ils sont indépendants — ne faites que ceux dont vous avez besoin.",
  "Assemble the itinerary JSON": "Assemblez le JSON d'itinéraire",
  "Hand the prepared files to a single prompt that reconciles them into one JSON.":
    "Confiez les fichiers préparés à un seul prompt qui les réconcilie en un unique JSON.",
  "Fill the gaps — if needed": "Comblez les manques — si besoin",
  "Only when the validator flags missing distances, durations or elevations.":
    "Seulement quand le validateur signale des distances, durées ou dénivelés manquants.",
  "Use it in the app": "Utilisez-le dans l'app",
  "Open the JSON here to finish it, then export and back it up.":
    "Ouvrez le JSON ici pour le finaliser, puis exportez-le et sauvegardez-le.",
  // chips + card affordances
  "Prompt": "Prompt",
  "In the app": "Dans l'app",
  "Gather": "À réunir",
  "Step by step": "Pas à pas",
  "Jump to this prompt ↓": "Aller à ce prompt ↓",
  // stage 1 — gather (input) cards
  "Gather your booking confirmations": "Réunir vos confirmations de réservation",
  "Gmail, inbox, photos": "Gmail, boîte mail, photos",
  ".mbox, emails, screenshots": ".mbox, e-mails, captures d'écran",
  "Round up every hotel, transport and activity booking you've made.":
    "Rassemblez toutes vos réservations d'hôtel, de transport et d'activité.",
  "Find every confirmation for the trip — hotels, flights or trains, car rental, tours and tickets.":
    "Retrouvez chaque confirmation du voyage — hôtels, vols ou trains, location de voiture, visites et billets.",
  "If you use Gmail, the quickest way is to give them all one label (a label is just a folder/tag — [how to create one](https://support.google.com/mail/answer/118708)), then download that label with [Google Takeout](https://takeout.google.com/), Google's official data-export tool: choose Mail, tick only that label, and you get a single “.mbox” file (one file holding those emails).":
    "Sous Gmail, le plus rapide est de leur donner à toutes un même libellé (un libellé, c'est juste un dossier/une étiquette — [comment en créer un](https://support.google.com/mail/answer/118708)), puis de télécharger ce libellé avec [Google Takeout](https://takeout.google.com/), l'outil officiel d'export de données de Google : choisissez Mail, cochez seulement ce libellé, et vous obtenez un seul fichier « .mbox » (un fichier contenant ces e-mails).",
  "You can freely mix source types — there's no either/or. Alongside (or instead of) the .mbox, paste individual confirmation emails and add screenshots or photos of any booking, including ones that only exist as a web page. The more you provide, the more complete the result.":
    "Vous pouvez librement mélanger les types de sources — pas de choix exclusif. En plus (ou à la place) du .mbox, collez des e-mails de confirmation individuels et ajoutez des captures d'écran ou photos de n'importe quelle réservation, y compris celles qui n'existent que sous forme de page web. Plus vous en fournissez, plus le résultat est complet.",
  "Collect your guidebook & reading": "Rassembler votre guide et vos lectures",
  "guidebook, web": "guide, web",
  "Gather the travel content you want your itinerary drawn from.":
    "Réunissez le contenu de voyage dont votre itinéraire s'inspirera.",
  "Get your guidebook as a PDF. A scan or clear photos of the pages work fine — the prompts can read images, so the text doesn't need to be selectable.":
    "Obtenez votre guide en PDF. Un scan ou des photos nettes des pages conviennent — les prompts lisent les images, le texte n'a donc pas besoin d'être sélectionnable.",
  "Save the links (or copy the text) of any blog posts or articles about the places you'll visit.":
    "Enregistrez les liens (ou copiez le texte) des articles de blog ou publications sur les lieux que vous visiterez.",
  "Sketch a rough day-by-day plan": "Esquisser un plan sommaire jour par jour",
  "you": "vous",
  "rough plan": "plan sommaire",
  "Decide the shape of the trip — mainly where you sleep each night.":
    "Décidez la forme du voyage — surtout où vous dormez chaque nuit.",
  "Write one line per day with its main destination — for example: “Day 1 → Paris, Day 2 → Mont-Saint-Michel, Day 3 → Saint-Malo”. No times or details needed; the prompts fill those in.":
    "Écrivez une ligne par jour avec sa destination principale — par exemple : « Jour 1 → Paris, Jour 2 → Mont-Saint-Michel, Jour 3 → Saint-Malo ». Aucun horaire ni détail nécessaire ; les prompts s'en chargent.",
  "Optionally, add anything you already know to steer the result — real dates, a rough theme for a day (“museums”, “beach day”), a must-do stop, or where you're sleeping. Every hint helps the LLM, but all are optional.":
    "Éventuellement, ajoutez ce que vous savez déjà pour orienter le résultat — des dates réelles, un thème approximatif pour une journée (« musées », « journée plage »), une visite incontournable, ou l'endroit où vous dormez. Chaque indice aide l'IA, mais tous sont facultatifs.",
  "Build your own map (optional)": "Créer votre propre carte (facultatif)",
  "KML file": "Fichier KML",
  "Prefer to plan the route yourself? Make a custom map by hand and export it.":
    "Vous préférez tracer l'itinéraire vous-même ? Créez une carte personnalisée à la main et exportez-la.",
  "Search for each place you want and add it as a pin; you can group related pins into layers if you like.":
    "Recherchez chaque lieu voulu et ajoutez-le comme repère ; vous pouvez regrouper les repères associés en calques si vous le souhaitez.",
  "If you'll be driving, add driving directions between your stops ([how to draw directions](https://support.google.com/mymaps/answer/3067635)) so the real road route is saved on the map.":
    "Si vous conduisez, ajoutez les itinéraires routiers entre vos étapes ([comment tracer un itinéraire](https://support.google.com/mymaps/answer/3067635)) pour enregistrer le vrai tracé sur la carte.",
  "Export the finished map to a KML file: open the map's menu (the three dots ⋮) and choose “Export to KML/KMZ”. Keep that file — it's a source for the next steps.":
    "Exportez la carte terminée en fichier KML : ouvrez le menu de la carte (les trois points ⋮) et choisissez « Exporter au format KML/KMZ ». Conservez ce fichier — c'est une source pour les étapes suivantes.",
  "Don't want to start from a blank page? The next section's “Map the guidebook” prompt builds a starter map from your guidebook that you then refine here instead.":
    "Vous ne voulez pas partir d'une page blanche ? Le prompt « Cartographier le guide » de la section suivante crée une carte de départ à partir de votre guide, que vous affinez ensuite ici.",
  // card A1 — extract bookings
  "Extract your bookings": "Extraire vos réservations",
  "Consolidate every booking confirmation into one attributed file.":
    "Rassembler chaque confirmation de réservation en un fichier sourcé.",
  "This prompt reads the confirmations you gathered and writes every detail into one neat file — so you never copy dates and reference numbers by hand.":
    "Ce prompt lit les confirmations que vous avez réunies et reporte chaque détail dans un seul fichier propre — vous ne recopiez plus jamais les dates et numéros de référence à la main.",
  "Open the prompt (in the 🤖 LLM prompts tab), copy it into an AI chat such as [Claude](https://claude.ai) or [ChatGPT](https://chatgpt.com), and attach your “.mbox” file, pasted emails and/or screenshots.":
    "Ouvrez le prompt (dans l'onglet 🤖 Prompts IA), copiez-le dans une IA comme [Claude](https://claude.ai) ou [ChatGPT](https://chatgpt.com), et joignez votre fichier « .mbox », vos e-mails collés et/ou vos captures d'écran.",
  "Double-check the file and correct it by hand if needed — it's plain text, so it opens in any text editor.":
    "Revérifiez le fichier et corrigez-le à la main si besoin — c'est du texte brut, il s'ouvre dans n'importe quel éditeur de texte.",
  "a bookings .md file": "un fichier .md de réservations",
  "It replies with a bookings `.md` file (a plain-text file) — one entry per booking, each noting where it came from, so nothing is made up.":
    "Elle répond avec un fichier `.md` de réservations (un fichier texte) — une entrée par réservation, chacune indiquant d'où elle vient, pour que rien ne soit inventé.",
  "This prompt reads your booking confirmations and writes every detail into one neat file — so you never copy dates and reference numbers by hand.":
    "Ce prompt lit vos confirmations de réservation et reporte chaque détail dans un seul fichier propre — vous ne recopiez plus jamais les dates et numéros de référence à la main.",
  "If you use Gmail: put all the trip's confirmation emails under one label (a label is just a folder/tag — [how to create one](https://support.google.com/mail/answer/118708)). Then download that label as a file with Google Takeout ([takeout.google.com](https://takeout.google.com/)), Google's official tool for exporting your own data: choose Mail, tick only that one label, and you'll receive a “.mbox” file (a single file holding those emails).":
    "Si vous utilisez Gmail : regroupez tous les e-mails de confirmation du voyage sous un même libellé (un libellé, c'est simplement un dossier/une étiquette — [comment en créer un](https://support.google.com/mail/answer/118708)). Téléchargez ensuite ce libellé sous forme de fichier avec Google Takeout ([takeout.google.com](https://takeout.google.com/)), l'outil officiel de Google pour exporter vos propres données : choisissez Mail, cochez seulement ce libellé, et vous recevrez un fichier « .mbox » (un seul fichier contenant ces e-mails).",
  "Not using Gmail? No problem — just copy-paste the text of each confirmation email, and/or add photos or screenshots of your hotel, transport and activity bookings.":
    "Pas de Gmail ? Aucun souci — copiez-collez simplement le texte de chaque e-mail de confirmation, et/ou ajoutez des photos ou captures d'écran de vos réservations d'hôtel, de transport et d'activités.",
  "Open the prompt (in the 🤖 LLM prompts tab), copy it into an AI chat such as [Claude](https://claude.ai) or [ChatGPT](https://chatgpt.com), and attach those files. It replies with a file called Bookings.md.":
    "Ouvrez le prompt (dans l'onglet 🤖 Prompts IA), copiez-le dans une IA comme [Claude](https://claude.ai) ou [ChatGPT](https://chatgpt.com), et joignez ces fichiers. Elle répond avec un fichier nommé Bookings.md.",
  "Bookings.md is a plain-text file that lists every booking with its details, and notes where each one came from — so nothing is made up.":
    "Bookings.md est un fichier texte qui liste chaque réservation avec ses détails, et indique d'où vient chacune — ainsi rien n'est inventé.",
  // card A2 — guidebook KML
  "Map the guidebook": "Cartographier le guide",
  "Guidebook PDF, blog posts": "PDF du guide, articles de blog",
  "Guidebook PDF, blog posts, rough plan": "PDF du guide, articles de blog, plan sommaire",
  "Turn a guidebook into a map of places you then refine by hand.":
    "Transformer un guide en une carte de lieux que vous affinez ensuite à la main.",
  "This step is optional — do it only if you want a real map of the places in your guidebook. It works best when you plan to drive.":
    "Cette étape est facultative — faites-la seulement si vous voulez une vraie carte des lieux de votre guide. Elle est surtout utile si vous prévoyez de conduire.",
  "Copy the prompt into an AI chat (Claude or ChatGPT) with your guidebook. It returns a “KML” file — a standard map file that simply lists places by name and location.":
    "Copiez le prompt dans une IA (Claude ou ChatGPT) avec votre guide. Elle renvoie un fichier « KML » — un fichier de carte standard qui liste simplement des lieux par nom et position.",
  "Go to [Google My Maps](https://www.google.com/mymaps) (a free Google tool for building your own maps) and click “Create a new map”.":
    "Allez sur [Google My Maps](https://www.google.com/mymaps) (un outil Google gratuit pour créer vos propres cartes) et cliquez sur « Créer une carte ».",
  "Import the KML file into that map (in the map, click Import and choose the file — [how to import](https://support.google.com/mymaps/answer/3024836)). Every place from your guidebook shows up as a pin.":
    "Importez le fichier KML dans cette carte (dans la carte, cliquez sur Importer et choisissez le fichier — [comment importer](https://support.google.com/mymaps/answer/3024836)). Chaque lieu de votre guide apparaît sous forme de repère.",
  "Check the pins: drag any that landed in the wrong place, and add any spots the guide mentions that are missing.":
    "Vérifiez les repères : déplacez ceux qui sont mal placés, et ajoutez les lieux que le guide mentionne mais qui manquent.",
  "If you'll be driving, add driving directions between the stops you'll drive between ([how to draw directions](https://support.google.com/mymaps/answer/3067635)) — this saves the real road route on the map.":
    "Si vous conduisez, ajoutez les itinéraires routiers entre les étapes que vous relierez en voiture ([comment tracer un itinéraire](https://support.google.com/mymaps/answer/3067635)) — cela enregistre le vrai tracé sur la carte.",
  "When you're happy, export the map back to a KML file: open the map's menu (the three dots ⋮) and choose “Export to KML/KMZ”. Keep that exported file for the next steps.":
    "Quand tout est bon, réexportez la carte en fichier KML : ouvrez le menu de la carte (les trois points ⋮) et choisissez « Exporter au format KML/KMZ ». Conservez ce fichier exporté pour les étapes suivantes.",
  // card A3 — itinerary from guidebook
  "Draft the day-by-day": "Rédiger le jour par jour",
  "Expand a one-line-per-day outline into a detailed, sourced itinerary.":
    "Développer un canevas d'une ligne par jour en un itinéraire détaillé et sourcé.",
  "This prompt turns your rough plan into a full day-by-day itinerary, using your guidebook as the source of ideas.":
    "Ce prompt transforme votre plan sommaire en un itinéraire complet jour par jour, en s'appuyant sur votre guide comme source d'idées.",
  "Copy the prompt into an AI chat (Claude or ChatGPT), then add your rough plan, the guidebook and any blog posts.":
    "Copiez le prompt dans une IA (Claude ou ChatGPT), puis ajoutez votre plan sommaire, le guide et d'éventuels articles de blog.",
  "an itinerary .md file": "un fichier .md d'itinéraire",
  "You get back an itinerary `.md` file: each day filled out with things to see and do, walks and hikes, and the guidebook page numbers it drew from — so you can double-check anything.":
    "Vous obtenez un fichier `.md` d'itinéraire : chaque journée étoffée de choses à voir et à faire, de marches et randonnées, et des numéros de page du guide utilisés — pour tout revérifier.",
  // card B1 — build full json
  "Assemble the full JSON": "Assembler le JSON complet",
  "bookings .md, itinerary .md, KML": "réservations .md, itinéraire .md, KML",
  "a travel .json file": "un fichier .json de voyage",
  "Merge the prepared files (plus any extra material) into one complete itinerary JSON.":
    "Fusionner les fichiers préparés (et tout autre document) en un JSON d'itinéraire complet.",
  "This is the main step: it combines everything above into one file this app can open — an “itinerary JSON” (JSON is just a structured text format that apps read).":
    "C'est l'étape principale : elle combine tout ce qui précède en un seul fichier que cette app peut ouvrir — un « JSON d'itinéraire » (le JSON est simplement un format de texte structuré que les applis lisent).",
  "Copy the prompt into an AI chat (Claude or ChatGPT), then attach the files you made: the bookings `.md`, the exported KML, and the itinerary `.md`. You don't need all three — use whichever you have.":
    "Copiez le prompt dans une IA (Claude ou ChatGPT), puis joignez les fichiers que vous avez créés : le `.md` de réservations, le KML exporté et le `.md` d'itinéraire. Les trois ne sont pas obligatoires — utilisez ceux que vous avez.",
  "It merges them into one itinerary. If two sources disagree — say two different check-in times — it points that out so you can decide which is right.":
    "Elle les fusionne en un seul itinéraire. Si deux sources se contredisent — par exemple deux heures d'arrivée différentes — elle le signale pour que vous tranchiez.",
  "You get one file named after your trip, ending in “.json”. That's what you open in the app in the next step.":
    "Vous obtenez un fichier au nom de votre voyage, se terminant par « .json ». C'est lui que vous ouvrez dans l'app à l'étape suivante.",
  // card C1 — fix missing
  "Fill the missing figures": "Compléter les valeurs manquantes",
  "a travel .json file, ⚠️ warnings": "un fichier .json de voyage, avertissements ⚠️",
  "an updated travel .json file": "un fichier .json de voyage mis à jour",
  "Turn the validator's warnings into a fill-in-the-blank worksheet.":
    "Transformer les avertissements du validateur en une fiche à compléter.",
  "Sometimes the itinerary is missing a distance, a duration, or the elevation of a drive or hike. This optional prompt helps you fill those in.":
    "Il manque parfois une distance, une durée ou le dénivelé d'un trajet ou d'une randonnée. Ce prompt facultatif vous aide à les compléter.",
  "Open your JSON file in this app (menu → Options → Open JSON…). Go to the 🔎 Findings tab and copy the ⚠️ warning lines it shows — these list exactly what's missing.":
    "Ouvrez votre fichier JSON dans cette app (menu → Options → Ouvrir un JSON…). Allez dans l'onglet 🔎 Diagnostics et copiez les lignes d'avertissement ⚠️ affichées — elles listent exactement ce qui manque.",
  "Copy the prompt into an AI chat (Claude or ChatGPT) with your JSON file and those warning lines.":
    "Copiez le prompt dans une IA (Claude ou ChatGPT) avec votre fichier JSON et ces lignes d'avertissement.",
  "It replies with a worksheet — a simple checklist of the blanks. For road distances it adds a [Google Maps](https://www.google.com/maps) link so you can read the number off the map; for hikes it pre-fills a best guess from the web, marked “to check” so you confirm it.":
    "Elle répond avec une fiche — une simple liste des cases à remplir. Pour les distances routières, elle ajoute un lien [Google Maps](https://www.google.com/maps) pour lire la valeur sur la carte ; pour les randonnées, elle pré-remplit une estimation issue du web, marquée « à vérifier ».",
  "Fill in the blanks, then either give the worksheet back to the prompt, or type the values straight into the ✏️ Edit tab of the app.":
    "Remplissez les cases, puis soit vous redonnez la fiche au prompt, soit vous saisissez les valeurs directement dans l'onglet ✏️ Édition de l'app.",
  // card D1 — open & fix
  "Open & fix it in the app": "Ouvrir et corriger dans l'app",
  "the travel .json file": "le fichier .json de voyage",
  "Import the JSON, then resolve anything the sources didn't cover.":
    "Importer le JSON, puis régler ce que les sources n'ont pas couvert.",
  "Everything so far happened in an AI chat. From here you work inside this app to finish your travel book.":
    "Jusqu'ici tout se passait dans une IA. À partir de maintenant, vous travaillez dans cette app pour finaliser votre carnet de voyage.",
  "Open the menu (☰, top-right) and choose Options → Open JSON…, then pick the “.json” file you made.":
    "Ouvrez le menu (☰, en haut à droite) et choisissez Options → Ouvrir un JSON…, puis sélectionnez le fichier « .json » que vous avez créé.",
  "Open the 🔎 Findings tab. It lists anything that's wrong (❌ errors) or worth checking (⚠️ warnings) in plain language, and points to the exact spot.":
    "Ouvrez l'onglet 🔎 Diagnostics. Il liste ce qui ne va pas (❌ erreurs) ou ce qui mérite vérification (⚠️ avertissements) en langage clair, et indique l'endroit exact.",
  "Open the ✏️ Edit tab to fix those and add anything missing, then press “Apply changes” to refresh the preview.":
    "Ouvrez l'onglet ✏️ Édition pour corriger cela et ajouter ce qui manque, puis appuyez sur « Appliquer les modifications » pour rafraîchir l'aperçu.",
  "When it looks right, save it from the Edit tab — that's your final travel `.json` file.":
    "Quand tout est bon, enregistrez depuis l'onglet Édition — c'est votre fichier `.json` de voyage final.",
  "the final travel .json file": "le fichier .json de voyage final",
  // card D2 — export & back up
  "Export & back it up": "Exporter et sauvegarder",
  "PDF, offline app, print": "PDF, app hors ligne, impression",
  "Take the finished travel book with you.": "Emportez le carnet de voyage terminé.",
  "Install this app on your phone (in your browser's menu, tap “Add to Home Screen” or “Install app”) and open your file there — the travel book then works even with no internet.":
    "Installez cette app sur votre téléphone (dans le menu de votre navigateur, touchez « Ajouter à l'écran d'accueil » ou « Installer l'application ») et ouvrez-y votre fichier — le carnet fonctionne alors même sans connexion internet.",
  "Make a printable PDF: menu → Options → Export, then “Generate PDF”.":
    "Créez un PDF imprimable : menu → Options → Exporter, puis « Générer le PDF ».",
  "Print that PDF and keep it in your bag as a paper backup — handy if your phone runs out of battery.":
    "Imprimez ce PDF et gardez-le dans votre sac comme sauvegarde papier — pratique si votre téléphone tombe en panne de batterie.",
  "Give it": "À fournir",
  "You get": "Résultat",
  "📋 Copy prompt": "📋 Copier le prompt",
  "✓ Copied": "✓ Copié",
  "Couldn't load this prompt.": "Impossible de charger ce prompt.",
  "Paste it into an LLM chat, then add your material.":
    "Collez-le dans une IA, puis ajoutez vos documents.",

  "Extract bookings into a file": "Extraire les réservations dans un fichier",
  "Gathers every booking scattered across your confirmations into one tidy Markdown file — transport, accommodation, car rentals and booked activities, one entry each, with every fact attributed to its source and gaps and contradictions flagged. It only transcribes what the sources say; it never invents or guesses. Feed the result to the itinerary-JSON prompt below.":
    "Rassemble toutes les réservations éparpillées dans vos confirmations en un seul fichier Markdown clair — transports, hébergements, locations de voiture et activités réservées, une entrée chacune, chaque information rattachée à sa source, avec les manques et les contradictions signalés. Il ne fait que transcrire ce que disent les sources ; il n'invente ni ne devine jamais. Fournissez le résultat au prompt de JSON d'itinéraire ci-dessous.",
  "Your booking confirmations, in any mix — screenshots or photos, an MBOX export (e.g. a Gmail label via Google Takeout), copy-pasted email text, or voucher PDFs. Overlaps and different languages are fine.":
    "Vos confirmations de réservation, dans n'importe quel mélange — captures d'écran ou photos, un export MBOX (par ex. un libellé Gmail via Google Takeout), du texte d'e-mail copié-collé, ou des bons en PDF. Les doublons et les langues différentes ne posent pas de problème.",
  "A single timestamped bookings_<trip>_<date>.md file — one entry per booking with its source noted, plus lists of conflicts and anything left uncertain.":
    "Un seul fichier horodaté bookings_<voyage>_<date>.md — une entrée par réservation avec sa source indiquée, plus la liste des conflits et de tout ce qui reste incertain.",

  "Build the full itinerary JSON": "Construire le JSON complet de l'itinéraire",
  "Turns raw trip material into one complete, ready-to-render itinerary JSON file. The prompt is self-contained: it carries every field, value format and rule the LLM needs to get the JSON right on the first pass.":
    "Transforme vos documents de voyage en un fichier JSON d'itinéraire complet, prêt à être rendu. Le prompt est autonome : il contient tous les champs, formats de valeurs et règles dont l'IA a besoin pour produire un JSON correct du premier coup.",
  "Your trip material — a brief, a day-by-day plan, booking-confirmation emails, hotel/rental vouchers, screenshots, a guidebook PDF, links to blog posts, a KML/KMZ track (e.g. exported from a custom Google Map), a GPX track for a hike or off-road drive, or an MBOX export (e.g. a Gmail label exported via Google Takeout).":
    "Vos documents de voyage — un brief, un programme jour par jour, des e-mails de confirmation, des bons d'hôtel/location, des captures d'écran, un PDF de guide, des liens vers des articles de blog, une trace KML/KMZ (par ex. exportée depuis une carte Google personnalisée), une trace GPX pour une randonnée ou une piste hors route, ou un export MBOX (par ex. un libellé Gmail exporté via Google Takeout).",
  "The more concrete the sources, the fewer gaps the LLM has to leave blank.":
    "Plus les sources sont concrètes, moins l'IA laisse de champs vides.",
  "A single <title>.json you can open here (Options → Open JSON…), plus a report of the gaps and any conflicts it found between your sources. A hike's GPX is embedded in the file itself, so its trail map and elevation profile come along with it.":
    "Un seul fichier <titre>.json que vous pouvez ouvrir ici (Options → Ouvrir JSON…), ainsi qu'un rapport des manques et des éventuels conflits entre vos sources. Le GPX d'une randonnée est intégré au fichier lui-même : son tracé et son profil altimétrique voyagent avec lui.",

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

  "Expand a guidebook into a day-by-day itinerary":
    "Développer un guide en un itinéraire jour par jour",
  "Turns a guidebook PDF plus a bare-bones outline (just days → destinations) into a detailed, chronological Markdown itinerary: each day expanded with guide-sourced activities and descriptions, clearly-labelled walks/hikes with their metrics, explicit “Route from X to Y” stops, and printed-page citations. It enriches your outline from the guide alone — it never invents facts.":
    "Transforme un PDF de guide et un canevas minimal (juste des jours → destinations) en un itinéraire Markdown détaillé et chronologique : chaque jour développé avec les activités et descriptions tirées du guide, des marches/randonnées clairement identifiées avec leurs données, des étapes explicites « Route de X à Y », et des références aux pages imprimées. Il enrichit votre canevas à partir du guide seul — sans jamais inventer de faits.",
  "A guidebook PDF for the region — even a scanned, image-only one (the prompt reads pages visually rather than assuming selectable text).":
    "Un PDF de guide pour la région — même scanné, en images seules (le prompt lit les pages visuellement plutôt que de supposer un texte sélectionnable).",
  "A very brief trip outline: one line per day with its destination (e.g. “Day 1 → Paris, Day 2 → Mont Saint-Michel…”). No timings needed.":
    "Un canevas de voyage très bref : une ligne par jour avec sa destination (par ex. « Jour 1 → Paris, Jour 2 → Mont Saint-Michel… »). Aucun horaire nécessaire.",
  "A timestamped itinerary_<destination>-<dates>_<date>.md you can then feed to the itinerary-JSON prompt above (or edit by hand first).":
    "Un fichier horodaté itinerary_<destination>-<dates>_<date>.md que vous pouvez ensuite fournir au prompt de JSON d'itinéraire ci-dessus (ou modifier à la main d'abord).",

  "Fix missing durations & distances": "Compléter les durées et distances manquantes",
  "Builds a fill-in-the-blank Markdown worksheet for the roads, hikes and activities that are missing a duration, distance or elevation — one entry per missing value, with Google Maps links for road distances and web-sourced estimates (tagged “to be checked”) for hikes.":
    "Construit une fiche Markdown à compléter pour les routes, randonnées et activités auxquelles il manque une durée, une distance ou un dénivelé — une entrée par valeur manquante, avec des liens Google Maps pour les distances routières et des estimations issues du web (marquées « à vérifier ») pour les randonnées.",
  "Your itinerary JSON.": "Votre JSON d'itinéraire.",
  "The ⚠️ warnings about missing duration/distance/elevation — copy them from the 🔎 Findings tab (or the validator output).":
    "Les avertissements ⚠️ concernant les durées/distances/dénivelés manquants — copiez-les depuis l'onglet 🔎 Diagnostics (ou la sortie du validateur).",
  "A <title>-missing.md worksheet to complete by hand, then merge the figures back into your JSON.":
    "Une fiche <titre>-missing.md à compléter à la main, puis à réintégrer dans votre JSON.",
};
