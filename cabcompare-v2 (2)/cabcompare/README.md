# CabCompare

CabCompare is a ride-comparison prototype with a responsive React/Vite interface and an independent Flask API. It does not currently have authorized access to any provider fare API, so it never displays sample or calculated amounts as provider prices. Booking remains with the ride provider.

The existing locker application in the parent workspace is not modified by this project.

## Included

- Route search with required-field, length, and identical-location validation.
- Provider status cards, route lookup, category selection, and booking links. Fare amounts, ETA, and provider availability are explicitly unavailable until authorized integrations exist.
- Browser geolocation after an explicit user click. Recent routes are stored only on the current device.
- Device-local recent searches and sample popular routes.
- Flask health, provider-status, popular-route, and comparison endpoints.
- Separate status modules for Uber, Rapido, Ola, and Namma Yatri. They report unavailable until an approved integration exists.
- MySQL schema for accounts, routes, searches, providers, fare observations, preferences, and favorite routes.
- Python unit tests for the comparison engine, unavailable-fare behavior, and booking URL generation.

## Run Locally

Requirements: Python 3.10+ and Node.js 20+ with npm. MySQL is optional for this demo release because the API does not persist searches or fares yet.

1. In PowerShell, create the local environment file and install backend dependencies:

   ```powershell
   cd cabcompare
   Copy-Item .env.example .env
   py -m venv backend/.venv
   .\backend\.venv\Scripts\Activate.ps1
   pip install -r backend/requirements.txt
   ```

2. Start the API from the `cabcompare` directory:

   ```powershell
   python -m backend.app
   ```

   API base URL: `http://127.0.0.1:5000`.

3. In a second terminal, install and start the frontend:

   ```powershell
   cd cabcompare/frontend
   Copy-Item .env.example .env
   npm install
   npm run dev
   ```

   Open the Vite URL printed in the terminal. In development, `/api` requests are proxied to `http://127.0.0.1:5000`, so the frontend still works if Vite selects a different port. Keep `VITE_API_BASE_URL` empty for this proxy; set it to an absolute API URL only when the API is hosted separately.

## API

- `GET /api/health` reports backend health and the current `unavailable` fare mode.
- `GET /api/providers` lists provider integration status.
- `GET /api/routes/popular` returns sample routes.
- `POST /api/rides/compare` accepts JSON such as `{"pickup":"Indiranagar, Bengaluru","destination":"MG Road, Bengaluru","category":"all","sort":"cheapest"}`.

Supported categories: `all`, `bike`, `auto`, `sedan`, `premium`. Sort values remain accepted for API compatibility. Comparison responses use `fare_source: "UNAVAILABLE"` and `fare_status: "UNAVAILABLE"` with null fare/ETA/availability values and the notice: "Live fare currently unavailable. Open the provider to check the current price." Route distance, when available, is informational only and is never used to synthesize provider fares. An invalid request returns a JSON `error` and HTTP 400.

## Database

Create the local database schema and provider seed records with a MySQL account that has permission to create a database:

```powershell
mysql -u root -p < database/schema.sql
mysql -u root -p cabcompare < database/seed.sql
```

Database connection variables are placeholders in `.env.example`. The initial API does not yet read or write MySQL; the schema is supplied for the persistence phase. Do not store precise locations longer than needed, and obtain user consent before enabling account-linked search history.

## Maps, Fares, and Booking Links

Location suggestions and route lookup use public OpenStreetMap services when no Google Maps key is configured. Google Maps can be enabled for Places, Geocoding, and Routes as described below. Location coordinates are sent to the backend for supported booking URL generation. The last successful route is kept in `sessionStorage` and restored in the same tab, including after reload; recent routes continue to be kept on-device in `localStorage`.

No live fare API or approved partner access is configured. The backend returns `UNAVAILABLE` rather than demo prices or locally calculated estimates. Public documentation checked:

- **Ola:** The [official ride estimate API](https://developers.olacabs.com/docs/ride-estimate) is `GET /v1/products`, takes pickup and drop coordinates, and documents `Authorization` and `x-app-token` headers. The estimate response includes category availability/ETA and `ride_estimate` ranges (`amount_min`, `amount_max`), with upfront fares limited to whitelisted partners. Ola states that its developer program is invite-only; applicants must request access, integrate against staging, and pass certification for production access. Public docs do not provide free self-service access or a pricing schedule. The [deep-link guide](https://developers.olacabs.com/docs/deep-linking) documents web (`book.olacabs.com`), app (`olacabs://app/launch`), and universal (`olawebcdn.com/assets/ola-universal-link.html`) entry points. The guide requires an Ola-issued `utm_source` XAPP token for its affiliate deep-link flow; none is configured here. With no token, CabCompare uses only the official web booking URL whose route fields were observed in the desktop browser test, and makes no affiliate or app-handoff claim. If a valid token is configured on the backend, a mobile universal link is also generated with `address`, `drop_address`, coordinates, and `landing_page=bk`; mobile handoff still needs device testing.
- **Uber:** The official [price-estimate endpoint](https://developer.uber.com/docs/riders/references/api/v1.2/estimates-price-get) requires Uber approval. It documents `prices[]` results with product display names, estimate/range, currency, distance, duration, and surge multiplier. It accepts a server token or a user OAuth token with any valid scope; the docs do not name a fare-specific scope. Uber's authentication docs say new server tokens are no longer issued. The [products endpoint](https://developer.uber.com/docs/riders/references/api/v1.2/products-get) lists products at a location but explicitly does not report real-time availability; the [time-estimate endpoint](https://developer.uber.com/docs/riders/references/api/v1.2/estimates-time-get) reports ETAs, requires Uber approval, and accepts a user OAuth token with any valid scope. The current docs do not establish free API access or list a price. Most importantly, the price API's current terms explicitly prohibit using it for price comparisons with competing third-party services. CabCompare therefore must not call this endpoint for its intended competitive comparison use. No approved API client is configured. The official [deep-link guide](https://developer.uber.com/docs/riders/ride-requests/tutorials/deep-links/introduction) documents the `https://m.uber.com/looking` universal/mobile-web link and URL-encoded `pickup` and `drop[0]` Location JSON objects. CabCompare puts the short label in `addressLine1`, the complete entered address in `addressLine2`, and coordinates in both objects. `UBER_CLIENT_ID` is added if configured for the documented handoff. The URL format is documented, but installed-app handoff and rendered location fidelity are not verified on Android/iOS.
- **Rapido:** Its [official site](https://www.rapido.bike/) was checked; no public official fare-estimate or route-prefill API was identified. The app links to the official site and tells the user to enter the route.
- **Namma Yatri:** The [official site](https://nammayatri.in/) and [public source organization](https://github.com/nammayatri) were checked. Public repositories do not grant this application production quote or booking access. No public partner fare API or route-prefill link was identified; the app links to the official site and requires manual entry.

Booking-link statuses distinguish desktop-web results from native-app behavior. Ola's official web booking page was opened with the selected route and visibly displayed both pickup and destination labels and coordinates in a desktop-browser test. Without the XAPP token, that observed web route is used as a fallback; the token is still required by Ola's documented affiliate link flow, and no app handoff is claimed. Uber's official mobile-web link contains the documented coordinate-bearing `pickup` and `drop[0]` objects and opened to vehicle selection in the available test, but Uber resolved the supplied coordinates to different displayed place names. CabCompare therefore includes the complete formatted address but does not claim that Uber will render it exactly. `UBER_CLIENT_ID` is not configured in this checkout, and installed-app handoff is untested. Rapido and Namma Yatri require manual entry; no public external route-prefill mechanism was identified. No Android/iOS device or native-app launch was available for verification.

## Verification

From the workspace root:

```powershell
python -m unittest cabcompare.backend.tests.test_comparison cabcompare.backend.tests.test_api -v
```

From `cabcompare/frontend`, after installing Node dependencies:

```powershell
npm run build
```

Screenshot checklist: desktop initial search view; mobile initial search view; desktop and mobile results with category/sort controls; location permission denied; API unavailable/error state; empty category state.

## Provider Verification Report

Checks below distinguish source documentation and URL generation from a real in-app booking. External URLs were fetched from this environment; Android/iOS app launches and rendered pickup/drop confirmation were not testable here.

| Provider | Fare retrieval | Pickup transfer | Destination transfer | Booking opens |
|---|---|---|---|---|
| Ola | **Unavailable** — invite-only API; no authorized credentials | **Verified in desktop web browser** — selected pickup was displayed | **Verified in desktop web browser** — selected destination was displayed | Official web link used without a token as an observed route-display fallback; with a configured XAPP token a documented universal URL is generated for mobile, but its app handoff is not device-tested |
| Uber | **Unavailable** — estimate API requires approval and is not permitted for this competitive comparison | Documented coordinates included; rendered place name differed, so exact display is **not verified** | Documented coordinates included; rendered place name differed, so exact display is **not verified** | Mobile web opened to vehicle selection; no `UBER_CLIENT_ID`, and installed-app behavior not tested |
| Rapido | **Unavailable** — no public official estimate API identified | **Not supported** by a verified public link | **Not supported** by a verified public link | Official website responded; booking flow not verified |
| Namma Yatri | **Unavailable** — no authorized public production quote access | **Not supported** by a verified public link | **Not supported** by a verified public link | Official website responded; booking flow not verified |

**Location data verification:** automated tests verify selected coordinates and complete address strings in generated URL parameters, correct percent encoding/JSON decoding, Ola's token-gated universal link parameters, and route lookup fallback. These tests do not establish that the external app displayed the locations. Confirm both endpoints in the provider before requesting a ride.

## Not Yet Implemented

MySQL persistence, registration/login, authorized search history, favorites, savings analytics, map route rendering, and provider fare APIs are not wired yet. The prior rate-card and demo fixtures remain in the repository for isolated development/tests only; they are not used in the production comparison endpoint.

**Location suggestions and routing.** Without a Google key, location suggestions use OpenStreetMap's Nominatim service and route metrics use Nominatim plus OSRM. Select a suggestion to attach coordinates; manually typed locations remain supported. With a Google key, enable *Maps JavaScript API*, *Places API (New)*, *Geocoding API*, and *Routes API*, restrict it to your site origins, and set `VITE_GOOGLE_MAPS_API_KEY` in `frontend/.env`. Restart `npm run dev`. Geolocation needs `localhost` or HTTPS. OpenStreetMap services have fair-use limits; do not use this public setup for high-traffic production.
