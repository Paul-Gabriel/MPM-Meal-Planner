// ---------- Modal helpers ----------
function openModal(day, meal) {
  const popup = document.getElementById(`${day}-${meal}-popup`);
  if (popup) popup.style.display = "flex";
}

function closeModal(day, meal) {
  const popup = document.getElementById(`${day}-${meal}-popup`);
  if (popup) popup.style.display = "none";
}

// ---------- Select recipe inside modal ----------
function selectRecipe(name, image, day, meal) {
  // Try to locate the preview element (img or placeholder)
  let preview =
    document.getElementById(`recipePreview-${day}-${meal}`) ||
    document.querySelector(
      `#${day}-${meal}-popup .recipe-modal-left img, #${day}-${meal}-popup .recipe-modal-left .no-image-placeholder`
    );

  if (!preview) {
    // Fallback: create an image directly in the left column of the modal
    const left = document.querySelector(`#${day}-${meal}-popup .recipe-modal-left`);
    if (left) {
      left.innerHTML = `<img id="recipePreview-${day}-${meal}" src="/static/pictures/${image}" alt="${name}" style="max-width:250px;border-radius:10px;">`;
    }
  } else if (preview.tagName && preview.tagName.toLowerCase() === "img") {
    preview.src = "/static/pictures/" + image;
    preview.alt = name;
  } else {
    // Placeholder -> replace it with the image
    preview.outerHTML = `<img id="recipePreview-${day}-${meal}" src="/static/pictures/${image}" alt="${name}" style="max-width:250px;border-radius:10px;">`;
  }

  // Set the hidden input with the chosen recipe
  const input = document.getElementById(`selectedRecipe-${day}-${meal}`);
  if (input) input.value = name;

  const kcalEl = document.getElementById(`kcal-${day}-${meal}`);
  if (kcalEl) {
    let kcal = 0;
    if (window.RECIPES_KCAL && Object.prototype.hasOwnProperty.call(window.RECIPES_KCAL, name)) {
      const v = window.RECIPES_KCAL[name];
      kcal = (typeof v === 'number') ? v : (parseInt(v, 10) || 0);
    }
    kcalEl.innerHTML = `Calories/serving: <strong>${kcal}</strong>`;
  }
}

// NEW: Initialize global calories map from hidden JSON if not present
(function initRecipeCalories(){
  if(window.RECIPES_KCAL) return; // already built
  const holder = document.getElementById('recipes-json');
  if(!holder) return;
  try {
    const raw = holder.getAttribute('data-recipes');
    if(!raw) return;
    const arr = JSON.parse(raw);
    window.RECIPES_KCAL = {};
    arr.forEach(r => {
      if(!r || typeof r !== 'object') return;
      const name = r.name;
      if(!name) return;
      const c = r.calories_per_serving ?? r.kalories_per_serving ?? 0;
      window.RECIPES_KCAL[name] = (typeof c === 'number') ? c : (parseInt(c,10) || 0);
    });
  } catch(e){ console.warn('Failed to init RECIPES_KCAL', e); }
})();

// ---------- Close modal on outside click (optional) ----------
window.onclick = function (event) {
  // If you want to close when clicking the internal overlay, keep this; otherwise you can remove it
  const modals = document.querySelectorAll(".popup");
  modals.forEach((m) => {
    if (event.target === m) m.style.display = "none";
  });
};

// ---------- Week dropdown ----------
function toggleWeekDropdown() {
  const dropdown = document.getElementById("weekDropdown");
  if (dropdown.style.display === "none" || dropdown.style.display === "") {
    dropdown.style.display = "block";
  } else {
    dropdown.style.display = "none";
  }
}

// Build the list of allowed weeks
function populateWeekList() {
  const weekList = document.getElementById("weekList");
  if (!weekList) return null;
  weekList.innerHTML = "";

  // Allowed interval (adjust as you like)
  const ALLOWED_START = new Date(2025, 8, 1); // 1 Sep 2025
  const ALLOWED_END   = new Date(2026, 11, 31);

  // Normalize to 00:00
  const today = new Date();
  today.setHours(0,0,0,0);

  // Move to the first Monday >= ALLOWED_START
  const d = new Date(ALLOWED_START);
  while (d.getDay() !== 1) d.setDate(d.getDate() + 1);

  let defaultMonday = null;

  for (let cur = new Date(d); cur <= ALLOWED_END; cur.setDate(cur.getDate() + 7)) {
    const monday = new Date(cur);
    const sunday = new Date(cur); sunday.setDate(sunday.getDate() + 6);

    const isCurrent = monday <= today && today <= sunday;

    const btn = document.createElement("div");
    btn.textContent =
      `${monday.toLocaleDateString()} - ${sunday.toLocaleDateString()}${isCurrent ? " — this week" : ""}`;
    btn.className = "week-option" + (isCurrent ? " current-week" : "");
    btn.style.padding = "8px";
    btn.style.cursor = "pointer";
    btn.dataset.value = toYMD(monday);
    btn.onclick = () => selectWeek(new Date(monday));

    if (isCurrent && !defaultMonday) {
      defaultMonday = new Date(monday); // remember current week
    }

    weekList.appendChild(btn);
  }

  return defaultMonday;
}


function toYMD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// ---------- Select week (fetch JSON + update UI) ----------
function selectWeek(mondayDate) {
  const sundayDate = new Date(mondayDate);
  sundayDate.setDate(mondayDate.getDate() + 6);

  const weekDisplay = document.getElementById("weekDisplay");
  if (weekDisplay) {
    weekDisplay.textContent = `${mondayDate.toLocaleDateString()} - ${sundayDate.toLocaleDateString()}`;
  }
  const dropdown = document.getElementById("weekDropdown");
  if (dropdown) dropdown.style.display = "none";

  const start = toYMD(mondayDate);
  window.CURRENT_MONDAY_YMD = start; // remember current Monday
  fetch(`/get_week?start=${encodeURIComponent(start)}`, { cache: "no-store" })
    .then((r) => {
      if (!r.ok) throw new Error("Week out of allowed range or bad date");
      return r.json();
    })
    .then(updateTable)
    .catch((error) => console.error("Error loading week:", error));
}

// ---------- Update only labels + recipe spans + hidden week/year ----------
// Inject helper before updateTable so it can be reused by deleteMeal as well.
function adjustMealButtons(day, meal, rawVal, dateStr) {
  const cell = document.getElementById(`${day}-${meal}`);
  if (!cell) return;

  // 🔧 1️⃣ Curăță doar butoanele din celulă (Add / Actions), dar NU pe cele din popup
  Array.from(cell.children).forEach(child => {
    if (child.tagName === 'BUTTON' && !child.closest('.popup')) {
      child.remove();
    }
  });

  const isEmpty = (!rawVal || rawVal === '-');
  const isCooked = (typeof rawVal === 'object' && rawVal && rawVal.cooked);

  // 🔧 2️⃣ Dacă e gătit, nu afișăm nimic
  if (isCooked) return;

  // 🔧 3️⃣ Dacă e gol, afișăm doar butonul Add
  if (isEmpty) {
    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.textContent = 'Add';
    addBtn.className = 'add-btn';
    addBtn.onclick = () => openModal(day, meal);
    cell.appendChild(addBtn);
    return;
  }

  // 🔧 4️⃣ Dacă există o rețetă planificată, afișăm doar Actions ▾
  const actionsBtn = document.createElement('button');
  actionsBtn.type = 'button';
  actionsBtn.className = 'slot-actions-btn';
  actionsBtn.dataset.day = day;
  actionsBtn.dataset.meal = meal;
  actionsBtn.dataset.date = dateStr || cell.getAttribute('data-date') || '';
  actionsBtn.textContent = 'Actions ▾';
  actionsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    openSlotActionMenu(actionsBtn);
  });
  cell.appendChild(actionsBtn);
}



function openSlotActionMenu(btn){
  closeAllSlotMenus();
  const day = btn.dataset.day; const meal = btn.dataset.meal; const dateStr = btn.dataset.date;
  const menu = document.createElement('div');
  menu.className = 'slot-action-menu';
  menu.dataset.day = day; menu.dataset.meal = meal;
  const today = new Date();
  const dd = String(today.getDate()).padStart(2,'0');
  const mm = String(today.getMonth()+1).padStart(2,'0');
  const yyyy = today.getFullYear();
  const todayStr = `${dd}.${mm}.${yyyy}`;
  const isToday = (dateStr === todayStr);
  // Determine if past day
  const parts = dateStr ? dateStr.split('.') : [];
  let isPast = false;
  if(parts.length === 3){
    const dObj = new Date(parseInt(parts[2],10), parseInt(parts[1],10)-1, parseInt(parts[0],10));
    dObj.setHours(0,0,0,0);
    const tC = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    isPast = dObj < tC;
  }
  // Build items
  const items = [];
  // Edit (disabled if past)
  items.push({label:'Edit', action: () => openModal(day, meal), disabled: isPast});
  // Cook (only today, not past, not cooked) -> open cooking panel
  items.push({label:'Cook', action: () => openCookPanel(day, meal), disabled: !isToday || isPast});
  // Delete (disabled if past)
  items.push({label:'Delete', action: () => deleteMeal(day, meal), danger:true, disabled:isPast});
  items.forEach(it => {
    const div = document.createElement('div');
    div.className = 'item' + (it.danger? ' danger':'') + (it.disabled? ' disabled':'');
    div.textContent = it.label;
    if(!it.disabled){
      div.addEventListener('click', (e)=>{
        e.stopPropagation();
        try { it.action(); } catch(_){ }
        closeAllSlotMenus();
      });
    }
    menu.appendChild(div);
  });
  // Positioning: attach inside the same table cell instead of at body level
const cell = btn.closest('td');
if (cell) {
  cell.style.position = 'relative';
  menu.style.position = 'absolute';
  menu.style.top = (btn.offsetTop + btn.offsetHeight + 4) + 'px';
  menu.style.left = btn.offsetLeft + 'px';
  cell.appendChild(menu);
} else {
  // fallback if not in table cell
  const rect = btn.getBoundingClientRect();
  menu.style.top = (window.scrollY + rect.bottom + 4) + 'px';
  menu.style.left = (window.scrollX + rect.left) + 'px';
  document.body.appendChild(menu);
}

setTimeout(() => {
  document.addEventListener('click', slotMenuOutside, { once: true });
  document.addEventListener('keydown', slotMenuEsc, { once: true });
}, 0);

}
function closeAllSlotMenus(){
  document.querySelectorAll('.slot-action-menu').forEach(m => m.remove());
}
function slotMenuOutside(){ closeAllSlotMenus(); }
function slotMenuEsc(e){ if(e.key === 'Escape'){ closeAllSlotMenus(); } }

// ---------- Update only labels + recipe spans + hidden week/year ----------
function updateTable(data) {
  // data = { meta:{week,year}, days:{ Monday:{date,breakfast,lunch,dinner}, ... } }
  const mealsOrder = ["breakfast", "lunch", "dinner"];
  const week = data?.meta?.week;
  const year = data?.meta?.year;
  const days = data?.days || {};

  // 1) update day labels
  Object.entries(days).forEach(([day, meals]) => {
    const labelEl = document.getElementById(`${day}-label`);
    if (labelEl) {
      labelEl.textContent = `${day} (${meals.date})`;
    }
  });

  // 2) update only the recipe slot-span per cell (keep modal & buttons intact initially, then rebuild buttons)
  Object.entries(days).forEach(([day, meals]) => {
    mealsOrder.forEach((meal) => {
      const slot = document.getElementById(`slot-${day}-${meal}`);
      if (!slot) return;
      const val = meals[meal];
      if (!val || val === "-") {
        slot.textContent = "-";
      } else if (typeof val === 'object' && val.cooked) {
        slot.innerHTML = `<span style="color:green; font-weight:bold;">${val.name} (Cooked)</span>`;
      } else {
        const name = (typeof val === 'string') ? val : val?.name;
        if(!name){ slot.textContent='-'; } else {
          const href = `/recipe/${encodeURIComponent(name)}`;
          slot.innerHTML = `<a href="${href}" style="color:#2c3e50;font-weight:600;text-decoration:none;">${name}</a>`;
        }
      }
      adjustMealButtons(day, meal, val, meals.date);
    });
  });

  // Recompute per-day calories using mapping (supports cooked objects)
  Object.entries(days).forEach(([day, meals]) => {
    let sum = 0;
    mealsOrder.forEach(meal => {
      const raw = meals[meal];
      if(!raw || raw === '-') return;
      const recipeName = (typeof raw === 'string') ? raw : raw?.name;
      if(!recipeName) return;
      if(window.RECIPES_KCAL && Object.prototype.hasOwnProperty.call(window.RECIPES_KCAL, recipeName)){
        const k = window.RECIPES_KCAL[recipeName];
        const n = (typeof k === 'number') ? k : parseInt(k,10);
        if(!Number.isNaN(n)) sum += n;
      }
    });
    const kcalCell = document.getElementById(`${day}-kcal`);
    if(kcalCell) kcalCell.textContent = sum;
  });


  const today = new Date(); today.setHours(0,0,0,0);

  function parseDMY(dmy) {
    // "dd.mm.yyyy" -> Date
    const [dd, mm, yyyy] = dmy.split('.').map(n => parseInt(n, 10));
    return new Date(yyyy, (mm || 1) - 1, dd || 1);
  }

  Object.entries(days).forEach(([day, meals]) => {
    const d = parseDMY(meals.date);
    const isPast = d < today;
    ["breakfast","lunch","dinner"].forEach(meal => {
      // Disable only the action buttons we control (Add/Edit/Delete), not cooked forms
      const cell = document.getElementById(`${day}-${meal}`);
      if(!cell) return;
      Array.from(cell.children).forEach(ch => {
        if(ch.tagName === 'BUTTON' && !ch.closest('form') && ch.classList.contains('del-btn') || (ch.textContent === 'Add' || ch.textContent === 'Edit')){
          ch.disabled = isPast;
          ch.title = isPast ? "Past date — editing disabled" : '';
          ch.classList.toggle('locked', isPast);
        }
      });
    });
  });


  // 3) push week/year to every modal form so Save writes to the correct week
  if (typeof week !== "undefined" && typeof year !== "undefined") {
    // Update week/year in all forms
    document.querySelectorAll('form.recipe-modal input[name="week"]').forEach(i=>i.value=week);
    document.querySelectorAll('form.recipe-modal input[name="year"]').forEach(i=>i.value=year);
    window.CURRENT_WEEK = week;
    window.CURRENT_YEAR = year; // ensure year tracked for cook API
    const slLink = document.getElementById('shoppingListLink');
    if(slLink){ slLink.href = `/shopping-list?week=${week}`; }
    // NEW: also sync the Nutrition panel with the new week
    const statsPanel = document.getElementById('statsPanel');
    if(statsPanel){
      statsPanel.setAttribute('data-week', week);
      statsPanel.setAttribute('data-year', year);
      // If the global refresh function exists, call it for immediate update
      if(typeof window.refreshNutritionPanel === 'function'){
        window.refreshNutritionPanel();
      }
    }
  }
  // After update, refresh the badge for the selected week
  if(typeof window.CURRENT_WEEK !== 'undefined') {
    refreshShoppingListBadge(window.CURRENT_WEEK);
  }
}


// ---------- init ----------
const defaultMonday = populateWeekList();
if (defaultMonday) {
  const sunday = new Date(defaultMonday);
  sunday.setDate(sunday.getDate() + 6);
  const weekDisplay = document.getElementById("weekDisplay");
  if (weekDisplay) {
    weekDisplay.textContent =
      `${defaultMonday.toLocaleDateString()} - ${sunday.toLocaleDateString()} — this week`;
  }
  selectWeek(defaultMonday); // fetch /get_week and update the table
}

// ---------- Shopping List badge refresh ----------
async function refreshShoppingListBadge(weekOverride){
  const today = new Date();
  function isoWeek(d){
    const dt = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = dt.getUTCDay() || 7; // ISO: Monday=1..Sunday=7
    dt.setUTCDate(dt.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(dt.getFullYear(),0,1));
    return Math.ceil((((dt - yearStart) / 86400000) + 1) / 7);
  }
  const currentIsoWeek = isoWeek(today);
  const w = (typeof weekOverride !== 'undefined') ? weekOverride : window.CURRENT_WEEK;
  let base = '/api/shopping-list';
  // If we know the target week, include it; otherwise rely on default (current week)
  if(typeof w !== 'undefined') {
    // Add skip_past=1 if this is the real current week so badge ignores past days
    if(w === currentIsoWeek) {
      base = `/api/shopping-list?week=${w}&skip_past=1`;
    } else {
      base = `/api/shopping-list?week=${w}`;
    }
  } else {
    // No explicit week yet, still try to filter current week by appending skip_past=1
    base = `/api/shopping-list?skip_past=1`;
  }
  try {
    const resp = await fetch(base, {cache:'no-store'});
    if(!resp.ok) return;
    const data = await resp.json();
    const countEl = document.getElementById('shoppingListCount');
    if(countEl){
      if(data.count && data.count > 0){
        countEl.textContent = data.count;
        countEl.style.display = 'inline-block';
      } else {
        countEl.textContent = '0';
        countEl.style.display = 'none';
      }
    }
  } catch(e){ console.warn('Could not refresh shopping list badge', e); }
}

// ---------- Intercept meal update forms to submit via fetch + refresh ----------
// ---------- Intercept meal update forms to submit via fetch + refresh ----------
function hookMealForms(){
  document.querySelectorAll('form.recipe-modal').forEach(form => {
    if(form.dataset.hooked === '1') return;
    form.dataset.hooked = '1';

    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const fd = new FormData(form);

      try {
        const resp = await fetch('/update_meal', { method:'POST', body: fd });

        const week = fd.get('week');
        const year = fd.get('year');

        if(week && year){
          const monday = window.CURRENT_MONDAY_YMD;
          if(monday){
            try {
              const r2 = await fetch(`/get_week?start=${encodeURIComponent(monday)}`, {cache:'no-store'});
              if(r2.ok){
                const json = await r2.json();
                updateTable(json);
                if(typeof window.refreshNutritionPanel === 'function'){
                  window.refreshNutritionPanel();
                }
              }
            } catch(e){ console.warn('Failed refresh after save', e); }
          }
          await refreshShoppingListBadge(week);
        }
      } catch(err){
        console.error('Update meal failed', err);
      }

      // Close modal
      const day = fd.get('day');
      const meal = fd.get('meal');
      if(day && meal){ closeModal(day, meal); }

      // Optimistic UI update
      const recipe = fd.get('recipe');
      if(day && meal && recipe){
        const slot = document.getElementById(`slot-${day}-${meal}`);
        if(slot){
          if(!recipe || recipe === '-') slot.textContent = '-';
          else {
            const href = `/recipe/${encodeURIComponent(recipe)}`;
            slot.innerHTML = `<a href="${href}" style="color:#2c3e50;font-weight:600;text-decoration:none;">${recipe}</a>`;
          }
        }

        // 🔧 FIX: Rebuild buttons so "Add" disappears immediately
        adjustMealButtons(day, meal, recipe, fd.get('date') || '');

        // Quick kcal update
        try {
          const dayRowKcal = document.getElementById(`${day}-kcal`);
          if(dayRowKcal && window.RECIPES_KCAL){
            const rowDayMeals = {};
            ['breakfast','lunch','dinner'].forEach(m=>{
              const sp = document.getElementById(`slot-${day}-${m}`);
              if(sp){
                const link = sp.querySelector('a');
                rowDayMeals[m] = link ? decodeURIComponent(link.getAttribute('href').split('/recipe/')[1]) : '-';
              }
            });
            let s=0;
            ['breakfast','lunch','dinner'].forEach(m=>{
              const nm=rowDayMeals[m];
              if(nm && nm!=='-' && window.RECIPES_KCAL[nm]) s+= window.RECIPES_KCAL[nm];
            });
            dayRowKcal.textContent = s;
          }
        } catch(e){ /* ignore */ }
      }
    });
  });
}


// ---------- Delete meal (set slot to '-') ----------
async function deleteMeal(day, meal){
  try {
    // Determine current week/year
    let week = window.CURRENT_WEEK;
    let year = window.CURRENT_YEAR;
    if(!year){
      const statsPanel = document.getElementById('statsPanel');
      if(statsPanel){ year = statsPanel.getAttribute('data-year'); }
    }
    if(!week){
      const statsPanel = document.getElementById('statsPanel');
      if(statsPanel){ week = statsPanel.getAttribute('data-week'); }
    }
    if(!week){
      const body = document.body;
      week = body.getAttribute('data-week');
      year = year || body.getAttribute('data-year');
    }
    if(!week || !year){
      console.warn('Cannot delete meal: missing week/year');
      return;
    }
    const fd = new FormData();
    fd.append('day', day);
    fd.append('meal', meal);
    fd.append('recipe', '-');
    fd.append('week', week);
    fd.append('year', year);
    // Optimistic UI update
    const slot = document.getElementById(`slot-${day}-${meal}`);
    if(slot) slot.textContent='-';
    // Rebuild buttons to show only Add now (fix stale Delete button)
    adjustMealButtons(day, meal, '-');
    // Recompute calories for the day optimistically
    try {
      const kcalCell = document.getElementById(`${day}-kcal`);
      if(kcalCell){
        let sum=0; ['breakfast','lunch','dinner'].forEach(m=>{
          if(m===meal) return; // deleted one becomes zero
          const sp = document.getElementById(`slot-${day}-${m}`);
          if(!sp) return;
          const a = sp.querySelector('a');
            if(a){
              const rec = decodeURIComponent(a.getAttribute('href').split('/recipe/')[1]);
              if(window.RECIPES_KCAL && window.RECIPES_KCAL[rec]) sum += window.RECIPES_KCAL[rec];
            }
        });
        kcalCell.textContent = sum;
      }
    } catch(e){/* ignore */}
    const resp = await fetch('/update_meal', { method:'POST', body: fd });
    // After server update, re-fetch full week to stay in sync
    const monday = window.CURRENT_MONDAY_YMD;
    if(monday){
      try {
        const r2 = await fetch(`/get_week?start=${encodeURIComponent(monday)}`, {cache:'no-store'});
        if(r2.ok){
          const json = await r2.json();
          updateTable(json);
        }
      } catch(e){ console.warn('Delete refresh failed', e); }
    }
    if(typeof window.refreshNutritionPanel === 'function') window.refreshNutritionPanel();
    refreshShoppingListBadge(week);
  } catch(err){
    console.error('deleteMeal failed', err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  hookMealForms();
  refreshShoppingListBadge();
});

// If later the tbody gets regenerated (e.g., selectWeek), re-attach hooks
const observer = new MutationObserver((mutList) => {
  for(const m of mutList){
    if(m.type === 'childList'){
      hookMealForms();
    }
  }
});
observer.observe(document.body, {subtree:true, childList:true});

// ====== COOK PANEL LOGIC ======
(function(){
  // We'll define a safe stub first so clicks before init don't break
  if(!window.openCookPanel){
    window.openCookPanel = function(){ console.warn('Cook panel not ready yet'); };
  }
  function initCookPanel(){
    const panel = document.getElementById('cookPanel');
    if(!panel){
      return; // markup still not present (unlikely after DOMContentLoaded, but safe)
    }
    const tbody = document.getElementById('cookIngTbody');
    const finishBtn = document.getElementById('cookPanelFinish');
    const cancelBtn = document.getElementById('cookPanelCancel');
    const closeBtn = document.getElementById('cookPanelClose');
    const msgDiv = document.getElementById('cookPanelMsg');
    const titleEl = document.getElementById('cookPanelTitle');

    function showPanel(){ panel.style.display='flex'; }
    function hidePanel(){ panel.style.display='none'; if(tbody) tbody.innerHTML=''; if(msgDiv){ msgDiv.style.display='none'; msgDiv.textContent=''; } }
    if(cancelBtn) cancelBtn.addEventListener('click', hidePanel);
    if(closeBtn) closeBtn.addEventListener('click', hidePanel);

    async function loadSlotRecipe(day, meal){
      let week = window.CURRENT_WEEK;
      let year = window.CURRENT_YEAR;
      if(!week || !year){
        const body = document.body;
        week = week || body.getAttribute('data-week');
        year = year || body.getAttribute('data-year');
      }
      if(!week || !year) throw new Error('Missing week/year');
      const url = `/api/plan/slot-recipe?day=${encodeURIComponent(day)}&meal=${encodeURIComponent(meal)}&week=${week}&year=${year}`;
      const resp = await fetch(url, {cache:'no-store'});
      if(!resp.ok) throw new Error(`Slot recipe fetch failed: ${resp.status}`);
      return resp.json();
    }

    window.openCookPanel = async function(day, meal){
      if(!tbody) return;
      try {
        if(titleEl) titleEl.textContent = `Cook recipe for ${day} - ${meal}`;
        tbody.innerHTML = '<tr><td colspan="3" style="padding:10px;font-size:.75rem;">Loading...</td></tr>';
        showPanel();
        const data = await loadSlotRecipe(day, meal);
        if(data.already_cooked){
          tbody.innerHTML = `<tr><td colspan=3 style="padding:10px; font-size:.75rem; color:green;">Already cooked: ${data.name}</td></tr>`;
          if(finishBtn) finishBtn.disabled = true;
          return;
        }
        if(finishBtn) finishBtn.disabled = false;
        const ings = data.ingredients || [];
        if(!ings.length){
          tbody.innerHTML = '<tr><td colspan=3 style="padding:10px;font-size:.75rem;">No ingredients listed.</td></tr>';
        } else {
          tbody.innerHTML = '';
          ings.forEach(ing => {
            const tr = document.createElement('tr');
            const qty = ing.default_quantity ?? 0;
            tr.innerHTML = `<td>${ing.name}</td>`+
              `<td><input type=\"number\" name=\"quantity\" data-name=\"${ing.name}\" data-orig=\"${qty}\" value=\"${qty}\" min=\"0\" style=\"width:80px;\"></td>`+
              `<td>${ing.unit || ''}</td>`;
            tbody.appendChild(tr);
          });
        }
        if(finishBtn){
          finishBtn.dataset.day = day;
            finishBtn.dataset.meal = meal;
        }
      } catch(e){
        tbody.innerHTML = `<tr><td colspan=3 style=\"padding:10px;font-size:.75rem;color:red;\">Error loading: ${e.message}</td></tr>`;
        if(finishBtn) finishBtn.disabled = true;
      }
    };

    async function cookSubmit(){
      if(!finishBtn || !tbody) return;
      const day = finishBtn.dataset.day;
      const meal = finishBtn.dataset.meal;
      if(!day || !meal) return;
      let week = window.CURRENT_WEEK;
      let year = window.CURRENT_YEAR;
      if(!week || !year){
        const body = document.body;
        week = week || body.getAttribute('data-week');
        year = year || body.getAttribute('data-year');
      }
      const overrides = [];
      tbody.querySelectorAll('input[name="quantity"]').forEach(inp => {
        const name = inp.dataset.name;
        let val = parseInt(inp.value || '0', 10);
        if(Number.isNaN(val) || val < 0) val = 0;
        overrides.push({ name, used_quantity: val });
      });
      const payload = { day, meal, week: parseInt(week,10), year: parseInt(year,10), overrides };
      finishBtn.disabled = true;
      if(msgDiv){
        msgDiv.style.display='block';
        msgDiv.style.background='#fff3cd';
        msgDiv.style.color='#8a6d3b';
        msgDiv.textContent='Cooking...';
      }
      try {
        const resp = await fetch('/api/cook', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
        if(!resp.ok){
          const errTxt = await resp.text();
          throw new Error(errTxt || resp.status);
        }
        if(msgDiv){
          msgDiv.style.background='#e8f5e9';
          msgDiv.style.color='#256029';
          msgDiv.textContent='Success! Updating plan...';
        }
        const monday = window.CURRENT_MONDAY_YMD;
        if(monday){
          try {
            const r2 = await fetch(`/get_week?start=${encodeURIComponent(monday)}`, {cache:'no-store'});
            if(r2.ok){ const j = await r2.json(); updateTable(j); }
          } catch(e){ /* ignore */ }
        }
        if(typeof window.refreshNutritionPanel === 'function') window.refreshNutritionPanel();
        setTimeout(()=> hidePanel(), 900);
      } catch(e){
        if(msgDiv){
          msgDiv.style.background='#ffebee';
          msgDiv.style.color='#b71c1c';
          msgDiv.textContent = 'Error: ' + (e.message||'cook failed');
        }
        finishBtn.disabled = false;
      }
    }
    if(finishBtn) finishBtn.addEventListener('click', cookSubmit);

    // Event delegation for any cook button
    document.addEventListener('click', (e)=>{
      const btn = e.target && e.target.closest('.cook-btn');
      if(btn){ const day = btn.dataset.day; const meal = btn.dataset.meal; if(day && meal) window.openCookPanel(day, meal); }
    });
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initCookPanel);
  } else {
    initCookPanel();
  }
})();
