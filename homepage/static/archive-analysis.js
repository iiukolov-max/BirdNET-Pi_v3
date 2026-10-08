(() => {
  const panel=document.getElementById('archive-analysis');
  if (!panel) return;
  const button=panel.querySelector('button'), progress=panel.querySelector('progress');
  const labels=JSON.parse(panel.dataset.i18n), locale=panel.dataset.language || 'en';
  const t=(key,values={})=>(labels[key] || key).replace(/\{(\w+)\}/g,(_,name)=>values[name] ?? '');
  const set=(field,value)=>{const node=panel.querySelector(`[data-field="${field}"]`);node.textContent=value;node.hidden=!value;};
  const number=(n,digits=0)=>Number(n).toLocaleString(locale,{maximumFractionDigits:digits});
  let active=false;
  async function update(start=false) {
    try {
      button.disabled=true;
      const options=start ? {method:'POST',body:new URLSearchParams({token:panel.dataset.token})} : {};
      const response=await fetch('scripts/archive_analysis.php',options), s=await response.json();
      if (response.status===409) {panel.remove();return;}
      if (!response.ok) throw new Error(s.error || labels.error);
      active=s.active;
      set('pending',t('pending',{n:number(s.pending)}));
      set('progress','');set('new_files','');set('eta','');set('errors','');
      if (active) {
        set('progress',s.status==='loading'?labels.loading:t('progress',{done:number(s.processed),total:number(s.total),left:number(s.job_remaining)}));
        if (s.recording_paused) set('progress',panel.querySelector('[data-field="progress"]').textContent+' '+labels.recording_paused);
        if (s.new_pending) set('new_files',t('new_files',{n:number(s.new_pending)}));
        let eta=s.expected_finish?t('eta',{time:new Date(s.expected_finish).toLocaleString(locale)}):labels.estimate_wait;
        if (s.files_per_minute) eta+=' · '+t('rate',{n:number(s.files_per_minute,1)});
        set('eta',eta);
      }
      const errors=[];
      if (s.failed) errors.push(t('failed',{n:number(s.failed)}));
      if (s.missing) errors.push(t('missing',{n:number(s.missing)}));
      if (s.status==='interrupted') errors.push(labels.interrupted);
      set('errors',errors.join(' '));
      const storage=s.storage;
      set('free',t('free',{n:number(storage.free_bytes/1024**3,2)}));
      set('capacity',storage.estimated_files===null?labels.space_wait:t('capacity',{n:number(storage.estimated_files)}));
      set('days',storage.estimated_days===null?'':t('days',{n:number(storage.estimated_days,1)}));
      progress.hidden=!active;progress.max=Math.max(1,s.total || 1);progress.value=(s.processed || 0)+(s.failed || 0)+(s.missing || 0);
      button.disabled=active || !Number.isFinite(s.pending) || s.pending<=0;
    } catch (e) {set('errors',e.message);button.disabled=true;}
  }
  button.addEventListener('click',()=>update(true));
  async function poll() {await update();if (panel.isConnected) setTimeout(poll,active?5000:30000);}
  poll();
})();
