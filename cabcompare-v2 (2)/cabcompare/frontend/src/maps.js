// Google Maps helpers: Places autocomplete (new Places API), place details, reverse geocoding.
const KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
export const mapsEnabled = Boolean(KEY)

let loader
function loadMaps() {
  if (!mapsEnabled) return Promise.reject(new Error('Google Maps key is not configured'))
  if (window.google?.maps?.importLibrary) return Promise.resolve()
  if (!loader) {
    loader = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(KEY)}&loading=async&v=weekly`
      script.async = true
      script.onload = resolve
      script.onerror = () => { loader = null; reject(new Error('Google Maps failed to load')) }
      document.head.appendChild(script)
    })
  }
  return loader
}

export async function newSessionToken() {
  await loadMaps()
  const { AutocompleteSessionToken } = await window.google.maps.importLibrary('places')
  return new AutocompleteSessionToken()
}

export async function suggestPlaces(input, sessionToken) {
  await loadMaps()
  const { AutocompleteSuggestion } = await window.google.maps.importLibrary('places')
  const { suggestions } = await AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input, sessionToken, includedRegionCodes: ['in'],
  })
  return suggestions
    .filter((item) => item.placePrediction)
    .map(({ placePrediction: p }) => ({
      id: p.placeId,
      main: p.mainText?.text || p.text.text,
      secondary: p.secondaryText?.text || '',
      text: p.text.text,
      prediction: p,
    }))
}

export async function placeCoordinates(suggestion) {
  const place = suggestion.prediction.toPlace()
  await place.fetchFields({ fields: ['location'] })
  return { text: suggestion.text, lat: place.location.lat(), lng: place.location.lng() }
}

export async function reverseGeocode(lat, lng) {
  await loadMaps()
  const { Geocoder } = await window.google.maps.importLibrary('geocoding')
  const { results } = await new Geocoder().geocode({ location: { lat, lng } })
  if (!results?.length) throw new Error('No address found')
  return results[0].formatted_address
}

// Real driving distance and traffic-aware time (needs "Routes API" enabled on the key).
export async function routeMetrics(from, to) {
  await loadMaps()
  const { Route } = await window.google.maps.importLibrary('routes')
  const point = (p) => (p.lat != null && p.lng != null ? { lat: p.lat, lng: p.lng } : p.text)
  const { routes } = await Route.computeRoutes({
    origin: point(from), destination: point(to),
    travelMode: 'DRIVING', routingPreference: 'TRAFFIC_AWARE',
    fields: ['distanceMeters', 'durationMillis'],
  })
  const best = routes?.[0]
  if (!best?.distanceMeters) throw new Error('No route found')
  return {
    distance_km: Math.round(best.distanceMeters / 100) / 10,
    duration_minutes: Math.max(1, Math.round(best.durationMillis / 60000)),
  }
}
