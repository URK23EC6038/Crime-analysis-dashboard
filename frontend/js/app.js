let map;

document.addEventListener('DOMContentLoaded', async () => {
    setInterval(() => document.getElementById('live-clock').innerText = new Date().toLocaleTimeString(), 1000);
    initMap();
    initSparklines();
    await loadSystem();
    const form = document.getElementById('officerForm');
    if(form) form.addEventListener('submit', async (e) => { e.preventDefault(); await submitCase(); });
});

function initSparklines() {
    new Chart(document.getElementById('spark1'), {type:'line', data:{labels:[1,2,3,4,5], datasets:[{data:[10,15,12,18,20], borderColor:'#06b6d4', borderWidth:2, pointRadius:0, tension:0.4}]}, options:{plugins:{legend:false}, scales:{x:{display:false}, y:{display:false}}, responsive:true, maintainAspectRatio:false}});
    new Chart(document.getElementById('spark2'), {type:'line', data:{labels:[1,2,3,4,5], datasets:[{data:[90,92,91,93,94], borderColor:'#a855f7', borderWidth:2, pointRadius:0, tension:0.4}]}, options:{plugins:{legend:false}, scales:{x:{display:false}, y:{display:false}}, responsive:true, maintainAspectRatio:false}});
}

async function loadSystem() {
    try {
        const res = await fetch('/api/intel-feed');
        if (!res.ok) throw new Error("Backend offline");
        const data = await res.json();
        
        document.getElementById('stat-total').innerText = data.brief.total_incidents.toLocaleString();
        document.getElementById('stat-risk').innerText = data.brief.critical_zone;
        document.getElementById('stat-safe').innerText = data.brief.safe_zone;
        document.getElementById('stat-score').innerText = data.brief.critical_score;

        updateMap(data.chart_data);
        updateAIFeed(data);
        
        const sel = document.getElementById('entry-district');
        if (sel && sel.options.length <= 1) data.chart_data.districts.sort().forEach(d => {
            const opt = document.createElement('option'); opt.value = d; opt.innerText = d; sel.appendChild(opt);
        });
    } catch (e) { console.error(e); }
}

async function submitCase() {
    const btn = document.querySelector('button[type="submit"]');
    const original = btn.innerHTML;
    btn.innerHTML = 'PROCESSING...';
    try {
        const res = await fetch('/api/add-case', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                district: document.getElementById('entry-district').value,
                crime_type: document.getElementById('entry-type').value,
                description: document.getElementById('entry-desc').value,
                severity: "High"
            })
        });
        if(res.ok) { alert("✅ LOGGED"); document.getElementById('entry-desc').value = ''; await loadSystem(); }
    } catch(e) { alert("❌ Error"); }
    btn.innerHTML = original;
}

function updateAIFeed(data) {
    const feed = document.getElementById('ai-feed');
    if(!feed) return;
    feed.innerHTML = '';
    data.predictive_drivers.forEach(d => {
        feed.innerHTML += `<div class="p-3 bg-slate-900/80 rounded border-l-2 border-purple-500 mb-2"><div class="flex justify-between"><span class="text-[10px] text-purple-400 font-bold">DRIVER DETECTED</span></div><div class="text-xs text-slate-300 mt-1"><span class="text-white font-bold">${d.Factor}</span> impact: ${(d.Impact_Score*100).toFixed(1)}%</div></div>`;
    });
}

function initMap() {
    map = L.map('map', { zoomControl: false }).setView([11.1271, 78.6569], 6);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '© OpenStreetMap' }).addTo(map);
    const legend = L.control({position: 'bottomright'});
    legend.onAdd = function () {
        const div = L.DomUtil.create('div', 'info legend');
        div.style.background = 'rgba(15,23,42,0.9)'; div.style.padding = '10px'; div.style.color = '#fff'; div.style.borderRadius = '8px'; div.style.fontSize = '10px';
        div.innerHTML = '<strong>Threat Map</strong><br><span style="color:#3b82f6">●</span> Accident<br><span style="color:#ef4444">●</span> Murder<br><span style="color:#a855f7">●</span> Harassment<br><span style="color:#f97316">●</span> Suicide';
        return div;
    };
    legend.addTo(map);
}

async function updateMap(chartData) {
    const res = await fetch('/api/geo-layers');
    const geojson = await res.json();
    if (!geojson.features) return;
    
    let maxAcc=1, maxMur=1, maxHar=1, maxSui=1;
    geojson.features.forEach(f => {
        const p = f.properties;
        if(p.accidents > maxAcc) maxAcc = p.accidents;
        if(p.murders > maxMur) maxMur = p.murders;
        if(p.harassment > maxHar) maxHar = p.harassment;
        if(p.suicides > maxSui) maxSui = p.suicides;
    });

    L.geoJSON(geojson, {
        style: (f) => {
            const p = f.properties;
            const sAcc = p.accidents/maxAcc, sMur = p.murders/maxMur, sHar = p.harassment/maxHar, sSui = p.suicides/maxSui;
            let color = '#10b981', max = 0;
            if (p.risk_score > 15) {
                if (sAcc > max) { max = sAcc; color = '#3b82f6'; }
                if (sMur > max) { max = sMur; color = '#ef4444'; }
                if (sHar > max) { max = sHar; color = '#a855f7'; }
                if (sSui > max) { max = sSui; color = '#f97316'; }
            }
            return { fillColor: color, weight: 1, opacity: 1, color: '#1e293b', fillOpacity: 0.7 };
        },
        onEachFeature: (f, l) => {
            const p = f.properties;
            const dName = p.DISTRICT || "District";
            l.bindPopup(`<div style="color:#020617"><strong>${dName}</strong><hr><span style="color:#3b82f6">Accidents: ${p.accidents}</span><br><span style="color:#ef4444">Violent: ${p.murders}</span><br><span style="color:#a855f7">Harassment: ${p.harassment}</span></div>`);
        }
    }).addTo(map);
}