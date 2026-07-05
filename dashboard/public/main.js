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

function renderCityChart(trends) {
  const overview = trends.city_overview;
  new Chart(document.getElementById('cityChart'), {
    type: 'line',
    data: {
      labels: overview.map(r => r.month),
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

function renderDistrictSection(trends) {
  const districts = Object.keys(trends.districts).sort();
  const defaultSelected = new Set(trends.latest_ranking.slice(0, 3).map(r => r.district));

  const picker = document.getElementById('district-picker');
  const canvas = document.getElementById('districtChart');
  let chart = null;

  const labels = trends.city_overview.map(r => r.month);

  function buildChart() {
    const selected = districts.filter(d => defaultSelected.has(d));
    if (chart) chart.destroy();
    chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: selected.map((d, i) => {
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
  }

  picker.innerHTML = districts.map(d =>
    `<button class="district-chip${defaultSelected.has(d) ? ' active' : ''}" data-district="${d}">${d}</button>`
  ).join('');

  picker.addEventListener('click', (e) => {
    const btn = e.target.closest('.district-chip');
    if (!btn) return;
    const d = btn.dataset.district;
    if (defaultSelected.has(d)) {
      defaultSelected.delete(d);
      btn.classList.remove('active');
    } else {
      defaultSelected.add(d);
      btn.classList.add('active');
    }
    buildChart();
  });

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
