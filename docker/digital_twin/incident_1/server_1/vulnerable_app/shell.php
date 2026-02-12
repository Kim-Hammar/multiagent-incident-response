<?php
session_start();
if (!isset($_SESSION['logged_in']) || $_SESSION['logged_in'] !== true) {
    header('Location: index.php');
    exit;
}

$output = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['host'])) {
    // VULNERABLE: Command injection — no input sanitization
    $host = $_POST['host'];
    $output = shell_exec("ping -c 2 " . $host);
}
?>
<!DOCTYPE html>
<html>
<head><title>System Diagnostics</title></head>
<body>
<h1>System Diagnostics</h1>
<p>Welcome, <?php echo htmlspecialchars($_SESSION['username']); ?></p>
<form method="POST">
    <label>Host to ping: <input type="text" name="host" placeholder="10.0.0.1"></label>
    <button type="submit">Run Diagnostics</button>
</form>
<?php if ($output): ?>
    <h2>Results:</h2>
    <pre><?php echo htmlspecialchars($output); ?></pre>
<?php endif; ?>
</body>
</html>
