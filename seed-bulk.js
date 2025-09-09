const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');

async function hashPassword(plain) {
  return bcrypt.hash(plain, 10);
}

function ensureDb(dbDir) {
  if (!fs.existsSync(dbDir)) fs.mkdirSync(dbDir);
}

async function run() {
  const inputPathArg = process.argv[2] || 'users.json';
  const inputPath = path.isAbsolute(inputPathArg)
    ? inputPathArg
    : path.join(__dirname, inputPathArg);

  if (!fs.existsSync(inputPath)) {
    console.error(`Input file not found: ${inputPath}`);
    process.exit(1);
  }

  const raw = fs.readFileSync(inputPath, 'utf8');
  let users;
  try {
    users = JSON.parse(raw);
  } catch (e) {
    console.error('Invalid JSON in users file.');
    process.exit(1);
  }

  if (!Array.isArray(users)) {
    console.error("users.json must be an array of { username, password, role } where role is 'teacher' or 'student'");
    process.exit(1);
  }

  const dbDir = path.join(__dirname, 'db');
  ensureDb(dbDir);
  const dbPath = path.join(dbDir, 'app.sqlite');
  const db = new sqlite3.Database(dbPath);

  // Ensure table exists
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

  const insertSql = 'INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, COALESCE(?, "student"))';
  const updateSql = 'UPDATE users SET password_hash = ?, role = COALESCE(?, role) WHERE username = ?';

  for (const u of users) {
    if (!u || !u.username || !u.password) {
      console.warn('Skipping invalid entry:', u);
      continue;
    }
    const hash = await hashPassword(u.password);
    await new Promise((resolve, reject) => {
      db.run(insertSql, [u.username, hash, u.role], function (err) {
        if (err) return reject(err);
        // If row was ignored (already exists), update password
        if (this.changes === 0) {
          db.run(updateSql, [hash, u.role, u.username], (err2) => (err2 ? reject(err2) : resolve()));
        } else {
          resolve();
        }
      });
    });
    console.log(`Upserted user: ${u.username}`);
  }

  db.close();
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});






