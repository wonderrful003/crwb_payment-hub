/* ========================================
   INDEX.JS — Upload, History, Detail, Polling
   Used in index.html
======================================== */

// ── Upload panel JS ──
const uploadArea      = document.getElementById('uploadArea');
const fileInput       = document.getElementById('id_excel_file');
const feedback        = document.getElementById('fileFeedback');
const fileIconEl      = document.getElementById('fileIcon');
const fileMsg         = document.getElementById('fileMsg');
const submitBtn       = document.getElementById('submitBtn');
const templateWarning = document.getElementById('templateWarning');
const templateWarnMsg = document.getElementById('templateWarningMsg');
const missingColsList = document.getElementById('missingColsList');
const paymentTypeEl   = document.getElementById('id_payment_type');

const ALLOWED_EXT = ['.xlsx', '.xls'];
const MAX_SIZE_MB = 10;

// ── Required columns per payment type ──
const TEMPLATE_COLUMNS = {
    salary: {
        label: 'Salary Payment',
        required: ['Trans Serial','Vote Num','Currency','Debit Account Num','Bank Name',
                   'Funding TRF Num','Credit Account Num','Credit Account Name',
                   'Payee BIC','Cost Center','Description','Amount','Value Date']
    },
    supplier: {
        label: 'Supplier Payment',
        required: ['Currency','Debit Account Num','Debit Account Name','Payment Amount',
                   'Payee Details','Invoice Num','Payee BIC','Credit Account Num',
                   'Cost Center','Description']
    },
    remittancePRN: {
        label: 'Remittance PRN',
        required: ['Debit Account Num','Debit Account Name','Currency','Credit Account Num',
                   'Payment Amount','Creditor Name','Payment Date','Date Created',
                   'Cost Centre','PRN']
    },
    remittanceTR: {
        label: 'Remittance TR',
        required: ['Debit Account Num','Debit Account Name','Currency','Credit Account Num',
                   'Payment Amount','Creditor Name','Payment Date','Date created','Cost Centre']
    },
    foreign: {
        label: 'Foreign Payment',
        required: ['Trans Serial','Currency','Debit Account','Account Name','Amount',
                   'Amount in words','Payee Details1','Payee Details2','Invoice Number',
                   'Bank Branch Code','Payee BIC','Credit Account','Cost Center',
                   'Approval Date','Surname','First Name','Sector Code',
                   'Industrial Class','BOP Category']
    }
};

let templateValid = null;

function setDropZoneState(state, filename) {
    const dropText = document.getElementById('dropText');
    const dropIcon = document.getElementById('dropIcon');
    if (!dropText || !dropIcon) return;
    if (state === 'selected') {
        dropIcon.innerHTML = '<i class="fas fa-file-excel" style="color:#10b981"></i>';
        dropText.innerHTML = `<strong style="color:var(--text-primary)">${filename}</strong> <span style="font-size:11px;color:var(--text-muted);display:block;margin-top:2px">Click to change file</span>`;
        uploadArea.style.borderColor = '#10b981';
        uploadArea.style.background = '#f0fdf4';
    } else if (state === 'error') {
        dropIcon.innerHTML = '<i class="fas fa-exclamation-triangle" style="color:var(--danger)"></i>';
        dropText.innerHTML = `<strong style="color:var(--danger)">Wrong template</strong> <span style="font-size:11px;color:var(--text-muted);display:block;margin-top:2px">Click to choose a different file</span>`;
        uploadArea.style.borderColor = 'var(--danger)';
        uploadArea.style.background = '#fef2f2';
    } else {
        dropIcon.innerHTML = '<i class="fas fa-cloud-upload-alt"></i>';
        dropText.innerHTML = 'Click to browse or drag &amp; drop';
        uploadArea.style.borderColor = '';
        uploadArea.style.background = '';
    }
}

function setFeedback(type, iconClass, message) {
    if (!feedback) return;
    feedback.style.display = 'block';
    feedback.style.background = type === 'success' ? '#f0fdf4' : '#fef2f2';
    feedback.style.color      = type === 'success' ? 'var(--success)' : 'var(--danger)';
    feedback.style.border     = type === 'success' ? '1px solid #bbf7d0' : '1px solid #fecaca';
    fileIconEl.className = `fas ${iconClass}`;
    fileMsg.textContent  = message;
}

function clearFeedback() {
    if (feedback) {
        feedback.style.display = 'none';
        fileMsg.textContent = '';
    }
    setDropZoneState('idle');
}

function clearTemplateWarning() {
    if (templateWarning) {
        templateWarning.style.display = 'none';
        templateValid = null;
    }
}

function resetUploadForm() {
    if (fileInput) {
        fileInput.value = '';
    }
    if (paymentTypeEl) {
        paymentTypeEl.selectedIndex = 0;
    }
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Process File';
    }
    clearFeedback();
    clearTemplateWarning();
}

function showTemplateWarning(paymentLabel, missing) {
    if (!templateWarning) return;
    templateWarning.style.display = 'block';
    templateWarnMsg.textContent =
        `This file doesn't look like a "${paymentLabel}" template. ` +
        `${missing.length} required column${missing.length > 1 ? 's are' : ' is'} missing.`;
    missingColsList.innerHTML = missing.map(c =>
        `<span style="display:inline-block;background:#fef3c7;border:1px solid #fde68a;border-radius:4px;padding:1px 7px;margin:2px 3px 2px 0;font-size:11.5px">${c}</span>`
    ).join('');
}

function readExcelColumns(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => {
            try {
                const data  = new Uint8Array(e.target.result);
                const wb    = XLSX.read(data, { type: 'array', sheetRows: 2 });
                const ws    = wb.Sheets[wb.SheetNames[0]];
                const rows  = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });
                const cols  = (rows[0] || []).map(c => String(c).replace(/\t/g, '').trim().replace(/\s+/g, ' '));
                resolve(cols);
            } catch (err) {
                reject(err);
            }
        };
        reader.onerror = () => reject(new Error('Could not read file'));
        reader.readAsArrayBuffer(file);
    });
}

async function validateFile(file) {
    clearTemplateWarning();
    if (!file) {
        clearFeedback();
        submitBtn.disabled = false;
        return false;
    }

    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!ALLOWED_EXT.includes(ext)) {
        setFeedback('error', 'fa-times-circle',
            `"${file.name}" is not a valid file. Please upload an Excel file (.xlsx or .xls).`);
        submitBtn.disabled = true;
        fileInput.value = '';
        return false;
    }

    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        setFeedback('error', 'fa-times-circle',
            `"${file.name}" is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum size is ${MAX_SIZE_MB} MB.`);
        submitBtn.disabled = true;
        fileInput.value = '';
        return false;
    }

    setFeedback('success', 'fa-check-circle', file.name);
    setDropZoneState('selected', file.name);
    submitBtn.disabled = false;

    const paymentType = paymentTypeEl ? paymentTypeEl.value : null;
    const tpl = paymentType ? TEMPLATE_COLUMNS[paymentType] : null;
    if (tpl && typeof XLSX !== 'undefined') {
        try {
            setFeedback('success', 'fa-spinner fa-pulse', `Reading "${file.name}"…`);
            const cols = await readExcelColumns(file);
            const colsLower = cols.map(c => c.toLowerCase());
            const missing   = tpl.required.filter(req =>
                !colsLower.includes(req.toLowerCase())
            );

            if (missing.length > 0) {
                templateValid = false;
                showTemplateWarning(tpl.label, missing);
                setFeedback('error', 'fa-exclamation-triangle',
                    `"${file.name}" — template mismatch (see warning below)`);
                setDropZoneState('error', file.name);
                submitBtn.disabled = true;
            } else {
                templateValid = true;
                setFeedback('success', 'fa-check-circle',
                    `"${file.name}" — columns verified ✓`);
                setDropZoneState('selected', file.name);
                submitBtn.disabled = false;
            }
        } catch (err) {
            templateValid = null;
            setFeedback('success', 'fa-check-circle', file.name);
            console.warn('Could not read Excel headers:', err);
        }
    }

    return true;
}

// ── Event Listeners ──
if (paymentTypeEl) {
    paymentTypeEl.addEventListener('change', () => {
        const currentFile = fileInput.files[0];
        if (currentFile) {
            validateFile(currentFile);
        }
    });
}

if (uploadArea && fileInput) {
    uploadArea.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        fileInput.click();
    });

    uploadArea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInput.click();
        }
    });

    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
        
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) {
            const dt = new DataTransfer();
            dt.items.add(droppedFile);
            fileInput.files = dt.files;
            validateFile(droppedFile);
        }
    });

    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            validateFile(file);
        } else {
            clearFeedback();
            submitBtn.disabled = false;
        }
    });
}

const uploadForm = document.getElementById('uploadForm');
if (uploadForm && fileInput) {
    uploadForm.addEventListener('submit', function(e) {
        const file = fileInput.files[0];

        if (!file) {
            e.preventDefault();
            setFeedback('error', 'fa-times-circle', 'Please select an Excel file before submitting.');
            return;
        }

        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        if (!ALLOWED_EXT.includes(ext)) {
            e.preventDefault();
            setFeedback('error', 'fa-times-circle',
                `"${file.name}" is not a valid file. Please upload an .xlsx or .xls file.`);
            return;
        }

        if (templateValid === false) {
            e.preventDefault();
            if (templateWarning) {
                templateWarning.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> Processing…';
    });
}

// ── Error modal ──
function showError(id, msg) {
    document.getElementById('errorJobId').textContent = id;
    document.getElementById('errorText').textContent  = msg;
    new bootstrap.Modal(document.getElementById('errorModal')).show();
}

// ── History inline filters ──
function histApplyFilters() {
    const statusF  = document.getElementById('histStatusFilter').value.toLowerCase();
    const paymentF = document.getElementById('histPaymentFilter').value.toLowerCase();
    const searchF  = document.getElementById('histSearch').value.toLowerCase();

    document.querySelectorAll('#histTable tbody tr[data-status]').forEach(row => {
        const matchStatus  = !statusF  || row.dataset.status.toLowerCase()  === statusF;
        const matchPayment = !paymentF || row.dataset.type.toLowerCase()     === paymentF;
        const matchSearch  = !searchF  || row.dataset.search.includes(searchF);
        row.style.display = (matchStatus && matchPayment && matchSearch) ? '' : 'none';
    });
}

function histReset() {
    document.getElementById('histStatusFilter').value  = '';
    document.getElementById('histPaymentFilter').value = '';
    document.getElementById('histSearch').value        = '';
    histApplyFilters();
}

// ── Job detail loader ──
// JOB_DATA is injected from Django template
const JOB_DATA = window.JOB_DATA || {};

function loadDetail(jobId) {
    showPanel('detail');
    const job = JOB_DATA[String(jobId)];

    if (!job) {
        document.getElementById('detail-content').innerHTML = '<div class="alert alert-danger">Job not found.</div>';
        return;
    }

    const statusBadge =
        job.status === 'SUCCESS' ? '<span class="badge-status badge-success"><i class="fas fa-check-circle"></i> Success</span>' :
        job.status === 'FAILED'  ? '<span class="badge-status badge-danger"><i class="fas fa-times-circle"></i> Failed</span>' :
                                   '<span class="badge-status badge-pending"><i class="fas fa-spinner fa-pulse"></i> Pending</span>';

    const downloadSection = job.download ? `
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:10px;">
            <span style="font-size:13px;color:var(--text-muted);font-weight:500;">Download as:</span>
            <a href="${job.download}?format=csv" class="btn-primary-custom" style="text-decoration:none;padding:6px 14px;font-size:12px;background:#217346;">
                <i class="fas fa-file-csv"></i> CSV
            </a>
            <a href="${job.download}?format=txt" class="btn-primary-custom" style="text-decoration:none;padding:6px 14px;font-size:12px;background:#6b7280;">
                <i class="fas fa-file-alt"></i> TXT
            </a>
            <a href="${job.download}?format=xlsx" class="btn-primary-custom" style="text-decoration:none;padding:6px 14px;font-size:12px;background:#1a6e3a;">
                <i class="fas fa-file-excel"></i> Excel
            </a>
            <span style="font-size:10px;color:var(--text-muted);margin-left:4px;">(default: CSV)</span>
        </div>
    ` : '';

    const errorBlock = job.error
        ? `<div class="alert alert-danger mt-3"><strong><i class="fas fa-exclamation-triangle me-2"></i>Error</strong><pre style="white-space:pre-wrap;margin:8px 0 0;font-size:12.5px">${job.error}</pre></div>`
        : '';

    let previewBlock = '';
    if (job.preview && job.preview.columns && job.preview.rows && job.preview.rows.length > 0) {

        let rows    = job.preview.rows.map(r => ({ ...r }));
        let columns = [...job.preview.columns];

        const refColIdx = columns.findIndex(c => c.toLowerCase().includes('reference'));
        const refCol    = refColIdx !== -1 ? columns[refColIdx] : null;

        if (job.reference_range && refCol) {
            const firstRef    = job.reference_range.split(/\s*[–\-]\s*/)[0].trim();
            const prefixMatch = firstRef.match(/^([A-Z]+)(\d+)$/);
            if (prefixMatch) {
                const refPrefix = prefixMatch[1];
                const firstNum  = parseInt(prefixMatch[2], 10);
                rows = rows.map((row, i) => {
                    const val = String(row[refCol] ?? '').trim();
                    if (!val) {
                        row[refCol] = `${refPrefix}${String(firstNum + i).padStart(8, '0')}`;
                    }
                    return row;
                });
            }
        }

        if (refCol && columns[0] !== refCol) {
            columns = [refCol, ...columns.filter(c => c !== refCol)];
        }

        const headerCells = columns.map(c => `<th style="white-space:nowrap">${c}</th>`).join('');
        const bodyRows = rows.map(row => {
            const cells = columns.map(c => {
                const val = String(row[c] ?? '').trim();
                const display = val.substring(0, 40) || '<span style="color:#cbd5e1">—</span>';
                return `<td>${display}</td>`;
            }).join('');
            return `<tr>${cells}</tr>`;
        }).join('');

        previewBlock = `
            <div class="card mt-4">
                <div class="card-header-custom">
                    <h5><i class="fas fa-table me-2" style="color:var(--accent)"></i>Data Preview — first 10 rows</h5>
                    ${job.preview.total_rows > 10 ? `<span style="font-size:12px;color:var(--text-muted)">${job.preview.total_rows} total rows</span>` : ''}
                </div>
                <div style="overflow-x:auto">
                    <table class="table mb-0" style="font-size:12px">
                        <thead><tr>${headerCells}</tr></thead>
                        <tbody>${bodyRows}</tbody>
                    </table>
                </div>
            </div>`;
    }

    document.getElementById('detail-content').innerHTML = `
        <div class="card">
            <div class="card-header-custom">
                <h5><i class="fas fa-file-alt me-2" style="color:var(--accent)"></i>Job #${job.id}</h5>
            </div>
            <div style="padding:20px">
                <div class="info-row"><span class="info-label">Payment Type</span><span class="info-val">${job.type}</span></div>
                <div class="info-row"><span class="info-label">Status</span><span class="info-val">${statusBadge}</span></div>
                <div class="info-row"><span class="info-label">Total Records</span><span class="info-val">${job.records}</span></div>
                ${job.reference_range ? `<div class="info-row"><span class="info-label">References</span><span class="info-val" style="font-family:monospace;font-size:13px">${job.reference_range}</span></div>` : ''}
                <div class="info-row"><span class="info-label">Uploaded By</span><span class="info-val">${job.user}</span></div>
                <div class="info-row"><span class="info-label">Created At</span><span class="info-val">${job.created}</span></div>
                <div class="info-row"><span class="info-label">Completed At</span><span class="info-val">${job.completed}</span></div>
                ${downloadSection ? `<div class="info-row"><span class="info-label">Download</span><span class="info-val">${downloadSection}</span></div>` : ''}
            </div>
            ${errorBlock}
        </div>
        ${previewBlock}`;
}

// ── Live stats polling ──
(function() {
    const STATS_URL = document.body.dataset.statsUrl || '/api/stats/';
    const POLL_MS   = 60000;

    const elMap = {
        total_jobs:      document.getElementById('stat-total-jobs'),
        successful:      document.getElementById('stat-successful'),
        failed:          document.getElementById('stat-failed'),
        total_processed: document.getElementById('stat-total-processed'),
    };

    function animateUpdate(el, newVal) {
        if (!el || el.textContent === String(newVal)) return;
        el.textContent = newVal;
        el.style.transition = 'opacity 0.15s';
        el.style.opacity = '0.3';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                el.style.opacity = '1';
            });
        });
    }

    function isDashboardVisible() {
        if (document.hidden) return false;
        const panel = document.getElementById('panel-dashboard');
        return panel && panel.classList.contains('active');
    }

    async function fetchStats() {
        if (!isDashboardVisible()) return;
        try {
            const res  = await fetch(STATS_URL, { credentials: 'same-origin' });
            if (!res.ok) return;
            const data = await res.json();
            animateUpdate(elMap.total_jobs,      data.total_jobs);
            animateUpdate(elMap.successful,      data.successful);
            animateUpdate(elMap.failed,          data.failed);
            animateUpdate(elMap.total_processed, data.total_processed);
        } catch (_) { /* silently ignore network errors */ }
    }

    setInterval(fetchStats, POLL_MS);

    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) fetchStats();
    });
})();

// ── Expose functions globally ──
window.showError = showError;
window.histApplyFilters = histApplyFilters;
window.histReset = histReset;
window.loadDetail = loadDetail;
window.resetUploadForm = resetUploadForm;
window.validateFile = validateFile;
window.JOB_DATA = JOB_DATA;