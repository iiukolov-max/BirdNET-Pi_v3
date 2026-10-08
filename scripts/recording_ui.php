<?php
function recording_strings($language) {
  static $catalog=null;
  if ($catalog===null) $catalog=json_decode(file_get_contents(__DIR__.'/recording_ui_i18n.json'),true);
  return array_merge($catalog['en'],$catalog[$language] ?? array());
}
function recording_text($text) {return htmlspecialchars($text,ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');}
