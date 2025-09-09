// server.js

// ## 1. Imports
const path = require('path');
const fs = require('fs');
const express = require('express');
const session = require('express-session');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const morgan = require('morgan');
const cors = require('cors');

// ## 2. App Initialization & Constants
const app = express();
const PORT = process.env.PORT || 3000;
const dbDir = path.join(__dirname, 'db');
const dbPath = path.join(dbDir, 'app.sqlite');
const staticDir = path.join(__dirname, 'SIHupastith');

// ## 3. Database Setup
// Ensure the 'db' directory exists before trying to create the database file
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir);
}
// Connect to the SQLite database
const db = new sqlite3.Database(dbPath);

// Create the 'users' table if it doesn't already exist.
// This table stores user credentials. The password is not stored directly;
// instead, a secure hash of the password is stored in 'password_hash'.
db.serialize(() => {
  db.run(
    `CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT CHECK(role IN ('teacher','student')) DEFAULT 'student',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`
  );

  // Attempt to add role column if table was created previously without it
  db.run(
    `ALTER TABLE users ADD COLUMN role TEXT CHECK(role IN ('teacher','student')) DEFAULT 'student'`,
    (err) => {
      // ignore error if column already exists
    }
  );

  // Store metadata for teacher document uploads (e.g., PDFs)
  db.run(
    `CREATE TABLE IF NOT EXISTS teacher_documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      uploader_user_id INTEGER NOT NULL,
      title TEXT,
      original_filename TEXT NOT NULL,
      stored_filename TEXT NOT NULL,
      mime_type TEXT,
      file_size_bytes INTEGER,
      uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (uploader_user_id) REFERENCES users(id) ON DELETE CASCADE
    )`
  );

  // Helpful index for quick lookups per uploader
  db.run(
    `CREATE INDEX IF NOT EXISTS idx_teacher_documents_uploader ON teacher_documents(uploader_user_id)`
  );
});

// ## 4. Middleware Configuration
app.use(morgan('dev')); // Logger for HTTP requests
app.use(cors({ origin: true, credentials: true })); // Enable Cross-Origin Resource Sharing
app.use(express.json()); // To parse JSON request bodies
app.use(express.urlencoded({ extended: true })); // To parse URL-encoded request bodies

// Session Middleware: This is the core of our authentication state.
// It creates a session for each user, stored server-side, and uses a cookie
// to identify the user's session on subsequent requests.
app.use(
  session({
    secret: process.env.SESSION_SECRET || 'change_this_secret_in_prod',
    resave: false,
    saveUninitialized: false, // Don't create a session until something is stored
    cookie: {
      httpOnly: true, // Prevents client-side JS from accessing the cookie
      maxAge: 1000 * 60 * 60 * 8, // Session cookie expires in 8 hours
      // secure: process.env.NODE_ENV === 'production' // Uncomment this in production to ensure cookie is sent only over HTTPS
    },
  })
);

// ## 5. Authentication Middleware
/**
 * A middleware function to protect routes.
 * It checks if a user ID exists in the session. If it does, the user is authenticated
 * and the request can proceed. If not, it denies access with a 401 Unauthorized error.
 */
function requireAuth(req, res, next) {
  if (req.session && req.session.userId) {
    return next();
  }
  // If the client expects HTML (normal page navigation), redirect to login page
  if (req.accepts('html')) {
    return res.redirect('/login.html');
  }
  // Default to JSON error for API/AJAX calls
  return res.status(401).json({ error: 'Unauthorized' });
}

// Additional middleware to enforce role on protected pages
function requireRole(expectedRole) {
  return function (req, res, next) {
    if (req.session && req.session.role === expectedRole) return next();
    if (req.accepts('html')) {
      // Redirect to appropriate entry page
      return res.redirect(expectedRole === 'teacher' ? '/login.html' : '/landingpagefinal1.html');
    }
    return res.status(403).json({ error: 'Forbidden' });
  };
}

// ## 6. Route Handlers

// Promisify the database `get` method to use with async/await
const dbGet = (sql, params) =>
  new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
  });

/**
 * Handles the login logic for both students and teachers.
 */
async function handleAuth(req, res) {
  const { username, teacher_id, password } = req.body;
  const resolvedUsername = (username || teacher_id || '').trim(); // Accept either 'username' or 'teacher_id'
  const resolvedPassword = (password || '').trim();
  const wantsJson = req.is('application/json'); // Check if the request expects a JSON response

  if (!resolvedUsername || !resolvedPassword) {
    const errorMsg = 'Username and password are required';
    return wantsJson ? res.status(400).json({ error: errorMsg }) : res.status(400).send(errorMsg);
  }

  try {
    // Find the user in the database by their username
    const sql = 'SELECT id, username, password_hash, role FROM users WHERE lower(username) = lower(?)';
    const user = await dbGet(sql, [resolvedUsername]);

    if (!user) {
      const errorMsg = 'Invalid credentials';
      return wantsJson ? res.status(401).json({ error: errorMsg }) : res.status(401).send(errorMsg);
    }

    // Compare the provided password with the stored hash using bcrypt
    const isPasswordValid = await bcrypt.compare(resolvedPassword, user.password_hash);

    if (!isPasswordValid) {
      const errorMsg = 'Invalid credentials';
      return wantsJson ? res.status(401).json({ error: errorMsg }) : res.status(401).send(errorMsg);
    }

    // --- Authentication Successful ---
    // Enforce role per endpoint
    const endpoint = req.path;
    if (endpoint === '/login/teacher' && user.role !== 'teacher') {
      const errorMsg = 'Teacher account required';
      return wantsJson ? res.status(403).json({ error: errorMsg }) : res.status(403).send(errorMsg);
    }
    if (endpoint === '/login' && user.role !== 'student') {
      const errorMsg = 'Student account required';
      return wantsJson ? res.status(403).json({ error: errorMsg }) : res.status(403).send(errorMsg);
    }
    // Store user ID, username and role in the session to mark them as logged in
    req.session.userId = user.id;
    req.session.username = user.username;
    req.session.role = user.role;

    // Respond based on the request type
    if (wantsJson) {
      return res.json({ success: true, username: user.username });
    }
    // If teacher endpoint used, go to teacher dashboard; else student dashboard
    if (req.path === '/login/teacher') {
      return res.redirect('/teacherdasboardsemifinal.html');
    }
    return res.redirect('/studentdashboard.html');
  } catch (e) {
    console.error('Authentication Error:', e);
    const errorMsg = 'An error occurred during authentication';
    return wantsJson ? res.status(500).json({ error: errorMsg }) : res.status(500).send(errorMsg);
  }
}

// ## 7. Route Definitions

// --- Auth Routes ---
app.post('/login', handleAuth);
app.post('/login/teacher', handleAuth);

app.post('/logout', (req, res) => {
  // Destroy the session to log the user out
  req.session.destroy(() => {
    res.clearCookie('connect.sid'); // The default session cookie name
    res.json({ success: true });
  });
});

// Route to check the current authentication status
app.get('/me', (req, res) => {
  if (req.session && req.session.userId) {
    return res.json({ authenticated: true, username: req.session.username, role: req.session.role });
  }
  return res.json({ authenticated: false });
});

// --- Static and Page-Serving Routes ---

// Serve assets like CSS, JS, and images from a public directory
app.use('/static', express.static(staticDir));

// Root route redirects to the login page
app.get('/', (req, res) => {
  res.redirect('/landingpagefinal1.html');
});

// Serve the teacher login page (always show the form)
app.get('/login.html', (req, res) => {
  res.sendFile(path.join(staticDir, 'teacherloginpage2.html'));
});

// Serve the student landing page explicitly (unprotected) for login
app.get('/landingpagefinal1.html', (req, res) => {
  res.sendFile(path.join(staticDir, 'landingpagefinal1.html'));
});

// Serve the forgot password page for both teacher and student flows
app.get('/forgetpassword.html', (req, res) => {
  res.sendFile(path.join(staticDir, 'forgetpasswordteacher.html'));
});

// --- Protected Routes ---
// This list contains all pages that require a user to be logged in.
const protectedPages = [
  'leaveapplication.html',
  'repository.html',
  'studentdashboard.html',
  'studentresult.html',
  'suggestionbox.html',
  'teacherdasboardsemifinal.html',
  'timetable.html',
];

// Dynamically create a protected route for each page in the list.
// The `requireAuth` middleware is applied here to ensure only authenticated users can access them.
protectedPages.forEach((page) => {
  app.get('/' + page, requireAuth, (req, res) => {
    res.sendFile(path.join(staticDir, page));
  });
});

// Enforce roles on dashboards
app.get('/teacherdasboardsemifinal.html', requireAuth, requireRole('teacher'), (req, res) => {
  res.sendFile(path.join(staticDir, 'teacherdasboardsemifinal.html'));
});
app.get('/studentdashboard.html', requireAuth, requireRole('student'), (req, res) => {
  res.sendFile(path.join(staticDir, 'studentdashboard.html'));
});

// --- Fallback 404 Handler ---
app.use((req, res) => {
  res.status(404).send('Not Found');
});

// ## 8. Server Start
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});