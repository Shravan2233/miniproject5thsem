# CabCompare

CabCompare is a ride-price comparison prototype. This first release contains a responsive React/Vite interface and an independent Flask API. Its sample fare records are static demo fixtures: they are not provider quotes, live prices, or availability, and no booking links are enabled. Booking remains with the ride provider.

The existing locker application in the parent workspace is not modified by this project.

## Included

- Route search with required-field, length, and identical-location validation.
- Demo fare cards, ride category filters, cheapest/fastest-pickup/best-value sorting, refresh, and source-aware lowest-price badge.
- Browser geolocation after an explicit user click. Coordinates are shown as the pickup text; no reverse geocoding or location history is performed.
- Device-local recent searches and sample popular routes.
- Flask health, provider-status, popular-route, and comparison endpoints.
- Separate status modules for Uber, Rapido, Ola, and Namma Yatri. They report unavailable until an approved integration exists.
- MySQL schema for accounts, routes, searches, providers, fare observations, preferences, and favorite routes.
- Python unit tests for the comparison engine and API responses.

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

   Open `http://localhost:5173`.

## API

- `GET /api/health` reports backend health and the current `demo` fare mode.
- `GET /api/providers` lists provider integration status.
- `GET /api/routes/popular` returns sample routes.
- `POST /api/rides/compare` accepts JSON such as `{"pickup":"Indiranagar, Bengaluru","destination":"MG Road, Bengaluru","category":"all","sort":"cheapest"}`.

Supported categories: `all`, `bike`, `auto`, `sedan`, `premium`. Sort values: `cheapest`, `pickup`, `best_value`. Comparison responses include `fare_source: "demo"`, `fare_status: "demo"`, and a notice that no live prices are connected. An invalid request returns a JSON `error` and HTTP 400.

## Database

Create the local database schema and provider seed records with a MySQL account that has permission to create a database:

```powershell
mysql -u root -p < database/schema.sql
mysql -u root -p cabcompare < database/seed.sql
```

Database connection variables are placeholders in `.env.example`. The initial API does not yet read or write MySQL; the schema is supplied for the persistence phase. Do not store precise locations longer than needed, and obtain user consent before enabling account-linked search history.

## Maps and Provider Integrations

No mapping or provider credentials are required for demo mode. To add autocomplete, route geometry, distance, and duration, choose a mapping service, configure its server-side credential in the environment, restrict the key by API and deployment origin where supported, and proxy protected requests through the backend. Browser geolocation is only a coordinate input in this release.

No live fare API or approved partner access is configured or claimed for Uber, Rapido, Ola, or Namma Yatri. Before enabling an adapter, verify the provider's current official partner documentation, obtain written access and credentials as required, and implement only documented APIs and supported app links. Do not scrape private endpoints or construct undocumented deep links. The current provider actions stay disabled because no verified booking URL is available.

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

## Not Yet Implemented

This is the first working comparison release, not the complete production platform. MySQL persistence, registration/login, authorized search history, favorites, savings analytics and Recharts dashboards, map autocomplete/route rendering, provider fare APIs, and verified app redirects are not wired yet. Demo fares must not be used to make a booking or savings claim.

## v2 Update: Google Maps places and booking links

**Google Maps (location search + "use my location").** Create a key in Google Cloud Console, enable *Maps JavaScript API*, *Places API (New)* and *Geocoding API*, restrict it to HTTP referrers (your site origins), and set `VITE_GOOGLE_MAPS_API_KEY` in `frontend/.env`. Restart `npm run dev`. Without a key the app still works with typed text, and the locate button shows coordinates. Geolocation needs `localhost` or HTTPS.

**Booking links.** Prices and the "Book on ..." button open the provider via `backend/providers/links.py`. Uber and Ola links carry the pickup/drop coordinates; Rapido and Namma Yatri open their official site because no verifiable route-prefill link exists, and the user enters the route there. The API now accepts optional `pickup_coords` / `destination_coords` (`{"lat":..,"lng":..}`) and returns `booking` and `booking_url` on every ride. Fares are still demo values until a provider fare API is approved. Verify the link formats against current provider docs before launch.

**Estimated fares.** With a Maps key, the browser gets the real driving distance and time (Routes API) and the backend turns them into estimates using the approximate rate cards in `backend/providers/rates.py`. Enable **Routes API** on your key as well. Edit the numbers in that file to match real prices. Without a key, sample fares are shown. These are estimates, not provider quotes.

**No Google key needed for estimates.** If the browser does not send a route (no Maps key), the backend looks up the route for free using OpenStreetMap Nominatim (addresses) and OSRM (driving distance). These are public community services with fair-use limits, fine for a project demo. If they cannot be reached, sample fares are shown.
