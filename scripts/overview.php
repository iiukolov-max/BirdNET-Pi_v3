<?php
error_reporting(E_ERROR);
ini_set('display_errors',1);
ini_set('session.gc_maxlifetime', 7200);
session_set_cookie_params(7200);
session_start();
require_once 'scripts/common.php';
$home = get_home();
$config = get_config();

set_timezone();
$myDate = date('Y-m-d');
$chart = "Combo-$myDate.png";

$db = new SQLite3('./scripts/birds.db', SQLITE3_OPEN_READONLY);
$db->busyTimeout(1000);

if(isset($_GET['custom_image'])){
  if(isset($config["CUSTOM_IMAGE"])) {
  ?>
    <br>
    <h3><?php echo $config["CUSTOM_IMAGE_TITLE"]; ?></h3>
    <?php
    $image_data = file_get_contents($config["CUSTOM_IMAGE"]);
    $image_base64 = base64_encode($image_data);
    $img_tag = "<img src='data:image/png;base64," . $image_base64 . "'>";
    echo $img_tag;
  }
  die();
}

if(isset($_GET['blacklistimage'])) {
  ensure_authenticated('You must be authenticated.');
  $imageid = $_GET['blacklistimage'];
  $file_handle = fopen($home."/BirdNET-Pi/scripts/blacklisted_images.txt", 'a+');
  fwrite($file_handle, $imageid . "\n");
  fclose($file_handle);
  unset($_SESSION['images']);
  die("OK");
}

if(isset($_GET['fetch_chart_string']) && $_GET['fetch_chart_string'] == "true") {
  $myDate = date('Y-m-d');
  $chart = "Combo-$myDate.png";
  echo $chart;
  die();
}

if (isset($_GET['ajax_overview'])) {
  require_once __DIR__.'/overview_summary.php';
  require_once __DIR__.'/overview_new_species.php';
  ob_start(); render_overview_summary(get_overview_summary($db)); $summary = ob_get_clean();
  ob_start(); render_overview_new_species(get_overview_new_species($db)); $species = ob_get_clean();
  $latest = $db->query('SELECT Date, Time, Sci_Name, Com_Name, Confidence, File_Name FROM detections ORDER BY Date DESC, Time DESC LIMIT 5');
  $rows = [];
  while ($row = $latest->fetchArray(SQLITE3_ASSOC)) $rows[] = $row;
  header('Content-Type: application/json; charset=utf-8');
  echo json_encode(['summary'=>$summary, 'species'=>$species, 'latest'=>hash('sha256', json_encode($rows))]);
  die();
}

if (get_included_files()[0] === __FILE__) {
  echo '<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Overview</title>
</head>';
}
?>
<div class="overview">
  <dialog style="margin-top: 5px;max-height: 95vh;
  overflow-y: auto;overscroll-behavior:contain" id="attribution-dialog">
    <h1 id="modalHeading"></h1>
    <p id="modalText"></p>
    <button onclick="hideDialog()">Close</button>
    <button style="font-weight:bold;color:blue" onclick="if(confirm('Are you sure you want to blacklist this image?')) { blacklistImage(); }" <?php if($config["IMAGE_PROVIDER"] === 'WIKIPEDIA'){ echo 'hidden';} ?> >Blacklist this image</button>
  </dialog>
  <script src="static/dialog-polyfill.js"></script>
  <script src="static/Chart.bundle.js"></script>
  <script src="static/chartjs-plugin-trendline.min.js"></script>
  <script>
  var last_photo_link;
  var dialog = document.querySelector('dialog');
  dialogPolyfill.registerDialog(dialog);

  function showDialog() {
    document.getElementById('attribution-dialog').showModal();
  }

  function hideDialog() {
    document.getElementById('attribution-dialog').close();
  }

  function blacklistImage() {
    const match = last_photo_link.match(/\d+$/); // match one or more digits
    const result = match ? match[0] : null; // extract the first match or return null if no match is found
    console.log(last_photo_link)
    const xhttp = new XMLHttpRequest();
    xhttp.onload = function() {
      if(this.responseText.length > 0) {
       location.reload();
      }
    }
    xhttp.open("GET", "overview.php?blacklistimage="+result, true);
    xhttp.send();

  }

  function shorten(u) {
    if (u.length < 48) {
      return u;
    }
    uend = u.slice(u.length - 16);
    ustart = u.substr(0, 32);
    var shorter = ustart + '...' + uend;
    return shorter;
  }

  function setModalText(iter, title, text, authorlink, photolink, licenseurl) {
    let text_display = shorten(text);
    let authorlink_display = shorten(authorlink);
    let licenseurl_display = shorten(licenseurl);
    document.getElementById('modalHeading').innerHTML = "Photo: \""+decodeURIComponent(title.replaceAll("+"," "))+"\" Attribution";
    document.getElementById('modalText').innerHTML = "<div><img style='border-radius:5px;max-height: calc(100vh - 15rem);display: block;margin: 0 auto;' src='"+photolink+"'></div><br><div style='white-space:nowrap'>Image link: <a target='_blank' href="+text+">"+text_display+"</a><br>Author link: <a target='_blank' href="+authorlink+">"+authorlink_display+"</a><br>License URL: <a href="+licenseurl+" target='_blank'>"+licenseurl_display+"</a></div>";
    last_photo_link = text;
    showDialog();
  }
  </script>  
<link rel="stylesheet" href="static/overview-layout.css?v=20261008-compact">
<div class="overview-stats">
<div class="right-column">
<div class="overview-row<?php echo (($config['OPERATION_MODE'] ?? 'normal')==='archive') ? ' has-archive' : ''; ?>">
<div class="left-column" aria-label="Detection statistics"></div>
<div class="overview-sidebar">
<?php if (($config['OPERATION_MODE'] ?? 'normal')==='archive') {
  require_once __DIR__.'/recording_ui.php';
  $recording_ui=recording_strings($config['DATABASE_LANG'] ?? 'en');
  if (!isset($_SESSION['archive_token'])) $_SESSION['archive_token']=bin2hex(random_bytes(32));
?>
<link rel="stylesheet" href="static/recording-mode.css">
<aside id="archive-analysis" class="archive-panel" dir="auto" lang="<?php echo recording_text(str_replace('_','-',$config['DATABASE_LANG'] ?? 'en')); ?>" data-token="<?php echo recording_text($_SESSION['archive_token']); ?>" data-language="<?php echo recording_text(str_replace('_','-',$config['DATABASE_LANG'] ?? 'en')); ?>" data-i18n="<?php echo recording_text(json_encode($recording_ui)); ?>">
  <h3><?php echo recording_text($recording_ui['title']); ?></h3>
  <button type="button" disabled><?php echo recording_text($recording_ui['start']); ?></button>
  <div role="status" aria-live="polite"><p data-field="pending"></p><p data-field="progress"></p><p data-field="new_files"></p><p data-field="eta"></p><p data-field="errors"></p></div>
  <progress hidden aria-label="<?php echo recording_text($recording_ui['title']); ?>"></progress>
  <p data-field="free"></p><p data-field="capacity"></p><p data-field="days"></p>
  <small><?php echo recording_text($recording_ui['cleanup_help']); ?></small>
</aside>
<script defer src="static/archive-analysis.js"></script>
<?php } ?>
<?php require_once __DIR__.'/overview_boot_history.php'; render_overview_boot_history(); ?>
</div>

<div class="overview-primary">
<?php
require_once __DIR__.'/overview_new_species.php';
render_overview_new_species(get_overview_new_species($db));
?>
<div class="chart">
<?php
$refresh = $config['RECORDING_LENGTH'];
$dividedrefresh = $refresh/4;
if($dividedrefresh < 1) { 
  $dividedrefresh = 1;
}
$time = time();
if (file_exists('./Charts/'.$chart)) {
  echo "<img id='chart' src=\"Charts/$chart?nocache=$time\">";
} 
?>
</div>

</div>
</div>
<section class="overview-recent">
<br>
<div style="padding-bottom:10px;" id="detections_table"><h3>Loading...</h3></div>
</section>

<div id="customimage"></div>
<br>

</div>
</div>
</div>
<script>
let overviewPending = false;
let latestDetections = null;
let latestMobile = null;
let summaryHtml = null;
let speciesHtml = null;
let overviewTimer = null;
let customImageTimer = null;
const overviewInterval = <?php echo max(5, intval($config['RECORDING_LENGTH'] / 4)); ?> * 1000;
const customImage = <?php echo json_encode(isset($config['CUSTOM_IMAGE']) && strlen($config['CUSTOM_IMAGE']) > 2); ?>;

async function refreshOverview() {
  if (document.hidden || overviewPending) return;
  if ([...document.querySelectorAll('#detections_table audio')].some(audio => !audio.paused && !audio.ended)) return;
  overviewPending = true;
  try {
    const response = await fetch('overview.php?ajax_overview=true');
    if (!response.ok) throw new Error('Overview statistics unavailable');
    const data = await response.json();
    const left = document.querySelector('.left-column');
    if (summaryHtml !== data.summary) {
      left.innerHTML = data.summary;
      summaryHtml = data.summary;
    }
    const species = document.querySelector('#overview-new-species');
    if (speciesHtml !== data.species && !species.contains(document.activeElement)) {
      species.outerHTML = data.species;
      speciesHtml = data.species;
    }
    const mobile = innerWidth <= 500;
    if (latestDetections !== data.latest || latestMobile !== mobile) {
      await loadFiveMostRecentDetections();
      latestDetections = data.latest;
      latestMobile = mobile;
      refreshTopTen();
    }
  } catch (error) {
    console.warn(error.message);
  } finally { overviewPending = false; }
}
async function loadFiveMostRecentDetections() {
  const response = await fetch('todays_detections.php?ajax_detections=true&display_limit=undefined&hard_limit=5' + (innerWidth <= 500 ? '&mobile=true' : ''));
  if (!response.ok) throw new Error('Recent detections unavailable');
  const html = await response.text();
  if (html.includes('Database is busy')) throw new Error('Detection database is busy');
  document.querySelector('#detections_table').innerHTML = html;
  const table = document.querySelector('#detections_table table');
  if (table) {
    const caption = table.createCaption();
    caption.innerHTML = '<h3>5 Most Recent Detections</h3>';
  }

  if (typeof initCustomAudioPlayers === 'function') initCustomAudioPlayers();
}
async function refreshTopTen() {
  const chart = document.getElementById('chart');
  if (!chart) return;
  try {
    const response = await fetch('overview.php?fetch_chart_string=true');
    if (response.ok) chart.src = 'Charts/' + (await response.text()).trim() + '?nocache=' + Date.now();
  } catch (error) { console.warn(error.message); }
}
async function refreshCustomImage() {
  try {
    const response = await fetch('overview.php?custom_image=true');
    if (response.ok) document.getElementById('customimage').innerHTML = await response.text();
  } catch (error) { console.warn(error.message); }
}
function startAutoRefresh() {
  clearInterval(overviewTimer);
  clearInterval(customImageTimer);
  overviewTimer = setInterval(refreshOverview, overviewInterval);
  if (customImage) {
    refreshCustomImage();
    customImageTimer = setInterval(refreshCustomImage, 1000);
  }
}
window.addEventListener('load', () => { refreshOverview(); startAutoRefresh(); });
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    clearInterval(overviewTimer);
    clearInterval(customImageTimer);
  } else { refreshOverview(); startAutoRefresh(); }
});
</script>

<style>
  .tooltip {
  background-color: white;
  border: 1px solid #ccc;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
  padding: 10px;
  transition: opacity 0.2s ease-in-out;
}
</style>
<script src="static/custom-audio-player.js?v=lazy-spectrogram-1"></script>
<script src="static/generateMiniGraph.js"></script>
<script>
// Listen for the scroll event on the window object
window.addEventListener('scroll', function() {
  // Get all chart elements
  var charts = document.querySelectorAll('.chartdiv');
  
  // Loop through all chart elements and remove them
  charts.forEach(function(chart) {
    chart.parentNode.removeChild(chart);
    window.chartWindow = undefined;
  });
});

</script>
