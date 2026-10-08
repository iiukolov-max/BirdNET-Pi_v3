<?php
error_reporting(E_ERROR);
ini_set('display_errors',1);

session_start();
require_once "scripts/common.php";
$user = get_user();
$home = get_home();

$fetch = shell_exec("sudo -u".$user." git -C ".$home."/BirdNET-Pi fetch 2>&1");
$str = trim(shell_exec("sudo -u".$user." git -C ".$home."/BirdNET-Pi status"));
if (preg_match("/behind '.*?' by (\d+) commit(s?)\b/", $str, $matches)) {
  $num_commits_behind = $matches[1];
}
if (preg_match('/\b(\d+)\b and \b(\d+)\b different commits each/', $str, $matches)) {
    $num1 = (int) $matches[1];
    $num2 = (int) $matches[2];
    $num_commits_behind = $num1 + $num2;
}
if (stripos($str, "Your branch is up to date") !== false) {
  $num_commits_behind = '0';
}
$_SESSION['behind'] = $num_commits_behind;
$_SESSION['behind_time'] = time();

$restore = "cat $home/BirdSongs/restore.log";
$max_upload_size = floor(disk_free_space("$home/BirdNET-Pi/") / 1.001);

?><html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<br>
<br>
<script>
var seconds = 0;
function update() {
  if(confirm('Are you sure you want to update?')) {
    setInterval(function(){ seconds += 1; document.getElementById('updatebtn').innerHTML = "Updating: <pre id='timer' class='bash'>"+new Date(seconds * 1000).toISOString().substring(14, 19)+"</pre>"; }, 1000);
    return true;
  } else {
    return false;
  }
}
</script>
<div class="systemcontrols">
<form action="views.php" method="GET">
  <div>
    <button type="submit" name="submit" value="sudo reboot" onclick="return confirm('Are you sure you want to reboot?')">Reboot</button>
  </div>
  <div>
    <button type="submit" name="submit" id="updatebtn" value="update_birdnet.sh" onclick="return update();">Update <?php if(isset($_SESSION['behind']) && $_SESSION['behind'] != "0" && $_SESSION['behind'] != "with"){?><div class="updatenumber"><?php echo $_SESSION['behind']; ?></div><?php } ?></button>
  </div>
  <div>
    <button type="submit" name="submit" value="sudo shutdown now" onclick="return confirm('Are you sure you want to shutdown?')">Shutdown</button>
  </div>
  <div>
    <button type="submit" name="submit" value="sudo clear_all_data.sh" onclick="return confirm('Delete all recordings, detection audio, spectrograms and charts, and reset BirdDB.txt? Detection database and settings are kept. Analysis will stop. This cannot be undone and may take up to 90 seconds.')">Clear ALL data</button>
  </div>
</form>
<div id="container">
  <button id="pickfile" type="button" href="javascript:;">Restore data</button>
</div>
<div><a href="scripts/backup.php" download ><button onclick="return confirm('Download backup? Note that this could take a long time.')">Backup data</button></a></div>
<?php
if (!isset($_SESSION['verified_export_token'])) {
  $_SESSION['verified_export_token'] = bin2hex(random_bytes(32));
}
?>
<style>
.systemcontrols .verified-export { text-align: center; }
.systemcontrols .verified-export h3,
.systemcontrols .verified-export p { width: 50%; margin: 12px auto; overflow-wrap: anywhere; }
.systemcontrols .verified-export h3 { margin-top: 28px; }
@media screen and (max-width: 1000px) {
  .systemcontrols .verified-export h3,
  .systemcontrols .verified-export p { width: 60%; }
}
@media screen and (max-width: 800px) {
  .systemcontrols .verified-export h3,
  .systemcontrols .verified-export p { width: 80%; }
}
</style>
<div class="verified-export">
  <h3>Detection review export</h3>
  <p>Export all detections, including TP, FP and unreviewed records.</p>
  <button type="button" id="verified-export-run">Generate BirdDB_verified.txt</button>
  <a href="scripts/verified_export.php?action=download" download="BirdDB_verified.txt" id="verified-export-download"><button type="button">Download BirdDB_verified.txt</button></a>
  <p id="verified-export-status" role="status" aria-live="polite"></p>
</div>
<script>
document.getElementById('verified-export-run').addEventListener('click', async function () {
  const button = this;
  const status = document.getElementById('verified-export-status');
  button.disabled = true;
  status.textContent = 'Generating export…';
  try {
    const body = new URLSearchParams({token: <?php echo json_encode($_SESSION['verified_export_token']); ?>});
    const response = await fetch('scripts/verified_export.php?action=run', {method: 'POST', body});
    if (response.status === 401) throw new Error('Sign in to Tools to export detections.');
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.message || 'Export failed.');
    status.textContent = 'Export ready: ' + result.rows + ' records. Use Download to save the file.';
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
</script>
<?php
  $cmd="cd ".$home."/BirdNET-Pi && sudo -u ".$user." git rev-list --max-count=1 HEAD";
  $curr_hash = shell_exec($cmd);
?>
  <p style="font-size:11px;text-align:center"></br></br>Running version: </p>
  <a href="https://github.com/iiukolov-max/BirdNET-Pi_v3/commit/<?php echo $curr_hash; ?>" target="_blank">
    <p style="font-size:11px;text-align:center;box-sizing: border-box"><?php echo $curr_hash; ?></p>
  </a>
  <pre id="console" style="text-align:center"></pre>
</div>
<script type="text/javascript">
// based on Custom example logic

var uploader = new plupload.Uploader({
    runtimes : 'html5',
    browse_button : 'pickfile', // you can pass an id...
    container: document.getElementById('container'), // ... or DOM Element itself
    url : 'scripts/restore.php',
    chunk_size: '2mb',
    multi_selection: false,

    filters : {
        max_file_size : '<?php echo "$max_upload_size"; ?>',
        mime_types: [
            {title : "Tar files", extensions : "tar"}
        ]
    },

    init: {
        FilesAdded: function(up, files) {
            uploader.start();
        },

        UploadProgress: function(up, file) {
            if (file.percent !== 100) {
                document.getElementById('pickfile').innerHTML = "<span>Uploading: <pre id='timer' class='bash'>" + String(file.percent).padStart(2, '0') + "%</pre></span>";
            } else {
                setInterval(function(){ seconds += 1; document.getElementById('pickfile').innerHTML = "Restoring: <pre id='timer' class='bash'>"+new Date(seconds * 1000).toISOString().substring(14, 19)+"</pre>"; }, 1000);
            }
        },

        FileUploaded: function(up, file, info) {
            // Called when file has finished uploading
            console.log('[FileUploaded] File:', file, "Info:", info);
            const xhttp = new XMLHttpRequest();
            xhttp.onload = function() {
                if(this.responseText.length > 0) {
                    document.body.innerHTML=this.responseText;
                }
            };
            xhttp.open("GET", "views.php?submit=<?php echo "$restore"; ?>");
            xhttp.send();
        },

        Error: function(up, err) {
            document.getElementById('console').appendChild(document.createTextNode("\nError #" + err.code + ": " + err.message));
        }
    }
});

uploader.init();
</script>
