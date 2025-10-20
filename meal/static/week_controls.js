(function () {
  const body = document.body;
  if (!body.dataset.week || !body.dataset.year) return;

  const curWeek = parseInt(body.dataset.week, 10);
  const curYear = parseInt(body.dataset.year, 10);

  const resetBtn = document.getElementById("resetWeek");
  const randomBtn = document.getElementById("randomizeWeek");
  const exportBtn = document.getElementById("exportPDF");
  const todayBtn = document.getElementById("todayWeek");
  const availBtn = document.getElementById("availableRecipes");
  const modal = document.getElementById("advRandModal");
  const closeBtn = document.getElementById("advRandClose");
  const cancelBtn = document.getElementById("advRandCancel");
  const form = document.getElementById("advRandForm");
  const replaceChk = document.getElementById("arReplaceExisting");
  const onlyAvailChk = document.getElementById("arOnlyAvailable");

  // Available modal elements
  const availModal = document.getElementById('availableModal');
  const availClose = document.getElementById('availableClose');
  const availCloseFooter = document.getElementById('availableCloseFooter');
  const availTbody = document.getElementById('availableTbody');
  const availLoading = document.getElementById('availableLoading');
  const availError = document.getElementById('availableError');
  const availSummary = document.getElementById('availableSummary');

  function openAvail(){ if(availModal){ availModal.style.display='flex'; } }
  function closeAvail(){ if(availModal){ availModal.style.display='none'; } }

  async function loadAvailable(){
    if(!availTbody) return;
    availTbody.innerHTML='';
    if(availError) availError.style.display='none';
    if(availLoading) availLoading.style.display='block';
    try {
      const resp = await fetch('/api/recipes/available');
      if(!resp.ok) throw new Error('HTTP '+resp.status);
      const data = await resp.json();
      const list = data.recipes || [];
      if(list.length===0){
        availTbody.innerHTML = '<tr><td colspan="4" style="padding:8px; font-size:.7rem; text-align:center; opacity:.7;">No available recipes.</td></tr>';
      } else {
        const frag = document.createDocumentFragment();
        list.forEach(r=>{
          const tr = document.createElement('tr');
          tr.innerHTML = `<td style="padding:6px 8px;">${r.name || ''}</td>`+
                         `<td style=\"padding:6px 8px; text-align:right;\">${r.servings ?? ''}</td>`+
                         `<td style=\"padding:6px 8px; text-align:right;\">${r.calories ?? ''}</td>`+
                         `<td style=\"padding:6px 8px; text-align:right; font-weight:600;\">${r.times_possible ?? 0}</td>`;
          frag.appendChild(tr);
        });
        availTbody.appendChild(frag);
      }
      if(availSummary){
        availSummary.textContent = `${data.count || 0} / ${data.total || list.length} available recipes`;
      }
    } catch(err){
      console.error(err);
      if(availError) availError.style.display='block';
    } finally {
      if(availLoading) availLoading.style.display='none';
    }
  }

  if(availBtn){
    availBtn.addEventListener('click', ()=>{ openAvail(); loadAvailable(); });
  }
  if(availClose) availClose.addEventListener('click', closeAvail);
  if(availCloseFooter) availCloseFooter.addEventListener('click', closeAvail);
  if(availModal){
    availModal.addEventListener('click', (e)=>{ if(e.target===availModal) closeAvail(); });
  }

  // Reset week
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (confirm("Are you sure you want to reset this week?")) {
        window.location.href = `/reset_week?week=${curWeek}&year=${curYear}`;
      }
    });
  }

  // Export PDF
  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      if (confirm("Do you want to export this week to PDF?")) {
        window.location.href = `/export_pdf?week=${curWeek}&year=${curYear}`;
      }
    });
  }

  if (todayBtn) {
    todayBtn.addEventListener("click", () => {
      const today = new Date();
      const tmp = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()));
      const dayNum = tmp.getUTCDay() || 7;
      tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
      const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
      const weekNo = Math.ceil((((tmp - yearStart) / 86400000) + 1) / 7);
      const isoYear = tmp.getUTCFullYear();


      window.location.href = `/?week=${weekNo}&year=${isoYear}`;
    });
  }

  function openAdv(){ if(modal){ modal.style.display = 'flex'; } }
  function closeAdv(){ if(modal){ modal.style.display = 'none'; } }

  if(randomBtn) randomBtn.addEventListener('click', openAdv);
  if(closeBtn) closeBtn.addEventListener('click', closeAdv);
  if(cancelBtn) cancelBtn.addEventListener('click', closeAdv);

  if(form){
    form.addEventListener('submit', async (e)=>{
      e.preventDefault();
      const days = Array.from(form.querySelectorAll('input.ar-day:checked')).map(i=>i.value);
      const payload = { week: curWeek, year: curYear, days: days.length? days : null, replace_existing: !!(replaceChk && replaceChk.checked), only_available: !!(onlyAvailChk && onlyAvailChk.checked) };
      try {
        const resp = await fetch('/randomize_custom', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
        if(!resp.ok){ alert('Randomize failed'); return; }
        const data = await resp.json();
        window.location.href = `/?week=${curWeek}&year=${curYear}&notice=random&chg=${data.modified}`;
      } catch(err){ console.error(err); alert('Unexpected error'); }
    });
  }
})();
