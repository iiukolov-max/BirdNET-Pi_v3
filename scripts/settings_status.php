<?php
require_once __DIR__.'/common.php';
ensure_authenticated();
session_write_close();
header('Content-Type: application/json; charset=utf-8');header('Cache-Control: no-store');
$job=$_GET['job'] ?? '';
if (!preg_match('/^[a-f0-9]{32}$/',$job)) {http_response_code(400);echo json_encode(array('error'=>'Invalid job'));exit;}
$command='sudo -n /usr/bin/python3 '.escapeshellarg(get_home().'/BirdNET-Pi/scripts/settings_jobs.py').' status '.escapeshellarg($job);
exec($command.' 2>/dev/null',$output,$code);
if ($code) {http_response_code(404);echo json_encode(array('error'=>'Job not found'));exit;}
echo implode("\n",$output);
