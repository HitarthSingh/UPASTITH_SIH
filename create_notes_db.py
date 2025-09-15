import os
import sqlite3


def ensure_uploads_dir(path: str = 'uploads') -> None:
    try:
        os.makedirs(path, exist_ok=True)
        print(f"✅ Ensured folder: {path}")
    except Exception as e:
        print(f"⚠️ Could not create folder '{path}': {e}")


def ensure_notes_db(db_path: str = 'notes.db') -> None:
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                teacher_id TEXT,
                teacher_name TEXT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS notes_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                student_id TEXT NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(note_id, student_id)
            )
            """
        )
        conn.commit()
        print(f"✅ Ensured database schema: {db_path}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    ensure_uploads_dir('uploads')
    ensure_notes_db('notes.db')
    print('Done.')


