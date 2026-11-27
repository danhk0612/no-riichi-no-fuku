import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'

export function PagedPane({ children, section, label }: { children: ReactNode; section?: string; label: string }) {
  const frame = useRef<HTMLDivElement>(null)
  const content = useRef<HTMLDivElement>(null)
  const starts = useRef([0])
  const tail = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({ page: 1, pages: 1 })

  useLayoutEffect(() => {
    const box = frame.current!
    const inner = content.current!
    box.scrollTop = 0
    function updatePage() {
      const stops = starts.current
      const next = stops.findIndex(top => top > box.scrollTop + 1)
      const page = next < 0 ? stops.length : Math.max(1, next)
      setPosition(old => old.page === page && old.pages === stops.length ? old : { page, pages: stops.length })
    }
    function measure() {
      const height = box.clientHeight
      if (!height) return
      const origin = inner.getBoundingClientRect().top
      const boundaries = [...inner.querySelectorAll('h2,h3,h4,summary,label,button,li,tr,blockquote')]
        .filter(el => el.getClientRects().length)
        .map(el => Math.max(0, Math.floor(el.getBoundingClientRect().top - origin)))
        .sort((a, b) => b - a)
      const stops = [0]
      let top = 0
      while (top + height < inner.offsetHeight - 1) {
        const limit = top + Math.max(1, height - 32)
        const boundary = boundaries.find(y => y > top + height / 2 && y <= limit)
        top = boundary ?? limit
        stops.push(top)
      }
      starts.current = stops
      // Let the final section start at its label even when the last page is short.
      tail.current!.style.height = (stops.length > 1 ? Math.max(0, top + height - inner.offsetHeight) : 0) + 'px'
      updatePage()
    }
    const observer = new ResizeObserver(measure)
    observer.observe(box)
    observer.observe(inner)
    box.addEventListener('scroll', updatePage)
    measure()
    return () => { observer.disconnect(); box.removeEventListener('scroll', updatePage) }
  }, [section])

  function turn(delta: number) {
    const box = frame.current!
    box.scrollTop = starts.current[position.page - 1 + delta] ?? 0
  }
  return <div className="paged-pane">
    <div className="page-window" ref={frame}><div ref={content}>{children}</div><div ref={tail} aria-hidden="true"/></div>
    {position.pages > 1 && <nav className="candidate-pages" aria-label={label + ' 페이지'}>
      <button type="button" disabled={position.page === 1} onClick={() => turn(-1)}>이전</button>
      <span aria-live="polite">{position.page} / {position.pages}</span>
      <button type="button" disabled={position.page === position.pages} onClick={() => turn(1)}>다음</button>
    </nav>}
  </div>
}
