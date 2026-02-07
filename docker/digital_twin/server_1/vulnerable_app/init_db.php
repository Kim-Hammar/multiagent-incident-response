<?php
require_once 'config.php';

$db = new SQLite3(DB_PATH);

$db->exec("CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user'
)");

$existing = $db->querySingle("SELECT COUNT(*) FROM users");
if ($existing == 0) {
    $db->exec("INSERT INTO users (username, password, role) VALUES ('admin', 'supersecret', 'admin')");
    $db->exec("INSERT INTO users (username, password, role) VALUES ('user1', 'password1', 'user')");
    $db->exec("INSERT INTO users (username, password, role) VALUES ('user2', 'password2', 'user')");
}

$db->close();
echo "Database initialized.\n";
?>
