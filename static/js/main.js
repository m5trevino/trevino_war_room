let jobList = [], currentJobId = null, currentTab = 'NEW';
let focusMode = 'LIST'; 
let tagCursorIndex = 0; 
let currentTags = []; 
let personas = [];

// INITIALIZATION
document.addEventListener('DOMContentLoaded', () => {
    switchTab('NEW');
    fetchPersonas();
});

async function fetchPersonas() {
    try {
        personas = await fetch('/api/personas').then(r=>r.json());
        const sel = document.getElementById('persona-select');
        if(sel && personas.length > 0) {
            sel.innerHTML = personas.map((p, i) => `<option value="${i}">${p.name}</option>`).join('');
            loadPersona();
        }
    } catch(e) { console.log("Persona fetch failed"); }
}

function loadPersona() {
    const sel = document.getElementById('persona-select');
    if(!sel) return;
    const idx = sel.value;
    const p = personas[idx];
    if(p) {
        document.getElementById('sys-prompt-area').value = p.system_prompt;
        document.getElementById('model-temp').value = p.temperature;
        document.getElementById('model-select').value = p.model;
    }
}

function toggleFactoryConfig() {
    const body = document.getElementById('config-body');
    const icon = document.getElementById('config-toggle-icon');
    if(body.style.display === 'none') {
        body.style.display = 'block';
        icon.innerText = '-';
    } else {
        body.style.display = 'none';
        icon.innerText = '+';
    }
}

async function loadJobs() {
    let statusQuery = currentTab;
    if (currentTab === 'REFINERY' || currentTab === 'FACTORY') statusQuery = 'APPROVED';
    if (currentTab === 'DELIVERED') statusQuery = 'DELIVERED'; 

    try {
        const res = await fetch(`/api/jobs?status=${statusQuery}`);
        jobList = await res.json();
    } catch (e) { jobList = []; }

    renderHeader();
    renderList();
    
    focusMode = 'LIST';
    tagCursorIndex = 0;
    updateFocusVisuals();
    
    if(jobList.length > 0) selectJob(jobList[0].id);
    else {
        clearPanes();
        const dBox = document.getElementById('std-desc-box');
        if(dBox) dBox.innerHTML = "SECTOR CLEAR.";
    }
    
    await updateStats();
    updateControls();
}

async function updateStats() {
    try {
        const s = await fetch('/api/status').then(r=>r.json());
        document.getElementById('s_scraped').textContent = s.session.scraped||0;
        document.getElementById('s_approved').textContent = s.session.approved||0;
        document.getElementById('s_denied').textContent = s.session.denied||0;
        document.getElementById('a_scraped').textContent = s.all_time.scraped||0;
        document.getElementById('a_approved').textContent = s.all_time.approved||0;
        document.getElementById('a_denied').textContent = s.all_time.denied||0;
    } catch(e) { console.log("Stats update failed"); }
}

function clearPanes() {
    ['std-desc-box', 'std-tags', 'factory-desc', 'refinery-new-tags', 'incinerator-stage', 'resume-content'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.innerHTML = "";
    });
}

function renderHeader() {
    const h = document.getElementById('grid-header');
    if (currentTab === 'NEW') {
        h.style.gridTemplateColumns = "50px 70px 80px 1fr 1fr";
        h.innerHTML = `<div>SCR</div><div>PAY</div><div>LOC</div><div>ROLE</div><div>CORP</div>`;
    } else if (currentTab === 'DENIED') {
        h.style.gridTemplateColumns = "1fr 1fr 80px 80px 80px";
        h.innerHTML = `<div>TITLE</div><div>CORP</div><div>PAY</div><div>LOC</div><div>TYPE</div>`;
    } else {
        h.style.gridTemplateColumns = "30px 1fr 1fr 0.8fr 50px 50px 50px";
        h.innerHTML = `<div><input type="checkbox" onclick="toggleAll(this)"></div><div>TITLE</div><div>CORP</div><div>CITY</div><div>APPR</div><div>AI</div><div>PDF</div>`;
    }
}

function renderList() {
    const c = document.getElementById('list-container');
    c.innerHTML = jobList.map(j => {
        let cols = '';
        if (currentTab === 'NEW') {
            cols = `
                <div style="color:${j.score>=50?'#ffd700':'#666'}">${j.score}</div>
                <div style="color:#00e676">${j.pay}</div>
                <div style="color:#8be9fd">${j.city}</div>
                <div style="font-weight:bold;white-space:nowrap;overflow:hidden">${j.title}</div>
                <div style="color:#ffd700;white-space:nowrap;overflow:hidden">${j.company}</div>
            `;
            return `<div class="job-row" id="row-${j.id}" style="grid-template-columns: 50px 70px 80px 1fr 1fr;" onclick="selectJob('${j.id}')">${cols}</div>`;
        } else if (currentTab === 'DENIED') {
            const type = j.status === 'AUTO_DENIED' ? 'AUTO' : 'MAN';
            cols = `
                <div style="font-weight:bold;white-space:nowrap;overflow:hidden">${j.title}</div>
                <div style="color:#ffd700;white-space:nowrap;overflow:hidden">${j.company}</div>
                <div style="color:#00e676">${j.pay}</div>
                <div style="color:#8be9fd">${j.city}</div>
                <div style="color:#f00">${type}</div>
            `;
            return `<div class="job-row" id="row-${j.id}" style="grid-template-columns: 1fr 1fr 80px 80px 80px;" onclick="selectJob('${j.id}')">${cols}</div>`;
        } else {
            const hasAI = j.has_ai ? '<span style="color:#00e676">✔</span>' : '<span style="color:#666">✘</span>';
            const hasPDF = j.has_pdf ? '<span style="color:#00e676">✔</span>' : '<span style="color:#666">✘</span>';
            cols = `
                <div onclick="event.stopPropagation()"><input type="checkbox" class="job-check" value="${j.id}"></div>
                <div style="font-weight:bold;white-space:nowrap;overflow:hidden">${j.title}</div>
                <div style="color:#ffd700;white-space:nowrap;overflow:hidden">${j.company}</div>
                <div style="color:#8be9fd">${j.city}</div>
                <div style="color:#00e676">✔</div>
                <div>${hasAI}</div>
                <div>${hasPDF}</div>
            `;
            return `<div class="job-row" id="row-${j.id}" style="grid-template-columns: 30px 1fr 1fr 0.8fr 50px 50px 50px;" onclick="selectJob('${j.id}')">${cols}</div>`;
        }
    }).join('');
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(t => {
        if(t.innerText.includes(tab) || (tab === 'NEW' && t.innerText === 'INCOMING')) t.classList.add('active');
        if(tab === 'DENIED' && t.innerText === 'GRAVEYARD') t.classList.add('active');
        if(tab === 'DELIVERED' && t.innerText === 'ARMORY') t.classList.add('active');
    });
    
    ['standard-view', 'refinery-view', 'factory-view', 'product-view', 'incinerator-view'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.style.display = 'none';
    });

    clearPanes();

    if (tab === 'NEW') document.getElementById('standard-view').style.display = 'flex';
    if (tab === 'DENIED') document.getElementById('incinerator-view').style.display = 'flex';
    if (tab === 'REFINERY') document.getElementById('refinery-view').style.display = 'flex';
    if (tab === 'FACTORY') document.getElementById('factory-view').style.display = 'flex';
    if (tab === 'DELIVERED') document.getElementById('product-view').style.display = 'flex';

    loadJobs();
}

function updateControls() {
    document.querySelectorAll('#controls button').forEach(b => b.style.display = 'none');
    
    if (currentTab === 'NEW') {
        document.getElementById('btn-a').style.display = 'inline-block';
        document.getElementById('btn-d').style.display = 'inline-block';
    }
    if (currentTab === 'DENIED') {
         document.getElementById('btn-r').style.display = 'inline-block';
    }
    if (currentTab === 'FACTORY') {
        document.getElementById('btn-p').style.display = 'inline-block';
        document.getElementById('btn-psel').style.display = 'inline-block';
        document.getElementById('btn-pall').style.display = 'inline-block';
    }
    if (currentTab === 'DELIVERED') {
        document.getElementById('btn-open-pdf').style.display = 'inline-block';
    }
}

async function selectJob(id) {
    currentJobId = id;
    document.querySelectorAll('.job-row').forEach(r=>r.classList.remove('active'));
    document.getElementById('row-'+id)?.classList.add('active');
    
    tagCursorIndex = 0;

    if (currentTab === 'DELIVERED') {
         const a = await fetch(`/api/get_artifact?id=${id}`).then(r=>r.json());
         document.getElementById('resume-content').innerText = a.content;
         return;
    }

    const d = await fetch(`/api/get_job_details?id=${id}`).then(r=>r.json());
    const job = jobList.find(j=>j.id===id);

    if (currentTab === 'NEW') {
        document.getElementById('std-desc-box').innerHTML = d.description;
        document.getElementById('std-tags').innerHTML = d.skills.map(s => 
            `<span class="skill-tag ${s.category === 'new' ? 'new' : 'sorted'}">${s.name}</span>`
        ).join('');
    }
    
    if (currentTab === 'REFINERY') {
        renderRefinery(d.skills);
    }

    if (currentTab === 'DENIED') {
        renderIncinerator(job, d.skills);
    }
    
    if (currentTab === 'FACTORY') {
        document.getElementById('factory-desc').innerHTML = d.description;
        const term = document.getElementById('factory-terminal');
        if(term.innerText.trim() === "") term.innerText = "> SYSTEM READY.";
        term.innerText += `\n> TARGET LOCKED: ${id}`;
    }
    
    updateVisualCursor();
}

function renderRefinery(skills) {
    if(skills) {
        const unsorted = skills.filter(s => s.category === 'new');
        currentTags = unsorted; 
    }
    const container = document.getElementById('refinery-new-tags');
    if(container) {
        container.innerHTML = currentTags.map((t, idx) => 
            `<span id="tag-${idx}" class="skill-tag new">${t.name}</span>`
        ).join('');
    }
    if(skills) {
        const q = skills.filter(s => s.category === 'qualifications');
        const s = skills.filter(s => s.category === 'skills');
        const b = skills.filter(s => s.category === 'benefits');
        document.querySelector('#col-q').innerHTML = `<div class="col-header">QUALS</div>` + q.map(t=>`<div class="skill-tag q">${t.name}</div>`).join('');
        document.querySelector('#col-s').innerHTML = `<div class="col-header">SKILLS</div>` + s.map(t=>`<div class="skill-tag s">${t.name}</div>`).join('');
        document.querySelector('#col-b').innerHTML = `<div class="col-header">BENEFITS</div>` + b.map(t=>`<div class="skill-tag b">${t.name}</div>`).join('');
    }
}

function renderIncinerator(job, skills) {
    if(job && skills) {
        const debris = [];
        debris.push({type: 'company', val: job.company, label: `CORP: ${job.company}`});
        debris.push({type: 'title', val: job.title, label: `ROLE: ${job.title}`});
        skills.forEach(s => debris.push({type: 'tag', val: s.name, label: s.name}));
        currentTags = debris;
    }
    const container = document.getElementById('incinerator-stage');
    if(container) {
        container.innerHTML = currentTags.map((item, idx) => 
            `<span id="tag-${idx}" class="chip ${item.type}">${item.label}</span>`
        ).join('');
    }
}

function updateVisualCursor() {
    document.querySelectorAll('.active-tag').forEach(e => e.classList.remove('active-tag'));
    if (focusMode === 'TAGS' && currentTags.length > 0) {
        if (tagCursorIndex >= currentTags.length) tagCursorIndex = Math.max(0, currentTags.length - 1);
        if (tagCursorIndex < 0) tagCursorIndex = 0;
        const el = document.getElementById(`tag-${tagCursorIndex}`);
        if (el) {
            el.classList.add('active-tag');
            el.scrollIntoView({block: 'nearest', inline: 'nearest'});
        }
    }
    updateFocusVisuals();
}

function updateFocusVisuals() {
    const left = document.getElementById('job-list-pane');
    const right = document.getElementById('detail-pane');
    left.style.boxShadow = 'none'; left.style.zIndex = '0';
    right.style.boxShadow = 'none'; right.style.zIndex = '0';
    if (focusMode === 'LIST') left.style.boxShadow = 'inset 0 0 0 2px var(--green)';
    else right.style.boxShadow = 'inset 0 0 0 2px var(--gold)';
}

async function harvestCurrentTag(category) {
    if (focusMode !== 'TAGS' || currentTags.length === 0) return;
    const tag = currentTags[tagCursorIndex];
    await fetch('/api/harvest_tag', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag: tag.name || tag.val, category: category})});
    currentTags.splice(tagCursorIndex, 1);
    renderRefinery(null);
    updateVisualCursor();
}

async function incinerateCurrentItem(typeOverride) {
    if (focusMode !== 'TAGS' || currentTags.length === 0) return;
    const item = currentTags[tagCursorIndex];
    let termToBan = item.val;
    if (typeOverride === 'company') {
        if (item.type !== 'company' && !confirm(`Ban Company: ${item.val}?`)) return;
        termToBan = item.val;
    } else if (typeOverride === 'title') {
        if (item.type !== 'title' && !confirm(`Ban Title: ${item.val}?`)) return;
        termToBan = item.val;
    } else { termToBan = item.val; }
    await fetch('/api/blacklist', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({term: termToBan})});
    currentTags.splice(tagCursorIndex, 1);
    renderIncinerator(null, null);
    updateVisualCursor();
}

async function action(act) {
    if(!currentJobId) return;
    
    if(act === 'process') {
         const sysPrompt = document.getElementById('sys-prompt-area').value;
         const temp = document.getElementById('model-temp').value;
         const model = document.getElementById('model-select').value;
         
         const term = document.getElementById('factory-terminal');
         term.innerText += "\n> DEPLOYING PARKER LEWIS PROTOCOL...";
         term.innerText += "\n> THIS MAY TAKE 10-20 SECONDS...";
         
         try {
             const res = await fetch('/api/process_job', {
                 method:'POST',
                 headers:{'Content-Type':'application/json'},
                 body:JSON.stringify({
                     id:currentJobId,
                     system_prompt: sysPrompt,
                     temperature: temp,
                     model: model
                 })
             });
             const data = await res.json();
             
             if(data.status==='processed') { 
                 term.innerText += "\n> JSON ACQUIRED.";
                 term.innerText += "\n> PDF GENERATED.";
                 term.innerText += "\n> ASSET MOVED TO ARMORY.";
                 alert("SUCCESS: PDF GENERATED AND SENT TO ARMORY."); 
                 loadJobs(); 
             } else {
                 term.innerText += "\n> ERROR: " + JSON.stringify(data);
             }
         } catch(e) {
             term.innerText += "\n> CRITICAL FAILURE: " + e;
         }
         return;
    }

    const endpoint = {'approve':'/api/approve', 'deny':'/api/deny', 'restore':'/api/restore'}[act];
    await fetch(endpoint, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentJobId})});
    const idx = jobList.findIndex(j=>j.id===currentJobId);
    if(idx > -1) {
        jobList.splice(idx, 1);
        document.getElementById('row-'+currentJobId).remove();
        if(jobList[idx]) selectJob(jobList[idx].id);
        else if(jobList[idx-1]) selectJob(jobList[idx-1].id);
        else { currentJobId = null; clearPanes(); }
    }
    updateStats();
}

function toggleAll(source) { document.querySelectorAll('.job-check').forEach(c => c.checked = source.checked); }
async function processAll() {
    if(!confirm("Process ALL?")) return;
    for (const job of [...jobList]) { selectJob(job.id); await action('process'); }
}
async function processSelected() {
    const checks = document.querySelectorAll('.job-check:checked');
    for (const c of checks) { selectJob(c.value); await action('process'); }
}
async function openImportModal() {
    document.getElementById('import-modal').style.display='flex';
    const files = await fetch('/api/scrapes').then(r=>r.json());
    document.getElementById('modal-file-list').innerHTML = files.map(f => `<div class="file-item"><input type="checkbox" value="${f}"> ${f}</div>`).join('');
}
async function executeMigration() {
    const checkboxes = document.querySelectorAll('#modal-file-list input:checked');
    const files = Array.from(checkboxes).map(c => c.value);
    if(files.length===0) return;
    await fetch('/api/migrate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({files:files})});
    document.getElementById('import-modal').style.display='none';
    loadJobs(); updateStats();
}
function openPDF() {
    const j = jobList.find(j=>j.id===currentJobId);
    window.open(`/done/${j.safe_title}_${j.id}.pdf`, '_blank');
}

document.addEventListener('keydown', e => {
    if(document.getElementById('import-modal').style.display === 'flex') return;
    if (e.key === 'Tab') {
        e.preventDefault();
        focusMode = (focusMode === 'LIST') ? 'TAGS' : 'LIST';
        updateVisualCursor();
        return;
    }
    if (e.key.startsWith('Arrow')) {
        if (focusMode === 'LIST') {
            e.preventDefault();
            const idx = jobList.findIndex(j=>j.id===currentJobId);
            if (e.key === 'ArrowDown' && jobList[idx+1]) selectJob(jobList[idx+1].id);
            if (e.key === 'ArrowUp' && jobList[idx-1]) selectJob(jobList[idx-1].id);
        } else if (focusMode === 'TAGS') {
            e.preventDefault();
            if (e.key === 'ArrowRight') tagCursorIndex++;
            if (e.key === 'ArrowLeft') tagCursorIndex--;
            updateVisualCursor();
        }
        return;
    }
    const k = e.key.toLowerCase();
    if (focusMode === 'LIST') {
        if (currentTab === 'NEW') {
            if (k === 'a') action('approve');
            if (k === 'd') action('deny');
        }
        if (currentTab === 'DENIED' && k === 'r') action('restore');
        if (currentTab === 'FACTORY' && k === 'p') action('process');
    }
    if (currentTab === 'REFINERY' && focusMode === 'TAGS') {
        if (k === 'q') harvestCurrentTag('qualifications');
        if (k === 's') harvestCurrentTag('skills');
        if (k === 'b') harvestCurrentTag('benefits');
    }
    if (currentTab === 'DENIED' && focusMode === 'TAGS') {
        if (k === 'c') incinerateCurrentItem('company');
        if (k === 't') incinerateCurrentItem('title');
        if (k === 'k') incinerateCurrentItem('tag');
    }
});
