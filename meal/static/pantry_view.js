// pantry_view.js - filtering & sorting for My Pantry (read-only page)
(function(){
    document.addEventListener('DOMContentLoaded', () => {
        const ingTbody = document.getElementById('view-ingredients-body');
        const cookedTbody = document.getElementById('view-cooked-body');
        if(!ingTbody || !cookedTbody) return; // not on this page

        const tagFilter = document.getElementById('view-ing-filter-tag');
        const ingSort = document.getElementById('view-ing-sort');
        const cookedSort = document.getElementById('view-cooked-sort');
        const tagOrderBtn = document.getElementById('view-ing-sort-tag-order');
        const container = document.querySelector('.view-context');
        const allowedTags = container?.getAttribute('data-allowed-tags')?.split(',')?.map(s=>s.trim()) || [];

        // ===== Filtering & Sorting =====
        function collectTags(){
            const set = new Set();
            ingTbody.querySelectorAll('tr').forEach(tr => {
                const t = (tr.querySelector('.tag')?.textContent || '').trim();
                if(t) set.add(t);
            });
            return Array.from(set).sort((a,b)=>a.localeCompare(b));
        }

        function buildTagOptions(){
            if(!tagFilter) return;
            const current = tagFilter.value || '__all__';
            const existing = collectTags();
            const ordered = [];
            allowedTags.forEach(t=>{ if(t==='other') return; ordered.push(t); });
            existing.forEach(t=>{ if(!allowedTags.includes(t)) ordered.push(t); });
            if(allowedTags.includes('other')) ordered.push('other');
            const seen = new Set();
            const optionsHtml = ordered.filter(t=>{ if(seen.has(t)) return false; seen.add(t); return true; })
                                       .map(t=>`<option value="${t}">${t}</option>`).join('');
            tagFilter.innerHTML = '<option value="__all__">All tags</option>' + optionsHtml;
            if([...tagFilter.options].some(o=>o.value===current)) tagFilter.value = current; else tagFilter.value='__all__';
        }

        function parseDisplayDate(ddmmyyyy){
            if(!/^\d{2}-\d{2}-\d{4}$/.test(ddmmyyyy)) return null;
            const [d,m,y] = ddmmyyyy.split('-').map(Number);
            return new Date(y, m-1, d).getTime();
        }

        function applyIngredientSort(){
            if(!ingSort) return;
            const crit = ingSort.value;
            const rows = Array.from(ingTbody.querySelectorAll('tr'));
            rows.sort((a,b)=>{
                if(crit === 'expiration'){
                    const da = parseDisplayDate((a.querySelector('.exp')?.textContent||'').trim());
                    const db = parseDisplayDate((b.querySelector('.exp')?.textContent||'').trim());
                    if(da===db) return (a.querySelector('.name')?.textContent||'').localeCompare(b.querySelector('.name')?.textContent||'');
                    if(da===null) return 1; if(db===null) return -1;
                    return da - db;
                }
                return (a.querySelector('.name')?.textContent||'').localeCompare(b.querySelector('.name')?.textContent||'');
            });
            rows.forEach(r=>ingTbody.appendChild(r));
        }

        function applyIngredientFilter(){
            if(!tagFilter) return;
            const sel = tagFilter.value;
            ingTbody.querySelectorAll('tr').forEach(r => {
                if(sel==='__all__') r.style.display='';
                else {
                    const t = (r.querySelector('.tag')?.textContent||'').trim();
                    r.style.display = (t===sel) ? '' : 'none';
                }
            });
        }

        function applyCookedSort(){
            if(!cookedSort) return;
            const crit = cookedSort.value;
            const rows = Array.from(cookedTbody.querySelectorAll('tr'));
            rows.sort((a,b)=>{
                if(crit==='servings'){
                    const sa = parseFloat(a.querySelector('.servings')?.textContent||'0');
                    const sb = parseFloat(b.querySelector('.servings')?.textContent||'0');
                    if(sa !== sb) return sa - sb;
                } else if(crit==='date'){
                    const da = parseDisplayDate((a.querySelector('.date')?.textContent||'').trim());
                    const db = parseDisplayDate((b.querySelector('.date')?.textContent||'').trim());
                    if(da!==db) return (da||0)-(db||0);
                }
                return (a.querySelector('.name')?.textContent||'').localeCompare(b.querySelector('.name')?.textContent||'');
            });
            rows.forEach(r=>cookedTbody.appendChild(r));
        }

        function sortIngredientsByTagOrder(){
            if(!allowedTags.length) return;
            const rows = Array.from(ingTbody.querySelectorAll('tr'));
            rows.sort((a,b)=>{
                const ta = (a.querySelector('.tag')?.textContent||'').trim().toLowerCase();
                const tb = (b.querySelector('.tag')?.textContent||'').trim().toLowerCase();
                const ia = allowedTags.indexOf(ta);
                const ib = allowedTags.indexOf(tb);
                if(ia!==-1 || ib!==-1){
                    if(ia===-1 && ib!==-1) return 1;
                    if(ib===-1 && ia!==-1) return -1;
                    if(ia!==ib) return ia - ib;
                } else {
                    if(ta!==tb) return ta.localeCompare(tb);
                }
                return (a.querySelector('.name')?.textContent||'').localeCompare(b.querySelector('.name')?.textContent||'');
            });
            rows.forEach(r=>ingTbody.appendChild(r));
        }

        // ===== NEW: Expiration / cooked indicator =====
        function markExpiringSoon() {
    const today = new Date();
    today.setHours(0, 0, 0, 0); // normalizează ora
    const MS_PER_DAY = 1000 * 60 * 60 * 24;

    function daysBetween(d1, d2) {
        const utc1 = Date.UTC(d1.getFullYear(), d1.getMonth(), d1.getDate());
        const utc2 = Date.UTC(d2.getFullYear(), d2.getMonth(), d2.getDate());
        return Math.floor((utc2 - utc1) / MS_PER_DAY);
    }

    // Ingrediente
    ingTbody.querySelectorAll('.exp').forEach(td => {
        const text = td.textContent.trim();
        if (!/^\d{2}-\d{2}-\d{4}$/.test(text)) return;
        const [d, m, y] = text.split('-').map(Number);
        const expDate = new Date(y, m - 1, d);
        expDate.setHours(0, 0, 0, 0);
        const diff = daysBetween(today, expDate);
        td.classList.remove('expiring-soon');
        if (diff >= 0 && diff <= 10) {
            td.classList.add('expiring-soon');
            td.title = `Expiring in ${diff} day${diff === 1 ? '' : 's'}`;
        }
    });

    // Rețete (gătite în ultimele 10 zile)
    cookedTbody.querySelectorAll('.date').forEach(td => {
        const text = td.textContent.trim();
        if (!/^\d{2}-\d{2}-\d{4}$/.test(text)) return;
        const [d, m, y] = text.split('-').map(Number);
        const cookedDate = new Date(y, m - 1, d);
        cookedDate.setHours(0, 0, 0, 0);
        const diff = daysBetween(cookedDate, today);
        td.classList.remove('expiring-soon');
        if (diff >= 0 && diff <= 10) {
            td.classList.add('expiring-soon');
            td.title = `Cooked ${diff} day${diff === 1 ? '' : 's'} ago`;
        }
    });
}


        // ===== Init setup =====
        [tagFilter, ingSort, cookedSort].forEach(sel=>{
            if(sel) sel.classList.add('control-lg');
        });

        buildTagOptions();
        applyIngredientSort();
        applyIngredientFilter();
        applyCookedSort();
        markExpiringSoon(); // 👈 aici se aplică marcajul

        // ===== Events =====
        if(tagFilter) tagFilter.addEventListener('change', ()=> { applyIngredientFilter(); markExpiringSoon(); });
        if(ingSort) ingSort.addEventListener('change', ()=> { applyIngredientSort(); applyIngredientFilter(); markExpiringSoon(); });
        if(cookedSort) cookedSort.addEventListener('change', ()=> { applyCookedSort(); markExpiringSoon(); });
        if(tagOrderBtn) tagOrderBtn.addEventListener('click', ()=>{ sortIngredientsByTagOrder(); applyIngredientFilter(); markExpiringSoon(); });
    });
})();
