<?php
function enqueue_settings($contents) {
  $command='sudo -n /usr/bin/python3 '.escapeshellarg(get_home().'/BirdNET-Pi/scripts/settings_jobs.py').' enqueue';
  $process=proc_open($command,array(0=>array('pipe','r'),1=>array('pipe','w'),2=>array('pipe','w')),$pipes);
  if (!is_resource($process)) throw new RuntimeException('Cannot queue settings');
  fwrite($pipes[0],$contents);fclose($pipes[0]);
  $output=stream_get_contents($pipes[1]);$error=stream_get_contents($pipes[2]);fclose($pipes[1]);fclose($pipes[2]);
  if (proc_close($process)!==0) throw new RuntimeException($error);
  return json_decode($output,true,512,JSON_THROW_ON_ERROR);
}
function settings_response($job) {
  if (isset($_POST['async'])) {header('Content-Type: application/json; charset=utf-8');echo json_encode($job);exit;}
  echo '<p role="status" id="settings-result" data-job="'.htmlspecialchars($job['job'],ENT_QUOTES).'">Settings are being applied in the background.</p>';
}
