<?php
function birdnet_service_catalog() {
    return json_decode(file_get_contents(__DIR__.'/service_policy.json'), true, 512, JSON_THROW_ON_ERROR);
}
function birdnet_service_allowed($unit, $config) {
    foreach (birdnet_service_catalog() as $row) {
        if (in_array($unit, $row['units'], true)) {
            return (!empty($row['fixed']) || (string)($config['SERVICE_ALLOW_'.$row['key']] ?? $row['default']) === '1')
                && in_array($config['OPERATION_MODE'] ?? 'normal', $row['modes'], true);
        }
    }
    return true;
}
function birdnet_service_settings($config) {
    echo '<fieldset id="service-permissions"><legend>Service launch permissions</legend>';
    echo '<input type="hidden" name="service_permissions_present" value="1">';
    echo '<p>Unchecked services stay off after mode changes and reboot. Economy temporarily enables Charts after completed manual analysis, then restores its previous setting. The selected mode also limits which services can run.</p>';
    echo '<table style="width:100%;border-collapse:collapse;text-align:left"><thead><tr><th scope="col">Service</th><th scope="col">Allow</th></tr></thead><tbody>';
    foreach (birdnet_service_catalog() as $row) {
        if (!empty($row['fixed'])) continue;
        $id = 'service_allow_'.strtolower($row['key']);
        $checked = (string)($config['SERVICE_ALLOW_'.$row['key']] ?? $row['default']) === '1';
        echo '<tr style="border-top:1px solid #8886"><td style="padding:8px 4px"><label for="'.$id.'">'.htmlspecialchars($row['label']).'</label></td><td style="padding:8px 4px"><input type="checkbox" id="'.$id.'" name="'.$id.'" value="1"'.($checked ? ' checked' : '').'></td></tr>';
    }
    echo '</tbody></table><p>Recording and BirdNET analysis follow the selected mode and cannot be disabled here.</p></fieldset>';
}
function birdnet_service_start_attributes($unit) {
    if (!birdnet_service_allowed($unit, get_config())) {
        echo ' disabled title="Blocked by Settings / operation mode"';
    }
}
