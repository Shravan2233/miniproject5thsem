import { useEffect, useRef, useState } from 'react'
import { MapPin, X } from 'lucide-react'
import { mapsEnabled, newSessionToken, placeCoordinates, suggestPlaces } from './maps.js'

// Combobox with Google Places suggestions. Works as a plain text field when no Maps key is set.
export default function LocationInput({ kicker, label, dotClass, value, onTyping, onPick, placeholder, inputRef, children }) {
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [busy, setBusy] = useState(false)
  const token = useRef(null)
  const wrapper = useRef(null)
  const text = value.text || ''

  useEffect(() => {
    if (!mapsEnabled || !open || text.trim().length < 3 || value.lat != null) { setItems([]); return undefined }
    let cancelled = false
    const timer = setTimeout(async () => {
      setBusy(true)
      try {
        token.current = token.current || (await newSessionToken())
        const found = await suggestPlaces(text.trim(), token.current)
        if (!cancelled) { setItems(found.slice(0, 5)); setActive(-1) }
      } catch { if (!cancelled) setItems([]) }
      finally { if (!cancelled) setBusy(false) }
    }, 250)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [text, open, value.lat])

  useEffect(() => {
    const close = (event) => { if (!wrapper.current?.contains(event.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  async function choose(item) {
    setOpen(false); setItems([])
    onPick({ text: item.text }) // show the label immediately
    try { onPick(await placeCoordinates(item)) } catch { /* label alone is still usable */ }
    token.current = null // a session ends once a place is selected
  }

  function onKeyDown(event) {
    if (!open || !items.length) return
    if (event.key === 'ArrowDown') { event.preventDefault(); setActive((i) => (i + 1) % items.length) }
    else if (event.key === 'ArrowUp') { event.preventDefault(); setActive((i) => (i <= 0 ? items.length - 1 : i - 1)) }
    else if (event.key === 'Enter' && active >= 0) { event.preventDefault(); choose(items[active]) }
    else if (event.key === 'Escape') setOpen(false)
  }

  const listId = `${kicker}-suggestions`
  return (
    <div className="location-input" ref={wrapper}>
      <span className={`location-dot ${dotClass}`} />
      <span className="input-copy">
        <span>{kicker}</span>
        <input
          ref={inputRef} aria-label={label} value={text} placeholder={placeholder} maxLength={160}
          role="combobox" aria-expanded={open && items.length > 0} aria-controls={listId} aria-autocomplete="list"
          autoComplete="off" onKeyDown={onKeyDown} onFocus={() => setOpen(true)}
          onChange={(event) => { onTyping(event.target.value); setOpen(true) }}
        />
      </span>
      {text && <button type="button" className="clear-button" aria-label={`Clear ${label.toLowerCase()}`} onClick={() => { onTyping(''); inputRef?.current?.focus() }}><X size={14} /></button>}
      {children}
      {open && (items.length > 0 || busy) && (
        <ul className="suggestions" id={listId} role="listbox">
          {items.map((item, index) => (
            <li key={item.id} role="option" aria-selected={index === active} className={index === active ? 'active' : ''}
              onMouseDown={(event) => { event.preventDefault(); choose(item) }} onMouseEnter={() => setActive(index)}>
              <MapPin size={16} /><span><strong>{item.main}</strong><small>{item.secondary}</small></span>
            </li>
          ))}
          {busy && !items.length && <li className="suggestions-note">Searching places…</li>}
          {items.length > 0 && <li className="suggestions-note powered">Powered by Google</li>}
        </ul>
      )}
    </div>
  )
}
