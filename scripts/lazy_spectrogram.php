<?php
require_once __DIR__ . '/common.php';
$config = get_config();
$user = get_user();
session_write_close();
function image_error($status) {
    http_response_code($status);
    header('Cache-Control: no-store');
    if ($status === 503) header('Retry-After: 2');
    exit;
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') image_error(405);
$relative = $_GET['audio'] ?? '';
if (!is_string($relative) || !preg_match('~^/?By_Date/\d{4}-\d{2}-\d{2}/[^/\x00-\x1f]+/[^/\x00-\x1f]+\.(flac|wav|mp3|ogg|opus)$~i', $relative)) image_error(400);
foreach (explode('/', ltrim($relative, '/')) as $part) {
    if ($part === '..' || $part === '.') image_error(400);
}
$root = realpath($config['EXTRACTED'] . '/By_Date');
$audio = realpath($config['EXTRACTED'] . '/' . ltrim($relative, '/'));
if ($root === false || $audio === false || !str_starts_with($audio, $root . '/') || !is_file($audio)) image_error(404);
$png = $audio . '.png';
if (is_link($png)) image_error(400);
if (!is_file($png) || filesize($png) === 0) {
    if (!is_file('/etc/birdnet/lazy-spectrograms.enabled')) image_error(404);
    // Argument arrays avoid shell interpolation; rendering runs without root.
    $command = ['sudo', '-n', '-u', $user, '/home/' . $user . '/BirdNET-Pi/birdnet/bin/python3',
                '/home/' . $user . '/BirdNET-Pi/scripts/lazy_spectrogram.py', $relative];
    $process = proc_open($command, [0 => ['pipe','r'], 1 => ['pipe','w'], 2 => ['pipe','w']], $pipes);
    if (!is_resource($process)) image_error(503);
    fclose($pipes[0]);
    stream_get_contents($pipes[1]);
    $error = stream_get_contents($pipes[2]);
    fclose($pipes[1]); fclose($pipes[2]);
    if (proc_close($process) !== 0) {
        error_log('On-demand spectrogram rendering failed');
        image_error(503);
    }
    clearstatcache(true, $png);
    if (!is_file($png) || filesize($png) === 0 || is_link($png)) image_error(503);
}
header('Content-Type: image/png');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: private, max-age=3600');
header('Content-Length: ' . filesize($png));
readfile($png);
