const PALETTE = ['#38bdf8', '#f472b6', '#facc15', '#4ade80', '#a78bfa', '#fb923c', '#2dd4bf', '#f87171'];

function formatMoney(n) {
  return new Intl.NumberFormat('zh-Hant-TW').format(Math.round(n));
}

function renderCards(trends) {
  const overview = trends.city_overview;
  const latest = overview[overview.length - 1];
  const container = document.getElementById('summary-cards');
  container.innerHTML = `
    <div class="card"><div class="label">最新資料月份</div><div class="value">${trends.latest_month}</div></div>
    <div class="card"><div class="label">全市每坪均價（元）</div><div class="value">${formatMoney(latest.avg_unit_price_ping)}</div></div>
    <div class="card"><div class="label">全市當月成交筆數</div><div class="value">${latest.transaction_count}</div></div>
    <div class="card"><div class="label">涵蓋行政區數</div><div class="value">${Object.keys(trends.districts).length}</div></div>
  `;
}

// 滾輪縮放：控制圖表 X 軸顯示的月份區間，右側永遠固定在最新月份（labels 最後一筆）。
function attachWheelZoom(canvas, labels, getChart, rangeLabelEl, { minWindow = 6 } = {}) {
  let visibleCount = labels.length;

  function apply() {
    const chart = getChart();
    if (!chart) return;
    const endIdx = labels.length - 1;
    const startIdx = Math.max(0, labels.length - visibleCount);
    chart.options.scales.x.min = labels[startIdx];
    chart.options.scales.x.max = labels[endIdx];
    chart.update('none');
    if (rangeLabelEl) {
      rangeLabelEl.textContent = visibleCount >= labels.length
        ? `完整區間 ${labels[startIdx]} ~ ${labels[endIdx]}`
        : `近 ${visibleCount} 個月（${labels[startIdx]} ~ ${labels[endIdx]}）`;
    }
  }

  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 0.85 : 1 / 0.85;
    visibleCount = Math.round(Math.min(labels.length, Math.max(minWindow, visibleCount * factor)));
    apply();
  }, { passive: false });

  return { apply };
}

function renderCityChart(trends) {
  const overview = trends.city_overview;
  const labels = overview.map(r => r.month);
  const canvas = document.getElementById('cityChart');
  const chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '全市每坪均價（元）',
        data: overview.map(r => r.avg_unit_price_ping),
        borderColor: PALETTE[0],
        backgroundColor: PALETTE[0] + '33',
        fill: true,
        tension: 0.25,
        pointRadius: 0,
      }],
    },
    options: {
      responsive: true,
      scales: {
        x: { ticks: { color: '#94a3b8', maxTicksLimit: 16 }, grid: { color: '#334155' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
      },
      plugins: { legend: { labels: { color: '#e2e8f0' } } },
    },
  });

  const zoom = attachWheelZoom(canvas, labels, () => chart, document.getElementById('city-chart-range'));
  zoom.apply();
}

function renderRankingChart(trends) {
  const ranking = trends.latest_ranking;
  new Chart(document.getElementById('rankingChart'), {
    type: 'bar',
    data: {
      labels: ranking.map(r => r.district),
      datasets: [{
        label: `${trends.ranking_period} 每坪中位數（元）`,
        data: ranking.map(r => r.median_unit_price_ping),
        backgroundColor: PALETTE[1],
      }],
    },
    options: {
      responsive: true,
      indexAxis: 'y',
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
      },
      plugins: { legend: { display: false } },
    },
  });
}

function colorForValue(v, min, max) {
  const stops = [
    { p: 0, c: [250, 204, 21] },   // 黃：低價
    { p: 1 / 3, c: [22, 163, 74] },  // 綠
    { p: 2 / 3, c: [37, 99, 235] },  // 藍
    { p: 1, c: [124, 58, 237] },   // 紫：高價
  ];
  const t = max > min ? (v - min) / (max - min) : 1;
  const tt = Math.max(0, Math.min(1, t));
  let i = 0;
  while (i < stops.length - 2 && tt > stops[i + 1].p) i++;
  const a = stops[i], b = stops[i + 1];
  const localT = (tt - a.p) / (b.p - a.p || 1);
  const rgb = a.c.map((v0, idx) => Math.round(v0 + (b.c[idx] - v0) * localT));
  return `rgb(${rgb.join(',')})`;
}

function renderDistrictSection(trends) {
  const districts = Object.keys(trends.districts).sort();
  const selected = new Set(trends.latest_ranking.slice(0, 3).map(r => r.district));
  const priceByDistrict = new Map(trends.latest_ranking.map(r => [r.district, r]));
  const prices = trends.latest_ranking.map(r => r.median_unit_price_ping);
  const priceMin = Math.min(...prices);
  const priceMax = Math.max(...prices);

  const picker = document.getElementById('district-picker');
  const canvas = document.getElementById('districtChart');
  const svg = document.getElementById('districtMap');
  const tooltip = document.getElementById('map-tooltip');
  const mapWrap = document.querySelector('.map-wrap');
  let chart = null;

  const labels = trends.city_overview.map(r => r.month);
  const zoom = attachWheelZoom(canvas, labels, () => chart, document.getElementById('district-chart-range'));

  function buildChart() {
    const selectedList = districts.filter(d => selected.has(d));
    if (chart) chart.destroy();
    chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: selectedList.map((d, i) => {
          const byMonth = new Map(trends.districts[d].map(r => [r.month, r.median_unit_price_ping]));
          return {
            label: d,
            data: labels.map(m => byMonth.get(m) ?? null),
            spanGaps: true,
            borderColor: PALETTE[i % PALETTE.length],
            backgroundColor: 'transparent',
            tension: 0.25,
            pointRadius: 0,
          };
        }),
      },
      options: {
        responsive: true,
        scales: {
          x: { ticks: { color: '#94a3b8', maxTicksLimit: 16 }, grid: { color: '#334155' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
        },
        plugins: { legend: { labels: { color: '#e2e8f0' } } },
      },
    });
    zoom.apply();
  }

  function syncUI() {
    picker.querySelectorAll('.district-chip').forEach(btn => {
      btn.classList.toggle('active', selected.has(btn.dataset.district));
    });
    svg.querySelectorAll('.map-district').forEach(path => {
      path.classList.toggle('selected', selected.has(path.dataset.district));
    });
  }

  function toggleDistrict(d) {
    if (selected.has(d)) {
      selected.delete(d);
    } else {
      selected.add(d);
    }
    syncUI();
    buildChart();
  }

  picker.innerHTML = districts.map(d =>
    `<button class="district-chip${selected.has(d) ? ' active' : ''}" data-district="${d}">${d}</button>`
  ).join('');
  picker.addEventListener('click', (e) => {
    const btn = e.target.closest('.district-chip');
    if (!btn) return;
    toggleDistrict(btn.dataset.district);
  });

  svg.setAttribute('viewBox', TAICHUNG_MAP_VIEWBOX);
  svg.innerHTML = Object.entries(TAICHUNG_DISTRICT_PATHS).map(([name, d]) => {
    const stat = priceByDistrict.get(name);
    const fill = stat ? colorForValue(stat.median_unit_price_ping, priceMin, priceMax) : null;
    const noData = !stat;
    return `<path class="map-district${noData ? ' no-data' : ''}${selected.has(name) ? ' selected' : ''}"
      data-district="${name}" d="${d}" ${fill ? `fill="${fill}"` : ''}></path>`;
  }).join('');

  svg.querySelectorAll('.map-district').forEach(path => {
    const name = path.dataset.district;
    const stat = priceByDistrict.get(name);
    path.addEventListener('click', () => {
      if (stat) toggleDistrict(name);
    });
    path.addEventListener('mousemove', (e) => {
      const rect = mapWrap.getBoundingClientRect();
      tooltip.style.left = `${e.clientX - rect.left}px`;
      tooltip.style.top = `${e.clientY - rect.top - 8}px`;
      tooltip.innerHTML = stat
        ? `<div class="name">${name}</div><div class="price">${formatMoney(stat.median_unit_price_ping)} 元/坪</div><div>近三個月 ${stat.transaction_count} 筆</div>`
        : `<div class="name">${name}</div><div>近三個月交易筆數不足</div>`;
      tooltip.classList.add('visible');
    });
    path.addEventListener('mouseleave', () => tooltip.classList.remove('visible'));
  });

  document.getElementById('legend-min').textContent = `${(priceMin / 10000).toFixed(1)}萬`;
  document.getElementById('legend-max').textContent = `${(priceMax / 10000).toFixed(1)}萬`;

  buildChart();
}

async function main() {
  const res = await fetch('/api/trends');
  if (!res.ok) {
    document.body.innerHTML = '<p style="padding:40px;color:#f87171">趨勢資料尚未產生，請先執行 python 資料管線（run_pipeline.py）。</p>';
    return;
  }
  const trends = await res.json();

  renderCards(trends);
  renderCityChart(trends);
  renderRankingChart(trends);
  renderDistrictSection(trends);

  document.getElementById('updated-at').textContent = `資料更新時間：${new Date(trends.updated_at).toLocaleString('zh-TW')}`;
}

main();
