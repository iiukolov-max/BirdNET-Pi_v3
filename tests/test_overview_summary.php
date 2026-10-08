<?php
require __DIR__.'/../scripts/overview_summary.php';
$db = new SQLite3(':memory:');
$db->exec('CREATE TABLE detections (Date TEXT, Sci_Name TEXT, Com_Name TEXT, File_Name TEXT)');
$db->exec('CREATE TABLE detection_reviews (file_path TEXT PRIMARY KEY, review_status TEXT, reviewed_at TEXT)');
function add_detection($db, $date, $species, $file, $review = null) {
  $q=$db->prepare('INSERT INTO detections VALUES (?,?,?,?)');
  foreach ([$date,$species,"Test Bird's",$file] as $i=>$v) $q->bindValue($i+1,$v,SQLITE3_TEXT);
  $q->execute();
  if ($review) {
    $q=$db->prepare('INSERT INTO detection_reviews VALUES (?,?,?)');
    foreach ([$date.'/Test_Birds/'.$file,$review,'2026-10-08'] as $i=>$v) $q->bindValue($i+1,$v,SQLITE3_TEXT);
    $q->execute();
  }
}
add_detection($db,'2026-10-08','Parus major','1','correct');
add_detection($db,'2026-10-08','Parus major','2','correct');
add_detection($db,'2026-10-02','Cyanistes caeruleus','3','false_positive'); // inclusive 7-day boundary
add_detection($db,'2026-10-01','Turdus merula','4','correct');
add_detection($db,'2026-09-09','Pica pica','5','correct'); // inclusive 30-day boundary
add_detection($db,'2026-09-08','Corvus corax','6','correct');
add_detection($db,'2026-10-09','Sturnus vulgaris','7','correct'); // future excluded
add_detection($db,'2026-10-08','Vulpes vulpes','fox','correct');
$actual=get_overview_summary($db,'2026-10-08');
$expected=['detections_week'=>4,'detections_month'=>6,'species_week'=>3,'species_month'=>5,'verified_week'=>2,'verified_month'=>4];
if ($actual!==$expected) throw new RuntimeException(json_encode($actual));
ob_start();render_overview_summary($actual);$html=ob_get_clean();
if (strpos($html,'Species')===false || strpos($html,'Verified')===false) throw new RuntimeException('Missing rendered sections');
$db->exec('DROP TABLE detection_reviews');
$counts=get_overview_summary($db,'2026-10-08');
if ($counts['verified_week']!==0 || $counts['verified_month']!==0) throw new RuntimeException('Legacy database failed');
$db->exec('DELETE FROM detections');
if (array_sum(get_overview_summary($db,'2026-10-08'))!==0) throw new RuntimeException('Empty database failed');
// Both windows must cross a year boundary correctly.
add_detection($db,'2025-12-28','Parus major','year');
$counts=get_overview_summary($db,'2026-01-03');
if ($counts['detections_week']!==1) throw new RuntimeException('Year boundary failed');
echo "PASS: date boundaries, future dates, unique species, duplicate confirmations, false positives, review path escaping, legacy/empty DB, year boundary, all animal species included\n";
