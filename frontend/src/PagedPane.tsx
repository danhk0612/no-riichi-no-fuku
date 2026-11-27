import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'

export function PagedPane({ children, section, label }: { children: ReactNode; section?: string; label: string }) {
  const frame = useRef<HTMLDivElement>(null)
  const content = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({ page: 1, pages: 1 })

  useLayoutEffect(() => {
    const box = frame.current!
    const inner = content.current!
    box.scrollTop = 0
    function measure() {
      if (!box.clientHeight) return
      // Leave a line of context when a paragraph or control crosses the boundary.
      const step = Math.max(1, box.clientHeight - 48)
      const end = Math.max(0, box.scrollHeight - box.clientHeight)
      const pages = 1 + Math.ceil(end / step)
      const page = end && box.scrollTop >= end - 1 ? pages : Math.min(pages, 1 + Math.floor(box.scrollTop / step))
      setPosition(old => old.page === page && old.pages === pages ? old : { page, pages })
    }
    const observer = new ResizeObserver(measure)
    observer.observe(box)
    observer.observe(inner)
    box.addEventListener('scroll', measure)
    measure()
    return () => { observer.disconnect(); box.removeEventListener('scroll', measure) }
  }, [section])

  function turn(delta: number) {
    const box = frame.current!
    box.scrollTop = Math.max(0, position.page - 1 + delta) * Math.max(1, box.clientHeight - 48)
  }
  return <div className="paged-pane">
    <div className="page-window" ref={frame}><div ref={content}>{children}</div></div>
    {position.pages > 1 && <nav className="candidate-pages" aria-label={label + ' 페이지'}>
      <button type="button" disabled={position.page === 1} onClick={() => turn(-1)}>이전</button>
      <span aria-live="polite">{position.page} / {position.pages}</span>
      <button type="button" disabled={position.page === position.pages} onClick={() => turn(1)}>다음</button>
    </nav>}
  </div>
}
