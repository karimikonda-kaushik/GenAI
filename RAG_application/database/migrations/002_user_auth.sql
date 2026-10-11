-- Per-user data isolation for multi-tenant security

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE images ADD COLUMN IF NOT EXISTS user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_images_user_id ON images(user_id);

-- Backfill existing rows to a legacy bucket (optional; remove if fresh DB)
UPDATE sessions SET user_id = 'legacy' WHERE user_id IS NULL;
UPDATE documents SET user_id = 'legacy' WHERE user_id IS NULL;
UPDATE images SET user_id = 'legacy' WHERE user_id IS NULL;
