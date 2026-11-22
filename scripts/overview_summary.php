<?php
/* Recording dates, inclusive calendar-day windows in the device's local timezone. */
function get_overview_summary($db, $today = null) {
  $today = $today ?? date('Y-m-d');
  $end = new DateTimeImmutable($today);
  $week = $end->modify('-6 days')->format('Y-m-d');
  $month = $end->modify('-29 days')->format('Y-m-d');
  $has_reviews = (bool)$db->querySingle("SELECT 1 FROM sqlite_master WHERE type='table' AND name='detection_reviews'");
  $verified = $has_reviews ? "EXISTS (SELECT 1 FROM detection_reviews r WHERE r.review_status='correct'
    AND r.file_path=d.Date || '/' || replace(replace(d.Com_Name, ' ', '_'), '''', '') || '/' || d.File_Name)" : '0';
  $statement = $db->prepare("SELECT
    COUNT(CASE WHEN d.Date >= :week THEN 1 END) AS detections_week,
    COUNT(*) AS detections_month,
    COUNT(DISTINCT CASE WHEN d.Date >= :week THEN d.Sci_Name END) AS species_week,
    COUNT(DISTINCT d.Sci_Name) AS species_month,
    COUNT(DISTINCT CASE WHEN d.Date >= :week AND $verified THEN d.Sci_Name END) AS verified_week,
    COUNT(DISTINCT CASE WHEN $verified THEN d.Sci_Name END) AS verified_month
    FROM detections d WHERE d.Date >= :month AND d.Date <= :today");
  if (!$statement) throw new RuntimeException('Cannot prepare overview statistics');
  $statement->bindValue(':week', $week, SQLITE3_TEXT);
  $statement->bindValue(':month', $month, SQLITE3_TEXT);
  $statement->bindValue(':today', $today, SQLITE3_TEXT);
  $result = $statement->execute();
  if (!$result) throw new RuntimeException('Cannot read overview statistics');
  $counts = array_map('intval', $result->fetchArray(SQLITE3_ASSOC));
  $result->finalize();
  $statement->close();
  return $counts;
}

function render_overview_summary($counts) {
  ?>
  <section class="summary-card" aria-labelledby="summary-detections-title">
    <h3 id="summary-detections-title">Detections</h3>
    <table aria-label="Detections over the last 7 and 30 days">
      <thead><tr><th scope="col">Period</th><th scope="col">7 days</th><th scope="col">30 days</th></tr></thead>
      <tbody><tr><th scope="row">Total</th><td><?php echo number_format($counts['detections_week']); ?></td><td><?php echo number_format($counts['detections_month']); ?></td></tr></tbody>
    </table>
  </section>
  <section class="summary-card" aria-labelledby="summary-species-title">
    <h3 id="summary-species-title">Species</h3>
    <table aria-label="Unique species over the last 7 and 30 days">
      <thead><tr><th scope="col">Period</th><th scope="col">7 days</th><th scope="col">30 days</th></tr></thead>
      <tbody><tr><th scope="row">Detected</th><td><?php echo number_format($counts['species_week']); ?></td><td><?php echo number_format($counts['species_month']); ?></td></tr>
      <tr class="summary-verified"><th scope="row">Verified</th><td><?php echo number_format($counts['verified_week']); ?></td><td><?php echo number_format($counts['verified_month']); ?></td></tr></tbody>
    </table>
  </section>
  <?php
}

/* Recording dates, using the same calendar-day windows as the other cards. */
function get_overview_audio_counts($db, $extracted, $today = null) {
  $today = $today ?? date('Y-m-d');
  $end = new DateTimeImmutable($today);
  $week = $end->modify('-6 days')->format('Y-m-d');
  $month = $end->modify('-29 days')->format('Y-m-d');
  $counts = ['processed_week'=>0, 'processed_month'=>0, 'saved_week'=>0, 'saved_month'=>0];
  $date = "substr(name, instr(name, '-birdnet-') - 10, 10)";
  foreach (['normal_processed', 'archive_processed'] as $table) {
    if (!$db->querySingle("SELECT 1 FROM sqlite_master WHERE type='table' AND name='$table'")) continue;
    $query = $db->prepare("SELECT COUNT(*) AS total, COUNT(CASE WHEN $date >= :week THEN 1 END) AS week
      FROM $table WHERE instr(name, '-birdnet-') >= 11 AND $date BETWEEN :month AND :today");
    $query->bindValue(':week', $week, SQLITE3_TEXT);
    $query->bindValue(':month', $month, SQLITE3_TEXT);
    $query->bindValue(':today', $today, SQLITE3_TEXT);
    $rows = $query->execute();
    $totals = $rows->fetchArray(SQLITE3_ASSOC);
    $counts['processed_month'] += $totals['total'];
    $counts['processed_week'] += $totals['week'];
    $rows->finalize();
    $query->close();
  }

  $query = $db->prepare("SELECT DISTINCT Date, Com_Name, File_Name FROM detections
    WHERE Date BETWEEN :month AND :today AND File_Name LIKE '%.flac'");
  $query->bindValue(':month', $month, SQLITE3_TEXT);
  $query->bindValue(':today', $today, SQLITE3_TEXT);
  $rows = $query->execute();
  $seen = [];
  $directory = rtrim($extracted, '/').'/By_Date/';
  while ($row = $rows->fetchArray(SQLITE3_ASSOC)) {
    $species = str_replace(["'", ' '], ['', '_'], $row['Com_Name']);
    $file = $row['File_Name'];
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/D', $row['Date']) || $species === '..' ||
        basename($species) !== $species || basename($file) !== $file) continue;
    $path = $directory.$row['Date'].'/'.$species.'/'.$file;
    if (isset($seen[$path]) || !is_file($path) || !filesize($path)) continue;
    $seen[$path] = true;
    ++$counts['saved_month'];
    if ($row['Date'] >= $week) ++$counts['saved_week'];
  }
  $rows->finalize();
  $query->close();
  return $counts;
}

function render_overview_audio_counts($counts) {
  ?>
  <section class="summary-card" aria-labelledby="summary-audio-title">
    <h3 id="summary-audio-title">Аудиофайлы</h3>
    <table aria-label="Аудиофайлы за 7 и 30 дней">
      <thead><tr><th scope="col">Период</th><th scope="col">7 дней</th><th scope="col">30 дней</th></tr></thead>
      <tbody>
        <tr><th scope="row">Проанализировано</th><td><?= number_format($counts['processed_week'], 0, '', ' ') ?></td><td><?= number_format($counts['processed_month'], 0, '', ' ') ?></td></tr>
        <tr><th scope="row">Сохранено файлов</th><td><?= number_format($counts['saved_week'], 0, '', ' ') ?></td><td><?= number_format($counts['saved_month'], 0, '', ' ') ?></td></tr>
        <tr><th scope="row">Осталось проанализировать</th><td data-pending-audio="pending_week">—</td><td data-pending-audio="pending_month">—</td></tr>
      </tbody>
    </table>
  </section>
  <?php
}
