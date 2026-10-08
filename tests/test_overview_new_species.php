<?php
require __DIR__.'/../scripts/overview_new_species.php';
$db=new SQLite3(':memory:');
$db->exec('CREATE TABLE detections (Date TEXT, Time TEXT, Sci_Name TEXT, Com_Name TEXT, Confidence REAL DEFAULT 0.8, File_Name TEXT DEFAULT "fixture.wav")');
function add_species_row($db,$date,$time,$sci,$common) {
  $q=$db->prepare('INSERT INTO detections (Date,Time,Sci_Name,Com_Name) VALUES (?,?,?,?)');
  foreach ([$date,$time,$sci,$common] as $i=>$v) $q->bindValue($i+1,$v,SQLITE3_TEXT);
  $q->execute();
}
add_species_row($db,'2026-09-30','12:00:00','old','Old species');
add_species_row($db,'2026-10-08','12:00:00','old','Old species');
add_species_row($db,'2026-10-01','00:00:00','boundary','Boundary species');
add_species_row($db,'2026-10-07','10:00:00','new','New species');
add_species_row($db,'2026-10-08','09:00:00','new','New species');
add_species_row($db,'2026-10-09','10:00:00','future','Future species');
$db->exec("UPDATE detections SET Confidence=0.63,File_Name='latest.flac' WHERE Sci_Name='new' AND Date='2026-10-08'");
$lists=get_overview_new_species($db,'2026-10-08');
if (array_column($lists['all'],'Sci_Name')!==['new','boundary','old']) throw new RuntimeException('First encounter sorting');
if (array_column($lists['month'],'Sci_Name')!==['new','boundary']) throw new RuntimeException('Month must exclude known species');
if ($lists['all'][0]['last_seen']!=='2026-10-08 09:00:00') throw new RuntimeException('Last encounter');
if ($lists['all'][0]['Confidence']!==0.63 || $lists['all'][0]['File_Name']!=='latest.flac') throw new RuntimeException('Confidence/file must match latest encounter');
ob_start();render_overview_new_species($lists);$html=ob_get_clean();
if (strpos($html,'Confidence: 63%')===false || strpos($html,'index.php?filename=latest.flac')===false) throw new RuntimeException('Confidence or recording link');
add_species_row($db,'2026-10-08','11:00:00','unsafe','<script>alert(1)</script>');
ob_start();render_overview_new_species(get_overview_new_species($db,'2026-10-08'));$html=ob_get_clean();
if (strpos($html,'<script>')!==false || strpos($html,'08.10.2026')===false) throw new RuntimeException('Escaping/date rendering');
for ($i=0;$i<20;$i++) add_species_row($db,'2026-10-08',sprintf('13:00:%02d',$i),'extra'.$i,'Extra '.$i);
$lists=get_overview_new_species($db,'2026-10-08');
if (count($lists['all'])!==10 || count($lists['month'])!==10 || $lists['all'][0]['Sci_Name']!=='extra19') throw new RuntimeException('Limit or time sorting');
$db->exec('DELETE FROM detections');
ob_start();render_overview_new_species(get_overview_new_species($db,'2026-01-01'));$html=ob_get_clean();
if (substr_count($html,'No new species')!==2) throw new RuntimeException('Empty state');
echo "PASS: first encounter order, month boundary, previously known species, last encounter, future exclusion, 10 limit, escaped names, empty lists\n";
