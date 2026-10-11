import { useRef } from 'react'

export default function ChatInput({ onSend, disabled }) {
  const inputRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    const text = inputRef.current.value.trim()
    if (!text || disabled) return
    onSend(text)
    inputRef.current.value = ''
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <textarea
        ref={inputRef}
        placeholder="Ask a question about your documents or images..."
        rows={1}
        disabled={disabled}
        onKeyDown={handleKeyDown}
      />
      <button type="submit" disabled={disabled} aria-label="Send message">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
        </svg>
      </button>
    </form>
  )
}
