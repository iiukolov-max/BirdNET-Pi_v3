<?php
function overview_chart_file($directory, $today = null) {
  $today = $today ?? date('Y-m-d');
  $files = glob(rtrim($directory, '/').'/Combo-????-??-??.png') ?: [];
  rsort($files, SORT_STRING);
  foreach ($files as $file) {
    $name = basename($file);
    if (preg_match('/^Combo-(\d{4}-\d{2}-\d{2})\.png$/D', $name, $match) && $match[1] <= $today && is_file($file)) return $name;
  }
  return '';
}
