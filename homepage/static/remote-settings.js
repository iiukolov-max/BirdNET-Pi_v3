(() => {
 const selection=document.getElementById('analysis_backend');
 const fields=document.getElementById('remote-analysis-fields');
 if(!selection || !fields)return;
 function update(){
  const remote=selection.value==='remote';
  fields.hidden=!remote;
  fields.querySelectorAll('input').forEach(input=>input.disabled=!remote);
  document.getElementById('remote_analysis_ip').required=remote;
 }
 selection.addEventListener('change',update);update();
})();
