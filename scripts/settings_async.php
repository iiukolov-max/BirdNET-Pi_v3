<?php
require_once __DIR__.'/service_policy.php';
function settings_assert_revision() {
  if (isset($_POST['config_revision']) && !hash_equals(hash_file('sha256','/etc/birdnet/birdnet.conf'),(string)$_POST['config_revision'])) {
    http_response_code(409);die('Settings changed since this form was opened. Reload the page.');
  }
}
function enqueue_settings($contents) {
  $source=file_get_contents('/etc/birdnet/birdnet.conf');
  $revision=hash('sha256',$source);
  if (isset($_POST['config_revision']) && !hash_equals($revision,(string)$_POST['config_revision'])) {
    throw new RuntimeException('Settings changed since this form was opened. Reload the page.',409);
  }
  $before=birdnet_config_parse($source);
  $after=birdnet_config_parse($contents);
  foreach (birdnet_service_catalog() as $row) {
    $key='SERVICE_ALLOW_'.$row['key'];
    $before[$key]=(string)($before[$key] ?? $row['default']);
    $after[$key]=(string)($after[$key] ?? $row['default']);
  }
  ksort($before);ksort($after);
  if ($before===$after) return array('status'=>'done','changed_keys'=>array(),'revision'=>$revision);
  $command='sudo -n /usr/bin/python3 '.escapeshellarg(get_home().'/BirdNET-Pi/scripts/settings_jobs.py').' enqueue '.escapeshellarg($revision);
  $process=proc_open($command,array(0=>array('pipe','r'),1=>array('pipe','w'),2=>array('pipe','w')),$pipes);
  if (!is_resource($process)) throw new RuntimeException('Cannot queue settings');
  fwrite($pipes[0],$contents);fclose($pipes[0]);
  $output=stream_get_contents($pipes[1]);$error=stream_get_contents($pipes[2]);fclose($pipes[1]);fclose($pipes[2]);
  if (proc_close($process)!==0) throw new RuntimeException($error);
  return json_decode($output,true,512,JSON_THROW_ON_ERROR);
}
function settings_response($job) {
  if (isset($_POST['async'])) {header('Content-Type: application/json; charset=utf-8');echo json_encode($job);exit;}
  if (($job['status'] ?? '')==='done') {echo '<p role="status">Settings saved.</p>';return;}
  echo '<p role="status" id="settings-result" data-job="'.htmlspecialchars($job['job'],ENT_QUOTES).'">Settings are being applied in the background.</p>';
}
