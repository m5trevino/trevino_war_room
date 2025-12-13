let jobList = [], currentJobId = null, currentTab = 'NEW';
let focusMode = 'JOBS'; 
let refineryTags = []; 
let currentTagIndex = 0;
let currentJobUrl = '';
let currentOffset = 0;
let totalJobs = 0;

document.getElementById('temp-slider').addEventListener('input', (e) => {
    document.getElementById('temp-val').innerText = e.target.value;
});

async function loadJobs(append=false) {
    let statusQuery = currentTab;
    if (currentTab === 'REFINERY' || currentTab === 'FACTORY') statusQuery = 'APPROVED';
    if (currentTab === 'DELIVERED') statusQuery = 'DELIVERED'; 

    if(!append) {
        currentOffset = 0;
        jobList = [];
        document.getElementById('list-container').innerHTML = "";
    }

    const res = await fetch(`/api/jobs?status=${statusQuery}&limit=50&offset=${currentOffset}`);
    const data = await res.json();
    const newJobs = data.jobs || [];
    totalJobs = data.total || 0;
    
    if(append) {
        jobList = jobList.concat(newJobs);
    } else {
        jobList = newJobs;
    }

    renderHeader();
    renderList(append);
    
    if (!append && jobList.length > 0) {
        selectJob(jobList[0].id);
    } else if (jobList.length === 0) {
        document.getElementById('global-job-header').style.display = 'none';
        if(document.getElementById('std-desc-box')) document.getElementById('std-desc-box').innerHTML = "<div style='padding:20px;text-align:center'>SECTOR CLEAR.</div>";
    }
    
    updateStats();
    updateControls();
    
    // PAGINATION LOGIC
    const btn = document.getElementById('load-more-btn');
    if (jobList.length < totalJobs) {
        btn.style.display = 'block';
        const remaining = totalJobs - jobList.length;
        const nextPageSize = Math.min(50, remaining);
        const currentPage = Math.floor(jobList.length / 50);
        const totalPages = Math.ceil(totalJobs / 50);
        
        btn.innerText = `LOAD NEXT ${nextPageSize} (SHOWING ${jobList.length} OF ${totalJobs} | PAGE ${currentPage} OF ${totalPages})`;
    } else {
        btn.style.display = 'none';
    }
}

function loadMore() {
    currentOffset += 50;
    loadJobs(true);
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
        h.style.gridTemplateColumns = "30px 1fr 1fr 1fr 140px"; 
        h.innerHTML = `<div><input type="checkbox" onclick="toggleAll(this)"></div><div>TITLE</div><div>CORP</div><div>CITY</div><div>CONTROLS</div>`;
    }
}

function renderList(append) {
    const c = document.getElementById('list-container');
    const html = jobList.map(j => {
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
            const btnPDF = j.has_pdf 
                ? `<span class="c-btn" style="border-color:#00e676; color:#00e676;" onclick="window.open('${j.pdf_link}', '_blank'); event.stopPropagation();">PDF</span>` 
                : `<span class="c-btn" style="border-color:#333; color:#333;">...</span>`;
            const btnDir = `<span class="c-btn" style="border-color:#ffd700; color:#ffd700;" onclick="openFolder('${j.id}'); event.stopPropagation();">DIR</span>`;
            const btnJob = `<span class="c-btn" style="border-color:#2196f3; color:#2196f3;" onclick="window.open('${j.job_url}', '_blank'); event.stopPropagation();">JOB</span>`;

            cols = `
                <div onclick="event.stopPropagation()"><input type="checkbox" class="job-check" value="${j.id}"></div>
                <div style="font-weight:bold;white-space:nowrap;overflow:hidden">${j.title}</div>
                <div style="color:#ffd700;white-space:nowrap;overflow:hidden">${j.company}</div>
                <div style="color:#8be9fd">${j.city}</div>
                <div style="display:flex; gap:5px;">${btnPDF}${btnDir}${btnJob}</div>
            `;
            return `<div class="job-row" id="row-${j.id}" style="grid-template-columns: 30px 1fr 1fr 1fr 140px;" onclick="selectJob('${j.id}')">${cols}</div>`;
        }
    }).join('');
    
    c.innerHTML = html;
}

async function action(act) {
    if(!currentJobId) return;
    
    if (act === 'process') {
        batchExecute(true); 
        return;
    }

    const targetId = currentJobId; 
    const endpoint = {'approve':'/api/approve', 'deny':'/api/deny', 'restore':'/api/restore'}[act];
    
    const row = document.getElementById('row-'+targetId);
    if(row) row.remove();
    
    const idx = jobList.findIndex(j=>j.id===targetId);
    if(idx > -1) {
        jobList.splice(idx, 1);
        if(jobList[idx]) selectJob(jobList[idx].id);
        else if(jobList[idx-1]) selectJob(jobList[idx-1].id);
        else {
            document.getElementById('global-job-header').style.display = 'none';
        }
    }

    fetch(endpoint, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:targetId})});
    
    updateStats(); 
}

async function purgeIncoming() {
    if(!confirm("HARD DELETE ALL 'NEW' JOBS? THIS IS PERMANENT.")) return;
    await fetch('/api/sweep_new', {method:'POST'});
    loadJobs(); 
}

async function openFolder(id) {
    await fetch('/api/open_folder', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id:id})});
}

function switchTab(tab) {
    currentTab = tab;
    focusMode = 'JOBS';
    currentTagIndex = 0;
    updateRefineryFocus();
    
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    const tabs = Array.from(document.querySelectorAll('.tab'));
    const map = {'NEW':0, 'REFINERY':1, 'FACTORY':2, 'DELIVERED':3, 'DENIED':4};
    if (tabs[map[tab]]) tabs[map[tab]].classList.add('active');
    
    ['standard-view', 'refinery-view', 'factory-view', 'product-view'].forEach(id => {
        if(document.getElementById(id)) document.getElementById(id).style.display = 'none';
    });

    if (tab === 'NEW' || tab === 'DENIED') document.getElementById('standard-view').style.display = 'flex';
    if (tab === 'REFINERY') document.getElementById('refinery-view').style.display = 'flex';
    if (tab === 'FACTORY') document.getElementById('factory-view').style.display = 'flex';
    if (tab === 'DELIVERED') document.getElementById('product-view').style.display = 'flex';

    loadJobs();
}

async function openImportModal() {
    document.getElementById('import-modal').style.display='flex';
    const files = await fetch('/api/scrapes').then(r=>r.json());
    
    document.getElementById('modal-file-list').innerHTML = files.map(f => {
        const badge = f.imported ? `<span style="color:#00e676; margin-left:10px; font-size:10px;">[IMPORTED]</span>` : "";
        const count = `<span style="color:#888; font-size:10px; margin-left:5px;">(${f.count} jobs | ${f.size} | ${f.date})</span>`;
        
        return `
        <div class="file-item" style="flex-direction:column; align-items:flex-start; border-bottom:1px solid #333; padding:10px;">
            <div style="display:flex; align-items:center; width:100%; margin-bottom:5px;">
                <input type="checkbox" value="${f.filename}" style="margin-right:10px;">
                <span style="color:#fff;">${f.filename}</span>
                ${count} ${badge}
            </div>
            <div style="display:flex; width:100%; gap:5px;">
                <input type="text" id="rename-${f.filename}" value="${f.suggested}" style="background:#000; color:#00e676; border:1px solid #333; padding:5px; flex:1; font-family:monospace;">
                <button onclick="applyRename('${f.filename}')" style="background:#2196f3; color:white; border:none; padding:5px 10px; cursor:pointer; font-size:10px;">SAVE NAME</button>
            </div>
        </div>`;
    }).join('');
}

async function applyRename(oldName) {
    const input = document.getElementById(`rename-${oldName}`);
    const newName = input.value;
    const res = await fetch('/api/rename_file', {
        method:'POST', 
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({old_name: oldName, new_name: newName})
    });
    const data = await res.json();
    if(data.status === 'renamed') {
        openImportModal(); 
    } else {
        alert("Error: " + data.error);
    }
}

async function executeMigration() {
    const checkboxes = document.querySelectorAll('#modal-file-list input:checked');
    const files = Array.from(checkboxes).map(c => c.value);
    if(files.length===0) return;
    document.querySelector('#import-modal button:last-child').innerText = "MIGRATING...";
    try {
        const res = await fetch('/api/migrate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({files:files})});
        const data = await res.json();
        alert(`REPORT: ${data.stats.new} New Jobs Added.`);
        switchTab('NEW');
    } catch(e) { alert("Migration Error."); }
    document.getElementById('import-modal').style.display='none';
}

function updateControls() {
    document.querySelectorAll('#controls button').forEach(b => b.style.display = 'none');
    
    if (currentTab === 'NEW') {
        document.getElementById('btn-a').style.display = 'inline-block';
        document.getElementById('btn-d').style.display = 'inline-block';
    }
    if (currentTab === 'FACTORY') {
        document.getElementById('btn-p').style.display = 'inline-block';
        document.getElementById('btn-b').style.display = 'inline-block';
        document.getElementById('btn-g').style.display = 'inline-block';
    }
    if (currentTab === 'DELIVERED') {
        document.getElementById('btn-pb').style.display = 'inline-block'; 
        document.getElementById('btn-d').style.display = 'inline-block'; 
    }
    if (currentTab === 'DENIED') {
        document.getElementById('btn-r').style.display = 'inline-block';
        document.getElementById('btn-bl').style.display = 'inline-block';
    }
}

async function selectJob(id) {
    currentJobId = id;
    document.querySelectorAll('.job-row').forEach(r=>r.classList.remove('active'));
    if(document.getElementById('row-'+id)) document.getElementById('row-'+id).classList.add('active');
    
    const d = await fetch(`/api/get_job_details?id=${id}`).then(r=>r.json());
    currentJobUrl = d.url; 
    const jobObj = jobList.find(j => j.id === id);

    const gh = document.getElementById('global-job-header');
    gh.style.display = 'flex';
    document.getElementById('g-job-title').innerText = jobObj ? jobObj.title : "UNKNOWN TARGET";
    document.getElementById('g-job-corp').innerText = jobObj ? jobObj.company : "";

    if (currentTab === 'DELIVERED') {
        const variants = await fetch(`/api/get_gauntlet_files?id=${id}`).then(r=>r.json());
        const sel = document.getElementById('result-selector');
        sel.innerHTML = `<option value="PRIMARY">PRIMARY (LATEST)</option>`;
        variants.forEach(v => {
            sel.innerHTML += `<option value="${v}">${v}</option>`;
        });
        
        const header = document.getElementById('product-header');
        header.innerHTML = `
            <select id="result-selector" onchange="loadArtifact(this.value)" style="flex:1; margin-right:5px;">
                <option value="PRIMARY">PRIMARY (LATEST)</option>
            </select>
            <button class="btn-link" style="background:var(--blue); color:#fff; border:none; padding:5px 10px; cursor:pointer;" onclick="openJobLink()">GO TO TARGET</button>
            <button class="btn-save" onclick="saveJSON()">SAVE</button>
            <button class="btn-pdf" onclick="openPDF()">PDF</button>
        `;

        await loadArtifact("PRIMARY");
        return;
    }

    if (currentTab === 'NEW' || currentTab === 'DENIED') {
        document.getElementById('std-desc-box').innerHTML = d.description;
        const allTags = d.skills.map(s => 
            `<span class="skill-tag ${s.category === 'new' ? 'new' : 'sorted'}">${s.name}</span>`
        ).join('');
        document.getElementById('std-tags').innerHTML = allTags;
    }
    
    if (currentTab === 'REFINERY') {
        renderRefinery(d.skills);
        if (focusMode === 'TAGS') {
            currentTagIndex = 0;
            updateRefineryFocus();
        }
    }
    
    if (currentTab === 'FACTORY') {
        const allTags = d.skills.map(s => 
            `<span class="skill-tag ${s.category === 'new' ? 'new' : 'sorted'}">${s.name}</span>`
        ).join('');
        document.getElementById('factory-intel').innerHTML = `
            <div style="margin-bottom:10px; color:#ffd700;">[STRATEGIC ASSETS]</div>
            ${allTags}
            <div style="margin:10px 0; color:#00e676;">[TARGET DESCRIPTION]</div>
            ${d.description}
        `;
    }
}

function openJobLink() {
    if(currentJobUrl && currentJobUrl !== '#') window.open(currentJobUrl, '_blank');
    else alert("No Uplink Available.");
}

async function loadArtifact(variant) {
    if(!currentJobId) return;
    const a = await fetch('/api/get_artifact', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({id:currentJobId, variant:variant})
    }).then(r=>r.json());
    document.getElementById('resume-content').value = a.content;
}

function renderRefinery(skills) {
    refineryTags = skills.filter(s => s.category === 'new');
    const q = skills.filter(s => s.category === 'qualifications');
    const s = skills.filter(s => s.category === 'skills');
    const b = skills.filter(s => s.category === 'benefits');

    document.getElementById('refinery-new-tags').innerHTML = refineryTags.map((t, i) => 
        `<span id="rtag-${i}" class="skill-tag new" onmousedown="clickSort('${t.name}')">${t.name}</span>`
    ).join('');

    document.querySelector('#col-q').innerHTML = `<div class="col-header">QUALS</div>` + q.map(t=>`<div class="skill-tag q">${t.name}</div>`).join('');
    document.querySelector('#col-s').innerHTML = `<div class="col-header">SKILLS</div>` + s.map(t=>`<div class="skill-tag s">${t.name}</div>`).join('');
    document.querySelector('#col-b').innerHTML = `<div class="col-header">BENEFITS</div>` + b.map(t=>`<div class="skill-tag b">${t.name}</div>`).join('');
    
    updateRefineryFocus();
}

function updateRefineryFocus() {
    if (currentTab !== 'REFINERY') return;
    const box = document.getElementById('unsorted-box');
    if (focusMode === 'TAGS') {
        box.style.border = "2px solid #00e676"; 
        box.style.background = "#1a261a"; 
    } else {
        box.style.borderBottom = "1px solid #333";
        box.style.borderTop = "none";
        box.style.borderLeft = "none";
        box.style.borderRight = "none";
        box.style.background = "#0d1117";
    }
    for (let i = 0; i < refineryTags.length; i++) {
        const el = document.getElementById(`rtag-${i}`);
        if (!el) continue;
        if (focusMode === 'TAGS' && i === currentTagIndex) {
            el.style.background = "#ffd700";
            el.style.color = "#000";
            el.style.borderColor = "#ffd700";
            el.scrollIntoView({block: 'nearest', inline: 'nearest'});
        } else {
            el.style.background = "transparent";
            el.style.color = "#ffd700";
            el.style.borderColor = "#ffd700";
        }
    }
}

async function clickSort(tag) { harvestTag(tag, 'skills'); }
async function harvestTag(tag, category) {
    await fetch('/api/harvest_tag', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag:tag, category:category})});
    await selectJob(currentJobId); 
    if (currentTagIndex >= refineryTags.length) currentTagIndex = Math.max(0, refineryTags.length - 1);
    updateRefineryFocus();
}

function log(msg) {
    const term = document.getElementById('factory-terminal');
    if(term) {
        term.innerHTML += msg; 
        term.scrollTop = term.scrollHeight;
    }
}

async function batchExecute(singleMode=false) {
    let targets = [];
    
    if (singleMode) {
        if(!currentJobId) return;
        targets = [currentJobId];
    } else {
        const checks = document.querySelectorAll('.job-check:checked');
        if(checks.length === 0) return alert("NO TARGETS SELECTED.");
        if(!confirm(`EXECUTE BATCH AI ON ${checks.length} TARGETS?`)) return;
        targets = Array.from(checks).map(c => c.value);
    }
    
    const term = document.getElementById('factory-terminal');
    if(term) {
        if(!singleMode) term.innerText = `> INITIALIZING BATCH PROTOCOL (${targets.length} TARGETS)...\n`;
        else term.innerText = `> ENGAGING TARGET: ${currentJobId}...\n`;
    }
    
    const model = document.getElementById('model-select').value;
    const temp = document.getElementById('temp-slider').value;

    for (const id of targets) {
        selectJob(id); 
        log(`<div style='color:#888'> > CONTACTING: ${model} for Job ${id}...</div>`);
        
        try {
            const res = await fetch('/api/process_job', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({id:id, model:model, temp:temp})
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                const row = document.getElementById('row-' + id);
                if(row) row.remove();
                const idx = jobList.findIndex(j => j.id === id);
                if (idx > -1) jobList.splice(idx, 1);
                
                let linkHtml = "";
                if(data.pdf_url) {
                    linkHtml = `<button style="background:#00e676; color:#00e676; border:none; padding:5px 10px; font-weight:bold; cursor:pointer; margin-top:5px;" onclick="window.open('${data.pdf_url}', '_blank')">OPEN PDF ASSET</button>`;
                }

                const html = `
                <div style="margin-top:20px; border-top: 1px dashed #444; padding-top:10px;">
                    <div style="color:#2196f3; font-weight:bold;">
                        TARGET: ${id} | MOVED TO ARMORY
                    </div>
                    <div style="color:#00e676; white-space:pre-wrap;">${data.response.substring(0, 100)}...</div>
                    ${linkHtml}
                    <div style="color:#888; font-size:10px; margin-top:10px;">
                        SAVED TO: ${data.file} | TIME: ${data.duration.toFixed(2)}s
                    </div>
                </div>
                `;
                log(html);
            } else {
                log(`<div style="color:red;">!!! FAILED: ${data.error}</div>`);
            }
        } catch(e) {
            log(`<div style="color:red;">!!! NETWORK ERROR: ${e}</div>`);
        }
    }
    log("<div style='color:#00e676; margin-top:20px; border-top:2px solid #00e676;'> > EXECUTION COMPLETE.</div>");
    loadJobs();
}

async function batchPDF() {
    const checks = document.querySelectorAll('.job-check:checked');
    if(checks.length === 0) return alert("NO TARGETS SELECTED.");
    if(!confirm(`RE-COMPILE PDFS FOR ${checks.length} TARGETS?`)) return;

    const btn = document.getElementById('btn-pb');
    const originalText = btn.innerText;
    btn.innerText = "WORKING...";
    
    for (const check of checks) {
        const id = check.value;
        try {
            await fetch("/api/generate_pdf", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({id: id})
            });
            const row = document.getElementById('row-'+id);
            if(row) {
                row.style.background = "#1a261a"; 
                setTimeout(() => row.style.background = "", 500);
            }
        } catch(e) {
            console.error(e);
        }
    }
    
    btn.innerText = originalText;
    alert("BATCH PDF RE-COMPILE COMPLETE. REFRESHING GRID.");
    loadJobs(); 
}

async function runGauntlet() {
    if(!currentJobId) return;
    if(!confirm("START CAMPAIGN?")) return;
    
    const term = document.getElementById('factory-terminal');
    term.innerHTML = "<div style='color:#00e676; border-bottom:1px solid #333; margin-bottom:10px;'> > CAMPAIGN INITIALIZED.</div>";

    const opts = document.getElementById('model-select').options;
    const models = Array.from(opts).map(o => o.value);
    const temp = document.getElementById('temp-slider').value;
    
    const now = new Date();
    const sessionId = now.toISOString().replace(/[:.]/g, '-');

    for (const model of models) {
        log(`<div style='color:#888'> > CONTACTING: ${model}...</div>`);
        await new Promise(r => setTimeout(r, 2000)); 
        
        try {
            const res = await fetch('/api/strike', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({
                    id: currentJobId, 
                    model: model, 
                    temp: temp,
                    session_id: sessionId
                })
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                log(`<div style="color:#00e676;">SUCCESS: ${model}</div>`);
            } else {
                log(`<div style="color:red;">!!! FAILURE: ${data.error}</div>`);
            }
        } catch (e) {
            log(`<div style="color:red;">!!! NETWORK ERROR: ${e}</div>`);
        }
    }
    log("<div style='color:#00e676; margin-top:20px; border-top:2px solid #00e676;'> > CAMPAIGN COMPLETE.</div>");
}

async function saveJSON() {
    if(!currentJobId) return;
    const content = document.getElementById('resume-content').value;
    await fetch('/api/get_artifact', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({id:currentJobId, save_content:content})
    });
    alert("Saved.");
}

function toggleAll(source) {
    document.querySelectorAll('.job-check').forEach(c => c.checked = source.checked);
}

async function blacklistEmployer() {
    if(!currentJobId) return;
    const job = jobList.find(j=>j.id===currentJobId);
    if(!confirm(`Blacklist ${job.company}?`)) return;
    await fetch('/api/blacklist', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({term:job.company})});
    action('deny');
}

async function updateStats() {
    const s = await fetch('/api/status').then(r=>r.json());
    // Only update ALL TIME and session GROQ
    document.getElementById('a_scraped').textContent = s.all_time.scraped||0;
    document.getElementById('a_approved').textContent = s.all_time.approved||0;
    document.getElementById('a_denied').textContent = s.all_time.denied||0;
}

async function openPDF() {
    if(!currentJobId) return;
    const btn = document.querySelector(".btn-pdf");
    const originalText = btn.innerText;
    btn.innerText = "GENERATING...";
    btn.style.background = "#fff";
    btn.style.color = "#000";
    
    try {
        const res = await fetch("/api/generate_pdf", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: currentJobId})
        });
        const data = await res.json();
        
        if(data.status === "success") {
            window.open(data.path, "_blank");
        } else {
            alert("PDF ERROR: " + data.message);
        }
    } catch(e) {
        alert("NETWORK ERROR: " + e);
    } finally {
        btn.innerText = originalText;
        btn.style.background = "";
        btn.style.color = "";
        loadJobs(); 
    }
}

document.addEventListener('keydown', e => {
    if(e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if(document.getElementById('import-modal').style.display === 'flex') return;

    if (e.key === 'Tab') {
        e.preventDefault(); 
        if (currentTab === 'REFINERY') {
            focusMode = (focusMode === 'JOBS') ? 'TAGS' : 'JOBS';
            if (focusMode === 'TAGS' && refineryTags.length > 0) {
                 if (currentTagIndex >= refineryTags.length) currentTagIndex = 0;
            }
            updateRefineryFocus();
        }
        return;
    }

    if(e.key==='ArrowDown' || e.key==='ArrowRight') {
        e.preventDefault();
        if (focusMode === 'JOBS') {
            const idx = jobList.findIndex(j=>j.id===currentJobId);
            if(jobList[idx+1]) selectJob(jobList[idx+1].id);
        }
        else if (focusMode === 'TAGS') {
            if (currentTagIndex < refineryTags.length - 1) {
                currentTagIndex++;
                updateRefineryFocus();
            }
        }
        return;
    }

    if(e.key==='ArrowUp' || e.key==='ArrowLeft') {
        e.preventDefault();
        if (focusMode === 'JOBS') {
            const idx = jobList.findIndex(j=>j.id===currentJobId);
            if(jobList[idx-1]) selectJob(jobList[idx-1].id);
        }
        else if (focusMode === 'TAGS') {
            if (currentTagIndex > 0) {
                currentTagIndex--;
                updateRefineryFocus();
            }
        }
        return;
    }

    if (focusMode === 'JOBS') {
        if(currentTab === 'NEW') {
            if(e.key==='a'||e.key==='A') action('approve');
            if(e.key==='d'||e.key==='D') action('deny');
        }
        if(currentTab === 'DENIED') {
            if(e.key==='r'||e.key==='R') action('restore');
        }
        if(currentTab === 'FACTORY') {
            if(e.key==='p'||e.key==='P') action('process');
        }
    }

    if (currentTab === 'REFINERY') {
        if (focusMode === 'TAGS' && refineryTags.length > 0) {
            const tag = refineryTags[currentTagIndex].name;
            if(e.key==='q'||e.key==='Q') harvestTag(tag, 'qualifications');
            if(e.key==='s'||e.key==='S') harvestTag(tag, 'skills');
            if(e.key==='b'||e.key==='B') harvestTag(tag, 'benefits');
        } 
    }
});

switchTab('NEW');
