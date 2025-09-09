const path = require('path');
const fs = require('fs');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');

async function main() {
  const dbDir = path.join(__dirname, 'db');
  if (!fs.existsSync(dbDir)) fs.mkdirSync(dbDir);
  const dbPath = path.join(dbDir, 'app.sqlite');
  const db = new sqlite3.Database(dbPath);

  const username = process.argv[2] || 'admin';
  const password = process.argv[3] || 'admin123';
  const role = process.argv[4] || 'teacher';
  const passwordHash = await bcrypt.hash(password, 10);

  await new Promise((resolve, reject) => {
    db.run(
      `CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('teacher','student')) DEFAULT 'student',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )`,
      (err) => (err ? reject(err) : resolve())
    );
  });

  await new Promise((resolve, reject) => {
    const sql = 'INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)';
    db.run(sql, [username, passwordHash, role], (err) => (err ? reject(err) : resolve()))
  });

  console.log(`Seeded user: ${username} (role=${role})`);
  db.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});








