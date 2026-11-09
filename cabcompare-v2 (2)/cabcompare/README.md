# CabCompare

CabCompare is a ride-price comparison prototype. This first release contains a responsive React/Vite interface and an independent Flask API. Its sample fare records are static demo fixtures: they are not provider quotes, live prices, or availability, and no booking links are enabled. Booking remains with the ride provider.

The existing locker application in the parent workspace is not modified by this project.

## Included

- Route search with required-field, length, and identical-location validation.
- Demo fare cards, ride category filters, cheapest/fastest-pickup/best-value sorting, refresh, and source-aware lowest-price badge.
- Browser geolocation after an explicit user click. Recent routes are stored only on the current device.
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

No mapping credentials are required for demo mode. The app uses public OpenStreetMap services for location suggestions and route lookup when no Google Maps key is configured; Google Maps can be enabled for Places, Geocoding, and Routes features as described below.

No live fare API or approved partner access is configured or claimed for Uber, Rapido, Ola, or Namma Yatri. Before enabling a quote adapter, verify the provider's current official partner documentation and obtain any required access. Do not scrape private endpoints or construct undocumented deep links. Current booking links use supported provider web entry points; providers without verified route-prefill support offer a copy-route action instead.

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

This is the first working comparison release, not the complete production platform. MySQL persistence, registration/login, authorized search history, favorites, savings analytics and Recharts dashboards, map route rendering, and provider fare APIs are not wired yet. Demo fares must not be used to make a booking or savings claim.

## v2 Update: Google Maps places and booking links

**Location suggestions and routing.** Without a Google key, location suggestions use OpenStreetMap's Nominatim service and route metrics use Nominatim plus OSRM. Select a suggestion to attach coordinates; manually typed locations remain supported. With a Google key, enable *Maps JavaScript API*, *Places API (New)*, *Geocoding API*, and *Routes API*, restrict it to your site origins, and set `VITE_GOOGLE_MAPS_API_KEY` in `frontend/.env`. Restart `npm run dev`. Geolocation needs `localhost` or HTTPS. OpenStreetMap services have fair-use limits; do not use this public setup for high-traffic production.

**Booking links.** Prices and the "Book on ..." button open the provider via `backend/providers/links.py`. Uber carries the entered pickup/drop text and coordinates when available; Ola carries text and coordinates when available. Rapido and Namma Yatri do not have a verified route-prefill link configured, so the app provides a copy-route action before you enter the trip in their app. The API accepts optional `pickup_coords` / `destination_coords` (`{"lat":..,"lng":..}`) and returns `booking` and `booking_url` on every ride. Verify link formats against current provider docs before launch.

**Estimated fares.** With route metrics, the backend turns distance and duration into indicative estimates using approximate rate cards in `backend/providers/rates.py`. Without route metrics, sample fares are shown. No real-time provider quotes are available in this project; fares vary by city, vehicle, demand, tolls, and app-specific fees. These figures cannot be expected to match the live price shown in a provider app.

**No Google key needed for estimates.** If the browser does not send a route (no Maps key), the backend looks up the route for free using OpenStreetMap Nominatim (addresses) and OSRM (driving distance). These are public community services with fair-use limits, fine for a project demo. If they cannot be reached, sample fares are shown.
