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
