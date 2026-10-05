<?php
require_once dirname(__DIR__) . '/scripts/common.php';
ensure_authenticated('You must be authenticated to export or download detections.');

function export_response($code, $data) {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data);
    exit;
}

$root = get_home() . '/BirdNET-Pi';
$output = $root . '/BirdDB_verified.txt';
$action = $_GET['action'] ?? '';
if ($action !== 'download' && $action !== 'run') {
    export_response(400, ['ok' => false, 'message' => 'Unknown action']);
}
if ($action === 'run') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        header('Allow: POST');
        export_response(405, ['ok' => false, 'message' => 'Use POST to start an export']);
    }
    $token = $_POST['token'] ?? '';
    if (!is_string($token) || !isset($_SESSION['verified_export_token']) ||
        !hash_equals($_SESSION['verified_export_token'], $token)) {
        export_response(403, ['ok' => false, 'message' => 'Reload System Controls and try again']);
    }
}
session_write_close();
$lock = fopen(sys_get_temp_dir() . '/birdnet-verified-' . hash('sha256', $root) . '.lock', 'c');
if ($lock === false) {
    export_response(500, ['ok' => false, 'message' => 'Cannot open export lock']);
}
$mode = $action === 'run' ? LOCK_EX : LOCK_SH;
if (!flock($lock, $mode | LOCK_NB)) {
    export_response(409, ['ok' => false, 'message' => 'Export is running. Please wait.']);
}
if ($action === 'download') {
    if (!is_file($output) || !is_readable($output)) {
        export_response(404, ['ok' => false, 'message' => 'Generate BirdDB_verified.txt first']);
    }
    header('Content-Type: text/plain; charset=utf-8');
    header('Content-Disposition: attachment; filename="BirdDB_verified.txt"');
    header('Content-Length: ' . filesize($output));
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    readfile($output);
    exit;
}
set_time_limit(0);
ignore_user_abort(true);
$command = ['sudo', '-n', '-u', get_user(), '/usr/bin/python3',
            $root . '/scripts/run_verified_export.py'];
$process = proc_open($command, [0 => ['pipe', 'r'], 1 => ['pipe', 'w'],
                               2 => ['pipe', 'w']], $pipes, $root);
if (!is_resource($process)) {
    export_response(500, ['ok' => false, 'message' => 'Cannot start exporter']);
}
fclose($pipes[0]);
$stdout = stream_get_contents($pipes[1]);
$stderr = stream_get_contents($pipes[2]);
fclose($pipes[1]);
fclose($pipes[2]);
$exitCode = proc_close($process);
$result = json_decode($stdout, true);
if (!is_array($result) || !array_key_exists('ok', $result)) {
    error_log('Verified export failed: ' . $stderr);
    export_response(500, ['ok' => false, 'message' => 'Exporter failed. See PHP log.']);
}
export_response($exitCode === 0 && $result['ok'] ? 200 : 500, $result);
