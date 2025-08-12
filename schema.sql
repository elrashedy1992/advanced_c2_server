CREATE TABLE IF NOT EXISTS victims (
    id TEXT PRIMARY KEY,
    ip_address TEXT,
    user_agent TEXT,
    permissions TEXT,
    first_seen DATETIME,
    last_seen DATETIME,
    is_online BOOLEAN
);

CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    victim_id TEXT,
    type TEXT,
    command TEXT,
    result TEXT,
    status TEXT,
    created_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY (victim_id) REFERENCES victims (id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
);
