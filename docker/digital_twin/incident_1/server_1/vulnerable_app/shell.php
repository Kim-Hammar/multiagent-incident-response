<?php
$output = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['cmd'])) {
    // VULNERABLE: Command injection — no input sanitization
    $cmd = $_POST['cmd'];
    $output = shell_exec($cmd);
}
?>
<!DOCTYPE html>
<html>
<head><title>System Diagnostics</title></head>
<body>
<h1>System Diagnostics</h1>
<form method="POST">
    <label>Command: <input type="text" name="cmd" placeholder="id"></label>
    <button type="submit">Run</button>
</form>
<?php if ($output): ?>
    <h2>Results:</h2>
    <pre><?php echo htmlspecialchars($output); ?></pre>
<?php endif; ?>
</body>
</html>
