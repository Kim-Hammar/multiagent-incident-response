<?php
require_once 'config.php';

session_start();

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['username']) && isset($_POST['password'])) {
    $db = new SQLite3(DB_PATH);
    // VULNERABLE: No prepared statements — SQL injection possible
    $username = $_POST['username'];
    $password = $_POST['password'];
    $query = "SELECT * FROM users WHERE username='$username' AND password='$password'";
    $result = $db->query($query);

    if ($row = $result->fetchArray()) {
        $_SESSION['logged_in'] = true;
        $_SESSION['username'] = $row['username'];
        $_SESSION['role'] = $row['role'];
        header('Location: shell.php');
        exit;
    } else {
        $error = "Invalid credentials.";
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
<form method="POST">
    <label>Username: <input type="text" name="username"></label><br>
    <label>Password: <input type="password" name="password"></label><br>
    <button type="submit">Login</button>
</form>
</body>
</html>
