<?php
function get_overview_new_species($db, $today = null) {
  $today = $today ?? date('Y-m-d');
  // Today and the preceding 30 calendar days form an inclusive 31-day window.
  $window_start = (new DateTimeImmutable($today))->modify('-30 days')->format('Y-m-d');
  $indexed = (bool)$db->querySingle("SELECT 1 FROM sqlite_master WHERE type='index' AND name='detections_Sci_Name_Date_Time'");
  if ($indexed) {
    $query = $db->prepare("WITH species_names AS (
      SELECT DISTINCT Sci_Name FROM detections
    ), species AS MATERIALIZED (
      SELECT Sci_Name, (
        SELECT d.Date || ' ' || d.Time FROM detections d
        WHERE d.Sci_Name=species_names.Sci_Name AND d.Date <= :today
          AND d.Time IS NOT NULL
        ORDER BY d.Date, d.Time LIMIT 1
      ) AS first_seen
      FROM species_names
    ), top_species AS MATERIALIZED (
      SELECT Sci_Name, first_seen, (
        SELECT d.Date || ' ' || d.Time FROM detections d
        WHERE d.Sci_Name=species.Sci_Name AND d.Date <= :today
          AND d.Time IS NOT NULL
        ORDER BY d.Date DESC, d.Time DESC LIMIT 1
      ) AS last_seen
      FROM species WHERE first_seen IS NOT NULL
      ORDER BY first_seen DESC, Sci_Name ASC LIMIT 10
    ) SELECT species.*, latest.Com_Name, latest.Confidence, latest.File_Name
      FROM top_species species JOIN detections latest ON latest.rowid = (
        SELECT d.rowid FROM detections d
        WHERE d.Sci_Name = species.Sci_Name AND d.Date = substr(species.last_seen, 1, 10)
          AND d.Time = substr(species.last_seen, 12)
        ORDER BY d.Confidence DESC, d.File_Name ASC, d.rowid ASC LIMIT 1
      ) ORDER BY species.first_seen DESC, species.Sci_Name ASC");
  } else {
    $query = $db->prepare("WITH species AS (
      SELECT Sci_Name,
             MIN(Date || ' ' || Time) AS first_seen,
             MAX(Date || ' ' || Time) AS last_seen
      FROM detections WHERE Date <= :today GROUP BY Sci_Name
    ), top_species AS MATERIALIZED (
      SELECT * FROM species WHERE last_seen IS NOT NULL
      ORDER BY first_seen DESC, Sci_Name ASC LIMIT 10
    ) SELECT species.*, latest.Com_Name, latest.Confidence, latest.File_Name
      FROM top_species species JOIN detections latest ON latest.rowid = (
        SELECT d.rowid FROM detections d
        WHERE d.Sci_Name = species.Sci_Name AND d.Date = substr(species.last_seen, 1, 10)
          AND d.Time = substr(species.last_seen, 12)
        ORDER BY d.Confidence DESC, d.File_Name ASC, d.rowid ASC LIMIT 1
      ) ORDER BY species.first_seen DESC, species.Sci_Name ASC LIMIT 10");
  }
  if (!$query) throw new RuntimeException('Cannot prepare new species list');
  $query->bindValue(':today', $today, SQLITE3_TEXT);
  $result = $query->execute();
  if (!$result) throw new RuntimeException('Cannot read new species list');
  $lists = ['all' => [], 'month' => []];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $lists['all'][] = $row;
    if (substr($row['first_seen'], 0, 10) >= $window_start) $lists['month'][] = $row;
  }
  $result->finalize();
  $query->close();
  return $lists;
}

function render_overview_new_species($lists) {
  $escape = static function($value) { return htmlspecialchars($value, ENT_QUOTES, 'UTF-8'); };
  ?>
  <section id="overview-new-species" class="new-species-panel">
    <table aria-label="Latest 10 newly discovered species and last encounter dates">
      <thead><tr><th scope="col">New species · All time</th><th scope="col" title="First detected in the last 31 days, including today">New species · Last month</th></tr></thead>
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
