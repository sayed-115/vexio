const urlInput = document.getElementById('url-input');
const fetchBtn = document.getElementById('fetch-btn');
const fetchSpinner = document.getElementById('fetch-spinner');
const btnText = document.querySelector('.btn-text');
const errorMessage = document.getElementById('error-message');

const resultsSection = document.getElementById('results-section');
const mediaThumb = document.getElementById('media-thumb');
const mediaTitle = document.getElementById('media-title');
const videoOptions = document.getElementById('video-options');

const progressSection = document.getElementById('progress-section');
const progressFill = document.getElementById('progress-fill');
const percentText = document.getElementById('percent-text');
const statusText = document.getElementById('status-text');
const actionArea = document.getElementById('action-area');
const saveFileBtn = document.getElementById('save-file-btn');
const resetBtn = document.getElementById('reset-btn');

let currentUrl = '';

fetchBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) return;

    // Reset UI
    resultsSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    errorMessage.classList.add('hidden');
    
    // Loading State
    fetchBtn.disabled = true;
    btnText.classList.add('hidden');
    fetchSpinner.classList.remove('hidden');

    try {
        const response = await fetch('/api/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Failed to fetch metadata");
        }

        const data = await response.json();
        currentUrl = url;
        
        // Populate Data
        mediaTitle.textContent = data.title;
        mediaThumb.src = data.thumbnail || '';
        
        // Build Video Resolution Buttons
        videoOptions.innerHTML = '';
        data.resolutions.forEach(res => {
            let label = `${res}p`;
            if (res === 2160) label = '4K (2160p)';
            if (res === 4320) label = '8K (4320p)';
            
            const btn = document.createElement('button');
            btn.className = 'opt-btn video-btn';
            btn.textContent = `${label} Video`;
            btn.onclick = () => startDownload(res.toString(), false);
            videoOptions.appendChild(btn);
        });

        resultsSection.classList.remove('hidden');
    } catch (err) {
        errorMessage.textContent = err.message;
        errorMessage.classList.remove('hidden');
    } finally {
        fetchBtn.disabled = false;
        btnText.classList.remove('hidden');
        fetchSpinner.classList.add('hidden');
    }
});

// Bind audio buttons
document.querySelectorAll('.audio-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        startDownload(e.target.dataset.id, true);
    });
});

async function startDownload(formatId, isAudio) {
    resultsSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    
    // Reset Progress UI
    progressFill.style.width = '0%';
    percentText.textContent = '0%';
    statusText.textContent = 'Initializing download engine...';
    actionArea.classList.add('hidden');
    
    try {
        const res = await fetch('/api/prepare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: currentUrl, format_id: formatId, is_audio: isAudio })
        });
        
        if (!res.ok) throw new Error("Failed to start download job");
        const data = await res.json();
        pollProgress(data.job_id);
        
    } catch (err) {
        statusText.textContent = `Error: ${err.message}`;
        statusText.classList.remove('pulse');
        statusText.style.color = '#FF4444';
    }
}

async function pollProgress(jobId) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/api/progress/${jobId}`);
            if (!res.ok) return;
            const job = await res.json();
            
            if (job.status === 'downloading') {
                progressFill.style.width = `${job.percent}%`;
                percentText.textContent = `${job.percent}%`;
                statusText.textContent = 'Downloading media segments...';
            } else if (job.status === 'merging') {
                progressFill.style.width = `100%`;
                percentText.textContent = `100%`;
                statusText.textContent = 'Stitching high-quality audio & video perfectly...';
            } else if (job.status === 'finished') {
                clearInterval(interval);
                progressFill.style.width = `100%`;
                percentText.textContent = `100%`;
                statusText.textContent = 'Processing Complete!';
                statusText.classList.remove('pulse');
                
                // Show Save button
                saveFileBtn.href = `/api/serve/${jobId}`;
                actionArea.classList.remove('hidden');
            } else if (job.status === 'error') {
                clearInterval(interval);
                statusText.textContent = `Processing failed: ${job.error}`;
                statusText.classList.remove('pulse');
                statusText.style.color = '#FF4444';
            }
            
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 1000);
}

resetBtn.addEventListener('click', () => {
    urlInput.value = '';
    progressSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
});
