// GHOST CLIENT v8: THE LABORATORY
let globalJobs = [];
let currentView = 'FEED';
let currentJobId = null;

const WAR_MODELS = [
    "moonshotai/kimi-k2-instruct", "llama-3.3-70b-versatile", "groq/compound",
    "openai/gpt-oss-safeguard-20b", "llama-3.1-8b-instant", "moonshotai/kimi-k2-instruct-0905",
    "qwen/qwen3-32b", "openai/gpt-oss-20b", "allam-2-7b", "meta-llama/llama-4-scout-17b-16e-instruct",
    "groq/compound-mini"
];

document.addEventListener("DOMContentLoaded", () => {
    switchView('FEED');
    setupSearch();
});

function switchView(view) {
    currentView = view;
    document.getElementById('nav-feed').className = view === 'FEED' ? 'nav-link active' : 'nav-link';
    document.getElementById('nav-archive').className = view === 'ARCHIVE' ? 'nav-link active' : 'nav-link';
    document.getElementById('view-feed').className = view === 'FEED' ? 'view-section active' : 'view-section';
    document.getElementById('view-archive').className = view === 'ARCHIVE' ? 'view-section active' : 'view-section';
    if (view === 'FEED') fetchFeed();
    if (view === 'ARCHIVE') fetchArchive();
}

async function fetchFeed() {
    const res = await fetch('/api/jobs?status=APPROVED');
    globalJobs = await res.json();
    renderFeedList(globalJobs);
    if (globalJobs.length > 0 && !currentJobId) loadDetail(globalJobs[0].id);
}

function renderFeedList(jobs) {
    const container = document.getElementById('feed-container');
    container.innerHTML = '';
    if (jobs.length === 0) {
        container.innerHTML = '<div style="padding:20px; color:#666;">No targets approved.</div>';
        return;
    }
    jobs.forEach(job => {
        const card = document.createElement('div');
        card.className = 'job-card';
        card.id = `card-${job.id}`;
        card.innerHTML = `
            <div class="badge-new">TARGET</div>
            <div class="job-title">${job.title}</div>
            <div class="job-company">${job.company}</div>
            <div class="job-loc">${job.city}</div>
            <div style="margin-top:10px;"><span class="pill-gray">${job.pay}</span></div>
            <div id="smuggler-${job.id}" style="margin-top:12px;"></div>
        `;
        card.addEventListener('click', () => loadDetail(job.id));
        container.appendChild(card);
        smuggleTags(job.id);
    });
}

async function loadDetail(id) {
    currentJobId = id;
    const job = globalJobs.find(j => j.id === id);
    if (!job) return;

    // RENDER HEADER
    document.getElementById('detail-header').innerHTML = `
        <div class="job-title" style="font-size:24px; margin-bottom:10px;">${job.title}</div>
        <div style="margin-bottom:12px; font-size:15px;">${job.company} • ${job.city}</div>
        
        <div style="margin-top:20px; display:flex; gap:10px;">
            <button id="btn-tailor" class="btn-action btn-tailor" style="flex:1; margin-bottom:0;" onclick="createTailored('${id}')">
                <i class="bi bi-magic"></i> Create Tailored
            </button>
            <button id="btn-settings" class="btn-gear" onclick="toggleSettings()">
                <i class="bi bi-gear-fill"></i>
            </button>
        </div>

        <!-- SETTINGS PANEL -->
        <div id="settings-panel" class="settings-panel">
            <div class="setting-row">
                <div class="setting-label">MODEL</div>
                <select id="set-model" class="groq-select">
                    ${WAR_MODELS.map(m => `<option value="${m}">${m}</option>`).join('')}
                </select>
            </div>
            
            <div class="setting-row">
                <div class="setting-label">
                    <span>PROTOCOL (PROMPT)</span>
                    <a href="#" onclick="savePrompt()" style="color:#2557a7; text-decoration:none;">Save As...</a>
                </div>
                <select id="prompt-select" class="groq-select" onchange="loadPromptContent(this.value)">
                    <option value="DEFAULT">PARKER LEWIS (DEFAULT)</option>
                </select>
            </div>

            <div class="setting-row">
                <textarea id="set-prompt" class="groq-textarea" placeholder="Load a protocol or type custom instructions..."></textarea>
            </div>
            
            <div class="setting-row">
                <div class="setting-label"><span>TEMP</span> <span id="val-temp" class="setting-val">0.6</span></div>
                <input type="range" id="set-temp" min="0" max="2" step="0.1" value="0.6" oninput="document.getElementById('val-temp').innerText = this.value">
            </div>

            <hr style="border:0; border-top:1px solid #eee; margin:15px 0;">
            
            <button class="btn-action" style="background:#b71b1b; color:#fff; border:none;" onclick="resetJob('${id}')">
                <i class="bi bi-trash"></i> DELETE ARTIFACTS & RESET
            </button>
        </div>
        
        <div style="margin-top:10px;">
             <button id="btn-pdf" class="btn-action btn-pdf" onclick="createPDF('${id}')">
                <i class="bi bi-file-earmark-pdf"></i> Create PDF
            </button>
            <div style="display:flex; gap:10px; margin-top:10px;">
                <button class="btn-target" onclick="window.open('${job.job_url}', '_blank')">Open Target Link <i class="bi bi-box-arrow-up-right"></i></button>
                <button class="btn-move" style="margin-left:auto; padding:5px 10px; border-radius:4px;" onclick="dismissJob('${id}')">Dismiss</button>
            </div>
        </div>
    `;

    // Fetch Description
    const res = await fetch(`/api/get_job_details?id=${id}`);
    const details = await res.json();
    renderDescription(details);
    
    // Init Prompts List
    loadPromptList();
}

function renderDescription(details) {
    const bodyBox = document.getElementById('detail-body');
    const skillHTML = details.skills.map(s => `<span class="skill-tag"><i class="bi bi-check-lg"></i>${s.name}</span>`).join('');
    bodyBox.innerHTML = `
        <div class="insight-box">
            <div class="insight-title">Profile insights</div>
            <div>${skillHTML || '<span style="color:#666;">No tags.</span>'}</div>
        </div>
        <div style="font-weight:700; font-size:18px; margin-bottom:12px;">Job details</div>
        <div style="font-size:15px; line-height:1.6; color:#1a1a1a;">${details.description}</div>
    `;
}

function toggleSettings() {
    const panel = document.getElementById('settings-panel');
    const btn = document.getElementById('btn-settings');
    if (panel.style.display === 'block') {
        panel.style.display = 'none';
        btn.classList.remove('active');
    } else {
        panel.style.display = 'block';
        btn.classList.add('active');
    }
}

// --- PROMPT MANAGER LOGIC ---
async function loadPromptList() {
    const res = await fetch('/api/prompts');
    const keys = await res.json();
    const sel = document.getElementById('prompt-select');
    sel.innerHTML = `<option value="DEFAULT">PARKER LEWIS (DEFAULT)</option>` + 
                    keys.map(k => `<option value="${k}">${k.toUpperCase()}</option>`).join('');
}

async function loadPromptContent(name) {
    const res = await fetch('/api/get_prompt_content', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name:name})
    });
    const data = await res.json();
    document.getElementById('set-prompt').value = data.content;
}

async function savePrompt() {
    const content = document.getElementById('set-prompt').value;
    if(!content) return alert("Prompt is empty.");
    const name = prompt("Name this Protocol:");
    if(!name) return;
    
    await fetch('/api/prompts', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name:name, content:content})
    });
    alert("Saved.");
    loadPromptList(); // Refresh dropdown
    document.getElementById('prompt-select').value = name;
}

// --- CORE ACTIONS ---
async function resetJob(id) {
    if(!confirm("CONFIRM BURN: This will delete the Resume and PDF for this target.")) return;
    const res = await fetch('/api/reset_job', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({id:id})
    });
    const data = await res.json();
    if(data.status === 'reset') {
        loadDetail(id); // Reload the pane to reset buttons
    } else {
        alert("Burn failed.");
    }
}

async function createTailored(id) {
    const btn = document.getElementById('btn-tailor');
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Processing...`;
    
    const model = document.getElementById('set-model').value;
    const temp = document.getElementById('set-temp').value;
    const promptVal = document.getElementById('set-prompt').value;

    try {
        const res = await fetch('/api/process_job', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: id, model: model, temp: temp, prompt_override: promptVal})
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            btn.innerHTML = `<i class="bi bi-eye"></i> View Tailored`;
            btn.onclick = () => viewTailored(id);
            btn.style.background = "#2a8547";
            document.getElementById('settings-panel').style.display = 'none';
            viewTailored(id);
        } else {
            alert("Gen Failed: " + data.error);
            btn.innerHTML = `<i class="bi bi-magic"></i> Create Tailored`;
        }
    } catch (e) { alert("Network Error"); }
}

async function viewTailored(id) {
    const res = await fetch('/api/get_artifact', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id:id, variant:'PRIMARY'})
    });
    const data = await res.json();
    document.getElementById('detail-body').innerHTML = `
        <div style="background:#f8f9fa; padding:15px; border-bottom:1px solid #ddd;">
            <strong>Generated Asset</strong> 
            <button class="btn-sm-ghost" style="float:right" onclick="loadDetail('${id}')">Back</button>
        </div>
        <textarea style="width:100%; height:600px; padding:15px; font-family:monospace; border:none; resize:none;">${data.content}</textarea>
    `;
}

async function createPDF(id) {
    const btn = document.getElementById('btn-pdf');
    btn.innerHTML = `Generating...`;
    try {
        const res = await fetch("/api/generate_pdf", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({id: id}) });
        const data = await res.json();
        if (data.status === "success") {
            btn.innerHTML = `<i class="bi bi-file-earmark-pdf"></i> View PDF`;
            btn.onclick = () => window.open(data.path, '_blank');
            btn.style.color = "#2a8547"; btn.style.borderColor = "#2a8547";
            window.open(data.path, '_blank');
        } else { alert("PDF Error: " + data.message); btn.innerHTML = `Create PDF`; }
    } catch(e) { alert("Error"); }
}

function dismissJob(id) {
    const card = document.getElementById(`card-${id}`);
    if(card) card.remove();
    document.getElementById('detail-header').innerHTML = '<div style="color:#666; padding:20px;">Dismissed.</div>';
    document.getElementById('detail-body').innerHTML = '';
}

async function fetchArchive() {
    const res = await fetch('/api/jobs?status=DELIVERED');
    const jobs = await res.json();
    const container = document.getElementById('archive-container');
    container.innerHTML = '';
    jobs.forEach(job => {
        const row = document.createElement('div');
        row.className = 'archive-row';
        const pdfBtn = job.has_pdf ? `<button class="btn-sm-ghost" style="color:#2a8547; border-color:#2a8547;" onclick="window.open('${job.pdf_link}', '_blank')">PDF</button>` : '';
        row.innerHTML = `
            <input type="checkbox" class="archive-check" value="${job.id}">
            <div class="archive-info">
                <div style="font-weight:700; font-size:16px;">${job.title}</div>
                <div style="font-size:14px; color:#595959;">${job.company}</div>
            </div>
            <div class="archive-actions">${pdfBtn}<button class="btn-sm-ghost" onclick="window.open('${job.job_url}', '_blank')">Link</button></div>
        `;
        container.appendChild(row);
    });
}
async function removeSelected() {
    const checks = document.querySelectorAll('.archive-check:checked');
    if(checks.length === 0) return;
    if(!confirm(`Delete ${checks.length}?`)) return;
    for (const c of checks) await fetch('/api/deny', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:c.value})});
    fetchArchive();
}
async function smuggleTags(id) {
    try {
        const res = await fetch(`/api/get_job_details?id=${id}`);
        const data = await res.json();
        const target = document.getElementById(`smuggler-${id}`);
        if (target && data.skills) target.innerHTML = `<ul style="margin:0; padding-left:18px; font-size:13px; color:#444;">${data.skills.slice(0,2).map(s => `<li>${s.name}</li>`).join('')}</ul>`;
    } catch(e){}
}
function setupSearch() {
    const btn = document.querySelector('.btn-find');
    const input = document.querySelector('.search-input');
    if (btn) btn.addEventListener('click', (e) => {
        e.preventDefault();
        const term = input.value.toLowerCase();
        const filtered = globalJobs.filter(j => j.title.toLowerCase().includes(term) || j.company.toLowerCase().includes(term));
        renderFeedList(filtered);
    });
}
