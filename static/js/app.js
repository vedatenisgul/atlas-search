window.updateHistoryList = async () => {
    const hc = document.getElementById('history-container');
    if(!hc) return;
    try {
        const res = await fetch('/api/crawler/history');
        const data = await res.json();
        const history = data.history || [];
        if(history.length === 0) {
            hc.innerHTML = '<p style="color:var(--text-secondary);">No historical records found.</p>';
            return;
        }
        let html = '<div style="display:flex; flex-direction:column; gap:15px;">';
        history.forEach(h => {
            html += `
            <div style="background:#fff; border:1px solid rgba(0,0,0,0.05); padding: 16px; border-radius: 12px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
                <div style="max-width: 70%;">
                    <strong style="color:var(--text-secondary); font-size:0.85rem;">${h.job_id}</strong>
                    <div style="margin-top:4px;">Seed: <a href="${h.seed_url}" target="_blank" style="color:var(--accent); text-decoration:none;">${h.seed_url}</a></div>
                    <div style="color:var(--text-secondary); font-size:0.85rem; margin-top:6px;">Depth: ${h.max_depth} | Queue Cap: ${h.queue_capacity} | Max Target: ${h.max_urls} | Visited: ${h.visited_count}</div>
                    ${h.created_at ? `<div style="font-size:0.75rem; color:#86868b; margin-top:6px;">🕒 Started: ${new Date(h.created_at*1000).toLocaleString()} ${h.ended_at ? '| 🛑 Ended: ' + new Date(h.ended_at*1000).toLocaleString() : ''}</div>` : ''}
                </div>
                <div style="padding:4px 8px; border-radius:4px; font-size:0.85rem; font-weight:600; background:rgba(0,0,0,0.03); color:var(--text-secondary);">
                    ${h.state}
                </div>
            </div>`;
        });
        html += '</div>';
        hc.innerHTML = html;
    } catch(err) {
        console.error(err);
    }
}

window.dismissJob = async (jobId) => {
    if(!confirm("Are you sure you want to dismiss and close this job?")) return;
    try {
        const res = await fetch(`/api/crawler/delete/${jobId}`, { method: 'DELETE' });
        if(res.ok) {
            if(window.refreshMetricsNative) window.refreshMetricsNative();
            window.updateHistoryList();
        } else {
            alert("Failed to dismiss job.");
        }
    } catch(err) {
        console.error(err);
    }
};

document.addEventListener('click', (e) => {
    if (e.target && e.target.classList.contains('copy-uuid')) {
        const uuid = e.target.getAttribute('data-uuid');
        if (uuid) {
            navigator.clipboard.writeText(uuid).then(() => {
                const originalText = e.target.innerHTML;
                e.target.textContent = "Copied!";
                e.target.style.color = "#34c759";
                setTimeout(() => {
                    e.target.innerHTML = originalText;
                    e.target.style.color = "#0071e3";
                }, 1500);
            });
        }
    }
});

document.addEventListener('DOMContentLoaded', () => {

    if(document.getElementById('history-container')) {
        window.updateHistoryList();
    }

    // Crawler Form Initialization
    const crawlerForm = document.getElementById('crawler-form');
    if (crawlerForm) {
        crawlerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('start-btn');
            const msgBox = document.getElementById('crawler-msg');
            
            btn.disabled = true;
            btn.textContent = "Deploying...";
            
            const payload = {
                url: document.getElementById('url').value,
                max_depth: parseInt(document.getElementById('max_depth').value),
                hit_rate: parseFloat(document.getElementById('hit_rate').value || 2.0),
                queue_capacity: parseInt(document.getElementById('queue_capacity').value || 10000),
                max_urls: parseInt(document.getElementById('max_urls').value || 1000)
            };
            
            try {
                const res = await fetch('/api/crawler/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                
                msgBox.classList.remove('hidden');
                msgBox.textContent = `Job Deployed Successfully! Internal Reference: ${data.job_id}`;
            } catch (err) {
                msgBox.classList.remove('hidden');
                msgBox.textContent = `Deployment Error: ${err.message}`;
            } finally {
                btn.disabled = false;
                btn.textContent = "Deploy Worker Job";
            }
        });
    }

    const btnResetAll = document.getElementById('btn-reset-all');
    if (btnResetAll) {
        btnResetAll.addEventListener('click', async () => {
            if (confirm("Are you sure you want to completely erase the crawler memory and reset all stats natively?")) {
                try {
                    await fetch('/api/system/reset', { method: 'POST' });
                    alert("System successfully reset natively.");
                    window.location.reload();
                } catch (err) {
                    alert("Reset failed: " + err.message);
                }
            }
        });
    }

    const jobsContainer = document.getElementById('jobs-container');
    const updateJobsList = (jobs) => {
        if (!jobsContainer) return;
        if (jobs.length === 0) {
            jobsContainer.innerHTML = '<p style="color:var(--text-secondary);">No running deployments.</p>';
            return;
        }
        
        let html = '<div style="display:flex; flex-direction:column; gap:10px;">';
        jobs.forEach(job => {
            const isPaused = job.state === 'Paused';
            const isRunning = job.state === 'Running';
            const isDone = ['Completed', 'Error', 'Stopped', 'Already Indexed'].includes(job.state);
            let stateColor = '#f5a623';
            let stateBg = 'rgba(245, 166, 35, 0.1)';
            if (isRunning || job.state === 'Completed' || job.state === 'Already Indexed') { stateColor = '#34c759'; stateBg = 'rgba(52, 199, 89, 0.1)'; }
            if (job.state === 'Error') { stateColor = '#ff3b30'; stateBg = 'rgba(255, 59, 48, 0.1)'; }
            
            html += `
            <div style="background:#fff; border:1px solid rgba(0,0,0,0.05); padding: 16px; border-radius: 12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div style="max-width: 50%; overflow:hidden;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <strong style="color:var(--accent);">${job.job_id}</strong>
                        <span style="font-size:0.85rem; padding: 4px 8px; border-radius:4px; background: ${stateBg}; color: ${stateColor}; transition: all 0.3s ease; white-space:nowrap;">${job.state}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        Seed: <a href="${job.seed_url}" target="_blank" style="color:var(--accent); text-decoration:none;">${job.seed_url}</a>
                    </div>
                </div>
                <div style="display:flex; gap: 8px; flex-wrap:wrap; align-items:center;">
                    ${!isDone ? `
                    <button class="btn-primary job-ctrl-btn" data-action="pause" data-id="${job.job_id}" style="padding:6px 12px; font-size:0.85rem; background:#f5a623;" ${isPaused ? 'disabled' : ''}>Pause</button>
                    <button class="btn-primary job-ctrl-btn" data-action="resume" data-id="${job.job_id}" style="padding:6px 12px; font-size:0.85rem; background:#34c759;" ${isRunning ? 'disabled' : ''}>Resume</button>
                    <button class="btn-primary job-ctrl-btn" data-action="stop" data-id="${job.job_id}" style="padding:6px 12px; font-size:0.85rem; background:#ff3b30;">Stop</button>
                    ` : `
                    <button class="btn-primary" onclick="dismissJob('${job.job_id}')" style="padding:6px 12px; font-size:0.85rem; background:transparent; border:1px solid #c7c7cc; color:#86868b;">Close</button>
                    `}
                    <a href="/status?id=${job.job_id}" class="btn-primary" style="padding:6px 12px; font-size:0.85rem; background:#0071e3; text-decoration:none;">Status View</a>
                </div>
            </div>`;
        });
        html += '</div>';
        jobsContainer.innerHTML = html;
        
        document.querySelectorAll('.job-ctrl-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const action = e.target.getAttribute('data-action');
                const id = e.target.getAttribute('data-id');
                await fetch(`/api/crawler/${action}/${id}`, { method: 'POST' });
                if (window.refreshMetricsNative) window.refreshMetricsNative();
                if (window.updateHistoryList) window.updateHistoryList();
            });
        });
    };

    // Extract ID from URL for targeted telemetry internally
    const urlParams = new URLSearchParams(window.location.search);
    const targetIdFromUrl = urlParams.get('id');
    const jobIdInput = document.getElementById('active-job-id');
    const clearJobIdBtn = document.getElementById('clear-job-id');
    const btnLoadStatus = document.getElementById('btn-load-status');
    const viewTitle = document.getElementById('view-title');
    const logsTitle = document.getElementById('logs-title');

    if (targetIdFromUrl && jobIdInput) {
        jobIdInput.value = targetIdFromUrl;
    }
    
    if (jobIdInput && clearJobIdBtn) {
        if(jobIdInput.value.trim() !== '') clearJobIdBtn.style.display = 'block';
        jobIdInput.addEventListener('input', () => {
            clearJobIdBtn.style.display = jobIdInput.value.trim() !== '' ? 'block' : 'none';
        });
        clearJobIdBtn.addEventListener('click', () => {
            jobIdInput.value = '';
            clearJobIdBtn.style.display = 'none';
            if (targetIdFromUrl) window.location.href = '/status';
        });
    }

    if (btnLoadStatus) {
        btnLoadStatus.addEventListener('click', () => {
            const given = jobIdInput.value.trim();
            if (given) window.location.href = `/status?id=${given}`;
            else window.location.href = `/status`;
        });
    }

    // Status / Observability Telemetry Polling (Every 2 seconds)
    const metricQueue = document.getElementById('metric-queue');
    if (metricQueue || jobsContainer) {
        const fetchMetrics = async () => {
            try {
                const jobIdInputEl = document.getElementById('active-job-id');
                const activeJobId = jobIdInputEl ? jobIdInputEl.value.trim() : null;
                
                let endpoint = '/api/metrics';
                if (activeJobId && metricQueue) {
                    endpoint = `/api/crawler/status/${activeJobId}`;
                }
                
                const res = await fetch(endpoint);
                const data = await res.json();
                
                    if (metricQueue) {
                        if (data.backpressure_status) {
                            let bpColor = '#34c759', bpBg = 'rgba(52, 199, 89, 0.1)';
                            if (data.backpressure_status === 'Back-pressure Active') { bpColor = '#f5a623'; bpBg = 'rgba(245, 166, 35, 0.1)'; }
                            else if (data.backpressure_status.includes('Critical')) { bpColor = '#ff3b30'; bpBg = 'rgba(255, 59, 48, 0.1)'; }
                            metricQueue.innerHTML = `${data.queue_size} <div style="margin-top:10px; display:flex; flex-direction:column; align-items:center; gap:6px;"><span style="padding:6px 14px; border-radius:14px; font-size:1rem; font-weight:600; color:${bpColor}; background:${bpBg};">${data.backpressure_status} (${data.queue_utilization}%)</span><span style="font-size:0.9rem; color:#86868b; font-weight:normal;">Throttling: ${data.throttling_status}</span></div>`;
                        } else {
                            metricQueue.textContent = data.queue_size;
                        }
                        
                        document.getElementById('metric-visited').textContent = data.total_visited;
                        document.getElementById('metric-workers').textContent = data.active_workers ?? (data.is_running ? '1' : '0');
                    
                    const logList = document.getElementById('log-list');
                    const queueList = document.getElementById('queue-list');
                    const queueTitle = document.getElementById('queue-title');
                    
                    if (logList) logList.innerHTML = '';
                    if (queueList) queueList.innerHTML = '';
                    
                    // Display top live URLs if targeted recursively
                    if (activeJobId && data.top_live_urls) {
                        if (viewTitle) viewTitle.textContent = "Targeted Job Telemetry";
                        if (logsTitle) logsTitle.textContent = "Live Processing Logs";
                        if (queueTitle) queueTitle.textContent = "Live Queue Stream";

                        if (queueList) {
                            if (data.current_url) {
                                queueList.innerHTML += `<li style="color:#34c759; margin-bottom:8px; display:block;"><span style="font-weight:600; padding:4px 8px; border-radius:4px; background:rgba(52, 199, 89, 0.1);">[ACTIVE]</span> <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:85%; display:inline-block; vertical-align:middle;">${data.current_url}</span></li>`;
                            }
                            if (data.top_live_urls.length === 0) {
                                queueList.innerHTML += '<li style="color:#86868b;">Queue is currently empty. Waiting for jobs...</li>';
                            }
                            data.top_live_urls.forEach(u => {
                                queueList.innerHTML += `<li style="color:#86868b; display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"><span style="font-family:monospace; margin-right:4px;">[QUEUED]</span> ${u}</li>`;
                            });
                        }
                    } else if (data.jobs !== undefined) {
                        if (viewTitle) viewTitle.textContent = "Global System Overview";
                        if (logsTitle) logsTitle.textContent = "Processing Logs";
                        if (queueTitle) queueTitle.textContent = "Active System Jobs";

                        if (queueList) {
                            if (data.jobs.length === 0) {
                                queueList.innerHTML += '<li style="color:var(--text-secondary);">No running background tasks.</li>';
                            }
                            data.jobs.forEach(j => {
                                const originUrl = j.seed_url || j.origin || "Origin unavailable";
                                let bpBadge = '';
                                if (j.backpressure_status) {
                                    let bpColor = '#34c759', bpBg = 'rgba(52, 199, 89, 0.1)';
                                    if (j.backpressure_status === 'Back-pressure Active') { bpColor = '#f5a623'; bpBg = 'rgba(245, 166, 35, 0.1)'; }
                                    else if (j.backpressure_status.includes('Critical')) { bpColor = '#ff3b30'; bpBg = 'rgba(255, 59, 48, 0.1)'; }
                                    bpBadge = `<div style="margin-top:10px; display:flex; align-items:center; gap:10px;"><span style="padding:4px 12px; border-radius:14px; font-size:0.85rem; font-weight:600; color:${bpColor}; background:${bpBg};">Health: ${j.backpressure_status} (${j.queue_utilization}%)</span><span style="font-size:0.85rem; color:#86868b;">Throttling: ${j.throttling_status}</span></div>`;
                                }
                                queueList.innerHTML += `<li style="display:flex; justify-content:space-between; margin-bottom:10px; padding-bottom:10px; border-bottom:1px solid rgba(0,0,0,0.05);"><div style="width:100%;"><span class="copy-uuid" data-uuid="${j.job_id}" style="color:#0071e3; font-weight:600; cursor:pointer;" title="Click to copy UUID">ID: ${j.job_id}</span><br><span style="color:#86868b; font-size:0.85rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:block;">${originUrl}</span>${bpBadge}</div><span style="color:${j.state === 'Running' ? '#34c759' : '#f5a623'}; font-weight:600; font-size:0.85rem;">${j.state}</span></li>`;
                            });
                        }
                    }
                    
                    if(data.logs.length === 0 && (!data.jobs || data.jobs.length === 0)) {
                        logList.innerHTML += '<li>System idling... listening for worker telemetry loops.</li>';
                    }
                    
                    const recentLogs = [...data.logs].reverse();
                    recentLogs.forEach(log => {
                        const li = document.createElement('li');
                        const d = new Date(log.timestamp * 1000).toLocaleTimeString();
                        li.textContent = `[${d}] [${log.level}] ${log.message}`;
                        logList.appendChild(li);
                    });

                    // Manage dynamic state visual feedback in status page.
                    const statusBox = document.getElementById('job-current-status');
                    const seedRefBox = document.getElementById('seed-url-reference');
                    const seedLink = document.getElementById('seed-link');
                    
                    if (statusBox) {
                        if (activeJobId) {
                            const isJobEndpoint = !!data.job_id;
                            let jobState = 'Unknown';
                            if (isJobEndpoint) {
                                 jobState = data.state || (data.is_running ? 'Running' : 'Paused');
                                 if (data.seed_url && seedRefBox) {
                                     seedRefBox.style.display = 'block';
                                     seedLink.href = data.seed_url;
                                     seedLink.textContent = data.seed_url;
                                 }
                            }
                            
                            statusBox.textContent = `Target: ${activeJobId} (${jobState})`;
                            
                            if (jobState === 'Completed') {
                                statusBox.style.background = '#34c759';
                                statusBox.style.color = '#fff';
                            } else if (jobState === 'Error') {
                                statusBox.style.background = '#ff3b30';
                                statusBox.style.color = '#fff';
                            } else if (jobState === 'Stopped' || jobState === 'Paused') {
                                statusBox.style.background = '#f5a623';
                                statusBox.style.color = '#fff';
                            } else {
                                statusBox.style.background = 'var(--accent)';
                                statusBox.style.color = '#fff';
                            }
                            
                            if (['Completed', 'Error', 'Stopped'].includes(jobState)) {
                                if (window.telemetryInterval) {
                                    clearInterval(window.telemetryInterval);
                                    window.telemetryInterval = null;
                                }
                                const btnPause = document.getElementById('btn-pause');
                                const btnResume = document.getElementById('btn-resume');
                                const btnStop = document.getElementById('btn-stop');
                                if(btnPause) btnPause.disabled = true;
                                if(btnResume) btnResume.disabled = true;
                                if(btnStop) btnStop.disabled = true;
                            }
                        } else {
                            statusBox.textContent = `Global Multi-Worker Mode`;
                            statusBox.style.color = '#34c759';
                            statusBox.style.background = 'rgba(52, 199, 89, 0.1)';
                            if (seedRefBox) seedRefBox.style.display = 'none';
                        }
                    }
                }
                
                if (jobsContainer) {
                    updateJobsList(data.jobs || []);
                }
            } catch (err) {
                console.error("Telemetry fetch error native:", err);
            }
        };
        window.refreshMetricsNative = fetchMetrics;
        fetchMetrics();
        window.telemetryInterval = setInterval(fetchMetrics, 2000); 
    }

    // Job Controls on Status Page
    const controlAction = async (action) => {
        const jobId = document.getElementById('active-job-id').value.trim();
        const msg = document.getElementById('control-msg');
        if (!jobId) {
            msg.textContent = "Please enter a Job ID.";
            msg.style.color = "#ff3b30";
            return;
        }
        try {
            const res = await fetch(`/api/crawler/${action}/${jobId}`, { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                const pastTense = action === 'stop' ? 'stopped' : action + 'd';
                msg.textContent = `Success: Worker ${pastTense}.`;
                msg.style.color = "#34c759";
            } else {
                msg.textContent = `Error: ${data.detail || 'Action failed'}`;
                msg.style.color = "#ff3b30";
            }
        } catch(err) {
            msg.textContent = `Error: ${err.message}`;
            msg.style.color = "#ff3b30";
        }
        setTimeout(() => msg.textContent = "", 3000);
    };

    const btnPause = document.getElementById('btn-pause');
    if (btnPause) {
        btnPause.addEventListener('click', () => controlAction('pause'));
        document.getElementById('btn-resume').addEventListener('click', () => controlAction('resume'));
        document.getElementById('btn-stop').addEventListener('click', () => controlAction('stop'));
    }

    // Search Engine Handling via API bridge natively utilizing limits and offsets organically
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        let currentOffset = 0;
        let activeQuery = "";
        const limitPerPage = 10;
        
        const fetchResults = async () => {
            const query = document.getElementById('query').value;
            const loader = document.getElementById('results-loader');
            const resultsBox = document.getElementById('search-results');
            const statsText = document.getElementById('search-stats');
            
            const btnPrevBlock = document.getElementById('btn-prev');
            const btnNextBlock = document.getElementById('btn-next');
            const pgIndicator = document.getElementById('pagination-state-indicator');
            const pgContainer = document.getElementById('pagination-container');
            
            activeQuery = query;
            loader.classList.remove('hidden');
            statsText.classList.add('hidden');
            resultsBox.innerHTML = '';
            if (pgContainer) pgContainer.classList.add('hidden');
            
            try {
                const res = await fetch(`/api/search?query=${encodeURIComponent(query)}&limit=${limitPerPage}&offset=${currentOffset}`);
                const data = await res.json();
                
                loader.classList.add('hidden');
                
                if (data.results.length === 0 && currentOffset === 0) {
                    resultsBox.innerHTML = '<p style="text-align:center; color:#86868b; margin-top:20px;">No match indices found in localized Trie.</p>';
                    return;
                }
                
                const total = data.total_results || 0;
                statsText.textContent = `Found ${total} result(s) for '${query}'`;
                statsText.classList.remove('hidden');
                
                data.results.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'result-item fade-in';
                    
                    div.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 4px;">
                            <a href="${item.url}" target="_blank" style="font-size:1.25rem; font-weight:600; color:#000; text-decoration:none; display:inline-block; word-wrap: break-word; overflow-wrap: anywhere;">${item.title || item.url}</a>
                            <span style="font-size:0.85rem; padding:4px 8px; background:rgba(0,113,227,0.1); color:var(--accent); border-radius:12px; font-weight:600; white-space:nowrap; flex-shrink:0; margin-left:12px;">Matches: ${item.frequency}</span>
                        </div>
                        <div style="font-size:0.85rem; color:#006621; margin-bottom: 6px; word-wrap: break-word; overflow-wrap: anywhere;">${item.url}</div>
                        <div style="font-size:0.95rem; color:#4d5156; line-height: 1.5; word-wrap: break-word; overflow-wrap: anywhere;">${item.snippet ? item.snippet + '...' : 'No text snippet available.'}</div>
                        
                        <div class="origin-text" style="color:var(--text-secondary); margin-top:16px; font-size:0.85rem; padding-top:12px; border-top:1px solid rgba(0,0,0,0.05); display:block; text-align:right;">
                            Originated from: <a href="${item.origin}" target="_blank" style="color:var(--text-secondary); text-decoration:underline; word-wrap: break-word; overflow-wrap: anywhere;">${item.origin}</a> <br><span style="font-size:0.75rem; opacity:0.7;">(Depth: ${item.depth})</span>
                        </div>
                    `;
                    resultsBox.appendChild(div);
                });
                
                if (pgContainer && total > limitPerPage) {
                    pgContainer.classList.remove('hidden');
                    
                    let currentPage = Math.floor(currentOffset / limitPerPage) + 1;
                    let totalPages = Math.ceil(total / limitPerPage);
                    
                    let startCount = currentOffset + 1;
                    let endCount = Math.min(currentOffset + limitPerPage, total);
                    pgIndicator.textContent = `Showing ${startCount}-${endCount} of ${total} (Page ${currentPage} of ${totalPages})`;
                    
                    btnPrevBlock.disabled = currentOffset <= 0;
                    btnNextBlock.disabled = currentOffset + limitPerPage >= total;
                    
                    if(btnPrevBlock.disabled) btnPrevBlock.style.opacity = '0.5';
                    else btnPrevBlock.style.opacity = '1';
                    
                    if(btnNextBlock.disabled) btnNextBlock.style.opacity = '0.5';
                    else btnNextBlock.style.opacity = '1';
                }
                
            } catch (err) {
                loader.classList.add('hidden');
                resultsBox.innerHTML = `<p style="text-align:center; color:red;">Engine traversal error encountered</p>`;
            }
        };

        const queryInput = document.getElementById('query');
        const btnClearSearch = document.getElementById('btn-clear-search');
        
        queryInput.addEventListener('input', () => {
            if(queryInput.value.length > 0) {
                btnClearSearch.style.display = 'block';
            } else {
                btnClearSearch.style.display = 'none';
            }
        });
        
        if (btnClearSearch) {
            btnClearSearch.addEventListener('click', () => {
                queryInput.value = '';
                btnClearSearch.style.display = 'none';
                document.getElementById('search-results').innerHTML = '';
                const statsText = document.getElementById('search-stats');
                if (statsText) statsText.classList.add('hidden');
                const pgContainer = document.getElementById('pagination-container');
                if (pgContainer) pgContainer.classList.add('hidden');
                
                // Reset URL params natively
                const url = new URL(window.location);
                url.searchParams.delete('query');
                window.history.replaceState({}, '', url);
            });
        }

        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            currentOffset = 0;
            
            // Set URL param natively for sharing
            const url = new URL(window.location);
            url.searchParams.set('query', queryInput.value);
            window.history.replaceState({}, '', url);
            
            fetchResults();
        });
        
        // Auto-run search if query in URL natively
        const queryFromUrl = new URLSearchParams(window.location.search).get('query');
        if (queryFromUrl) {
            queryInput.value = queryFromUrl;
            btnClearSearch.style.display = 'block';
            fetchResults();
        }
        
        // Ensure Enter key triggers search properly without submit button.
        queryInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                currentOffset = 0;
                const url = new URL(window.location);
                url.searchParams.set('query', queryInput.value);
                window.history.replaceState({}, '', url);
                fetchResults();
            }
        });
        
        const btnPrevBlock = document.getElementById('btn-prev');
        const btnNextBlock = document.getElementById('btn-next');
        
        if (btnPrevBlock) {
            btnPrevBlock.addEventListener('click', () => {
                if (currentOffset >= limitPerPage) {
                    currentOffset -= limitPerPage;
                    fetchResults();
                }
            });
        }
        if (btnNextBlock) {
            btnNextBlock.addEventListener('click', () => {
                currentOffset += limitPerPage;
                fetchResults();
            });
        }
    }
});
