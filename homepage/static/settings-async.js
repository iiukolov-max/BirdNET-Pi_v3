(() => {
 const form=document.getElementById('basicform') || document.getElementById('advancedform');
 if (!form) return;
 const labels=JSON.parse(form.dataset.i18n || '{}');
 const message=document.createElement('p');message.setAttribute('role','status');form.append(message);
 let busy=false;
 function saved(state) {
  message.textContent=labels.saved;
  const revision=form.elements.namedItem('config_revision');
  if (revision && state.revision) revision.value=state.revision;
  const date=form.elements.namedItem('date'), time=form.elements.namedItem('time');
  if (date && time) {
   form.elements.namedItem('initial_clock_mode').value=date.disabled?'ntp':'manual';
   form.elements.namedItem('initial_date').value=date.value;
   form.elements.namedItem('initial_time').value=time.value;
  }
 }
 async function watch(job) {
  const deadline=Date.now()+8*60*1000;
  while (Date.now()<deadline) {
   await new Promise(resolve=>setTimeout(resolve,750));
   const response=await fetch('scripts/settings_status.php?job='+encodeURIComponent(job),{signal:AbortSignal.timeout(20000)}), state=await response.json();
   if (!response.ok) throw new Error(state.error || labels.save_error);
   if (state.status==='failed') throw new Error(state.error || labels.save_error);
   if (state.status==='done') return state;
   if (!['queued','applying'].includes(state.status)) throw new Error(labels.save_error);
  }
  throw new Error('Settings are still being applied. Reload to check their status.');
 }
 form.addEventListener('submit',async event=>{
  if (event.submitter && event.submitter.name==='run_species_count') return;
  event.preventDefault();
  if (busy) return;
  busy=true;
  const button=event.submitter || form.querySelector('button[type=submit]');
  const views=document.querySelector('.views');
  if (views) views.style.opacity='';
  button.disabled=true;button.classList.add('disabled');button.textContent=labels.update;message.textContent=labels.saving;
  form.setAttribute('aria-busy','true');
  try {
   const data=new FormData(form);data.set('async','1');
   if (button.name) data.set(button.name,button.value);
   const target=form.id==='basicform'?'scripts/config.php':'scripts/advanced.php';
   const response=await fetch(target,{method:'POST',body:data,signal:AbortSignal.timeout(45000)});
   const text=await response.text();let result;
   try {result=JSON.parse(text);} catch (_) {throw new Error(text.replace(/<[^>]+>/g,' ').trim().slice(0,500) || labels.save_error);}
   if (!response.ok) throw new Error(result.error || labels.save_error);
   if (result.status!=='done') {
    if (!result.job) throw new Error(result.error || labels.save_error);
    result=await watch(result.job);
   }
   saved(result);
  } catch (error) {message.textContent=error.message;}
  finally {
   busy=false;button.disabled=false;button.textContent=labels.update;button.classList.remove('disabled');
   form.removeAttribute('aria-busy');if (views) views.style.opacity='';
  }
 });
})();
