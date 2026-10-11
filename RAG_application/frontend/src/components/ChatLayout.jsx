import { useEffect, useRef, useState } from 'react'
import {
  createSession,
  getMessages,
  listDocuments,
  listImages,
  sendMessage,
} from '../api'
import ChatInput from './ChatInput'
import FileUploadZone from './FileUploadZone'
import MessageList from './MessageList'

export default function ChatLayout() {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [uploads, setUploads] = useState({ documents: [], images: [] })
  const bottomRef = useRef(null)

  const refreshUploads = async () => {
    const [documents, images] = await Promise.all([listDocuments(), listImages()])
    setUploads({ documents, images })
  }

  useEffect(() => {
    createSession().then((session) => {
      setSessionId(session.id)
    })
    refreshUploads().catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = async (text) => {
    if (!sessionId) return

    const userMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
    }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    try {
      const response = await sendMessage(sessionId, text)
      setMessages((prev) => [
        ...prev,
        {
          id: response.message_id,
          role: 'assistant',
          content: response.content,
          sources: response.sources,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Sorry, something went wrong: ${err.message}`,
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="chat-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>RAG Chat</h1>
          <p>Document & image Q&A</p>
        </div>

        <FileUploadZone onUploadComplete={refreshUploads} />

        <div className="upload-list">
          <h3>Documents ({uploads.documents.length})</h3>
          <ul>
            {uploads.documents.map((doc) => (
              <li key={doc.id} title={doc.filename}>
                <span className="file-icon">📄</span>
                <span className="file-name">{doc.filename}</span>
                <span className={`file-status file-status--${doc.status}`}>{doc.status}</span>
              </li>
            ))}
          </ul>

          <h3>Images ({uploads.images.length})</h3>
          <ul>
            {uploads.images.map((img) => (
              <li key={img.id} title={img.filename}>
                <span className="file-icon">🖼</span>
                <span className="file-name">{img.filename}</span>
                <span className={`file-status file-status--${img.status}`}>{img.status}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <main className="chat-main">
        <MessageList messages={messages} isLoading={isLoading} />
        <div ref={bottomRef} />
        <ChatInput onSend={handleSend} disabled={isLoading || !sessionId} />
      </main>
    </div>
  )
}
