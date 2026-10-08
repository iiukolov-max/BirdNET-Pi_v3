<?php
require __DIR__.'/../scripts/service_policy.php';
function verify($condition, $message) { if (!$condition) throw new RuntimeException($message); }
ob_start(); birdnet_service_settings(['SERVICE_ALLOW_TERMINAL'=>'0']); $html=ob_get_clean();
verify(substr_count($html, 'type="checkbox"')===6, 'Six optional service permissions');
verify(!str_contains($html, 'name="service_allow_recording"'), 'Recording cannot be restricted');
verify(!str_contains($html, 'name="service_allow_analysis"'), 'Analysis cannot be restricted');
verify(!preg_match('/id="service_allow_terminal"[^>]*checked/', $html), 'Unchecked permission persists');
verify(birdnet_service_allowed('birdnet_recording.service', ['SERVICE_ALLOW_RECORDING'=>'0']), 'Core recording always permitted');
verify(!birdnet_service_allowed('web_terminal.service', ['SERVICE_ALLOW_TERMINAL'=>'0']), 'Terminal is denied');
verify(!birdnet_service_allowed('chart_viewer.service', ['OPERATION_MODE'=>'archive']), 'Economy adds restrictions');
echo "Service permissions PHP tests passed\n";
