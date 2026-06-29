/**
 * AutoBlog AI — Frontend JavaScript
 * Login auth, multi-provider settings, blog verify, tab nav, generate, history.
 */

// ============================================
// State
// ============================================
let currentTab = 'generate';
let historyPage = 1;
const HISTORY_LIMIT = 20;
let currentHistoryData = [];
let isGoogleConnected = false;
let providersData = {};
let currentProvider = 'gemini';

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', async () => {
    // Cek auth parameter di URL (setelah OAuth callback)
    const urlParams = new URLSearchParams(window.location.search);
    const authResult = urlParams.get('auth');
    if (authResult === 'success') {
        showToast('Berhasil terhubung ke Google! ✅', 'success');
        window.history.replaceState({}, '', '/');
    } else if (authResult === 'denied') {
        showToast('Anda membatalkan koneksi Google.', 'warning');
        window.history.replaceState({}, '', '/');
    } else if (authResult === 'error') {
        showToast('Gagal terhubung ke Google. Coba lagi.', 'error');
        window.history.replaceState({}, '', '/');
    }

    // Load providers info
    await loadProviders();

    // Cek login status
    await checkLoginStatus();
});

// ============================================
// Login Auth
// ============================================
async function checkLoginStatus() {
    try {
        const response = await fetch('/api/login/status');
        const data = await response.json();

        if (data.authenticated) {
            showMainApp();
            checkAuthStatus();
            loadSettingsData();
        } else if (data.setup_required) {
            showLoginOverlay('setup');
        } else {
            showLoginOverlay('login');
        }
    } catch (error) {
        console.error('Failed to check login status:', error);
        showLoginOverlay('login');
    }
}

function showLoginOverlay(mode) {
    const overlay = document.getElementById('loginOverlay');
    const setupForm = document.getElementById('loginSetupForm');
    const loginForm = document.getElementById('loginForm');

    overlay.classList.remove('hidden');
    document.getElementById('mainApp').classList.add('hidden');

    if (mode === 'setup') {
        setupForm.classList.remove('hidden');
        loginForm.classList.add('hidden');
    } else {
        setupForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
        document.getElementById('loginKeyInput').focus();
    }
}

function showMainApp() {
    document.getElementById('loginOverlay').classList.add('hidden');
    document.getElementById('mainApp').classList.remove('hidden');
}

async function handleSetupKey() {
    const key = document.getElementById('setupKeyInput').value;
    const confirm = document.getElementById('setupKeyConfirm').value;

    if (key.length < 4) {
        showToast('Login key minimal 4 karakter.', 'warning');
        return;
    }
    if (key !== confirm) {
        showToast('Konfirmasi key tidak cocok.', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/login/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key }),
        });
        const data = await response.json();

        if (response.ok) {
            showToast('Login key berhasil dibuat! 🎉', 'success');
            showMainApp();
            checkAuthStatus();
            loadSettingsData();
        } else {
            const detail = data.detail || data;
            showToast(detail.message || 'Gagal membuat login key.', 'error');
        }
    } catch (error) {
        showToast('Gagal membuat login key.', 'error');
    }
}

async function handleLogin() {
    const key = document.getElementById('loginKeyInput').value;
    const errorEl = document.getElementById('loginError');

    if (!key) {
        errorEl.textContent = 'Masukkan login key.';
        errorEl.classList.remove('hidden');
        return;
    }

    try {
        const btn = document.getElementById('loginBtn');
        btn.disabled = true;
        btn.textContent = 'Memverifikasi...';

        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key }),
        });
        const data = await response.json();

        if (response.ok) {
            errorEl.classList.add('hidden');
            showToast('Login berhasil! 🎉', 'success');
            showMainApp();
            checkAuthStatus();
            loadSettingsData();
        } else {
            const detail = data.detail || data;
            errorEl.textContent = detail.message || 'Login key salah.';
            errorEl.classList.remove('hidden');
        }

        btn.disabled = false;
        btn.textContent = 'Masuk';
    } catch (error) {
        errorEl.textContent = 'Gagal terhubung ke server.';
        errorEl.classList.remove('hidden');
    }
}

async function handleLogout() {
    if (!confirm('Yakin ingin logout?')) return;
    try {
        await fetch('/api/logout', { method: 'POST' });
        showToast('Logout berhasil.', 'success');
        showLoginOverlay('login');
        document.getElementById('loginKeyInput').value = '';
    } catch (error) {
        showToast('Gagal logout.', 'error');
    }
}

// ============================================
// Providers
// ============================================
async function loadProviders() {
    try {
        const response = await fetch('/api/providers');
        providersData = await response.json();
    } catch (error) {
        console.error('Failed to load providers:', error);
        // Fallback data
        providersData = {
            gemini: { name: 'Google Gemini', models: [{ id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' }], default_model: 'gemini-2.0-flash', key_placeholder: 'AIzaSy...', key_url: 'https://aistudio.google.com/apikey' },
            deepseek: { name: 'DeepSeek', models: [{ id: 'deepseek-chat', name: 'DeepSeek V4 Pro' }], default_model: 'deepseek-chat', key_placeholder: 'sk-...', key_url: 'https://platform.deepseek.com/api_keys' },
            openai: { name: 'OpenAI', models: [{ id: 'gpt-4o', name: 'GPT-4o' }], default_model: 'gpt-4o', key_placeholder: 'sk-proj-...', key_url: 'https://platform.openai.com/api-keys' },
            sumopod: { name: 'SumoPod AI', models: [{ id: 'gpt-4o-mini', name: 'GPT-4o Mini' }], default_model: 'gpt-4o-mini', key_placeholder: 'sk-...', key_url: 'https://ai.sumopod.com' },
            bynara: { 
                name: 'Bynara Router', 
                models: [
                    { id: 'mimo-v2.5-pro-free', name: 'Mimo v2.5 Pro Free (Reasoning)' },
                    { id: 'mimo-v2.5-free', name: 'Mimo v2.5 Free (Reasoning)' },
                    { id: 'mistral-large', name: 'Mistral Large (Cepat & Akurat)' },
                    { id: 'mistral-medium-3-5', name: 'Mistral Medium 3.5 (Cepat)' }
                ], 
                default_model: 'mimo-v2.5-pro-free', 
                key_placeholder: 'sk-nry-...', 
                key_url: 'https://router.bynara.id' 
            },
            dahono: {
                name: 'Dahono Labs',
                models: [
                    { id: 'dahono/deepseek-v4-flash', name: 'DeepSeek V4 Flash (Free)' },
                    { id: 'dahono/deepseek-v3.2', name: 'DeepSeek V3.2 (Free)' },
                    { id: 'dahono/ai-chat', name: 'Dahono AI Chat (Free)' },
                    { id: 'dahono/deepseek-v4-pro', name: 'DeepSeek V4 Pro (Paid)' }
                ],
                default_model: 'dahono/deepseek-v4-flash',
                key_placeholder: 'dahono-...',
                key_url: 'https://labs.dahono.com/gateway/docs'
            },
            custom: { name: 'Custom (OpenAI Compatible)', models: [], default_model: '', key_placeholder: 'sk-...', key_url: '#' },
        };
    }
}

function onProviderChange() {
    const provider = document.getElementById('settingProvider').value;
    currentProvider = provider;
    updateProviderUI(provider);
}

function updateProviderUI(provider) {
    const info = providersData[provider];
    if (!info) return;

    const modelSelectContainer = document.getElementById('modelSelectContainer');
    const customUrlContainer = document.getElementById('customUrlContainer');
    const customModelContainer = document.getElementById('customModelContainer');

    if (provider === 'custom') {
        modelSelectContainer.classList.add('hidden');
        customUrlContainer.classList.remove('hidden');
        customModelContainer.classList.remove('hidden');
    } else {
        modelSelectContainer.classList.remove('hidden');
        customUrlContainer.classList.add('hidden');
        customModelContainer.classList.add('hidden');

        // Update model dropdown
        const modelSelect = document.getElementById('settingModel');
        modelSelect.innerHTML = '';
        info.models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.name;
            modelSelect.appendChild(opt);
        });
    }

    // Update API key field
    document.getElementById('apiKeyLabel').textContent = `${info.name} API Key`;
    document.getElementById('settingApiKey').placeholder = info.key_placeholder;
    document.getElementById('apiKeyUrl').href = info.key_url;
    document.getElementById('apiKeyUrl').textContent = info.name;

    // Update label di generate card
    document.getElementById('providerLabel').textContent = `Menggunakan ${info.name}`;

    // Clear API key field (since each provider has different key)
    document.getElementById('settingApiKey').value = '';
}


// ============================================
// Tab Navigation
// ============================================
function switchTab(tab) {
    currentTab = tab;
    const sections = {
        generate: document.getElementById('sectionGenerate'),
        history: document.getElementById('sectionHistory'),
        schedule: document.getElementById('sectionSchedule'),
    };
    const tabs = {
        generate: document.getElementById('tabGenerate'),
        history: document.getElementById('tabHistory'),
        schedule: document.getElementById('tabSchedule'),
    };

    // Hide all sections, deactivate all tabs
    Object.values(sections).forEach(s => { if (s) s.classList.add('hidden'); });
    Object.values(tabs).forEach(t => {
        if (t) {
            t.classList.remove('tab-active');
            t.classList.add('text-gray-400');
        }
    });

    // Activate selected
    if (sections[tab]) sections[tab].classList.remove('hidden');
    if (tabs[tab]) {
        tabs[tab].classList.add('tab-active');
        tabs[tab].classList.remove('text-gray-400');
    }

    if (tab === 'history') loadHistory();
    if (tab === 'schedule') loadScheduleQueue();
}

// ============================================
// Generate Article
// ============================================
async function handleGenerate(event) {
    event.preventDefault();
    const topic = document.getElementById('topicInput').value.trim();
    const mode = document.getElementById('modeSelect').value;

    if (!topic) {
        showToast('⚠️ Topik tidak boleh kosong.', 'warning');
        return;
    }

    showLoading(true);
    hideResult();
    hideError();
    setGenerateButtonState(true);
    animateLoadingSteps();

    try {
        const grounding = document.getElementById('searchGroundingCheckbox').checked;
        const dualLanguage = document.getElementById('dualLanguageCheckbox').checked;
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                topic, 
                status: mode, 
                search_grounding: grounding,
                dual_language: dualLanguage
            }),
        });
        if (!response.ok) {
            let errorText = `Terjadi kesalahan pada server (HTTP ${response.status})`;
            if (response.status === 504) {
                errorText = "Proses AI Timeout (504). Waktu pengerjaan melebihi batas default Nginx (60s). Silakan tingkatkan proxy_read_timeout di Nginx Proxy Manager.";
            } else {
                try {
                    const errorData = await response.json();
                    const detail = errorData.detail || errorData;
                    errorText = detail.message || errorText;
                } catch (_) {}
            }
            throw new Error(errorText);
        }

        const data = await response.json();

        showResult(data);
        showToast(`Artikel "${data.title}" berhasil dipublikasikan! 🎉`, 'success');
        document.getElementById('topicInput').value = '';
    } catch (error) {
        showError(error.message);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
        setGenerateButtonState(false);
    }
}

function showLoading(show) {
    const loadingCard = document.getElementById('loadingCard');
    if (show) {
        loadingCard.classList.remove('hidden');
        loadingCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        loadingCard.classList.add('hidden');
    }
}

function animateLoadingSteps() {
    const steps = [
        { el: 'step1', title: 'Menghubungi AI...', subtitle: 'Mengirim topik ke AI untuk generate artikel', delay: 0 },
        { el: 'step2', title: 'Memformat artikel...', subtitle: 'Memproses dan memformat artikel HTML', delay: 3000 },
        { el: 'step3', title: 'Mempublikasikan...', subtitle: 'Mengirim artikel ke Google Blogger', delay: 6000 },
    ];

    steps.forEach(step => {
        const indicator = document.querySelector(`#${step.el} .step-indicator`);
        indicator.classList.remove('active', 'done');
        document.querySelector(`#${step.el} span`).classList.remove('text-gray-300');
        document.querySelector(`#${step.el} span`).classList.add('text-gray-500');
    });

    steps.forEach((step, index) => {
        setTimeout(() => {
            const loadingCard = document.getElementById('loadingCard');
            if (loadingCard.classList.contains('hidden')) return;
            if (index > 0) {
                const prevIndicator = document.querySelector(`#${steps[index - 1].el} .step-indicator`);
                prevIndicator.classList.remove('active');
                prevIndicator.classList.add('done');
            }
            const indicator = document.querySelector(`#${step.el} .step-indicator`);
            indicator.classList.add('active');
            document.querySelector(`#${step.el} span`).classList.remove('text-gray-500');
            document.querySelector(`#${step.el} span`).classList.add('text-gray-300');
            document.getElementById('loadingTitle').textContent = step.title;
            document.getElementById('loadingSubtitle').textContent = step.subtitle;
        }, step.delay);
    });
}

function setGenerateButtonState(loading) {
    const btn = document.getElementById('generateBtn');
    if (loading) {
        btn.disabled = true;
        btn.innerHTML = `<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Memproses...`;
    } else {
        btn.disabled = false;
        btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Generate & Publish`;
    }
}

function showResult(data) {
    const card = document.getElementById('resultCard');
    card.classList.remove('hidden');
    document.getElementById('resultTitle').textContent = data.title || 'Artikel berhasil dipublikasikan';
    const link = document.getElementById('resultLink');
    if (data.article_url) { link.href = data.article_url; link.classList.remove('hidden'); } else { link.classList.add('hidden'); }
    if (data.html_preview) { document.getElementById('previewContent').innerHTML = data.html_preview; }
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideResult() { document.getElementById('resultCard').classList.add('hidden'); document.getElementById('previewContent').classList.add('hidden'); }
function showError(message) { const card = document.getElementById('errorCard'); card.classList.remove('hidden'); document.getElementById('errorMessage').textContent = message; card.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
function hideError() { document.getElementById('errorCard').classList.add('hidden'); }
function togglePreview() { document.getElementById('previewContent').classList.toggle('hidden'); document.getElementById('previewChevron').classList.toggle('rotate-180'); }

// ============================================
// History
// ============================================
async function loadHistory() {
    try {
        const response = await fetch(`/api/history?page=${historyPage}&limit=${HISTORY_LIMIT}`);
        if (response.status === 401) { checkLoginStatus(); return; }
        const data = await response.json();
        currentHistoryData = data.data || [];
        renderHistory(data);
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function renderHistory(data) {
    const tbody = document.getElementById('historyTableBody');
    const countEl = document.getElementById('historyCount');
    const paginationEl = document.getElementById('historyPagination');
    countEl.textContent = `${data.total} artikel`;

    if (!data.data || data.data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="px-6 py-12 text-center text-gray-500"><svg class="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>Belum ada riwayat artikel</td></tr>`;
        paginationEl.classList.add('hidden');
        return;
    }

    let html = '';
    data.data.forEach((item, index) => {
        const num = (data.page - 1) * HISTORY_LIMIT + index + 1;
        const date = formatDate(item.created_at);
        const statusBadge = item.status === 'SUKSES' ? '<span class="px-2.5 py-1 rounded-full text-xs font-medium bg-accent-green/10 text-accent-green">✅ Sukses</span>'
            : item.status === 'PENDING' ? '<span class="px-2.5 py-1 rounded-full text-xs font-medium bg-accent-orange/10 text-accent-orange">⏳ Pending</span>'
            : '<span class="px-2.5 py-1 rounded-full text-xs font-medium bg-accent-red/10 text-accent-red">❌ Gagal</span>';
        const modeBadge = item.publish_mode === 'live' ? '<span class="px-2 py-0.5 rounded text-xs bg-accent-blue/10 text-accent-blue">Live</span>' : '<span class="px-2 py-0.5 rounded text-xs bg-white/5 text-gray-400">Draft</span>';
        let actions = `<div class="flex items-center gap-3">`;
        // Detail (always visible)
        actions += `<button onclick="showHistoryDetail(${item.id})" class="text-accent-cyan hover:text-white transition-colors" title="Lihat Detail & Log"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg></button>`;
        
        // Link or Retry
        if (item.status === 'SUKSES' && item.article_url) {
            actions += `<a href="${item.article_url}" target="_blank" class="text-accent-purple hover:text-white transition-colors" title="Buka Artikel"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg></a>`;
        } else if (item.status === 'GAGAL') {
            const escapedTopic = escapeHtml(item.topic).replace(/'/g, "\\'");
            actions += `<button onclick="retryGenerate('${escapedTopic}', '${item.publish_mode}')" class="text-accent-orange hover:text-white transition-colors" title="Ulangi"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18.5M4 9h5v-.582"/></svg></button>`;
        }
        
        // Delete (always visible)
        actions += `<button onclick="deleteHistoryItem(${item.id}, event)" class="text-accent-red hover:text-white transition-colors" title="Hapus"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>`;
        actions += `</div>`;

        const topicDisplay = item.title || item.topic;
        const truncatedTopic = topicDisplay.length > 50 ? topicDisplay.substring(0, 50) + '...' : topicDisplay;
        html += `<tr class="hover:bg-white/[0.02] transition-colors"><td class="px-6 py-4 text-sm text-gray-500 font-mono">${num}</td><td class="px-6 py-4 text-sm text-gray-400 whitespace-nowrap">${date}</td><td class="px-6 py-4 text-sm text-gray-200" title="${escapeHtml(topicDisplay)}">${escapeHtml(truncatedTopic)}</td><td class="px-6 py-4">${modeBadge}</td><td class="px-6 py-4">${statusBadge}</td><td class="px-6 py-4">${actions}</td></tr>`;
    });
    tbody.innerHTML = html;

    const totalPages = Math.ceil(data.total / HISTORY_LIMIT);
    if (totalPages > 1) {
        paginationEl.classList.remove('hidden');
        const start = (data.page - 1) * HISTORY_LIMIT + 1;
        const end = Math.min(data.page * HISTORY_LIMIT, data.total);
        document.getElementById('paginationInfo').textContent = `Menampilkan ${start}-${end} dari ${data.total}`;
        document.getElementById('prevBtn').disabled = data.page <= 1;
        document.getElementById('nextBtn').disabled = data.page >= totalPages;
    } else {
        paginationEl.classList.add('hidden');
    }
}

function changePage(delta) { historyPage += delta; if (historyPage < 1) historyPage = 1; loadHistory(); }

// ============================================
// Settings Modal
// ============================================
function openSettings() {
    document.getElementById('settingsModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    loadSettingsData();
    checkAuthStatus();
}

function closeSettings() {
    document.getElementById('settingsModal').classList.add('hidden');
    document.body.style.overflow = '';
}

async function loadSettingsData() {
    try {
        const response = await fetch('/api/settings');
        if (response.status === 401) { checkLoginStatus(); return; }
        const data = await response.json();

        // Set provider
        const provider = data.ai_provider || 'gemini';
        currentProvider = provider;
        document.getElementById('settingProvider').value = provider;
        updateProviderUI(provider);

        // Set custom fields if applicable
        if (data.custom_base_url) {
            document.getElementById('settingCustomUrl').value = data.custom_base_url;
        }
        if (data.custom_model) {
            document.getElementById('settingCustomModel').value = data.custom_model;
        }

        // Set model (only if not custom)
        if (provider !== 'custom' && data.ai_model) {
            document.getElementById('settingModel').value = data.ai_model;
        }

        // Set API key placeholder (masked)
        const keyField = document.getElementById('settingApiKey');
        const maskedKey = data[`${provider}_api_key`] || '';
        if (maskedKey && !maskedKey.startsWith('*')) {
            keyField.value = maskedKey;
        } else {
            keyField.value = '';
            if (maskedKey) keyField.placeholder = maskedKey;
        }

        // Set blog ID
        document.getElementById('settingBlogId').value = data.blog_id || '';

        // Set default status (draft vs live)
        document.getElementById('settingDefaultStatus').value = data.default_status || 'draft';

        // Load image settings
        const imgEnabled = data.image_api_enabled || false;
        document.getElementById('settingImageEnabled').checked = imgEnabled;
        toggleImageSettings();

        document.getElementById('settingImageBaseUrl').value = data.image_base_url || 'https://api.premzone.co';
        document.getElementById('settingImageModel').value = data.image_model || 'cx/gpt-5.5';
        document.getElementById('settingImagePrompt').value = data.image_prompt_template || 'A flat style vector illustration of [TOPIK], modern design, vibrant colors, clean background';

        const imgKeyField = document.getElementById('settingImageApiKey');
        const maskedImgKey = data.image_api_key || '';
        if (maskedImgKey && !maskedImgKey.startsWith('*')) {
            imgKeyField.value = maskedImgKey;
        } else {
            imgKeyField.value = '';
            if (maskedImgKey) imgKeyField.placeholder = maskedImgKey;
        }

        // Update provider label di generate card
        const info = providersData[provider];
        if (info) {
            document.getElementById('providerLabel').textContent = `Menggunakan ${info.name}`;
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveSettings() {
    const provider = document.getElementById('settingProvider').value;
    const model = document.getElementById('settingModel').value;
    const apiKey = document.getElementById('settingApiKey').value.trim();
    const blogId = document.getElementById('settingBlogId').value.trim();

    const imgEnabled = document.getElementById('settingImageEnabled').checked;
    const imgBaseUrl = document.getElementById('settingImageBaseUrl').value.trim();
    const imgModel = document.getElementById('settingImageModel').value.trim();
    const imgApiKey = document.getElementById('settingImageApiKey').value.trim();
    const imgPrompt = document.getElementById('settingImagePrompt').value.trim();

    const defaultStatus = document.getElementById('settingDefaultStatus').value;

    const payload = {
        ai_provider: provider,
        default_status: defaultStatus,
        image_api_enabled: imgEnabled,
        image_base_url: imgBaseUrl,
        image_model: imgModel,
        image_prompt_template: imgPrompt,
    };

    if (provider === 'custom') {
        const customUrl = document.getElementById('settingCustomUrl').value.trim();
        const customModel = document.getElementById('settingCustomModel').value.trim();
        payload.custom_base_url = customUrl;
        payload.custom_model = customModel;
    } else {
        payload.ai_model = model;
    }

    // Simpan API key ke field yang sesuai
    if (apiKey) {
        payload[`${provider}_api_key`] = apiKey;
    }
    if (imgApiKey) {
        payload.image_api_key = imgApiKey;
    }
    if (blogId) {
        payload.blog_id = blogId;
    }

    try {
        const btn = document.getElementById('saveSettingsBtn');
        btn.disabled = true;
        btn.textContent = 'Menyimpan...';

        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (response.ok) {
            showToast('Pengaturan berhasil disimpan! ✅', 'success');
            closeSettings();
            // Update provider label
            const info = providersData[provider];
            if (info) {
                document.getElementById('providerLabel').textContent = `Menggunakan ${info.name}`;
            }
        } else {
            const data = await response.json();
            showToast(data.message || 'Gagal menyimpan pengaturan.', 'error');
        }

        btn.disabled = false;
        btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> Simpan`;
    } catch (error) {
        showToast('Gagal menyimpan pengaturan.', 'error');
    }
}

function toggleImageSettings() {
    const enabled = document.getElementById('settingImageEnabled').checked;
    const fields = document.getElementById('imageSettingsFields');
    if (enabled) {
        fields.classList.remove('hidden');
    } else {
        fields.classList.add('hidden');
    }
}



function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    input.type = input.type === 'password' ? 'text' : 'password';
}

// ============================================
// Blog ID Verification
// ============================================
async function verifyBlogId() {
    const blogId = document.getElementById('settingBlogId').value.trim();
    const resultEl = document.getElementById('blogVerifyResult');
    const btn = document.getElementById('verifyBlogBtn');

    if (!blogId) {
        showToast('Masukkan Blog ID terlebih dahulu.', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Checking...`;

    try {
        const response = await fetch('/api/blog/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blog_id: blogId }),
        });

        const data = await response.json();

        if (response.ok) {
            resultEl.className = 'mb-4 p-3 rounded-xl border text-sm border-accent-green/20 bg-accent-green/5';
            resultEl.innerHTML = `
                <div class="flex items-center gap-2 text-accent-green font-medium mb-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    Blog Terhubung!
                </div>
                <p class="text-gray-300">📝 <strong>${escapeHtml(data.blog_name)}</strong></p>
                <p class="text-gray-400 text-xs mt-1">URL: ${escapeHtml(data.blog_url)} · ${data.total_posts} post</p>
            `;
        } else {
            const detail = data.detail || data;
            resultEl.className = 'mb-4 p-3 rounded-xl border text-sm border-accent-red/20 bg-accent-red/5';
            resultEl.innerHTML = `
                <div class="flex items-center gap-2 text-accent-red font-medium">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    ${escapeHtml(detail.message || 'Gagal memverifikasi blog.')}
                </div>
            `;
        }
        resultEl.classList.remove('hidden');
    } catch (error) {
        resultEl.className = 'mb-4 p-3 rounded-xl border text-sm border-accent-red/20 bg-accent-red/5';
        resultEl.innerHTML = `<p class="text-accent-red">Gagal terhubung ke server.</p>`;
        resultEl.classList.remove('hidden');
    }

    btn.disabled = false;
    btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Cek`;
}

// ============================================
// Google Auth
// ============================================
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/status');
        if (response.status === 401) return;
        const data = await response.json();
        isGoogleConnected = data.connected;
        updateAuthUI(data.connected);
    } catch (error) {
        console.error('Failed to check auth status:', error);
        updateAuthUI(false);
    }
}

function updateAuthUI(connected) {
    const dot = document.getElementById('authDot');
    const text = document.getElementById('authText');
    const statusText = document.getElementById('googleStatusText');
    const statusSub = document.getElementById('googleStatusSub');
    const authBtn = document.getElementById('googleAuthBtn');
    const authIcon = document.getElementById('googleAuthIcon');

    if (connected) {
        dot.className = 'w-2 h-2 rounded-full bg-accent-green';
        text.textContent = 'Terhubung';
        text.className = 'text-accent-green hidden sm:inline text-sm';
        statusText.textContent = 'Terhubung ke Google';
        statusText.className = 'text-sm font-medium text-accent-green';
        statusSub.textContent = 'Siap untuk publish artikel';
        authBtn.textContent = 'Disconnect';
        authBtn.className = 'px-4 py-2 rounded-lg bg-accent-red/10 text-accent-red text-sm font-medium hover:bg-accent-red/20 transition-all';
        authBtn.onclick = handleGoogleDisconnect;
        authIcon.className = 'w-8 h-8 rounded-lg bg-accent-green/10 flex items-center justify-center';
        authIcon.innerHTML = `<svg class="w-4 h-4 text-accent-green" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`;
    } else {
        dot.className = 'w-2 h-2 rounded-full bg-red-500 animate-pulse';
        text.textContent = 'Belum Terhubung';
        text.className = 'text-gray-400 hidden sm:inline text-sm';
        statusText.textContent = 'Belum Terhubung';
        statusText.className = 'text-sm font-medium text-gray-300';
        statusSub.textContent = 'Hubungkan untuk publish artikel';
        authBtn.textContent = 'Connect';
        authBtn.className = 'px-4 py-2 rounded-lg bg-accent-blue/10 text-accent-blue text-sm font-medium hover:bg-accent-blue/20 transition-all';
        authBtn.onclick = handleGoogleAuth;
        authIcon.className = 'w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center';
        authIcon.innerHTML = `<svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>`;
    }
}

function handleGoogleAuth() { window.location.href = '/api/auth/google'; }

async function handleGoogleDisconnect() {
    if (!confirm('Yakin ingin memutuskan koneksi Google?')) return;
    try {
        const response = await fetch('/api/auth/disconnect', { method: 'POST' });
        if (response.ok) {
            showToast('Berhasil terputus dari Google.', 'success');
            checkAuthStatus();
        }
    } catch (error) {
        showToast('Gagal memutuskan koneksi.', 'error');
    }
}

// ============================================
// Toast Notifications
// ============================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const colors = { success: 'border-accent-green/30 bg-accent-green/5', error: 'border-accent-red/30 bg-accent-red/5', warning: 'border-accent-orange/30 bg-accent-orange/5', info: 'border-accent-blue/30 bg-accent-blue/5' };
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `glass-card rounded-xl px-4 py-3 border ${colors[type]} max-w-sm animate-toast-in flex items-start gap-3`;
    toast.innerHTML = `<span class="text-base flex-shrink-0 mt-0.5">${icons[type]}</span><p class="text-sm text-gray-200 flex-grow">${escapeHtml(message)}</p><button onclick="this.parentElement.remove()" class="text-gray-500 hover:text-gray-300 flex-shrink-0 mt-0.5"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></button>`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.animation = 'toastOut 0.3s ease forwards'; setTimeout(() => toast.remove(), 300); }, 5000);
}

// ============================================
// Utilities
// ============================================
function formatDate(dateStr) {
    if (!dateStr) return '-';
    try { const date = new Date(dateStr); return date.toLocaleDateString('id-ID', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }); } catch { return dateStr; }
}

function escapeHtml(text) {
    if (!text) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSettings(); });


// ============================================
// AI Connection Test
// ============================================
async function testAIConnection() {
    const provider = document.getElementById('settingProvider').value;
    const model = document.getElementById('settingModel').value;
    const apiKey = document.getElementById('settingApiKey').value.trim();
    const customUrl = document.getElementById('settingCustomUrl').value.trim();
    const customModel = document.getElementById('settingCustomModel').value.trim();
    const resultEl = document.getElementById('aiTestResult');
    const btn = document.getElementById('testAIBtn');

    if (!apiKey && !document.getElementById('settingApiKey').placeholder) {
        showToast('Masukkan API Key terlebih dahulu.', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `<svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Testing...`;

    const payload = {
        provider: provider,
        api_key: apiKey || "", // Backend will read from database if empty/masked in real calls, but for testing we send input
    };

    if (provider === 'custom') {
        payload.custom_base_url = customUrl;
        payload.model = customModel;
    } else {
        payload.model = model;
    }

    try {
        const response = await fetch('/api/settings/test-ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            resultEl.className = 'mb-4 p-3 rounded-xl border text-sm border-accent-green/20 bg-accent-green/5';
            resultEl.innerHTML = `
                <div class="flex items-center gap-2 text-accent-green font-medium mb-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    Koneksi Sukses!
                </div>
                <p class="text-gray-300 text-xs">${escapeHtml(data.message)}</p>
            `;
        } else {
            resultEl.className = 'mb-4 p-3 rounded-xl border text-sm border-accent-red/20 bg-accent-red/5';
            resultEl.innerHTML = `
                <div class="flex items-center gap-2 text-accent-red font-medium mb-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    Koneksi Gagal
                </div>
                <p class="text-gray-400 text-xs">${escapeHtml(data.message || 'Koneksi ke AI gagal.')}</p>
            `;
        }
        resultEl.classList.remove('hidden');
    } catch (error) {
        resultEl.className = 'mb-4 p-3 rounded-xl border text-sm border-accent-red/20 bg-accent-red/5';
        resultEl.innerHTML = `<p class="text-accent-red">Gagal terhubung ke server.</p>`;
        resultEl.classList.remove('hidden');
    }

    btn.disabled = false;
    btn.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Tes AI`;
}

// ============================================
// Retry Generate Failed Article
// ============================================
function retryGenerate(topic, publishMode) {
    // Pindah ke tab generate
    switchTab('generate');
    // Isi field topic dan mode select
    document.getElementById('topicInput').value = topic;
    document.getElementById('modeSelect').value = publishMode;
    // Tampilkan notifikasi
    showToast(`Mengulangi generate topik: "${topic}"`, 'info');
    // Kirim formulir secara otomatis
    const form = document.querySelector('form');
    if (form) {
        // Panggil handler generate dengan mock event
        handleGenerate({ preventDefault: () => {} });
    }
}


// ============================================
// History Actions: Detail and Delete
// ============================================
function showHistoryDetail(id) {
    const item = currentHistoryData.find(x => x.id === id);
    if (!item) return;

    document.getElementById('detailTopic').textContent = item.topic || '-';
    document.getElementById('detailTitle').textContent = item.title || '-';
    
    // Status Badge
    const statusEl = document.getElementById('detailStatus');
    if (item.status === 'SUKSES') {
        statusEl.innerHTML = '<span class="px-2 py-0.5 rounded text-xs bg-accent-green/10 text-accent-green font-medium">✅ Sukses</span>';
    } else if (item.status === 'PENDING') {
        statusEl.innerHTML = '<span class="px-2 py-0.5 rounded text-xs bg-accent-orange/10 text-accent-orange font-medium">⏳ Pending</span>';
    } else {
        statusEl.innerHTML = '<span class="px-2 py-0.5 rounded text-xs bg-accent-red/10 text-accent-red font-medium">❌ Gagal</span>';
    }

    document.getElementById('detailDate').textContent = formatDate(item.created_at);

    // Error message container
    const errContainer = document.getElementById('detailErrorContainer');
    if (item.status === 'GAGAL' && item.error_message) {
        errContainer.classList.remove('hidden');
        document.getElementById('detailErrorMessage').textContent = item.error_message;
    } else {
        errContainer.classList.add('hidden');
    }

    // Timeline / Steps log
    const timelineEl = document.getElementById('detailTimeline');
    timelineEl.innerHTML = '';

    let steps = [];
    if (item.generation_log) {
        try {
            steps = JSON.parse(item.generation_log);
        } catch (e) {
            console.error('Failed to parse generation log:', e);
        }
    }

    if (steps.length === 0) {
        timelineEl.innerHTML = `<p class="text-xs text-gray-500 italic py-4">Tidak ada data log langkah (mungkin artikel lama atau langsung gagal sebelum langkah AI dimulai).</p>`;
    } else {
        steps.forEach((step, idx) => {
            const isSuccess = step.status === 'SUKSES';
            const statusIndicator = isSuccess 
                ? '<span class="w-2.5 h-2.5 rounded-full bg-accent-green mt-1.5 flex-shrink-0"></span>'
                : '<span class="w-2.5 h-2.5 rounded-full bg-accent-red mt-1.5 flex-shrink-0 animate-pulse"></span>';
            const statusLabel = isSuccess
                ? '<span class="text-[10px] px-1.5 py-0.5 rounded bg-accent-green/10 text-accent-green">Sukses</span>'
                : '<span class="text-[10px] px-1.5 py-0.5 rounded bg-accent-red/10 text-accent-red">Gagal</span>';

            const stepHtml = `
                <div class="relative flex gap-4 items-start pl-1">
                    ${statusIndicator}
                    <div class="flex-grow bg-white/[0.01] border border-white/5 rounded-xl p-4">
                        <div class="flex items-center justify-between cursor-pointer" onclick="toggleTimelineDetails(${idx})">
                            <span class="text-xs font-semibold text-gray-200">${escapeHtml(step.step)}</span>
                            <div class="flex items-center gap-2 text-xs">
                                ${statusLabel}
                                <svg id="chevron-step-${idx}" class="w-3.5 h-3.5 text-gray-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                            </div>
                        </div>
                        <div id="details-step-${idx}" class="hidden mt-3 space-y-3 pt-3 border-t border-white/5 text-xs">
                            <div>
                                <p class="text-gray-500 font-semibold mb-1">PROMPT / INPUT:</p>
                                <pre class="bg-dark-900/60 p-3 rounded-lg border border-white/5 font-mono text-[10px] overflow-x-auto whitespace-pre-wrap select-text leading-relaxed text-gray-300">${escapeHtml(step.prompt)}</pre>
                            </div>
                            <div>
                                <p class="text-gray-500 font-semibold mb-1">RESPON / OUTPUT:</p>
                                <pre class="bg-dark-900/60 p-3 rounded-lg border border-white/5 font-mono text-[10px] overflow-x-auto whitespace-pre-wrap select-text leading-relaxed text-gray-300">${escapeHtml(step.response)}</pre>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            timelineEl.innerHTML += stepHtml;
        });
    }

    // Link button
    const linkBtn = document.getElementById('detailLinkBtn');
    if (item.status === 'SUKSES' && item.article_url) {
        linkBtn.href = item.article_url;
        linkBtn.classList.remove('hidden');
    } else {
        linkBtn.classList.add('hidden');
    }

    // Open Modal
    document.getElementById('historyDetailModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeHistoryDetail() {
    document.getElementById('historyDetailModal').classList.add('hidden');
    document.body.style.overflow = '';
}

function toggleTimelineDetails(index) {
    const details = document.getElementById(`details-step-${index}`);
    const chevron = document.getElementById(`chevron-step-${index}`);
    details.classList.toggle('hidden');
    chevron.classList.toggle('rotate-180');
}

async function deleteHistoryItem(id, event) {
    if (event) event.stopPropagation();
    if (!confirm('Yakin ingin menghapus riwayat postingan ini dari database?')) return;

    try {
        const response = await fetch(`/api/history/${id}`, {
            method: 'DELETE',
        });
        const data = await response.json();
        if (response.ok) {
            showToast('Riwayat berhasil dihapus. 🗑️', 'success');
            loadHistory();
        } else {
            showToast(data.message || 'Gagal menghapus riwayat.', 'error');
        }
    } catch (error) {
        showToast('Gagal terhubung ke server.', 'error');
    }
}


// ============================================
// Schedule Batch Functions
// ============================================

/**
 * Set default start date to tomorrow on page load.
 */
(function initScheduleDefaults() {
    const dateInput = document.getElementById('scheduleStartDate');
    if (dateInput) {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        dateInput.value = tomorrow.toISOString().split('T')[0];
    }
})();

/**
 * Collect all topic values from dynamic input fields.
 */
function getTopicsFromInputs() {
    const inputs = document.querySelectorAll('#topicInputList .topic-input');
    return Array.from(inputs).map(i => i.value.trim()).filter(t => t);
}

/**
 * Update the topic count badge.
 */
function updateTopicCount() {
    const count = document.querySelectorAll('#topicInputList .topic-row').length;
    const badge = document.getElementById('topicCountBadge');
    if (badge) badge.textContent = `${count} topik`;
}

/**
 * Re-index all topic rows (update the numbering after add/remove).
 */
function reindexTopicRows() {
    const rows = document.querySelectorAll('#topicInputList .topic-row');
    rows.forEach((row, idx) => {
        row.dataset.index = idx;
        row.querySelector('span').textContent = idx + 1;
    });
    updateTopicCount();
}

/**
 * Add a new empty topic input row.
 */
function addTopicRow(value = '') {
    const list = document.getElementById('topicInputList');
    const idx = list.querySelectorAll('.topic-row').length;
    const row = document.createElement('div');
    row.className = 'topic-row flex items-center gap-2';
    row.dataset.index = idx;
    row.style.opacity = '0';
    row.style.transform = 'translateY(-8px)';
    row.innerHTML = `
        <span class="text-xs text-gray-500 w-6 text-center flex-shrink-0">${idx + 1}</span>
        <input type="text" class="topic-input flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-accent-purple/50 focus:ring-1 focus:ring-accent-purple/30 transition-all text-sm" placeholder="Masukkan topik/prompt artikel..." value="${escapeHtml(value)}">
        <button onclick="removeTopicRow(this)" class="p-2 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all flex-shrink-0" title="Hapus topik">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>
    `;
    list.appendChild(row);
    // Animate in
    requestAnimationFrame(() => {
        row.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
        row.style.opacity = '1';
        row.style.transform = 'translateY(0)';
    });
    updateTopicCount();
    // Focus the new input
    if (!value) {
        const input = row.querySelector('.topic-input');
        setTimeout(() => input.focus(), 50);
    }
}

/**
 * Remove a topic row. Keep at least 1 row.
 */
function removeTopicRow(btn) {
    const list = document.getElementById('topicInputList');
    const rows = list.querySelectorAll('.topic-row');
    if (rows.length <= 1) {
        // Don't remove last row, just clear it
        rows[0].querySelector('.topic-input').value = '';
        showToast('ℹ️ Minimal harus ada 1 topik.', 'warning');
        return;
    }
    const row = btn.closest('.topic-row');
    row.style.transition = 'opacity 0.15s ease, transform 0.15s ease';
    row.style.opacity = '0';
    row.style.transform = 'translateX(20px)';
    setTimeout(() => {
        row.remove();
        reindexTopicRows();
    }, 150);
}

/**
 * Clear all topic rows and reset to a single empty one.
 */
function clearAllTopics() {
    const list = document.getElementById('topicInputList');
    list.innerHTML = `
        <div class="topic-row flex items-center gap-2" data-index="0">
            <span class="text-xs text-gray-500 w-6 text-center flex-shrink-0">1</span>
            <input type="text" class="topic-input flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-accent-purple/50 focus:ring-1 focus:ring-accent-purple/30 transition-all text-sm" placeholder="Masukkan topik/prompt artikel...">
            <button onclick="removeTopicRow(this)" class="p-2 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all flex-shrink-0" title="Hapus topik">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
        </div>
    `;
    updateTopicCount();
    // Reset file input
    const fileInput = document.getElementById('excelUpload');
    if (fileInput) fileInput.value = '';
    showToast('🗑️ Semua topik telah dihapus.', 'success');
}

/**
 * Handle Excel/CSV file upload and parse topics from it.
 */
function handleExcelUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
            const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });

            // Try to find a "topik" column header
            let topicColIdx = 0;
            const headerRow = jsonData[0];
            if (headerRow) {
                const idx = headerRow.findIndex(h =>
                    typeof h === 'string' && h.toLowerCase().replace(/\s/g, '').includes('topik')
                );
                if (idx >= 0) topicColIdx = idx;
            }

            // Extract topics, skip header if we found a named column
            const startRow = topicColIdx >= 0 && headerRow ? 1 : 0;
            const topics = [];
            for (let i = startRow; i < jsonData.length; i++) {
                const row = jsonData[i];
                if (row && row[topicColIdx]) {
                    const val = String(row[topicColIdx]).trim();
                    if (val) topics.push(val);
                }
            }

            if (topics.length === 0) {
                showToast('⚠️ Tidak ada topik ditemukan di file Excel.', 'warning');
                return;
            }

            // Clear existing and add new
            const list = document.getElementById('topicInputList');
            list.innerHTML = '';
            topics.forEach(t => addTopicRow(t));
            reindexTopicRows();
            showToast(`✅ Berhasil mengimpor ${topics.length} topik dari "${file.name}".`, 'success');

        } catch (err) {
            console.error('Excel parse error:', err);
            showToast('❌ Gagal membaca file. Pastikan format .xlsx, .xls, atau .csv.', 'error');
        }
    };
    reader.readAsArrayBuffer(file);
}

/**
 * Parse topics from dynamic inputs, compute schedule, and render a preview table.
 */
function previewSchedule() {
    const startDate = document.getElementById('scheduleStartDate').value;
    const interval = parseInt(document.getElementById('scheduleInterval').value) || 2;
    const topics = getTopicsFromInputs();
    const dualLanguage = document.getElementById('scheduleDualLanguage').checked;

    if (topics.length === 0) {
        showToast('⚠️ Masukkan minimal satu topik.', 'warning');
        return;
    }
    if (!startDate) {
        showToast('⚠️ Pilih tanggal mulai.', 'warning');
        return;
    }

    const tbody = document.getElementById('schedulePreviewBody');
    tbody.innerHTML = '';
    let counter = 1;

    topics.forEach((topic, idx) => {
        const releaseDate = new Date(startDate);
        releaseDate.setDate(releaseDate.getDate() + idx * interval);
        const dateStr = releaseDate.toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

        // Indonesian row — 09:00
        tbody.innerHTML += `
            <tr class="hover:bg-white/5 transition-colors">
                <td class="px-5 py-3 text-gray-500">${counter++}</td>
                <td class="px-5 py-3 text-gray-200">${escapeHtml(topic)}</td>
                <td class="px-5 py-3"><span class="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-medium">🇮🇩 Indonesia</span></td>
                <td class="px-5 py-3 text-gray-400">${dateStr}, 09:00 WIB</td>
            </tr>
        `;
        
        // English row — 15:00 (only if dual language is active)
        if (dualLanguage) {
            tbody.innerHTML += `
                <tr class="hover:bg-white/5 transition-colors">
                    <td class="px-5 py-3 text-gray-500">${counter++}</td>
                    <td class="px-5 py-3 text-gray-200">${escapeHtml(topic)}</td>
                    <td class="px-5 py-3"><span class="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 text-xs font-medium">🇬🇧 English</span></td>
                    <td class="px-5 py-3 text-gray-400">${dateStr}, 15:00 WIB</td>
                </tr>
            `;
        }
    });

    document.getElementById('schedulePreview').classList.remove('hidden');
    document.getElementById('scheduleResults').classList.add('hidden');
    document.getElementById('scheduleProgress').classList.add('hidden');

    const totalArticles = dualLanguage ? topics.length * 2 : topics.length;
    showToast(`📅 Preview ${topics.length} topik = ${totalArticles} artikel.`, 'success');
}

/**
 * Send schedule-batch request to the backend and render results.
 */
async function runScheduleBatch() {
    const startDate = document.getElementById('scheduleStartDate').value;
    const interval = parseInt(document.getElementById('scheduleInterval').value) || 2;
    const topics = getTopicsFromInputs();
    const searchGrounding = document.getElementById('scheduleSearchGrounding').checked;
    const dualLanguage = document.getElementById('scheduleDualLanguage').checked;

    if (!topics.length || !startDate) {
        showToast('⚠️ Lengkapi topik dan tanggal mulai.', 'warning');
        return;
    }

    // Show progress
    const btn = document.getElementById('btnRunSchedule');
    btn.disabled = true;
    btn.innerHTML = `
        <div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
        Mengantrekan...
    `;
    
    const totalArticles = dualLanguage ? topics.length * 2 : topics.length;
    document.getElementById('scheduleProgress').classList.remove('hidden');
    document.getElementById('scheduleProgressBar').style.width = '30%';
    document.getElementById('scheduleProgressText').textContent = `Memasukkan ${topics.length} topik (${totalArticles} artikel) ke antrean...`;

    try {
        const response = await fetch('/api/schedule-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topics: topics,
                start_date: startDate,
                interval_days: interval,
                search_grounding: searchGrounding,
                dual_language: dualLanguage,
            }),
        });

        if (!response.ok) {
            let errorText = `Terjadi kesalahan (HTTP ${response.status})`;
            if (response.status === 504) {
                errorText = "Server Timeout (504): Penjadwalan batch memakan waktu terlalu lama. Silakan tingkatkan proxy_read_timeout di Nginx Proxy Manager.";
            } else {
                try {
                    const data = await response.json();
                    errorText = data.detail?.message || data.message || errorText;
                } catch (_) {}
            }
            showToast(`❌ ${errorText}`, 'error');
            return;
        }

        const data = await response.json();
        showToast(data.message || 'Antrean berhasil disimpan!', 'success');
        clearAllTopics(); // Kosongkan input setelah sukses
        loadScheduleQueue(); // Muat ulang tabel antrean aktif
        document.getElementById('schedulePreview').classList.add('hidden'); // Sembunyikan preview

    } catch (error) {
        showToast('❌ Gagal terhubung ke server.', 'error');
    } finally {
        // Reset button
        btn.disabled = false;
        btn.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>
            Jadwalkan Semua
        `;
        setTimeout(() => {
            document.getElementById('scheduleProgress').classList.add('hidden');
        }, 1000);
    }
}

/**
 * Fetch and render all active items in the database schedule queue.
 */
async function loadScheduleQueue() {
    const tbody = document.getElementById('scheduleQueueBody');
    if (!tbody) return;

    try {
        const response = await fetch('/api/schedule-queue');
        const data = await response.json();

        if (response.ok && data.data) {
            const queue = data.data;
            if (queue.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="px-5 py-8 text-center text-gray-500">
                            Belum ada antrean jadwal penerbitan.
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = '';
            queue.forEach((item, idx) => {
                let scheduledDisplay = '-';
                if (item.scheduled_at) {
                    try {
                        const d = new Date(item.scheduled_at);
                        scheduledDisplay = d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) + ' ' + d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
                    } catch(e) {
                        scheduledDisplay = item.scheduled_at;
                    }
                }

                // Badge status styling
                let statusClass = 'bg-gray-500/10 text-gray-400';
                if (item.status === 'PENDING') statusClass = 'bg-accent-orange/10 text-accent-orange';
                else if (item.status === 'GENERATING') statusClass = 'bg-accent-purple/10 text-accent-purple animate-pulse';
                else if (item.status === 'SUKSES') statusClass = 'bg-emerald-500/10 text-emerald-400';
                else if (item.status === 'GAGAL') statusClass = 'bg-red-500/10 text-red-400';

                const langClass = item.language === 'Indonesia'
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : 'bg-blue-500/10 text-blue-400';
                const langFlag = item.language === 'Indonesia' ? '🇮🇩' : '🇬🇧';

                // Topic title link (if success)
                const titleDisplay = item.title
                    ? (item.article_url ? `<a href="${item.article_url}" target="_blank" class="text-accent-cyan hover:underline">${escapeHtml(item.title)}</a>` : escapeHtml(item.title))
                    : '<span class="text-gray-600">-</span>';

                // Cancel button only for PENDING status
                let actionBtn = '<span class="text-gray-600">-</span>';
                if (item.status === 'PENDING') {
                    actionBtn = `
                        <button onclick="cancelScheduleItem(${item.id})" class="px-2.5 py-1 rounded bg-red-500/10 hover:bg-red-500/25 text-red-400 text-xs font-semibold transition-colors" title="Batalkan jadwal">
                            Batal
                        </button>
                    `;
                }

                const errorTooltip = item.error_message ? ` title="${escapeHtml(item.error_message)}"` : '';

                tbody.innerHTML += `
                    <tr class="hover:bg-white/5 transition-colors">
                        <td class="px-5 py-3 text-gray-500">${idx + 1}</td>
                        <td class="px-5 py-3 text-gray-200 max-w-[180px] truncate" title="${escapeHtml(item.topic)}">${escapeHtml(item.topic)}</td>
                        <td class="px-5 py-3"><span class="px-2 py-0.5 rounded-md ${langClass} text-xs font-medium">${langFlag} ${item.language}</span></td>
                        <td class="px-5 py-3 text-gray-400 text-xs">${scheduledDisplay} WIB</td>
                        <td class="px-5 py-3"><span class="px-2 py-0.5 rounded-md ${statusClass} text-xs font-semibold cursor-default"${errorTooltip}>${item.status}</span></td>
                        <td class="px-5 py-3">${actionBtn}</td>
                    </tr>
                `;
            });
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-5 py-8 text-center text-red-400">
                        Gagal memuat antrean jadwal dari server.
                    </td>
                </tr>
            `;
        }
    } catch(err) {
        console.error("Queue load error:", err);
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-5 py-8 text-center text-red-400">
                    Koneksi error. Gagal memuat antrean.
                </td>
            </tr>
        `;
    }
}

/**
 * Cancel and delete a schedule item from the queue database.
 */
async function cancelScheduleItem(id) {
    if (!confirm("Apakah Anda yakin ingin membatalkan jadwal rilis artikel ini?")) return;

    try {
        const response = await fetch(`/api/schedule-queue/${id}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (response.ok) {
            showToast("📅 Antrean berhasil dibatalkan.", "success");
            loadScheduleQueue();
        } else {
            showToast(data.message || "Gagal membatalkan antrean.", "error");
        }
    } catch (err) {
        showToast("❌ Gagal terhubung ke server.", "error");
    }
}


/**
 * Helper: escape HTML entities.
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Build and download a template Excel file using SheetJS in the frontend.
 */
function downloadExcelTemplate() {
    try {
        const wb = XLSX.utils.book_new();
        const data = [
            ["topik"],
            ["Kampus Terbaik di Karawang"],
            ["Tips Merawat Laptop Agar Awet dan Tahan Lama"],
            ["Panduan Memulai Bisnis Online Tanpa Modal untuk Pemula"]
        ];
        const ws = XLSX.utils.aoa_to_sheet(data);
        XLSX.utils.book_append_sheet(wb, ws, "Template Autopost");
        XLSX.writeFile(wb, "template_jadwal_autopost.xlsx");
        showToast("📥 Template Excel berhasil diunduh!", "success");
    } catch (err) {
        console.error("Template download error:", err);
        showToast("❌ Gagal mengunduh template.", "error");
    }
}


