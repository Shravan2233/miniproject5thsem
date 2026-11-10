import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import {
  ArrowDownUp, ArrowRight, Bike, CarFront, Clock3, Copy,
  Crosshair, ExternalLink, MapPin, Navigation, RefreshCw, ShieldCheck, Sparkles,
  TrainFront, TriangleAlert, Zap,
} from 'lucide-react'
import LocationInput from './LocationInput.jsx'
import { mapsEnabled, reverseGeocode, routeMetrics } from './maps.js'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const ROUTES = [
  ['Indiranagar, Bengaluru', 'MG Road, Bengaluru'],
  ['Bandra, Mumbai', 'Lower Parel, Mumbai'],
  ['Connaught Place, Delhi', 'Hauz Khas, Delhi'],
]
const CATEGORIES = [
  { id: 'all', label: 'All rides', icon: Sparkles },
  { id: 'bike', label: 'Bike', icon: Bike },
  { id: 'auto', label: 'Auto', icon: Navigation },
  { id: 'sedan', label: 'Sedan', icon: CarFront },
  { id: 'premium', label: 'Premium', icon: TrainFront },
]
const place = (text) => ({ text })
const hasCoords = (p) => p.lat != null && p.lng != null
const asPlace = (p) => (typeof p === 'string' ? place(p) : p)
const normalizeRoute = (r) => ({ pickup: asPlace(r.pickup), destination: asPlace(r.destination) })
const ACTIVE_ROUTE_KEY = 'cabcompare-active-route'

function readActiveRoute() {
  try {
    const stored = sessionStorage.getItem(ACTIVE_ROUTE_KEY)
    if (!stored) return { route: null, warning: '' }

    const parsed = JSON.parse(stored)
    const savedPlace = (value) => {
      if (!value || typeof value.text !== 'string' || !value.text.trim()) return null
      const result = { text: value.text }
      if (Number.isFinite(value.lat) && Number.isFinite(value.lng)
        && value.lat >= -90 && value.lat <= 90
        && value.lng >= -180 && value.lng <= 180) {
        result.lat = value.lat
        result.lng = value.lng
      }
      return result
    }
    const pickup = savedPlace(parsed?.pickup)
    const destination = savedPlace(parsed?.destination)
    return pickup && destination
      ? { route: { pickup, destination }, warning: '' }
      : { route: null, warning: '' }
  } catch {
    return {
      route: null,
      warning: 'This browser could not restore the last route from this tab.',
    }
  }
}

function bookingUrl(booking) {
  if (!booking?.mobile_url) return booking?.url
  const isMobile = navigator.userAgentData?.mobile
    ?? (/Android|iPhone|iPod|iPad/i.test(navigator.userAgent)
      || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1))
  return isMobile ? booking.mobile_url : booking.url
}

function App() {
  const [restoration] = useState(readActiveRoute)
  const [pickup, setPickup] = useState(() => restoration.route?.pickup || place(''))
  const [destination, setDestination] = useState(() => restoration.route?.destination || place(''))
  const [route, setRoute] = useState(restoration.route)
  const [rides, setRides] = useState([])
  const [category, setCategory] = useState('all')
  const [loading, setLoading] = useState(false)
  const [pendingCoordinates, setPendingCoordinates] = useState({ pickup: false, destination: false })
  const [locating, setLocating] = useState(false)
  const [error, setError] = useState('')
  const [updatedAt, setUpdatedAt] = useState('')
  const [metrics, setMetrics] = useState(null)
  const [notice, setNotice] = useState('')
  const [copyFeedback, setCopyFeedback] = useState('')
  const [storageWarning, setStorageWarning] = useState(restoration.warning)
  const destinationRef = useRef(null)
  const resultsRef = useRef(null)
  const [recent, setRecent] = useState(() => {
    try { return JSON.parse(localStorage.getItem('cabcompare-recent') || '[]').map(normalizeRoute) } catch { return [] }
  })
  const resolvingCoordinates = Object.values(pendingCoordinates).some(Boolean)

  async function search(nextRoute, nextCategory = category, { scroll = false } = {}) {
    setLoading(true)
    setError('')
    try {
      const body = { pickup: nextRoute.pickup.text, destination: nextRoute.destination.text, category: nextCategory }
      if (hasCoords(nextRoute.pickup)) body.pickup_coords = { lat: nextRoute.pickup.lat, lng: nextRoute.pickup.lng }
      if (hasCoords(nextRoute.destination)) body.destination_coords = { lat: nextRoute.destination.lat, lng: nextRoute.destination.lng }
      let gotMetrics = null
      if (mapsEnabled) {
        try { gotMetrics = await routeMetrics(nextRoute.pickup, nextRoute.destination) } catch { /* route distance is optional */ }
        if (gotMetrics) body.route_metrics = gotMetrics
      }
      const response = await axios.post(`${API_BASE}/api/rides/compare`, body)
      setMetrics(response.data.route_metrics || null)
      setNotice(response.data.notice)
      setRoute(nextRoute)
      setPickup(nextRoute.pickup)
      setDestination(nextRoute.destination)
      setRides(response.data.rides)
      setUpdatedAt(response.data.last_updated)
      setCopyFeedback('')
      try {
        sessionStorage.setItem(ACTIVE_ROUTE_KEY, JSON.stringify(nextRoute))
        setStorageWarning('')
      } catch {
        setStorageWarning('This browser could not save the route for a return to this tab.')
      }
      setRecent((current) => {
        const same = (a, b) => a.pickup.text === b.pickup.text && a.destination.text === b.destination.text
        const updated = [nextRoute, ...current.filter((item) => !same(item, nextRoute))].slice(0, 4)
        try { localStorage.setItem('cabcompare-recent', JSON.stringify(updated)) } catch { /* storage unavailable */ }
        return updated
      })
      if (scroll) setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60)
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'Could not load comparisons. Check that the CabCompare API is running and try again.')
      setRides([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (route) search(route, category)
  }, [category])

  function handleSubmit(event) {
    event.preventDefault()
    if (resolvingCoordinates) {
      setError('Wait for the selected pickup and destination coordinates to finish loading.')
      return
    }
    if (!pickup.text.trim() || !destination.text.trim()) {
      setError(!pickup.text.trim() ? 'Enter a pickup location, or tap the locate button.' : 'Enter where you want to go.')
      return
    }
    search({ pickup, destination }, category, { scroll: true })
  }

  function swapLocations() {
    setPickup(destination)
    setDestination(pickup)
  }

  async function copyTripText() {
    const text = `Pickup: ${route.pickup.text}\nDrop: ${route.destination.text}`
    if (!navigator.clipboard?.writeText) {
      setCopyFeedback(`Clipboard is unavailable. Copy these details manually: ${text}`)
      return
    }
    try {
      await navigator.clipboard.writeText(text)
      setCopyFeedback('Pickup and destination copied. Paste them into the provider app.')
    } catch {
      setCopyFeedback(`Could not access the clipboard. Copy these details manually: ${text}`)
    }
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setError('Location is not available in this browser. You can enter your pickup manually.')
      return
    }
    setError('')
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        const { latitude: lat, longitude: lng } = coords
        let text = `Current location (${lat.toFixed(4)}, ${lng.toFixed(4)})`
        if (mapsEnabled) { try { text = await reverseGeocode(lat, lng) } catch { /* keep coordinates as the label */ } }
        setPickup({ text, lat, lng })
        setLocating(false)
        destinationRef.current?.focus()
      },
      (failure) => {
        setLocating(false)
        setError(failure.code === 1
          ? 'Location permission was blocked. Allow it in your browser settings, or type your pickup instead.'
          : 'We could not find your location. Check GPS/network, or type your pickup instead.')
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
    )
  }

  const formattedTime = updatedAt ? new Date(updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="CabCompare home">
          <span className="brand-mark"><ArrowDownUp size={19} strokeWidth={2.8} /></span>
          <span>cab<span>compare</span></span>
        </a>
        <nav className="nav-links" aria-label="Main navigation">
          <a className="nav-active" href="#compare">Compare</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <span className="demo-pill"><span /> Live fares unavailable</span>
      </header>

      <main id="top">
        <section className="hero-grid" id="compare">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-line" /> THE SMARTER WAY TO GET THERE</div>
            <h1>Plan your ride.<br /><span>Book direct.</span></h1>
            <p className="hero-subtitle">Check whether an authorized quote is available, then confirm the current fare and availability with your provider.</p>
            <div className="trust-row"><ShieldCheck size={16} /><span>Booking stays with your ride provider</span></div>
          </div>

          <form className="search-panel" onSubmit={handleSubmit}>
            <div className="panel-heading">
              <div><span className="panel-kicker">PLAN YOUR RIDE</span><h2>Where are you headed?</h2></div>
              <span className="route-icon"><Navigation size={19} /></span>
            </div>
            <div className="location-fields">
              <LocationInput kicker="FROM" label="Pickup location" dotClass="pickup-dot" value={pickup} placeholder="Pickup location"
                onTyping={(text) => setPickup(place(text))} onPick={setPickup}
                onCoordinatesPending={(pending) => setPendingCoordinates((current) => ({ ...current, pickup: pending }))}>
                <button className="icon-button locate-button" type="button" onClick={useCurrentLocation} disabled={locating || pendingCoordinates.pickup} title="Use my current location" aria-label="Use my current location">
                  {locating ? <span className="button-spinner dark" /> : <Crosshair size={17} />}
                </button>
              </LocationInput>
              <button className="swap-button" type="button" onClick={swapLocations} disabled={resolvingCoordinates} title="Swap pickup and destination" aria-label="Swap pickup and destination"><ArrowDownUp size={15} /></button>
              <LocationInput kicker="TO" label="Destination" dotClass="destination-dot" value={destination} placeholder="Where to?" inputRef={destinationRef}
                onTyping={(text) => setDestination(place(text))} onPick={setDestination} searchContext={pickup}
                onCoordinatesPending={(pending) => setPendingCoordinates((current) => ({ ...current, destination: pending }))} />
            </div>
            <button className="search-button" type="submit" disabled={loading || resolvingCoordinates}>
              {loading ? <><span className="button-spinner" /> Comparing rides</> : <>Compare rides <ArrowRight size={17} /></>}
            </button>
            {error && <div className="error-message" role="alert"><TriangleAlert size={16} />{error}</div>}
            <div className="form-footnote"><span className="privacy-dot" /> {mapsEnabled ? 'Suggestions by Google Maps. ' : 'Type an area or landmark. '}Your route is only used to compare this trip</div>
          </form>
        </section>

        {route ? (
          <section className="results-section" aria-live="polite" ref={resultsRef}>
            <div className="results-topline">
              <div>
                <div className="section-overline">YOUR ROUTE</div>
                <div className="route-summary"><span>{route.pickup.text}</span><ArrowRight size={16} /><span>{route.destination.text}</span></div>
              </div>
              <button type="button" className="refresh-button" onClick={() => search(route)} disabled={loading}>
                <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh comparison
              </button>
            </div>
            <div className="results-toolbar">
              <div className="category-tabs" role="tablist" aria-label="Choose a requested ride category">
                {CATEGORIES.map(({ id, label, icon: Icon }) => <button key={id} type="button" role="tab" aria-selected={category === id} className={category === id ? 'category-tab selected' : 'category-tab'} onClick={() => setCategory(id)}><Icon size={16} />{label}</button>)}
              </div>
            </div>
            <div className="results-meta"><span>{rides.length} providers{metrics ? ` · ${metrics.distance_km} km · about ${metrics.duration_minutes} min route` : ''}</span><span className="updated-label"><Clock3 size={13} /> Updated {formattedTime || 'just now'}</span></div>
            {loading ? <div className="ride-list" aria-label="Loading ride options">{[1, 2, 3].map((item) => <div className="skeleton-card" key={item}><span /><div><i /><i /></div><i /><span /></div>)}</div> : rides.length ? (
              <div className="ride-list">
                {rides.map((ride) => <article className={ride.is_lowest ? 'ride-card lowest-card' : 'ride-card'} key={ride.id}>
                  <div className={`provider-symbol ${ride.ride_type}`} aria-hidden="true">{ride.ride_type === 'bike' ? <Bike size={20} /> : ride.ride_type === 'auto' ? <Navigation size={19} /> : <CarFront size={20} />}</div>
                  <div className="ride-main">
                    <div className="ride-title-row"><h3>{ride.provider}</h3></div>
                    <div className="ride-details"><span>{ride.requested_category ? `Requested: ${ride.requested_category}` : 'Vehicle category not returned'}</span><span className="detail-separator" /><span><Clock3 size={13} /> ETA unavailable</span><span className="detail-separator" /><span>Availability not checked</span></div>
                    <div className="fare-source"><span className="unavailable-tag">{ride.fare_status}</span><span>{ride.fare_message}</span></div>
                  </div>
                  <div className="ride-price unavailable-price" aria-label={`${ride.provider} live fare unavailable`}><strong>—</strong><span>Live fare unavailable</span></div>
                  <div className="ride-action">
                    <div className="provider-actions">
                      {!ride.booking?.prefilled && <button className="copy-route-button" type="button" onClick={copyTripText}><Copy size={13} /> Copy route</button>}
                      <a className="provider-button" href={bookingUrl(ride.booking)} target="_blank" rel="noopener noreferrer">Book on {ride.provider} <ExternalLink size={14} /></a>
                    </div>
                    <span>{ride.booking?.message}</span>
                  </div>
                </article>)}
              </div>
            ) : <div className="empty-state"><MapPin size={21} /><strong>No ride options in this category</strong><span>Try another ride type or compare all rides.</span></div>}
            {copyFeedback && <p className="copy-feedback" role="status">{copyFeedback}</p>}
            {storageWarning && <p className="copy-feedback" role="status">{storageWarning}</p>}
            <div className="fare-disclaimer"><TriangleAlert size={16} /><span>{notice}</span></div>
          </section>
        ) : (
          <section className="discovery-section">
            <div className="discovery-column">
              <div className="section-heading"><div><div className="section-overline">PICK UP WHERE YOU LEFT OFF</div><h2>Recent searches</h2></div><span className="small-caption">Saved on this device</span></div>
              {recent.length ? <div className="recent-list">{recent.map((item, index) => <button type="button" className="recent-route" key={`${item.pickup.text}-${index}`} onClick={() => search(item, category, { scroll: true })}><span className="recent-route-icon"><Clock3 size={16} /></span><span className="recent-route-text"><strong>{item.pickup.text}</strong><span>{item.destination.text}</span></span><ArrowRight size={16} /></button>)}</div> : <p className="muted-copy">Your recent routes will show up here.</p>}
            </div>
            <div className="discovery-column popular-column">
              <div className="section-heading"><div><div className="section-overline">ROUTES TO EXPLORE</div><h2>Popular routes</h2></div><span className="sample-note">Sample routes</span></div>
              <div className="popular-list">{ROUTES.map(([from, to]) => <button type="button" className="popular-route" key={from} onClick={() => search({ pickup: place(from), destination: place(to) }, category, { scroll: true })}><span className="popular-route-points"><span><i />{from}</span><span><i />{to}</span></span><span className="popular-route-action">Compare <ArrowRight size={14} /></span></button>)}</div>
            </div>
          </section>
        )}

        <section className="how-section" id="how-it-works">
          <div className="how-heading"><div className="section-overline">A BETTER WAY TO BOOK</div><h2>Three steps. Better choices.</h2></div>
          <div className="how-steps">
            <div className="how-step"><span className="step-number">01</span><div><h3>Enter your route</h3><p>Tell us where your trip starts and ends.</p></div></div>
            <div className="step-rule" />
            <div className="how-step"><span className="step-number">02</span><div><h3>Check provider status</h3><p>See whether a provider can return an authorized fare.</p></div></div>
            <div className="step-rule" />
            <div className="how-step"><span className="step-number">03</span><div><h3>Check the current fare</h3><p>Open the provider and confirm the trip before booking.</p></div></div>
          </div>
        </section>
      </main>

      <footer className="footer"><a className="brand footer-brand" href="#top"><span className="brand-mark"><ArrowDownUp size={16} strokeWidth={2.8} /></span><span>cab<span>compare</span></span></a><span>Provider-led bookings. Live fare access is not configured.</span><span className="footer-status"><Zap size={13} /> Fares unavailable</span></footer>
    </div>
  )
}

export default App