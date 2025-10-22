setTimeout(()=>{const el=document.getElementById('flashNotice');if(el){el.classList.add('hide');setTimeout(()=>el.remove(),600);}},4000);
(function(){
  const PANEL_KEY = 'alertsPanelHidden';
  const TAB_KEY = 'alertsActiveTab';
  const panel = document.getElementById('alertsPanel');
  const btn = document.getElementById('alertsMainBtn');
  if(!panel || !btn) return;

  // Limit table height to 5 rows (header + up to 5 body rows) with scroll inside wrapper
  function limitAlertTables(){
    const wrappers = panel.querySelectorAll('.alerts-table-wrapper');
    wrappers.forEach(w => {
      const table = w.querySelector('table');
      if(!table) return;
      const headerRow = table.querySelector('thead tr');
      const bodyRows = table.querySelectorAll('tbody tr');
      if(!bodyRows.length || !headerRow) return;
      w.style.maxHeight = '';
      const headerH = headerRow.getBoundingClientRect().height || 30;
      const firstH = bodyRows[0].getBoundingClientRect().height || 26;
      const visible = Math.min(5, bodyRows.length);
      const target = headerH + firstH * visible + 2;
      w.style.maxHeight = target + 'px';
      w.style.overflowY = (bodyRows.length > 5) ? 'auto' : 'hidden';
    });
  }

  const total = btn.getAttribute('data-total');
  function setButtonLabel(open){
     if(open){
       btn.innerHTML = 'Alerts (<span id="alertsTotalBadge">'+ total +'</span>)';
     } else {
       btn.textContent = 'Show alerts';
     }
  }

  function openPanel(){
    panel.classList.add('open');
    panel.setAttribute('aria-hidden','false');
    localStorage.setItem(PANEL_KEY,'0');
    setButtonLabel(true);
    setTimeout(limitAlertTables, 40);
  }
  function closePanel(){
    panel.classList.remove('open');
    panel.setAttribute('aria-hidden','true');
    localStorage.setItem(PANEL_KEY,'1');
    setButtonLabel(false);
  }
  function togglePanel(){
    if(panel.classList.contains('open')) closePanel(); else openPanel();
  }

  btn.addEventListener('click', togglePanel);
  const hideBtn = document.getElementById('hideAlertsBtn');
  if(hideBtn) hideBtn.addEventListener('click', closePanel);
  const hideBoth = document.getElementById('hideBothBtn');
  if(hideBoth) hideBoth.addEventListener('click', closePanel);

  const tabs = Array.from(panel.querySelectorAll('.alerts-tab'));
  function activateTab(name){
    tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === name));
    panel.querySelectorAll('.alerts-list').forEach(l => {
      l.style.display = (l.getAttribute('data-content') === name) ? 'block' : 'none';
    });
    localStorage.setItem(TAB_KEY, name);
    setTimeout(limitAlertTables, 20);
  }
  tabs.forEach(t => t.addEventListener('click', () => activateTab(t.dataset.tab)));

  window.addEventListener('resize', () => limitAlertTables());
  document.addEventListener('DOMContentLoaded', () => limitAlertTables());

  const hidden = localStorage.getItem(PANEL_KEY) === '1';
  if(!hidden){ setTimeout(openPanel, 40); } else { setButtonLabel(false); }
  const savedTab = localStorage.getItem(TAB_KEY);
  if(savedTab && tabs.some(t => t.dataset.tab === savedTab)) activateTab(savedTab); else if(tabs.length) activateTab(tabs[0].dataset.tab);
})();
(function(){
  const PANEL_KEY='statsPanelHidden';
  const TAB_KEY='statsPanelTab';
  const panel=document.getElementById('statsPanel');
  const btn=document.getElementById('statsMainBtn');
  if(!panel||!btn) return;
  const tabs=[...panel.querySelectorAll('.stats-tab')];
  function setBtn(open){ btn.textContent = open? 'Stats' : 'Show stats'; }
  function open(){ panel.classList.add('open'); panel.setAttribute('aria-hidden','false'); localStorage.setItem(PANEL_KEY,'0'); setBtn(true); }
  function close(){ panel.classList.remove('open'); panel.setAttribute('aria-hidden','true'); localStorage.setItem(PANEL_KEY,'1'); setBtn(false); }
  function toggle(){ panel.classList.contains('open')?close():open(); }
  btn.addEventListener('click',toggle);
  const hide=document.getElementById('hideStatsBtn'); if(hide) hide.addEventListener('click',close);
  const hide2=document.getElementById('hideStatsFooterBtn'); if(hide2) hide2.addEventListener('click',close);
  function activate(name){
    tabs.forEach(t=>t.classList.toggle('active', t.dataset.tab===name));
    panel.querySelectorAll('.stats-view').forEach(v=>{ v.style.display = (v.getAttribute('data-content')===name)?'block':'none'; });
    localStorage.setItem(TAB_KEY,name);
  }
  tabs.forEach(t=>t.addEventListener('click',()=>activate(t.dataset.tab)));
  const hidden= localStorage.getItem(PANEL_KEY)==='1';
  const saved = localStorage.getItem(TAB_KEY);
  if(!hidden) setTimeout(open,60); else setBtn(false);
  if(saved && tabs.some(t=>t.dataset.tab===saved)) activate(saved); else activate('week');
})();
(function(){
  // Real-time nutrition updater
  const panel=document.getElementById('statsPanel');
  const refreshBtn=document.getElementById('statsRefreshBtn');
  const autoChk=document.getElementById('statsAutoRefresh');
  if(!panel) return;
  const week=panel.getAttribute('data-week');
  const year=panel.getAttribute('data-year');
  const weekCal=document.getElementById('stats-week-cal');
  const weekPro=document.getElementById('stats-week-pro');
  const weekCarbs=document.getElementById('stats-week-carbs');
  const weekFats=document.getElementById('stats-week-fats');
  const daysBody=document.getElementById('statsDaysBody');
  let timer=null;

  function applyNutrition(data){
    if(!data) return;
    const wt=data.week_totals||{};
    if(weekCal) weekCal.textContent = wt.calories ?? 0;
    if(weekPro) weekPro.textContent = wt.protein ?? 0;
    if(weekCarbs) weekCarbs.textContent = wt.carbs ?? wt.carbohydrates ?? 0;
    if(weekFats) weekFats.textContent = wt.fats ?? wt.fat ?? 0;
    if(daysBody){
      const days=data.days||{};
      // Build set of existing row day names
      const existing=new Set();
      daysBody.querySelectorAll('tr').forEach(r=>existing.add(r.getAttribute('data-day')));
      // Add missing rows
      Object.keys(days).forEach(dayName=>{
        if(!existing.has(dayName)){
          const tr=document.createElement('tr');
          tr.setAttribute('data-day',dayName);
          tr.innerHTML=`<td class="sd-name"></td><td class="sd-cal"></td><td class="sd-pro"></td><td class="sd-carbs"></td><td class="sd-fats"></td>`;
          daysBody.appendChild(tr);
        }
      });
      // Update each row
      daysBody.querySelectorAll('tr').forEach(r=>{
        const dn=r.getAttribute('data-day');
        const obj=days[dn];
        if(!obj){ r.querySelector('.sd-cal').textContent='0'; r.querySelector('.sd-pro').textContent='0'; r.querySelector('.sd-carbs').textContent='0'; r.querySelector('.sd-fats').textContent='0'; return; }
        r.querySelector('.sd-name').textContent=dn;
        r.querySelector('.sd-cal').textContent=obj.calories ?? 0;
        r.querySelector('.sd-pro').textContent=obj.protein ?? 0;
        r.querySelector('.sd-carbs').textContent=obj.carbs ?? 0;
        r.querySelector('.sd-fats').textContent=obj.fats ?? 0;
      });
    }
  }
  let inflight=false;
  async function fetchNutrition(){
    if(inflight) return; inflight=true;
    panel.classList.add('refreshing');
    try {
      const resp=await fetch(`/api/nutrition?week=${week}&year=${year}`, {cache:'no-store'});
      if(resp.ok){
        const data=await resp.json();
        applyNutrition(data);
      }
    } catch(e){ console.warn('Nutrition fetch failed', e); }
    finally { inflight=false; panel.classList.remove('refreshing'); }
  }
  function schedule(){
    if(timer) clearTimeout(timer);
    if(autoChk && autoChk.checked){
      timer=setTimeout(()=>{ fetchNutrition().then(schedule); }, 30000);
    }
  }
  if(refreshBtn) refreshBtn.addEventListener('click', ()=>{ fetchNutrition(); schedule(); });
  if(autoChk) autoChk.addEventListener('change', ()=> schedule());
  // Expose for other scripts (e.g., after meal update via AJAX in future)
  window.refreshNutritionPanel = () => { fetchNutrition(); schedule(); };
  // Initial schedule (small delay so initial paint stable)
  setTimeout(()=>{ schedule(); }, 4000);
})();
// PATCH: dynamic total + bulk delete support injected
(function(){
  const PANEL_KEY = 'alertsPanelHidden';
  const TAB_KEY = 'alertsActiveTab';
  const panel = document.getElementById('alertsPanel');
  const btn = document.getElementById('alertsMainBtn');
  if(!panel || !btn) return;
  function getCurrentTotal(){
    const badge = document.getElementById('alertsPanelTotal');
    if(badge) return parseInt(badge.textContent||'0',10)||0;
    const attr = btn.getAttribute('data-total');
    return parseInt(attr||'0',10)||0;
  }
  // Replace original setButtonLabel logic if already defined
  // We rely on existing open/close script loaded earlier; if not, this still handles button label updates.
  function setButtonLabel(open){
    const total = getCurrentTotal();
    if(open){
      btn.innerHTML = 'Alerts (<span id="alertsTotalBadge">'+ total +'</span>)';
    } else {
      btn.textContent = 'Show alerts';
      btn.setAttribute('data-total', String(total));
    }
  }
  // Expose for other scripts (optional)
  window.__updateAlertsButton = setButtonLabel;

  // Bulk delete logic
  const bulkBtn = document.getElementById('bulkDeleteExp');
  const selectAll = document.getElementById('expSelectAll');
  function updateBulkState(){
    if(!bulkBtn) return;
    const checks = Array.from(document.querySelectorAll('.exp-select'));
    const selected = checks.filter(c=>c.checked);
    bulkBtn.disabled = selected.length === 0;
    if(selectAll){
      const all = selected.length && selected.length === checks.length;
      selectAll.checked = all;
      selectAll.indeterminate = selected.length>0 && selected.length < checks.length;
    }
  }
  document.addEventListener('change', (e)=>{
    if(e.target && e.target.classList && e.target.classList.contains('exp-select')) updateBulkState();
    if(e.target === selectAll){
      const val = selectAll.checked;
      document.querySelectorAll('.exp-select').forEach(cb=> cb.checked = val);
      updateBulkState();
    }
  });
  if(bulkBtn){
    bulkBtn.addEventListener('click', async ()=>{
      const names = Array.from(document.querySelectorAll('.exp-select:checked')).map(c=>c.getAttribute('data-name')).filter(Boolean);
      if(!names.length) return;
      if(!confirm('Delete selected expiring ingredients?')) return;
      try {
        const resp = await fetch('/api/pantry/ingredients/bulk-delete', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({names})});
        if(!resp.ok){ alert('Delete failed'); return; }
        const data = await resp.json();
        data.deleted.forEach(n=>{
          const row = document.querySelector(`tr[data-name="${CSS.escape(n)}"]`);
          if(row) row.remove();
        });
        // Recompute counts
        const expRows = document.querySelectorAll('.exp-select').length; // remaining expiring rows
        const lowRows = document.querySelectorAll('[data-content="lowstock"] tbody tr').length;
        const totalBadge = document.getElementById('alertsPanelTotal');
        if(totalBadge){ totalBadge.textContent = String(expRows + lowRows); }
        const expTab = document.getElementById('expTabCount'); if(expTab) expTab.textContent = String(expRows);
        if(expRows === 0){
          const expList = document.querySelector('.alerts-list[data-content="expiring"]');
          if(expList) expList.style.display='none';
          // Switch to lowstock tab if exists
          const lowTabBtn = document.querySelector('.alerts-tab[data-tab="lowstock"]');
          if(lowTabBtn){ lowTabBtn.click(); }
        }
        // Update button label if panel open
        if(panel.classList.contains('open')) setButtonLabel(true); else setButtonLabel(false);
        updateBulkState();
      } catch(err){ console.error(err); alert('Unexpected error'); }
    });
    updateBulkState();
  }
})();