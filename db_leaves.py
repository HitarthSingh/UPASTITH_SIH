import sqlite3

def init_leave_db(db_path: str) -> None:
    """Ensure leaves.db has the expected leave_applications schema."""
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leave_applications'")
        exists = c.fetchone() is not None

        desired_columns = [
            ("id", "INTEGER", 0),
            ("student_name", "TEXT", 1),
            ("student_id", "TEXT", 0),
            ("reason", "TEXT", 1),
            ("start_date", "TEXT", 1),
            ("end_date", "TEXT", 1),
            ("status", "TEXT", 0),
            ("attached_document", "TEXT", 0),
            ("created_at", "TIMESTAMP", 0),
            ("updated_at", "TIMESTAMP", 0),
        ]

        def create_with_desired_schema(table_name: str) -> None:
            c.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    student_id TEXT,
                    reason TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    attached_document TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        if not exists:
            create_with_desired_schema("leave_applications")
            conn.commit()
            return

        c.execute("PRAGMA table_info(leave_applications)")
        current_info = c.fetchall()
        current_cols = [(row[1], row[2], row[3]) for row in current_info]

        if current_cols != desired_columns:
            create_with_desired_schema("leave_applications_new")

            current_col_names = {name for (name, _type, _nn) in current_cols}
            copy_cols = [name for (name, _type, _nn) in desired_columns if name in current_col_names and name != "attached_document"]
            if copy_cols:
                cols_csv = ", ".join(copy_cols)
                c.execute(
                    f"INSERT INTO leave_applications_new ({cols_csv}) SELECT {cols_csv} FROM leave_applications"
                )

            c.execute("DROP TABLE leave_applications")
            c.execute("ALTER TABLE leave_applications_new RENAME TO leave_applications")

        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


