let jobList = [], currentJobId = null, currentTab = 'NEW';

async function loadJobs() {
    let statusQuery = currentTab;
    if (currentTab === 'REFINERY' || currentTab === 'FACTORY') statusQuery = 'APPROVED';
    if (currentTab === 'DELIVERED') statusQuery = 'DELIVERED'; 

    const res = await fetch(`/api/jobs?status=${statusQuery}`);
    jobList = await res.json();
    renderHeader();
    renderList();
    
    // Select current if exists, else first, else null
    if (currentJobId && jobList.find(j => j.id === currentJobId)) {
        selectJob(currentJobId);
    } else if (jobList.length > 0) {
        selectJob(jobList[0].id);
    } else {
        if(document.getElementById('std-desc-box')) document.getElementById('std-desc-box').innerHTML = "<div style='padding:20px;text-align:center'>SECTOR CLEAR. NO TARGETS.</div>";
        if(document.getElementById('std-tags')) document.getElementById('std-tags').innerHTML = "";
    }
    updateStats();
    updateControls();
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
    // Find tab by text content usually, or just index if simpler. 
    // Since we pass 'NEW'/'APPROVED' etc, we iterate:
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

function updateControls() {
    document.querySelectorAll('#controls button').forEach(b => b.style.display = 'none');
    
    if (currentTab === 'NEW') {
        document.getElementById('btn-a').style.display = 'inline-block';
        document.getElementById('btn-d').style.display = 'inline-block';
    }
    if (currentTab === 'FACTORY') {
        document.getElementById('btn-p').style.display = 'inline-block';
        document.getElementById('btn-psel').style.display = 'inline-block';
        document.getElementById('btn-pall').style.display = 'inline-block';
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
    
    if (currentTab === 'DELIVERED') {
        const d = await fetch(`/api/get_job_details?id=${id}`).then(r=>r.json());
        const a = await fetch(`/api/get_artifact?id=${id}`).then(r=>r.json());
        document.getElementById('desc-box').innerHTML = d.description;
        document.getElementById('resume-content').innerText = a.content;
        return;
    }

    const d = await fetch(`/api/get_job_details?id=${id}`).then(r=>r.json());
    
    // RENDER STANDARD VIEW
    if (currentTab === 'NEW' || currentTab === 'DENIED') {
        document.getElementById('std-desc-box').innerHTML = d.description;
        const allTags = d.skills.map(s => 
            `<span class="skill-tag ${s.category === 'new' ? 'new' : 'sorted'}">${s.name}</span>`
        ).join('');
        document.getElementById('std-tags').innerHTML = allTags;
    }
    
    if (currentTab === 'REFINERY') renderRefinery(d.skills);
    
    // FACTORY TERMINAL LOGIC (THE FIX)
    if (currentTab === 'FACTORY') {
        document.getElementById('factory-desc').innerHTML = d.description;
        const term = document.getElementById('factory-terminal');
        // Only reset terminal if we switched to a DIFFERENT job
        if (!term.dataset.jobId || term.dataset.jobId !== id) {
            term.innerText = `> TARGET LOCKED: ${id}\n> READY TO PROCESS.`;
            term.dataset.jobId = id; // Tag the terminal so we know who owns it
        }
    }
}

function renderRefinery(skills) {
    const unsorted = skills.filter(s => s.category === 'new');
    const q = skills.filter(s => s.category === 'qualifications');
    const s = skills.filter(s => s.category === 'skills');
    const b = skills.filter(s => s.category === 'benefits');
    document.getElementById('refinery-new-tags').innerHTML = unsorted.map(t => `<span class="skill-tag new" onmousedown="clickSort('${t.name}')">${t.name}</span>`).join('');
    document.querySelector('#col-q').innerHTML = `<div class="col-header">QUALS</div>` + q.map(t=>`<div class="skill-tag q">${t.name}</div>`).join('');
    document.querySelector('#col-s').innerHTML = `<div class="col-header">SKILLS</div>` + s.map(t=>`<div class="skill-tag s">${t.name}</div>`).join('');
    document.querySelector('#col-b').innerHTML = `<div class="col-header">BENEFITS</div>` + b.map(t=>`<div class="skill-tag b">${t.name}</div>`).join('');
}

async function clickSort(tag) { harvestTag(tag, 'skills'); }
async function harvestTag(tag, category) {
    await fetch('/api/harvest_tag', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag:tag, category:category})});
    selectJob(currentJobId); 
}

function log(msg) {
    const term = document.getElementById('factory-terminal');
    if(term) {
        term.innerText += `\n> ${msg}`;
        term.scrollTop = term.scrollHeight;
    }
}

async function action(act) {
    if(!currentJobId) return;
    
    if (act === 'process') {
        log(`INITIATING ${currentJobId}...`);
        const res = await fetch('/api/process_job', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentJobId})});
        const data = await res.json();
        if (data.status === 'processed') { 
            log(`SUCCESS: Saved to ${data.file_saved}`);
            log(`KEY USED: ${data.key}`);
            loadJobs(); // Refresh checks, but selectJob won't wipe terminal now
        }
        else log(`ERROR: ${data.error}`);
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
    }
    updateStats();
}

function toggleAll(source) {
    document.querySelectorAll('.job-check').forEach(c => c.checked = source.checked);
}

async function processSelected() {
    const checks = document.querySelectorAll('.job-check:checked');
    if(checks.length === 0) return alert("No targets selected.");
    if(!confirm(`Execute AI on ${checks.length} targets?`)) return;
    
    for (const c of checks) {
        selectJob(c.value); // Selects job, terminal updates safely
        await action('process'); // Logs append
    }
}

async function processAll() {
    if(!confirm("Process ALL staged jobs?")) return;
    for (const job of [...jobList]) {
        selectJob(job.id);
        await action('process');
    }
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
    document.getElementById('s_scraped').textContent = s.session.scraped||0;
    document.getElementById('s_approved').textContent = s.session.approved||0;
    document.getElementById('s_denied').textContent = s.session.denied||0;
    document.getElementById('a_scraped').textContent = s.all_time.scraped||0;
    document.getElementById('a_approved').textContent = s.all_time.approved||0;
    document.getElementById('a_denied').textContent = s.all_time.denied||0;
}

function openPDF() {
    const safeTitle = jobList.find(j=>j.id===currentJobId).safe_title;
    window.open(`/done/${safeTitle}_${currentJobId}.pdf`, '_blank');
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
    document.querySelector('#import-modal button:last-child').innerText = "MIGRATING...";
    try {
        const res = await fetch('/api/migrate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({files:files})});
        const data = await res.json();
        alert(`REPORT: ${data.stats.new} New Jobs Added.`);
        switchTab('NEW');
    } catch(e) { alert("Migration Error."); }
    document.getElementById('import-modal').style.display='none';
}

document.addEventListener('keydown', e => {
    if(document.getElementById('import-modal').style.display === 'flex') return;
    if(e.key==='ArrowDown'||e.key==='ArrowUp') {
        e.preventDefault();
        const idx = jobList.findIndex(j=>j.id===currentJobId);
        const next = e.key==='ArrowDown' ? idx+1 : idx-1;
        if(jobList[next]) selectJob(jobList[next].id);
    }
    if(currentTab === 'NEW') {
        if(e.key==='a'||e.key==='A') action('approve');
        if(e.key==='d'||e.key==='D') action('deny');
    }
    if(currentTab === 'REFINERY') {
        const firstTag = document.querySelector('.skill-tag.new')?.innerText;
        if (firstTag) {
            if(e.key==='q'||e.key==='Q') harvestTag(firstTag, 'qualifications');
            if(e.key==='s'||e.key==='S') harvestTag(firstTag, 'skills');
            if(e.key==='b'||e.key==='B') harvestTag(firstTag, 'benefits');
        }
    }
    if(currentTab === 'FACTORY') {
        if(e.key==='p'||e.key==='P') action('process');
    }
    if(currentTab === 'DENIED') {
        if(e.key==='r'||e.key==='R') action('restore');
    }
});

// FORCE START ON 'NEW' TAB
switchTab('NEW');
