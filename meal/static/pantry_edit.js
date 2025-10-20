// Refactored editing: separate expandable form row with vertical fields & labels

document.addEventListener('DOMContentLoaded', () => {
    const ingTbody = document.getElementById('ingredients-body');
    const cookedTbody = document.getElementById('cooked-body');
    const addIngBtn = document.getElementById('add-ingredient');
    const addCookedBtn = document.getElementById('add-cooked');
    const toastContainer = document.getElementById('toast-container');

    let current = null; // { sourceRow, formRow, kind, mode, originalName }

    function showToast(message, type='success', timeout=2500){
        const t = document.createElement('div');
        t.className = 'toast ' + type;
        t.textContent = message;
        toastContainer.appendChild(t);
        setTimeout(()=> t.classList.add('hide'), timeout);
        setTimeout(()=> t.remove(), timeout+400);
    }

    function validateIngredient(data){
        if(!data.name) return 'Name required';
        if(isNaN(data.default_quantity)) return 'Quantity must be number';
        if(!data.unit) return 'Unit required';
        if(!/^\d{2}-\d{2}-\d{4}$/.test(data.data_expirare)) return 'Expiration format DD-MM-YYYY';
        const tag = (data.tags && data.tags[0]) || '';
        if(!tag) return 'Tag required';
        return null;
    }
    function validateCooked(data){
        if(!data.name) return 'Name required';
        if(!/^\d{2}-\d{2}-\d{4}$/.test(data.date_cooked)) return 'Date format DD-MM-YYYY';
        if(isNaN(data.servings)) return 'Servings must be number';
        if(!data.unit) return 'Unit required';
        return null;
    }

    function closeCurrent(){
        if(!current) return;
        current.sourceRow.classList.remove('being-edited');
        current.formRow.remove();
        current = null;
    }

    function buildFormRow(kind, data, mode){
        const colCount = 5; // both tables have 5 columns incl. Actions
        const tr = document.createElement('tr');
        tr.className = 'edit-form-row';
        const td = document.createElement('td');
        td.colSpan = colCount;
        td.innerHTML = buildFormHTML(kind, data, mode);
        tr.appendChild(td);
        return tr;
    }

    // Allowed tags (ordered)
    const ALLOWED_TAGS = [
        'fruits','vegetables','meat-chicken','meat-beef','meat-pork','pasta','frozen','fish','seafood','dairy','cheese','condiment','baking','canned','grains','oil','sauce','spice','other'
    ];

    function buildFormHTML(kind, data, mode){
        if(kind==='ingredient'){
            const isoExp = toISODate(data.data_expirare||'');
            const currentTag = (data.tags && data.tags[0]) || '';
            const listForDatalist = ALLOWED_TAGS.slice();
            if(currentTag && !listForDatalist.includes(currentTag)) listForDatalist.splice(listForDatalist.length-1,0,currentTag);
            const datalist = `<datalist id="tag-options">${listForDatalist.map(t=>`<option value="${t}"></option>`).join('')}</datalist>`;
            return `
            <div class="edit-form">
              <div class="edit-field"><label>Name</label><input type="text" id="ef-name" value="${escapeHtml(data.name||'')}" /></div>
              <div class="edit-field"><label>Quantity</label><input type="number" id="ef-qty" value="${escapeHtml(data.default_quantity ?? '')}" /></div>
              <div class="edit-field"><label>Unit</label><input type="text" id="ef-unit" value="${escapeHtml(data.unit||'')}" /></div>
              <div class="edit-field"><label>Tag</label><input type="text" id="ef-tag" list="tag-options" value="${escapeHtml(currentTag)}" />${datalist}</div>
              <div class="edit-field"><label>Expiration (DD-MM-YYYY)</label><input type="date" id="ef-exp" value="${isoExp}" /></div>
              <div class="edit-actions">
                <button class="main-btn small save-btn">Save</button>
                <button class="main-btn small secondary cancel-btn">Cancel</button>
                <button class="main-btn small danger delete-btn">Delete</button>
              </div>
            </div>`;
        } else {
            const isoCooked = toISODate(data.date_cooked||'');
            return `
            <div class="edit-form">
              <div class="edit-field"><label>Name</label><input type="text" id="ef-name" value="${escapeHtml(data.name||'')}" /></div>
              <div class="edit-field"><label>Servings</label><input type="number" id="ef-servings" value="${escapeHtml(data.servings ?? '')}" /></div>
              <div class="edit-field"><label>Unit</label><input type="text" id="ef-unit" value="${escapeHtml(data.unit||'')}" /></div>
              <div class="edit-field"><label>Date Cooked (DD-MM-YYYY)</label><input type="date" id="ef-date" value="${isoCooked}" /></div>
              <div class="edit-actions">
                <button class="main-btn small save-btn">Save</button>
                <button class="main-btn small secondary cancel-btn">Cancel</button>
                <button class="main-btn small danger delete-btn">Delete</button>
              </div>
            </div>`;
        }
    }

    function escapeHtml(str){
        return String(str).replace(/[&<>"]+/g, s=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[s]));
    }

    function startEdit(row, kind, mode){
        // mode: 'edit' | 'add'
        if(current){
            if(current.sourceRow === row) return; // already editing this row
            closeCurrent();
        }
        row.classList.add('being-edited');
        const data = extractRowData(row, kind, mode);
        const formRow = buildFormRow(kind, data, mode);
        row.after(formRow);
        current = { sourceRow: row, formRow, kind, mode, originalName: data.name };
        autoFocusFirst(formRow);
        scrollIntoView(formRow);
    }

    function extractRowData(row, kind, mode){
        if(mode==='add'){
            return kind==='ingredient' ? { name:'', default_quantity:'', unit:'', data_expirare:'', tags:['other'] }
                                      : { name:'', date_cooked:'', servings:'', unit:'' };
        }
        if(kind==='ingredient'){
            return {
                name: row.querySelector('.name').textContent.trim(),
                default_quantity: row.querySelector('.qty').textContent.trim(),
                unit: row.querySelector('.unit').textContent.trim(),
                tags: [row.querySelector('.tags').textContent.trim() || 'other'],
                data_expirare: row.querySelector('.exp').textContent.trim()
            };
        } else {
            return {
                name: row.querySelector('.name').textContent.trim(),
                date_cooked: row.querySelector('.date').textContent.trim(),
                servings: row.querySelector('.servings').textContent.trim(),
                unit: row.querySelector('.unit').textContent.trim()
            };
        }
    }

    function gatherFormData(kind){
        if(kind==='ingredient'){
            let tagVal = document.getElementById('ef-tag').value.trim().toLowerCase();
            if(!ALLOWED_TAGS.includes(tagVal)) tagVal = 'other';
            return {
                name: document.getElementById('ef-name').value.trim(),
                default_quantity: Number(document.getElementById('ef-qty').value.trim()),
                unit: document.getElementById('ef-unit').value.trim(),
                tags: [tagVal],
                data_expirare: toDisplayDate(document.getElementById('ef-exp').value.trim())
            };
        } else {
            return {
                name: document.getElementById('ef-name').value.trim(),
                date_cooked: toDisplayDate(document.getElementById('ef-date').value.trim()),
                servings: Number(document.getElementById('ef-servings').value.trim()),
                unit: document.getElementById('ef-unit').value.trim()
            };
        }
    }

    function applyDataToRow(row, kind, data){
        if(kind==='ingredient'){
            row.querySelector('.name').textContent = data.name;
            row.querySelector('.qty').textContent = data.default_quantity;
            row.querySelector('.unit').textContent = data.unit;
            row.querySelector('.tags').textContent = (data.tags||[]).join(', ');
            row.querySelector('.exp').textContent = data.data_expirare;
        } else {
            row.querySelector('.name').textContent = data.name;
            row.querySelector('.date').textContent = data.date_cooked;
            row.querySelector('.servings').textContent = data.servings;
            row.querySelector('.unit').textContent = data.unit;
        }
        row.dataset.name = data.name;
    }

    function saveCurrent(){
        if(!current) return;
        const { kind, mode, originalName, sourceRow } = current;
        const data = gatherFormData(kind);
        const err = kind==='ingredient'? validateIngredient(data): validateCooked(data);
        if(err){ showToast(err,'error'); return; }
        const base = kind==='ingredient'? '/api/pantry/ingredient' : '/api/pantry/cooked';
        const method = mode==='add' ? 'POST' : 'PUT';
        const url = mode==='add' ? base : `${base}/${encodeURIComponent(originalName)}`;
        fetch(url,{ method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(data) })
            .then(r=>{ if(!r.ok) return r.json().then(j=>{ throw new Error(j.detail||'Save failed');}); return r.json(); })
            .then(()=>{
                applyDataToRow(sourceRow, kind, data);
                showToast('Saved successfully');
                closeCurrent();
            })
            .catch(e=> showToast(e.message,'error'));
    }

    function deleteCurrent(){
        if(!current) return;
        const { kind, mode, sourceRow } = current;
        if(mode==='add'){ sourceRow.remove(); closeCurrent(); return; }
        const name = sourceRow.dataset.name;
        if(!confirm(`Delete ${kind} '${name}'?`)) return;
        const base = kind==='ingredient'? '/api/pantry/ingredient' : '/api/pantry/cooked';
        fetch(`${base}/${encodeURIComponent(name)}`, { method:'DELETE' })
            .then(r=>{ if(!r.ok) return r.json().then(j=>{ throw new Error(j.detail||'Delete failed');}); })
            .then(()=>{ sourceRow.remove(); showToast('Deleted'); closeCurrent(); })
            .catch(e=> showToast(e.message,'error'));
    }

    function addRow(kind){
        const tbody = kind==='ingredient'? ingTbody : cookedTbody;
        const tr = document.createElement('tr');
        tr.dataset.kind = kind;
        tr.dataset.name = '';
        if(kind==='ingredient'){
            tr.innerHTML = `<td class='val name'></td><td class='val qty'></td><td class='val unit'></td><td class='val tags'></td><td class='val exp'></td><td class='actions'><button class='main-btn small edit-btn'>Edit</button> <button class='main-btn small delete-btn danger'>Delete</button></td>`;
        } else {
            tr.innerHTML = `<td class='val name'></td><td class='val servings'></td><td class='val unit'></td><td class='val date'></td><td class='actions'><button class='main-btn small edit-btn'>Edit</button> <button class='main-btn small delete-btn danger'>Delete</button></td>`;
        }
        tbody.appendChild(tr);
        startEdit(tr, kind, 'add');
    }

    function autoFocusFirst(formRow){
        const inp = formRow.querySelector('input');
        if(inp) setTimeout(()=>inp.focus(), 30);
    }

    function scrollIntoView(el){
        const rect = el.getBoundingClientRect();
        if(rect.top < 110 || rect.bottom > window.innerHeight){
            window.scrollBy({ top: rect.top - 100, behavior: 'smooth' });
        }
    }

    function toISODate(ddmmyyyy){
        if(!/^\d{2}-\d{2}-\d{4}$/.test(ddmmyyyy)) return '';
        const [d,m,y] = ddmmyyyy.split('-');
        return `${y}-${m}-${d}`;
    }
    function toDisplayDate(iso){
        if(!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
        const [y,m,d] = iso.split('-');
        return `${d}-${m}-${y}`;
    }

    function collectDistinctTags(){
        const set = new Set();
        ingTbody.querySelectorAll('tr').forEach(r=>{
            const t = (r.querySelector('.tags')?.textContent||'').trim();
            if(t) set.add(t);
        });
        return Array.from(set).sort((a,b)=>a.localeCompare(b));
    }

    const tagFilterSelect = document.getElementById('ing-filter-tag');

    function buildTagFilterOptions(){
        if(!tagFilterSelect) return;
        const current = tagFilterSelect.value || '__all__';
        const existing = collectDistinctTags();
        const ordered = [];
        ALLOWED_TAGS.forEach(tag=>{ if(tag==='other') return; ordered.push(tag); });
        existing.forEach(t=>{ if(!ALLOWED_TAGS.includes(t)) ordered.push(t); });
        ordered.push('other');
        const seen = new Set();
        const optionsHtml = ordered.filter(t=>{ if(seen.has(t)) return false; seen.add(t); return true; })
                                   .map(t=>`<option value="${t}">${t}</option>`).join('');
        tagFilterSelect.innerHTML = '<option value="__all__">All tags</option>' + optionsHtml;
        if([...tagFilterSelect.options].some(o=>o.value===current)) tagFilterSelect.value = current; else tagFilterSelect.value='__all__';
    }

    function applyTagFilter(){
        if(!tagFilterSelect) return;
        const sel = tagFilterSelect.value;
        ingTbody.querySelectorAll('tr').forEach(r=>{
            if(sel==='__all__') { r.style.display=''; return; }
            const t = (r.querySelector('.tags')?.textContent||'').trim();
            r.style.display = (t===sel) ? '' : 'none';
        });
    }

    if(tagFilterSelect){
        tagFilterSelect.addEventListener('change', ()=>{ applyTagFilter(); });
        buildTagFilterOptions();
    }

    const originalApplyDataToRow = applyDataToRow;
    applyDataToRow = function(row, kind, data){
        originalApplyDataToRow(row, kind, data);
        if(kind==='ingredient') buildTagFilterOptions();
    };

    const originalAddRow = addRow;
    addRow = function(kind){
        originalAddRow(kind);
        if(kind==='ingredient') buildTagFilterOptions();
    };

    document.addEventListener('click', e=>{
        const btn = e.target.closest('button');
        if(!btn) return;
        if(btn === addIngBtn){ addRow('ingredient'); return; }
        if(btn === addCookedBtn){ addRow('cooked'); return; }
        if(btn.classList.contains('edit-btn')){
            const row = btn.closest('tr');
            startEdit(row, row.dataset.kind, 'edit');
            return;
        }
        if(btn.classList.contains('save-btn')){ saveCurrent(); return; }
        if(btn.classList.contains('cancel-btn')){ closeCurrent(); return; }
        if(btn.classList.contains('delete-btn')){
            if(current && btn.closest('.edit-form')){ deleteCurrent(); }
            else {
                const row = btn.closest('tr');
                const kind = row.dataset.kind;
                const name = row.dataset.name;
                if(!confirm(`Delete ${kind} '${name}'?`)) return;
                const base = kind==='ingredient'? '/api/pantry/ingredient' : '/api/pantry/cooked';
                fetch(`${base}/${encodeURIComponent(name)}`, { method:'DELETE' })
                    .then(r=>{ if(!r.ok) return r.json().then(j=>{ throw new Error(j.detail||'Delete failed');}); })
                    .then(()=>{ row.remove(); showToast('Deleted'); if(kind==='ingredient') { buildTagFilterOptions(); applyTagFilter(); } })
                    .catch(err=> showToast(err.message,'error'));
            }
            return;
        }
    });

    if(tagFilterSelect) applyTagFilter();

    document.addEventListener('keydown', e=>{
        if(!current) return;
        if(e.key==='Escape'){ closeCurrent(); }
        else if(e.key==='Enter'){
            if(document.activeElement && current.formRow.contains(document.activeElement)){
                e.preventDefault();
                saveCurrent();
            }
        }
    });
});
