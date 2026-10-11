import { useRef, useState } from 'react'
import { uploadDocument, uploadImage } from '../api'

export default function FileUploadZone({ onUploadComplete }) {
  const fileRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [status, setStatus] = useState(null)

  const handleFiles = async (files) => {
    if (!files?.length) return
    setUploading(true)
    setStatus(null)

    const results = []
    for (const file of files) {
      try {
        const isImage = file.type.startsWith('image/')
        const result = isImage
          ? await uploadImage(file)
          : await uploadDocument(file)
        results.push({ ok: true, filename: file.name, ...result })
      } catch (err) {
        results.push({ ok: false, filename: file.name, error: err.message })
      }
    }

    setUploading(false)
    const failed = results.filter((r) => !r.ok)
    if (failed.length) {
      setStatus({ type: 'error', text: `Failed: ${failed.map((f) => f.filename).join(', ')}` })
    } else {
      setStatus({ type: 'success', text: `Indexed ${results.length} file(s)` })
    }
    onUploadComplete?.()
  }

  const onDrop = (e) => {
    e.preventDefault()
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="upload-zone">
      <div
        className={`upload-drop ${uploading ? 'upload-drop--active' : ''}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md,image/*"
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="upload-icon">↑</div>
        <p className="upload-title">
          {uploading ? 'Indexing...' : 'Drop files here'}
        </p>
        <p className="upload-hint">PDF, TXT, MD, or images</p>
      </div>
      {status && (
        <p className={`upload-status upload-status--${status.type}`}>{status.text}</p>
      )}
    </div>
  )
}
