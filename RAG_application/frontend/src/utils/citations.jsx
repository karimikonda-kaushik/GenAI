/**
 * Renders AI message text with highlighted inline citations [1], [2], etc.
 */
export function renderWithCitations(text, sources = []) {
  if (!text) return null

  const parts = text.split(/(\[\d+\])/g)

  return parts.map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (!match) {
      return <span key={index}>{part}</span>
    }

    const citeNum = match[1]
    const source = sources.find((s) => String(s.citation) === citeNum)
    const title = source
      ? `${source.filename}${source.chunk_index != null ? ` (chunk ${source.chunk_index + 1})` : ''}`
      : `Source ${citeNum}`

    return (
      <sup key={index} className="inline-citation" title={title}>
        [{citeNum}]
      </sup>
    )
  })
}
