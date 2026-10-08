<?php
function render_overview_boot_history($path = '/var/lib/birdnet-boot-history/recent.json') {
  $rows = is_readable($path) ? json_decode(file_get_contents($path), true) : [];
  if (!is_array($rows)) $rows = [];
  ?>
  <section id="boot-history" class="boot-history-panel" aria-labelledby="boot-history-title">
    <h3 id="boot-history-title">Recent boots</h3>
    <table><thead><tr><th scope="col">Date</th><th scope="col">Time</th><th scope="col">RTC</th></tr></thead><tbody>
    <?php $shown = 0;
    foreach ($rows as $row) {
      if (!is_array($row) || empty($row['time']) || !is_string($row['time'])) continue;
      try { $time = new DateTimeImmutable($row['time']); } catch (Exception $e) { continue; }
      if (++$shown > 3) break;
      $rtc = $row['rtc'] ?? null;
      $label = $rtc === true ? 'Present' : ($rtc === false ? 'Absent' : 'Unknown');
      $state = $rtc === true ? 'present' : ($rtc === false ? 'absent' : 'unknown'); ?>
      <tr><td><?php echo $time->format('d.m.Y'); ?></td><td><?php echo $time->format('H:i:s'); ?></td><td><span class="rtc-badge rtc-<?php echo $state; ?>"><?php echo $label; ?></span></td></tr>
    <?php } ?>
    <?php if (!$shown) { ?><tr><td colspan="3" class="boot-history-empty">No recorded boots</td></tr><?php } ?>
    </tbody></table>
  </section>
  <?php
}
