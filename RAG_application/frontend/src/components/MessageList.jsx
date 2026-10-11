import { renderWithCitations } from '../utils/citations'

export default function MessageList({ messages, isLoading }) {
  return (
    <div className="message-list">
      {messages.length === 0 && !isLoading && (
        <div className="empty-state">
          <div className="empty-icon">✦</div>
          <h2>Ask anything about your documents</h2>
          <p>Upload PDFs, text files, or images, then start a conversation.</p>
        </div>
      )}

      {messages.map((msg) => (
        <div key={msg.id} className={`message message--${msg.role}`}>
          <div className="message-avatar">
            {msg.role === 'user' ? 'You' : 'AI'}
          </div>
          <div className="message-body">
            <div className="message-content">
              {msg.role === 'assistant'
                ? renderWithCitations(msg.content, msg.sources)
                : msg.content}
            </div>
            {msg.sources?.length > 0 && (
              <div className="message-sources">
                <span className="sources-label">Sources</span>
                {msg.sources.map((src) => (
                  <span
                    key={src.citation ?? src.filename}
                    className="source-chip"
                    title={`Relevance: ${src.score?.toFixed?.(3) ?? src.score}`}
                  >
                    <span className="cite-num">[{src.citation}]</span>
                    {src.type === 'image' ? '🖼' : '📄'} {src.filename}
                    {src.chunk_index != null && (
                      <span className="chunk-ref"> §{src.chunk_index + 1}</span>
                    )}
                    {src.match && <em className="match-badge"> {src.match}</em>}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="message message--assistant">
          <div className="message-avatar">AI</div>
          <div className="message-body">
            <div className="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
