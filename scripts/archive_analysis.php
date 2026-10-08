<?php
require_once __DIR__.'/common.php';
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
$config=get_config();
require_once __DIR__.'/recording_ui.php';
$labels=recording_strings($config['DATABASE_LANG'] ?? 'en');
if (($config['OPERATION_MODE'] ?? 'normal') !== 'archive') {
  http_response_code(409); echo json_encode(array('error'=>$labels['normal'])); exit;
}
if ($_SERVER['REQUEST_METHOD']==='POST') {
  ensure_authenticated();
  if (session_status() !== PHP_SESSION_ACTIVE) session_start();
  if (!isset($_POST['token'],$_SESSION['archive_token']) || !hash_equals($_SESSION['archive_token'],$_POST['token'])) {
    http_response_code(403);echo json_encode(array('error'=>$labels['error']));exit;
  }
  session_write_close();
  exec('sudo /usr/bin/python3 '.escapeshellarg(get_home().'/BirdNET-Pi/scripts/archive_analysis_control.py').' start 2>&1',$output,$code);
  if ($code!==0) {http_response_code(500);echo json_encode(array('error'=>implode("\n",$output)));exit;}
} elseif ($_SERVER['REQUEST_METHOD']!=='GET') {http_response_code(405);exit;}
$command='sudo -u '.escapeshellarg(get_user()).' /usr/bin/python3 '.escapeshellarg(get_home().'/BirdNET-Pi/scripts/archive_analysis.py').' status';
exec($command.' 2>/dev/null',$outputStatus,$code);
if ($code!==0) {http_response_code(500);echo json_encode(array('error'=>$labels['error']));exit;}
echo implode("\n",$outputStatus);
