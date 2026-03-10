<?php
require_once 'config.php';

session_start();

if (isset($_REQUEST['user']) && isset($_REQUEST['pass'])) {
    $db = new SQLite3(DB_PATH);
    // VULNERABLE: No prepared statements — SQL injection possible
    $user = $_REQUEST['user'];
    $pass = $_REQUEST['pass'];
    $query = "SELECT username, password, role FROM users WHERE username='$user' AND password='$pass'";
    $result = $db->query($query);

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // POST login: set session and redirect to shell
        if ($row = $result->fetchArray()) {
            $_SESSION['logged_in'] = true;
            $_SESSION['username'] = $row['username'];
            $_SESSION['role'] = $row['role'];
            header('Location: shell.php');
            exit;
        } else {
            $error = "Invalid credentials.";
        }
    } else {
        // GET request: display query results inline
        $rows = [];
        while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
            $rows[] = $row;
        }
    }
    $db->close();
}
?>
<!DOCTYPE html>
<html>
<head><title>Customer Portal - Login</title></head>
<body>
<h1>Customer Portal</h1>
<?php if (isset($error)): ?>
    <p style="color:red"><?php echo htmlspecialchars($error); ?></p>
<?php endif; ?>
<?php if (!empty($rows)): ?>
    <table border="1">
        <tr><th>Username</th><th>Password</th><th>Role</th></tr>
        <?php foreach ($rows as $r): ?>
            <tr>
                <td><?php echo htmlspecialchars($r['username']); ?></td>
                <td><?php echo htmlspecialchars($r['password']); ?></td>
                <td><?php echo htmlspecialchars($r['role']); ?></td>
            </tr>
        <?php endforeach; ?>
    </table>
<?php endif; ?>
<form method="POST">
    <label>Username: <input type="text" name="user"></label><br>
    <label>Password: <input type="password" name="pass"></label><br>
    <button type="submit">Login</button>
</form>
</body>
</html>
