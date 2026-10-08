(() => {
 const form=document.getElementById('basicform') || document.getElementById('advancedform');
 if (!form) return;
 const labels=JSON.parse(form.dataset.i18n || '{}');
 const message=document.createElement('p');message.setAttribute('role','status');form.append(message);
 async function watch(job,button) {
  for (;;) {
   await new Promise(resolve=>setTimeout(resolve,1500));
   const response=await fetch('scripts/settings_status.php?job='+encodeURIComponent(job)), state=await response.json();
   if (!response.ok) throw new Error(state.error || labels.save_error);
   if (state.status==='failed') throw new Error(state.error || labels.save_error);
   if (state.status==='done') {message.textContent=labels.saved;button.disabled=false;button.textContent=labels.update;button.classList.remove('disabled');return;}
  }
 }
 form.addEventListener('submit',async event=>{
  if (event.submitter && event.submitter.name==='run_species_count') return;
  event.preventDefault();
  const button=event.submitter || form.querySelector('button[type=submit]');
  button.disabled=true;button.textContent=labels.update;message.textContent=labels.saving;
  const data=new FormData(form);data.set('async','1');
  if (button.name) data.set(button.name,button.value);
  const target=form.id==='basicform'?'scripts/config.php':'scripts/advanced.php';
  try {
   const response=await fetch(target,{method:'POST',body:data});
   const text=await response.text();let result;
   try {result=JSON.parse(text);} catch (_) {throw new Error(text.replace(/<[^>]+>/g,' ').trim().slice(0,500) || labels.save_error);}
   if (!response.ok || !result.job) throw new Error(result.error || labels.save_error);
   await watch(result.job,button);
  } catch (error) {message.textContent=error.message;button.disabled=false;button.textContent=labels.update;button.classList.remove('disabled');}
 });
})();
