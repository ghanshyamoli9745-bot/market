/**
 * NEPSE PRO TERMINAL - FULL FEATURE ENGINE
 * Updated with Advanced API Key System & Cross-Device Sync
 */

const API_BASE = '/api';

// State Management
const State = {
    marketData: [],
    currentSearch: '',
    currentModalSymbol: null,
    clientId: localStorage.getItem('nepse-pro-client-id') || (Math.random().toString(36).substring(2) + Date.now().toString(36)),
    userEmail: localStorage.getItem('nepse-pro-email') || '',
    apiKey: '',
    apiScope: 'all',
    currentModule: 'market',
    currentFilter: 'LIVE MARKET',
    watchlist: new Set(),
    portfolio: [],
    alerts: []
};

// DOM Cache
const UI = {
    clock: document.getElementById('digital-clock'),
    statusDot: document.getElementById('market-status-dot'),
    statusText: document.getElementById('market-status-text'),
    nepseIndex: document.getElementById('nepse-index'),
    nepseChange: document.getElementById('nepse-change'),
    totalTurnover: document.getElementById('total-turnover'),
    totalScripts: document.getElementById('total-scripts'),
    mainTbody: document.getElementById('main-tbody'),
    gainersList: document.getElementById('gainers-list'),
    losersList: document.getElementById('losers-list'),
    sectorsList: document.getElementById('sectors-list'),
    searchInput: document.getElementById('search-input'),
    loader: document.getElementById('loader'),
    ticker: document.getElementById('ticker'),
    
    // Modules
    modules: document.querySelectorAll('.module'),
    navItems: document.querySelectorAll('.nav-item'),
    
    // Portfolio
    portfolioTbody: document.getElementById('portfolio-tbody'),
    pTotalValue: document.getElementById('p-total-value'),
    pTotalPL: document.getElementById('p-total-pl'),
    pModal: document.getElementById('portfolio-modal'),
    addPBtn: document.getElementById('add-to-portfolio-btn'),
    
    // Alerts
    alertsTbody: document.getElementById('alerts-tbody'),
    
    // Modals
    detailModal: document.getElementById('detail-modal'),
    apiModal: document.getElementById('api-modal'),
    apiBtn: document.getElementById('api-btn'),
    apiKeyCode: document.getElementById('api-key-code'),
    apiEmailInput: document.getElementById('api-email-input'),
    apiScopeSelect: document.getElementById('api-scope-select')
};

// --- INITIALIZATION ---

function init() {
    initFirebase();
    setupEventListeners();
    startClock();
    fetchInitialData();
    document.getElementById('display-client-id').textContent = State.clientId;
    if (State.userEmail) UI.apiEmailInput.value = State.userEmail;
    if (window.lucide) lucide.createIcons();
}

async function fetchInitialData() {
    try {
        const res = await fetch(`${API_BASE}/dashboard-summary`);
        if (res.ok) {
            const data = await res.json();
            processMarketData(data);
        }
    } catch (e) { console.error(e); }
    finally { hideLoader(); }
}

function setupEventListeners() {
    UI.navItems.forEach(item => {
        item.addEventListener('click', () => switchModule(item.getAttribute('data-module')));
    });

    document.querySelectorAll('.tab[data-filter]').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab[data-filter]').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            State.currentFilter = tab.getAttribute('data-filter');
            renderMainTable();
        });
    });

    UI.searchInput.addEventListener('input', (e) => {
        State.currentSearch = e.target.value.toLowerCase();
        renderMainTable();
    });

    UI.apiBtn.addEventListener('click', () => UI.apiModal.style.display = 'block');
    document.getElementById('verify-email-btn').addEventListener('click', syncUserKey);
    document.getElementById('toggle-key-btn').addEventListener('click', toggleApiKey);
    document.getElementById('copy-btn').addEventListener('click', copyApiKey);
    document.getElementById('generate-btn').addEventListener('click', generateScopedKey);

    UI.addPBtn.addEventListener('click', () => UI.pModal.style.display = 'block');
    document.getElementById('p-save-btn').addEventListener('click', saveToPortfolio);

    window.onclick = (e) => { if (e.target.classList.contains('modal')) e.target.style.display = 'none'; };
    document.querySelectorAll('.close-modal').forEach(btn => btn.onclick = () => document.querySelectorAll('.modal').forEach(m => m.style.display = 'none'));
}

// --- SYNC & API ---

async function syncUserKey() {
    const email = UI.apiEmailInput.value.trim().toLowerCase();
    if (!email) return notify("Email required for sync", "danger");

    try {
        const res = await fetch(`${API_BASE}/auth/sync?email=${email}`);
        const data = await res.json();
        if (data.api_key) {
            State.userEmail = email;
            State.apiKey = data.api_key;
            State.apiScope = data.scope;
            localStorage.setItem('nepse-pro-email', email);
            
            UI.apiKeyCode.value = State.apiKey;
            UI.apiScopeSelect.value = State.apiScope;
            document.getElementById('api-key-display').style.display = 'block';
            document.getElementById('api-auth-section').style.display = 'none';
            notify("Identity Verified & Keys Synced", "success");
            
            // Sync to Firebase for cross-device persistence
            firebase.database().ref(`clients/${State.clientId}`).update({ 
                email: State.userEmail,
                api_key: State.apiKey,
                api_scope: State.apiScope
            });
        }
    } catch (e) { notify("Sync Failed", "danger"); }
}

async function generateScopedKey() {
    const email = State.userEmail;
    const scope = UI.apiScopeSelect.value;
    
    try {
        const res = await fetch(`${API_BASE}/auth/generate?email=${email}&scope=${scope}`);
        const data = await res.json();
        if (data.api_key) {
            State.apiKey = data.api_key;
            State.apiScope = data.scope;
            UI.apiKeyCode.value = State.apiKey;
            notify(`New ${scope} key generated!`);
            
            firebase.database().ref(`clients/${State.clientId}`).update({ 
                api_key: State.apiKey,
                api_scope: State.apiScope
            });
        }
    } catch (e) { notify("Generation failed", "danger"); }
}

// --- CORE LOGIC ---

function switchModule(moduleName) {
    State.currentModule = moduleName;
    UI.navItems.forEach(item => item.classList.toggle('active', item.getAttribute('data-module') === moduleName));
    UI.modules.forEach(mod => mod.classList.toggle('active', mod.id === `module-${moduleName}`));
    if (moduleName === 'portfolio') renderPortfolio();
    if (moduleName === 'alerts') renderAlertsModule();
}

function initFirebase() {
    const config = {
        apiKey: "AIzaSyD0kFkl5z80JHXmGwdGgZciXxY8E1ts85E",
        authDomain: "stock-market-e710b.firebaseapp.com",
        databaseURL: "https://stock-market-e710b-default-rtdb.firebaseio.com",
        projectId: "stock-market-e710b"
    };
    if (!firebase.apps.length) firebase.initializeApp(config);
    const db = firebase.database();
    
    db.ref(`clients/${State.clientId}`).on('value', (snap) => {
        const val = snap.val();
        if (val) {
            if (val.api_key) { State.apiKey = val.api_key; UI.apiKeyCode.value = State.apiKey; }
            if (val.watchlist) State.watchlist = new Set(Object.keys(val.watchlist));
            if (val.portfolio) State.portfolio = Object.values(val.portfolio);
            if (val.alerts) State.alerts = Object.values(val.alerts);
            renderMainTable(); renderPortfolio(); renderAlertsModule();
        }
    });

    db.ref('dashboard').on('value', (snap) => {
        const data = snap.val();
        if (data) { processMarketData(data); hideLoader(); }
    });
}

function processMarketData(data) {
    if (data.summary) renderSummary(data.summary);
    if (data.prices) {
        State.marketData = data.prices;
        renderMainTable(); renderTicker();
        if (State.currentModule === 'portfolio') renderPortfolio();
    }
    if (data.gainers) renderRankList(data.gainers, UI.gainersList, true);
    if (data.losers) renderRankList(data.losers, UI.losersList, false);
    if (data.sectors) renderSectors(data.sectors);
}

// --- RENDERING ---

function renderSummary(s) {
    UI.nepseIndex.textContent = parseFloat(s.index_value || 0).toLocaleString();
    const isPos = s.change >= 0;
    UI.nepseChange.textContent = `${isPos ? '▲' : '▼'} ${Math.abs(s.change)} (${s.percent_change}%)`;
    UI.nepseChange.className = isPos ? 'positive-text' : 'negative-text';
    UI.totalTurnover.textContent = 'Rs. ' + (parseFloat(s.total_turnover || 0) / 10000000).toFixed(2) + ' Cr';
    UI.totalScripts.textContent = s.total_scripts || 0;
    const isOpen = s.market_status === 'OPEN';
    UI.statusDot.className = `dot ${isOpen ? 'open' : 'closed'}`;
    UI.statusText.textContent = s.market_status || 'OFFLINE';
}

function renderMainTable() {
    let data = [...State.marketData];
    if (State.currentFilter === 'TOP GAINERS') data.sort((a, b) => b.percent_change - a.percent_change);
    else if (State.currentFilter === 'TOP LOSERS') data.sort((a, b) => a.percent_change - b.percent_change);
    if (State.currentSearch) data = data.filter(d => d.symbol.toLowerCase().includes(State.currentSearch) || (d.name && d.name.toLowerCase().includes(State.currentSearch)));
    if (State.currentModule === 'watchlist') data = data.filter(d => State.watchlist.has(d.symbol));

    UI.mainTbody.innerHTML = data.map(item => {
        const isPos = item.change >= 0;
        const isWatched = State.watchlist.has(item.symbol);
        return `
            <tr>
                <td><span style="cursor:pointer; color:${isWatched ? '#f59e0b' : 'var(--text-dim)'}" onclick="toggleWatchlist('${item.symbol}')">${isWatched ? '★' : '☆'}</span></td>
                <td><span class="symbol-tag">${item.symbol}</span></td>
                <td class="price-val">${parseFloat(item.price).toLocaleString()}</td>
                <td class="${isPos ? 'positive-text' : 'negative-text'} font-mono">${isPos ? '+' : ''}${item.change}</td>
                <td class="${isPos ? 'positive-text' : 'negative-text'} font-mono">${isPos ? '+' : ''}${item.percent_change}%</td>
                <td class="font-mono">${formatVol(item.volume)}</td>
                <td>
                    <div style="display:flex; gap:0.5rem">
                        <button class="btn-analyze" onclick="openSymbolAnalysis('${item.symbol}')">ANALYZE</button>
                        <button class="btn-analyze" onclick="openAlertPrompt('${item.symbol}', ${item.price})">🔔</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function renderPortfolio() {
    if (!UI.portfolioTbody) return;
    let totalVal = 0, totalCost = 0;
    UI.portfolioTbody.innerHTML = State.portfolio.map(item => {
        const live = State.marketData.find(p => p.symbol === item.symbol) || { price: item.buyPrice, percent_change: 0 };
        const currentVal = item.units * live.price, cost = item.units * item.buyPrice, pl = currentVal - cost, plPercent = ((pl / cost) * 100).toFixed(2);
        totalVal += currentVal; totalCost += cost;
        return `
            <tr>
                <td><span class="symbol-tag">${item.symbol}</span></td>
                <td class="font-mono">${item.units}</td>
                <td class="font-mono">${item.buyPrice}</td>
                <td class="font-mono">${live.price}</td>
                <td class="font-mono">${currentVal.toLocaleString()}</td>
                <td class="${pl >= 0 ? 'positive-text' : 'negative-text'} font-mono">${pl >= 0 ? '+' : ''}${pl.toFixed(2)}</td>
                <td class="${pl >= 0 ? 'positive-text' : 'negative-text'} font-mono">${plPercent}%</td>
                <td><button class="btn-analyze" style="border-color:var(--danger); color:var(--danger)" onclick="removeFromPortfolio('${item.symbol}')">SELL</button></td>
            </tr>
        `;
    }).join('');
    UI.pTotalValue.textContent = 'Rs. ' + totalVal.toLocaleString();
    const totalPL = totalVal - totalCost;
    UI.pTotalPL.textContent = (totalPL >= 0 ? '+' : '') + totalPL.toLocaleString();
    UI.pTotalPL.className = totalPL >= 0 ? 'positive-text font-mono' : 'negative-text font-mono';
}

function renderAlertsModule() {
    if (!UI.alertsTbody) return;
    UI.alertsTbody.innerHTML = State.alerts.map(a => `
        <tr>
            <td><span class="symbol-tag">${a.symbol}</span></td>
            <td class="font-mono">${a.target}</td>
            <td>${a.type} TARGET</td>
            <td><span class="positive-text">ACTIVE</span></td>
            <td><button class="btn-analyze" onclick="removeAlert('${a.id}')">CLEAR</button></td>
        </tr>
    `).join('');
}

// --- ACTIONS ---

async function saveToPortfolio() {
    const symbol = document.getElementById('p-input-symbol').value.toUpperCase();
    const units = parseFloat(document.getElementById('p-input-units').value);
    const buyPrice = parseFloat(document.getElementById('p-input-price').value);
    if (symbol && units && buyPrice) {
        await firebase.database().ref(`clients/${State.clientId}/portfolio/${symbol}`).set({ symbol, units, buyPrice });
        UI.pModal.style.display = 'none';
        notify(`Added ${symbol} to portfolio`);
    }
}

async function removeFromPortfolio(symbol) {
    await firebase.database().ref(`clients/${State.clientId}/portfolio/${symbol}`).remove();
    notify(`Sold ${symbol}`);
}

async function toggleWatchlist(symbol) {
    if (State.watchlist.has(symbol)) {
        State.watchlist.delete(symbol);
        await firebase.database().ref(`clients/${State.clientId}/watchlist/${symbol}`).remove();
    } else {
        State.watchlist.add(symbol);
        await firebase.database().ref(`clients/${State.clientId}/watchlist/${symbol}`).set(true);
    }
    notify(`Watchlist updated: ${symbol}`);
}

function openAlertPrompt(symbol, currentPrice) {
    const target = prompt(`Set alert for ${symbol} (Current: ${currentPrice})`, currentPrice);
    if (target && !isNaN(target)) {
        const id = Date.now();
        const alert = { id, symbol, target: parseFloat(target), type: target > currentPrice ? 'ABOVE' : 'BELOW' };
        firebase.database().ref(`clients/${State.clientId}/alerts/${id}`).set(alert);
        notify(`Alert set for ${symbol}`);
    }
}

async function removeAlert(id) { await firebase.database().ref(`clients/${State.clientId}/alerts/${id}`).remove(); notify(`Alert cleared`); }

// --- UTILS ---

function startClock() { setInterval(() => { UI.clock.textContent = new Date().toLocaleTimeString('en-US', { hour12: false }); }, 1000); }
function hideLoader() { UI.loader.style.opacity = '0'; setTimeout(() => UI.loader.style.display = 'none', 500); }
function formatVol(v) { const n = parseFloat(v || 0); if (n >= 1000000) return (n/1000000).toFixed(2) + 'M'; if (n >= 1000) return (n/1000).toFixed(1) + 'K'; return n.toLocaleString(); }
function notify(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    document.getElementById('notification-container').appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function renderRankList(data, container, isPositive) { container.innerHTML = data.slice(0, 10).map(item => `<div class="rank-item"><strong>${item.symbol}</strong><span class="${isPositive ? 'positive-text' : 'negative-text'}">${isPositive ? '+' : ''}${item.percent_change}%</span></div>`).join(''); }
function renderSectors(sectors) { UI.sectorsList.innerHTML = sectors.slice(0, 10).map(s => `<div class="rank-item"><span>${s.sector}</span><span class="${parseFloat(s.percent_change) >= 0 ? 'positive-text' : 'negative-text'}">${s.percent_change}%</span></div>`).join(''); }
function renderTicker() {
    const items = State.marketData.slice(0, 30);
    UI.ticker.innerHTML = [...items, ...items].map(item => `<span class="ticker-item">${item.symbol} <span style="color:var(--text-primary)">${item.price}</span> <span class="${item.change >= 0 ? 'positive-text' : 'negative-text'}">${item.change >= 0 ? '▲' : '▼'}${Math.abs(item.percent_change)}%</span></span>`).join('');
}

function toggleApiKey() {
    const input = UI.apiKeyCode;
    const type = input.type === 'password' ? 'text' : 'password';
    input.type = type;
    document.getElementById('toggle-key-btn').textContent = type === 'password' ? 'SHOW' : 'HIDE';
}

async function copyApiKey() {
    await navigator.clipboard.writeText(UI.apiKeyCode.value);
    const btn = document.getElementById('copy-btn');
    btn.textContent = 'COPIED';
    setTimeout(() => btn.textContent = 'COPY', 2000);
}

async function openSymbolAnalysis(symbol) {
    UI.detailModal.style.display = 'block';
    document.getElementById('modal-company-name').textContent = symbol;
    document.getElementById('modal-company-symbol').textContent = 'LOADING...';
    try {
        const [fRes, hRes] = await Promise.allSettled([fetch(`${API_BASE}/fundamentals/${symbol}`), fetch(`${API_BASE}/history/${symbol}`)]);
        let fund = fRes.status === 'fulfilled' && fRes.value.ok ? await fRes.value.json() : {};
        let history = hRes.status === 'fulfilled' && hRes.value.ok ? await hRes.value.json() : [];
        document.getElementById('modal-company-symbol').textContent = fund.sector || 'EQUITY';
        document.getElementById('fundamental-grid').innerHTML = [{ label: 'MARKET CAP', val: fund.market_cap }, { label: 'EPS (TTM)', val: fund.eps_ttm }, { label: 'P/E RATIO', val: fund.pe_ratio }, { label: 'BOOK VALUE', val: fund.book_value }].map(m => `<div class="mini-stat"><label>${m.label}</label><span>${m.val || 'N/A'}</span></div>`).join('');
        document.getElementById('m-business').textContent = fund.business_model || 'Analysis pending...';
        document.getElementById('m-future').textContent = fund.future_growth || 'Projection pending...';
        initChart(history, symbol);
    } catch (e) { console.error(e); }
}

function initChart(data, symbol) {
    const container = document.getElementById('company-chart');
    container.innerHTML = '';
    if (!data.length) return;
    const chart = LightweightCharts.createChart(container, { layout: { background: { color: '#050608' }, textColor: '#8b949e' }, grid: { vertLines: { color: '#161b22' }, horzLines: { color: '#161b22' } }, timeScale: { borderColor: '#30363d' } });
    const series = chart.addCandlestickSeries({ upColor: '#3fb950', downColor: '#f85149', borderVisible: false, wickUpColor: '#3fb950', wickDownColor: '#f85149' });
    series.setData(data.map(d => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close })));
    chart.timeScale().fitContent();
}

window.toggleWatchlist = toggleWatchlist;
window.openSymbolAnalysis = openSymbolAnalysis;
window.openAlertPrompt = openAlertPrompt;
window.removeFromPortfolio = removeFromPortfolio;
window.removeAlert = removeAlert;

init();
