<?php
function get_overview_new_species($db, $today = null) {
  $today = $today ?? date('Y-m-d');
  $month = (new DateTimeImmutable($today))->format('Y-m-01');
  $lists = [];
  foreach (['all' => '', 'month' => 'WHERE species.first_seen >= :month'] as $key => $filter) {
    $query = $db->prepare("WITH species AS (
      SELECT Sci_Name,
             MIN(Date || ' ' || Time) AS first_seen,
             MAX(Date || ' ' || Time) AS last_seen
      FROM detections WHERE Date <= :today GROUP BY Sci_Name
    ) SELECT species.*, latest.Com_Name, latest.Confidence, latest.File_Name
      FROM species JOIN detections latest ON latest.rowid = (
        SELECT d.rowid FROM detections d
        WHERE d.Sci_Name = species.Sci_Name AND d.Date || ' ' || d.Time = species.last_seen
        ORDER BY d.Confidence DESC, d.File_Name ASC LIMIT 1
      ) $filter ORDER BY species.first_seen DESC, species.Sci_Name ASC LIMIT 10");
    if (!$query) throw new RuntimeException('Cannot prepare new species list');
    $query->bindValue(':today', $today, SQLITE3_TEXT);
    if ($key === 'month') $query->bindValue(':month', $month, SQLITE3_TEXT);
    $result = $query->execute();
    if (!$result) throw new RuntimeException('Cannot read new species list');
    $lists[$key] = [];
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) $lists[$key][] = $row;
    $result->finalize();$query->close();
  }
  return $lists;
}

function render_overview_new_species($lists) {
  $escape = static function($value) { return htmlspecialchars($value, ENT_QUOTES, 'UTF-8'); };
  ?>
  <section id="overview-new-species" class="new-species-panel">
    <table aria-label="Latest 10 newly discovered species and last encounter dates">
      <thead><tr><th scope="col">New species · All time</th><th scope="col">New species · This month</th></tr></thead>
      <tbody>
      <?php for ($i=0,$count=max(1,count($lists['all']),count($lists['month']));$i<$count;$i++) { ?>
        <tr><?php foreach (['all','month'] as $key) { ?><td>
          <?php if (isset($lists[$key][$i])) { $row=$lists[$key][$i]; ?>
            <div class="new-species-heading">
              <a class="new-species-name" target="_top" href="index.php?<?php echo $escape(http_build_query(['filename'=>$row['File_Name']])); ?>"><?php echo $escape($row['Com_Name'] ?: $row['Sci_Name']); ?></a>
              <?php $confidence = is_numeric($row['Confidence']) ? round((float)$row['Confidence'] * 100) . '%' : '—'; ?>
              <span class="new-species-confidence" title="Confidence" aria-label="Confidence: <?php echo $confidence; ?>"><?php echo $confidence; ?></span>
            </div>
            <span class="new-species-date">Last seen: <time datetime="<?php echo $escape(substr($row['last_seen'],0,10)); ?>"><?php echo (new DateTimeImmutable($row['last_seen']))->format('d.m.Y'); ?></time></span>
          <?php } elseif ($i===0) { ?><span class="new-species-empty">No new species</span><?php } ?>
        </td><?php } ?></tr>
      <?php } ?>
      </tbody>
    </table>
  </section>
  <?php
}
