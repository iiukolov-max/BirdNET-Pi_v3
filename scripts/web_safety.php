<?php
/* Shared boundary checks for web requests; preserve Unicode as data. */
function birdnet_config_value($value): string {
  $value = (string)$value;
  if (preg_match('/[\x00-\x1f\x7f]/', $value)) throw new InvalidArgumentException('Control characters are not allowed in settings');
  if ($value !== '' && !in_array(strtolower($value),['true','false','on','off','yes','no','none','null'],true) && preg_match('~^[a-zA-Z0-9_./:@%+,=\-]+$~D', $value)) return $value;
  return '"' . strtr($value, ['\\'=>'\\\\', '"'=>'\\"', '$'=>'\\$', '`'=>'\\`']) . '"';
}
function birdnet_config_parse(string $source): array {
  $result = [];
  foreach (preg_split('/\r?\n/', $source) as $line) {
    if (!preg_match('/^([A-Za-z_][A-Za-z_0-9]*)=(.*)$/', $line, $match)) continue;
    $value = trim($match[2]);
    if (strlen($value)>=2 && $value[0]==='"' && substr($value,-1)==='"') $value = strtr(substr($value,1,-1), ['\\\\'=>'\\', '\\"'=>'"', '\\$'=>'$', '\\`'=>'`']);
    elseif (in_array(strtolower($value),['true','on','yes'],true)) $value='1';
    elseif (in_array(strtolower($value),['false','off','no','none','null'],true)) $value='';
    $result[$match[1]] = $value;
  }
  return $result;
}
function birdnet_config_update(string $source, array $values): string {
  foreach ($values as $key=>$value) {
    if (!preg_match('/^[A-Za-z_][A-Za-z_0-9]*$/D', $key)) throw new InvalidArgumentException('Invalid setting key');
    $line = $key.'='.birdnet_config_value($value);$pattern='/^'.preg_quote($key,'/').'=.*$/m';
    if (preg_match($pattern,$source)) $source=preg_replace_callback($pattern,fn()=> $line,$source);
    else $source=rtrim($source)."\n".$line."\n";
  }
  return $source;
}
function birdnet_number($value, float $min, float $max): string {
  if (!is_scalar($value) || !is_numeric($value) || !is_finite((float)$value) || (float)$value<$min || (float)$value>$max) throw new InvalidArgumentException('Setting outside allowed range');
  return (string)$value;
}
function birdnet_path_inside(string $base, string $path): string {
  $base=realpath($base);$real=realpath($path);
  if ($base===false || $real===false || !str_starts_with($real,$base.DIRECTORY_SEPARATOR)) throw new InvalidArgumentException('Invalid recording path');
  return $real;
}
function birdnet_relative_recording(string $name): string {
  if ($name==='' || str_contains($name,"\0") || str_contains($name,'\\') || $name[0]==='/' || in_array('..',explode('/',$name),true)) throw new InvalidArgumentException('Invalid recording path');
  return $name;
}
function birdnet_command(array $args): string {return implode(' ',array_map('escapeshellarg',$args));}
