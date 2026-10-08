<?php
require __DIR__.'/../scripts/overview_boot_history.php';
$path=tempnam(sys_get_temp_dir(),'boot-history-');
try {
  $rows=[];
  for ($i=0;$i<7;$i++) $rows[]=['time'=>'2026-10-08T10:00:0'.$i.'+03:00','rtc'=>$i===0 ? true : ($i===1 ? false : null)];
  file_put_contents($path,json_encode($rows));
  ob_start();render_overview_boot_history($path);$html=ob_get_clean();
  if (substr_count($html,'08.10.2026')!==3 || strpos($html,'10:00:03')!==false) throw new RuntimeException('Three-row limit');
  foreach (['Present','Absent','Unknown','10:00:00'] as $text) if (strpos($html,$text)===false) throw new RuntimeException('Missing '.$text);
  file_put_contents($path,'invalid');ob_start();render_overview_boot_history($path);$html=ob_get_clean();
  if (strpos($html,'No recorded boots')===false) throw new RuntimeException('Invalid JSON');
  file_put_contents($path,json_encode([['time'=>'<script>alert(1)</script>','rtc'=>true]]));
  ob_start();render_overview_boot_history($path);$html=ob_get_clean();
  if (strpos($html,'<script>')!==false) throw new RuntimeException('Unsafe date');
} finally { unlink($path); }
echo "PASS: three rows, date/time, RTC states, invalid/unsafe input\n";
