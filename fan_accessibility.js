/* Fan Accessibility & Equity — native canvas module for Premier League Atlas.
   Add <script src="fan_accessibility.js"></script> immediately before </body>.
   It adds one GIS Lab tab and does not replace or modify existing experiments. */
(() => {
  'use strict';
  const DATA_BASE = './data/fan-accessibility/';
  const GEO_FILE = 'fan_accessibility.geojson.gz';
  const SUMMARY_FILE = 'fan_accessibility_summary.json';
  const CLUBS = [
    ['ARS','Arsenal',51.555,-0.108],['AVL','Aston Villa',52.509,-1.885],['BOU','Bournemouth',50.735,-1.838],
    ['BRE','Brentford',51.491,-0.289],['BHA','Brighton',50.862,-0.083],['CHE','Chelsea',51.482,-0.191],
    ['COV','Coventry City',52.4488,-1.4958],['CRY','Crystal Palace',51.398,-0.086],['EVE','Everton',53.426,-3.004],
    ['FUL','Fulham',51.475,-0.222],['HUL','Hull City',53.7463,-0.3677],['IPS','Ipswich Town',52.055,1.1445],
    ['LEE','Leeds',53.778,-1.572],['LIV','Liverpool',53.431,-2.961],['MCI','Man City',53.483,-2.2],
    ['MUN','Man United',53.463,-2.291],['NEW','Newcastle',54.976,-1.622],['NFO',"Nott'm Forest",52.94,-1.133],
    ['SUN','Sunderland',54.915,-1.388],['TOT','Tottenham',51.604,-0.066]
  ];
  const COLORS = {'0-30':'#00d69a','30-60':'#a8d65e','60-90':'#f4bd55','90+':'#ed6688'};
  const $ = id => document.getElementById(id);
  const ar = () => { try { return typeof LANG !== 'undefined' && LANG === 'ar'; } catch (_) { return document.documentElement.dir === 'rtl'; } };
  const tr = (en, arabic) => ar() ? arabic : en;
  const fmt = n => Number(n || 0).toLocaleString(ar() ? 'ar-EG' : 'en-GB');
  const pct = n => n == null ? '—' : `${Number(n).toFixed(1)}%`;
  const mins = n => n == null ? '—' : `${Number(n).toFixed(1)} ${tr('min','دقيقة')}`;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  const style = document.createElement('style');
  style.textContent = `
  #p-fae{margin-top:4px}.fae-shell{background:var(--card);border:1px solid var(--line);border-radius:24px;padding:clamp(13px,2.3vw,24px);box-shadow:var(--shadow);overflow:hidden}
  .fae-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:15px}.fae-kicker{font-size:10px;letter-spacing:.16em;font-weight:800;color:var(--acc)}
  .fae-title{font:700 clamp(23px,3vw,35px)/1.08 "Iowan Old Style",Georgia,serif;margin:5px 0}.fae-lede{font-size:13px;color:var(--mut);max-width:68ch;margin:6px 0 0}
  .fae-status{font-size:11px;border:1px solid var(--line);border-radius:99px;padding:6px 10px;white-space:nowrap;color:var(--mut)}
  .fae-kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;margin:14px 0}.fae-kpi{background:var(--bg);border:1px solid var(--line);border-radius:15px;padding:11px;min-width:0}.fae-kpi b{display:block;font:700 clamp(19px,2.3vw,27px)/1.05 "Iowan Old Style",Georgia,serif;overflow-wrap:anywhere}.fae-kpi span{display:block;color:var(--mut);font-size:11px;margin-top:5px}
  .fae-layout{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(255px,.8fr);gap:13px;align-items:start}.fae-mapbox{background:#190020;border:1px solid rgba(255,255,255,.12);border-radius:19px;overflow:hidden;position:relative}.fae-mapbox canvas{width:100%;height:auto;display:block;cursor:crosshair}.fae-map-foot{display:flex;flex-wrap:wrap;gap:10px 15px;padding:10px 13px;color:#e8ddeb;font-size:11px;border-top:1px solid rgba(255,255,255,.12)}.fae-legend{display:inline-flex;align-items:center;gap:6px}.fae-swatch{width:10px;height:10px;border-radius:3px;display:inline-block}
  .fae-side{background:var(--bg);border:1px solid var(--line);border-radius:18px;padding:13px;min-width:0}.fae-side label{display:block;font-size:11px;color:var(--mut);margin:0 0 5px}.fae-side select{margin:0 0 10px}.fae-detail{border-top:1px solid var(--line);padding-top:11px;margin-top:4px}.fae-detail h4{font:700 20px/1.1 "Iowan Old Style",Georgia,serif;margin:0 0 8px}.fae-kv{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid var(--line);font-size:12px}.fae-kv span{color:var(--mut)}.fae-kv b{text-align:end}.fae-list{margin-top:16px}.fae-list h4{font:700 20px Georgia,serif;margin:0 0 8px}.fae-rank{display:grid;grid-template-columns:26px 1fr auto;gap:8px;align-items:center;padding:8px 5px;border-bottom:1px solid var(--line);font-size:12px;cursor:pointer}.fae-rank:hover{background:var(--bg)}.fae-rank strong{font-weight:700}.fae-rank small{display:block;color:var(--mut);font-size:10px}.fae-bar{height:4px;background:var(--line);border-radius:9px;overflow:hidden;margin-top:5px}.fae-bar i{display:block;height:100%;background:var(--acc)}.fae-compare{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.fae-compare>div{border:1px solid var(--line);border-radius:12px;padding:9px;min-width:0}.fae-compare b{display:block;font-size:15px}.fae-compare small{color:var(--mut);font-size:10px}.fae-story{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-top:14px}.fae-story article{border:1px solid var(--line);border-radius:14px;padding:12px;background:var(--bg)}.fae-story strong{display:block;font:700 17px Georgia,serif;margin-bottom:5px}.fae-story p{font-size:12px;color:var(--mut);margin:0}.fae-method{margin-top:14px;border-top:1px solid var(--line);padding-top:12px;font-size:11px;color:var(--mut);line-height:1.6}.fae-method a{color:inherit}.fae-empty{padding:28px;border:1px dashed var(--line);border-radius:16px;color:var(--mut);text-align:center}.fae-error{color:#d54b70}.fae-small{font-size:10px;color:var(--mut);line-height:1.5}
  @media(max-width:850px){.fae-layout{grid-template-columns:1fr}.fae-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.fae-kpi:last-child{grid-column:span 2}.fae-story{grid-template-columns:1fr}.fae-head{flex-direction:column}.fae-status{white-space:normal}}
  `;
  document.head.appendChild(style);

  function install() {
    const tabs = $('tabs');
    const scbi = $('p-scbi');
    if (!tabs || !scbi || $('p-fae')) return false;
    const tab = document.createElement('button');
    tab.type = 'button'; tab.dataset.tab = 'fae'; tab.setAttribute('aria-pressed','false');
    tab.textContent = tr('Fan accessibility','إمكانية الوصول للملاعب');
    tabs.appendChild(tab);
    const panel = document.createElement('section');
    panel.id = 'p-fae'; panel.hidden = true;
    panel.innerHTML = `
      <div class="fae-shell">
        <div class="fae-head"><div><div class="fae-kicker">POPULATION / ROAD NETWORK / SPATIAL EQUITY · 03</div>
          <h3 class="fae-title">${tr('Fan Accessibility & Equity','إمكانية الوصول والعدالة المكانية للملاعب')}</h3>
          <p class="fae-lede">${tr('How many people can reach a Premier League stadium within a modeled driving time? Explore every LSOA, compare club catchments and reveal where access is geographically uneven.','كم عدد السكان الذين يمكنهم الوصول إلى ملعب خلال زمن قيادة محسوب؟ استكشف مناطق LSOA وقارن نطاقات الأندية واكتشف تفاوت سهولة الوصول جغرافيًا.')}</p></div>
          <div class="fae-status" id="fae-status">${tr('Checking data…','جارٍ التحقق من البيانات…')}</div></div>
        <div id="fae-content"><div class="fae-empty">${tr('Loading verified accessibility data…','جارٍ تحميل بيانات الوصول والتحقق منها…')}</div></div>
      </div>`;
    scbi.insertAdjacentElement('afterend', panel);

    // Keep the existing tab system intact; just make sure our panel closes when
    // any of the original tabs is selected.
    tabs.querySelectorAll('[data-tab]:not([data-tab="fae"])').forEach(b => b.addEventListener('click', () => { panel.hidden = true; tab.setAttribute('aria-pressed','false'); }));
    tab.addEventListener('click', () => {
      tabs.querySelectorAll('[data-tab]').forEach(b => b.setAttribute('aria-pressed', b === tab ? 'true' : 'false'));
      document.querySelectorAll('[id^="p-"]').forEach(p => { if (p.id !== 'p-fae') p.hidden = true; });
      panel.hidden = false;
      if (window.__faeRender) window.__faeRender();
    });
    const languageButton = $('lang');
    if (languageButton) languageButton.addEventListener('click', () => setTimeout(() => {
      tab.textContent = tr('Fan accessibility','إمكانية الوصول للملاعب');
      if (window.__faeRebuild) window.__faeRebuild();
    }, 0));
    return true;
  }

  async function readGzipJSON(url) {
    const response = await fetch(url, {cache:'no-cache'});
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const buffer = await response.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
      if (!('DecompressionStream' in window)) throw new Error('This browser cannot decompress the published .gz file.');
      const stream = new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'));
      return JSON.parse(await new Response(stream).text());
    }
    return JSON.parse(new TextDecoder().decode(buffer));
  }

  let fc = null, summary = null, features = [], selected = null, activeClub = 'ALL', activeBand = 'ALL', compareClub = '';
  let canvas = null, ctx = null, mapW = 900, mapH = 620, centroids = [];
  const x = lon => 50 + (lon + 6.5) / 8.8 * 800;
  const y = lat => 28 + (56.0 - lat) / 6.5 * 545;
  const getCentroid = geom => {
    let sx=0, sy=0, n=0;
    const visit = ring => { for (const p of ring) { if (Array.isArray(p) && p.length >= 2) { sx += p[0]; sy += p[1]; n++; } } };
    if (!geom) return null;
    if (geom.type === 'Polygon') geom.coordinates.forEach(visit);
    else if (geom.type === 'MultiPolygon') geom.coordinates.forEach(poly => poly.forEach(visit));
    return n ? [sx/n, sy/n] : null;
  };
  function pathForGeom(geom) {
    const path = new Path2D();
    if (!geom) return path;
    const rings = geom.type === 'Polygon' ? geom.coordinates : geom.type === 'MultiPolygon' ? geom.coordinates.flat() : [];
    for (const ring of rings) {
      if (!ring.length) continue;
      path.moveTo(x(ring[0][0]), y(ring[0][1]));
      for (let i=1;i<ring.length;i++) path.lineTo(x(ring[i][0]), y(ring[i][1]));
      path.closePath();
    }
    return path;
  }
  function bandOf(minutes) { return minutes <= 30 ? '0-30' : minutes <= 60 ? '30-60' : minutes <= 90 ? '60-90' : '90+'; }
  function visible(f) {
    const p=f.properties;
    if (activeClub !== 'ALL' && p.club_code !== activeClub) return false;
    if (activeBand !== 'ALL' && p.access_band !== activeBand) return false;
    return true;
  }
  function drawMap() {
    if (!canvas || !ctx || !features.length) return;
    ctx.clearRect(0,0,mapW,mapH);
    const grad=ctx.createLinearGradient(0,0,mapW,mapH);grad.addColorStop(0,'#18001e');grad.addColorStop(1,'#2b1035');ctx.fillStyle=grad;ctx.fillRect(0,0,mapW,mapH);
    // Subtle geographic graticule.
    ctx.strokeStyle='rgba(255,255,255,.075)';ctx.lineWidth=1;
    for(let lon=-6;lon<=2;lon+=2){ctx.beginPath();ctx.moveTo(x(lon),20);ctx.lineTo(x(lon),585);ctx.stroke();}
    for(let lat=50;lat<=56;lat+=1){ctx.beginPath();ctx.moveTo(35,y(lat));ctx.lineTo(865,y(lat));ctx.stroke();}
    // Aggregate polygons into a handful of paths so 30k+ LSOAs remain responsive.
    const paths={'0-30':new Path2D(),'30-60':new Path2D(),'60-90':new Path2D(),'90+':new Path2D()}, muted=new Path2D();
    for(const f of features){const p=f.properties;const dim=(activeClub!=='ALL'&&p.club_code!==activeClub)||(activeBand!=='ALL'&&p.access_band!==activeBand);(dim?muted:paths[p.access_band]||muted).addPath(pathForGeom(f.geometry));}
    for(const band of ['90+','60-90','30-60','0-30']){ctx.fillStyle=COLORS[band];ctx.globalAlpha=.9;ctx.fill(paths[band],'evenodd');}
    ctx.fillStyle='#514957';ctx.globalAlpha=.24;ctx.fill(muted,'evenodd');ctx.globalAlpha=1;
    // Stadium points, deliberately restrained so the choropleth remains primary.
    for(const c of CLUBS){const px=x(c[3]),py=y(c[2]);ctx.beginPath();ctx.arc(px,py,4.2,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.lineWidth=1.5;ctx.strokeStyle='#21002a';ctx.stroke();}
    ctx.font='700 9px system-ui';ctx.textAlign='left';ctx.textBaseline='middle';
    for(const c of CLUBS){if(['ARS','BRE','BHA','CHE','CRY','FUL','TOT'].includes(c[0]))continue;const px=x(c[3]),py=y(c[2]);ctx.lineWidth=2.5;ctx.strokeStyle='#21002a';ctx.fillStyle='#fff';ctx.strokeText(c[0],px+6,py-6);ctx.fillText(c[0],px+6,py-6);}
    if(selected){const c=selected._centroid;if(c){ctx.beginPath();ctx.arc(x(c[0]),y(c[1]),7,0,Math.PI*2);ctx.strokeStyle='#fff';ctx.lineWidth=2.5;ctx.stroke();}}
    ctx.fillStyle='rgba(255,255,255,.82)';ctx.font='700 13px system-ui';ctx.fillText('ENGLAND · LSOA 2021',22,22);
  }
  function kpi(value,label){return `<div class="fae-kpi"><b>${value}</b><span>${label}</span></div>`;}
  function kv(label,value){return `<div class="fae-kv"><span>${label}</span><b>${value}</b></div>`;}
  function catchmentRows(){
    const rows=(summary.club_catchments||[]).slice().sort((a,b)=>b.assigned_population-a.assigned_population);
    const max=Math.max(1,...rows.map(r=>r.assigned_population));
    return rows.map((r,i)=>`<div class="fae-rank" data-code="${esc(r.code)}"><span>${String(i+1).padStart(2,'0')}</span><div><strong>${esc(r.name)}</strong><small>${fmt(r.lsoa_count)} LSOAs · ${pct(r.within_60_pct)} ${tr('within 60 min','خلال 60 دقيقة')}</small><div class="fae-bar"><i style="width:${Math.max(1,r.assigned_population/max*100)}%"></i></div></div><b>${fmt(r.assigned_population)}</b></div>`).join('');
  }
  function buildContent() {
    const c30=summary.coverage_by_minutes['30'],c60=summary.coverage_by_minutes['60'],c90=summary.coverage_by_minutes['90'];
    const largest=(summary.club_catchments||[]).slice().sort((a,b)=>b.assigned_population-a.assigned_population)[0];
    const slowest=(summary.club_catchments||[]).filter(r=>r.weighted_p90_minutes!=null).sort((a,b)=>b.weighted_p90_minutes-a.weighted_p90_minutes)[0];
    const p=summary.population_total;
    $('fae-content').innerHTML=`
      <div class="fae-kpis">
        ${kpi(fmt(p),tr('Population represented','السكان المشمولون'))}
        ${kpi(pct(c30.share_pct),tr('Within 30 min','خلال 30 دقيقة'))}
        ${kpi(pct(c60.share_pct),tr('Within 60 min','خلال 60 دقيقة'))}
        ${kpi(pct(c90.share_pct),tr('Within 90 min','خلال 90 دقيقة'))}
        ${kpi(mins(summary.weighted_median_minutes),tr('Weighted median','الوسيط الموزون'))}
      </div>
      <div class="fae-layout">
        <div class="fae-mapbox"><canvas id="fae-map" width="900" height="620" role="img" aria-label="LSOA choropleth of modeled driving time to the fastest Premier League stadium"></canvas>
          <div class="fae-map-foot">${['0-30','30-60','60-90','90+'].map(b=>`<span class="fae-legend"><i class="fae-swatch" style="background:${COLORS[b]}"></i>${b} ${tr('min','دقيقة')}</span>`).join('')}<span>${tr('● Stadiums','● الملاعب')}</span></div></div>
        <aside class="fae-side">
          <label for="fae-club">${tr('Highlight a club catchment','إبراز نطاق نادي')}</label>
          <select id="fae-club"><option value="ALL">${tr('All clubs · national view','كل الأندية · عرض إنجلترا')}</option>${CLUBS.map(c=>`<option value="${c[0]}">${esc(c[1])}</option>`).join('')}</select>
          <label for="fae-band">${tr('Filter driving-time band','تصفية حسب زمن القيادة')}</label>
          <select id="fae-band"><option value="ALL">${tr('All time bands','كل الفئات الزمنية')}</option><option value="0-30">0–30 min</option><option value="30-60">30–60 min</option><option value="60-90">60–90 min</option><option value="90+">90+ min</option></select>
          <label for="fae-compare">${tr('Compare with another club','مقارنة مع نادٍ آخر')}</label>
          <select id="fae-compare"><option value="">${tr('Choose a club','اختر ناديًا')}</option>${CLUBS.map(c=>`<option value="${c[0]}">${esc(c[1])}</option>`).join('')}</select>
          <div class="fae-detail" id="fae-detail"><h4>${tr('Select an LSOA','اختر منطقة LSOA')}</h4><p class="fae-small">${tr('Click a small area on the map to inspect its population, fastest stadium and modeled driving time.','اضغط على منطقة صغيرة بالخريطة لمعرفة عدد سكانها وأقرب ملعب وزمن القيادة المحسوب.')}</p></div>
          <div class="fae-compare" id="fae-compare-box" hidden></div>
          <p class="fae-small" style="margin:12px 0 0">${tr('The map assigns each LSOA to the stadium with the fastest modeled drive.','تُسند كل منطقة إلى الملعب ذي أسرع زمن قيادة محسوب.')}</p>
        </aside>
      </div>
      <div class="fae-story">
        <article><strong>${tr('Geographic reach','الانتشار الجغرافي')}</strong><p>${tr(`${pct(c90.share_pct)} of the represented population is within a modeled 90-minute drive of at least one stadium.`,`${pct(c90.share_pct)} من السكان المشمولين يقعوا ضمن 90 دقيقة قيادة محسوبة من ملعب واحد على الأقل.`)}</p></article>
        <article><strong>${tr('Largest assigned catchment','أكبر نطاق وصول')}</strong><p>${largest?`${esc(largest.name)} · ${fmt(largest.assigned_population)} ${tr('people','نسمة')}`:tr('No result','لا توجد نتيجة')}</p></article>
        <article><strong>${tr('Longest upper-tail access','الأطول في ذيل زمن الوصول')}</strong><p>${slowest?`${esc(slowest.name)} · P90 ${mins(slowest.weighted_p90_minutes)}`:tr('No result','لا توجد نتيجة')}</p></article>
      </div>
      <div class="fae-list"><h4>${tr('Club catchment comparison','مقارنة نطاقات الأندية')}</h4><p class="fae-small">${tr('Population assigned to each club by fastest modeled driving time. Select a row to highlight its LSOAs.','السكان المسندون لكل نادٍ حسب أسرع زمن قيادة محسوب. اختر صفًا لإبراز مناطقه على الخريطة.')}</p><div id="fae-rankings">${catchmentRows()}</div></div>
      <div class="fae-method"><b>${tr('Method & limitations','المنهجية والقيود')}</b><br>
      ${tr('ONS mid-2024 LSOA population estimates are joined to ONS 2021 population-weighted centroids and 2021 LSOA boundaries. Each centroid is routed to all 20 stadiums with the OpenRouteService driving-car matrix; the fastest modeled route determines its catchment and time band. Population metrics are weighted by the LSOA population.','تُربط تقديرات سكان ONS لمنتصف 2024 بمراكز الثقل السكاني لمناطق LSOA لعام 2021 وحدودها. يُحسب زمن القيادة من كل مركز إلى الملاعب العشرين عبر مصفوفة OpenRouteService، ويحدد أسرع زمن نطاق الوصول والفئة الزمنية. تُوزن المؤشرات بعدد السكان في كل منطقة.')}<br>
      ${tr('This is potential geographic accessibility, not supporter location, ticket ownership or attendance. A centroid represents an area rather than every resident. Times are modeled and exclude live traffic, matchday congestion, parking and public transport. Population and boundary vintages differ (2024 vs 2021).','هذا يقيس إمكانية الوصول الجغرافي، وليس أماكن المشجعين أو حاملي التذاكر أو الحضور الفعلي. مركز المنطقة يمثلها ولا يمثل موقع كل فرد. أزمنة القيادة محسوبة وليست لحظية ولا تشمل ازدحام يوم المباراة أو مواقف السيارات أو النقل العام. سنة السكان 2024 وسنة الحدود 2021.')}<br>
      <a href="https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/lowersuperoutputareamidyearpopulationestimates" target="_blank" rel="noopener">ONS population</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap attribution</a> · <a href="https://openrouteservice.org/" target="_blank" rel="noopener">OpenRouteService</a><br>
      <span>${tr('Generated','تاريخ الإنشاء')}: ${esc(summary.generated_utc||'—')} · ${fmt(summary.mapped_lsoa_count)} ${tr('mapped LSOAs','منطقة مرسومة')} · ${tr('Weighted P90','المئين 90 الموزون')}: ${mins(summary.weighted_p90_minutes)} · Gini: ${Number(summary.population_weighted_gini).toFixed(3)}</span>
      </div>`;
    canvas=$('fae-map');ctx=canvas.getContext('2d');
    $('fae-club').value=activeClub; $('fae-band').value=activeBand;
    $('fae-club').addEventListener('change',e=>{activeClub=e.target.value;selected=null;drawMap();renderDetail();});
    $('fae-band').addEventListener('change',e=>{activeBand=e.target.value;drawMap();});
    $('fae-compare').addEventListener('change',e=>{compareClub=e.target.value;renderCompare();});
    $('fae-rankings').querySelectorAll('[data-code]').forEach(row=>row.addEventListener('click',()=>{activeClub=row.dataset.code;activeBand='ALL';$('fae-club').value=activeClub;$('fae-band').value='ALL';selected=null;drawMap();renderDetail();}));
    canvas.addEventListener('click',onMapClick);
    drawMap();
  }
  function renderDetail(){
    const box=$('fae-detail');if(!box)return;
    if(!selected){
      if(activeClub==='ALL'){box.innerHTML=`<h4>${tr('National accessibility','إمكانية الوصول على مستوى إنجلترا')}</h4>${kv(tr('Weighted P90','المئين 90 الموزون'),mins(summary.weighted_p90_minutes))}${kv(tr('Population-weighted Gini','معامل جيني الموزون'),Number(summary.population_weighted_gini).toFixed(3))}`;}
      else {const r=(summary.club_catchments||[]).find(x=>x.code===activeClub);box.innerHTML=r?`<h4>${esc(r.name)}</h4>${kv(tr('Assigned population','السكان ضمن النطاق'),fmt(r.assigned_population))}${kv(tr('LSOAs','مناطق LSOA'),fmt(r.lsoa_count))}${kv(tr('Weighted median','الوسيط الموزون'),mins(r.weighted_median_minutes))}${kv('P90',mins(r.weighted_p90_minutes))}${kv(tr('Within 60 min','خلال 60 دقيقة'),pct(r.within_60_pct))}`:'';}
      return;
    }
    const p=selected.properties;
    box.innerHTML=`<h4>${tr('Selected LSOA','منطقة LSOA المحددة')}</h4>${kv(tr('Area code','كود المنطقة'),esc(p.lsoa))}${kv(tr('Population','عدد السكان'),fmt(p.population))}${kv(tr('Fastest stadium','أسرع ملعب'),esc(p.club_name))}${kv(tr('Driving time','زمن القيادة'),mins(p.minutes))}${kv(tr('Modeled road distance','مسافة الطريق المحسوبة'),p.distance_km==null?'—':`${Number(p.distance_km).toFixed(1)} km`)}${kv(tr('Access band','فئة الوصول'),esc(p.access_band)+' min')}`;
  }
  function renderCompare(){
    const box=$('fae-compare-box');if(!box)return;
    const a=(summary.club_catchments||[]).find(r=>r.code===activeClub);
    const b=(summary.club_catchments||[]).find(r=>r.code===compareClub);
    if(!a||!b||a.code===b.code){box.hidden=true;return;}
    box.hidden=false;
    box.innerHTML=[a,b].map(r=>`<div><small>${esc(r.name)}</small><b>${fmt(r.assigned_population)}</b><small>${tr('assigned population','سكان النطاق')}</small>${kv(tr('Median','الوسيط'),mins(r.weighted_median_minutes))}${kv('P90',mins(r.weighted_p90_minutes))}${kv(tr('Within 60 min','خلال 60 دقيقة'),pct(r.within_60_pct))}</div>`).join('');
  }
  function onMapClick(e){
    if(!centroids.length)return;
    const rect=canvas.getBoundingClientRect();const px=(e.clientX-rect.left)*mapW/rect.width,py=(e.clientY-rect.top)*mapH/rect.height;
    let best=null,bd=18*18;
    for(const f of centroids){if(!visible(f))continue;const c=f._centroid;if(!c)continue;const dx=x(c[0])-px,dy=y(c[1])-py,d=dx*dx+dy*dy;if(d<bd){bd=d;best=f;}}
    if(best){selected=best;drawMap();renderDetail();}
  }
  async function load() {
    if(!install()) return;
    const status=$('fae-status');
    try {
      const [geo,stats]=await Promise.all([readGzipJSON(DATA_BASE+GEO_FILE),fetch(DATA_BASE+SUMMARY_FILE,{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(`${r.status} ${r.statusText}`);return r.json();})]);
      if(geo.type!=='FeatureCollection'||!Array.isArray(geo.features)||geo.features.length<30000)throw new Error('GeoJSON integrity check failed: expected at least 30,000 LSOA polygons.');
      if(Number(stats.mapped_lsoa_count)!==geo.features.length||!Array.isArray(stats.club_catchments)||stats.club_catchments.length!==20)throw new Error('Summary/geometry mismatch or missing club summaries.');
      fc=geo;summary=stats;features=geo.features;
      centroids=features.map(f=>{f._centroid=getCentroid(f.geometry);return f;});
      status.textContent=tr('Verified · '+fmt(features.length)+' LSOAs','تم التحقق · '+fmt(features.length)+' منطقة');
      buildContent();
      window.__faeRebuild=()=>{status.textContent=tr('Verified · '+fmt(features.length)+' LSOAs','تم التحقق · '+fmt(features.length)+' منطقة');buildContent();};
      window.__faeRender=()=>{if(!canvas){buildContent();}else{drawMap();renderDetail();}};
    } catch(err) {
      status.textContent=tr('Data unavailable','البيانات غير متاحة');
      $('fae-content').innerHTML=`<div class="fae-empty fae-error"><b>${tr('The accessibility layer is not published yet.','طبقة إمكانية الوصول لم تُنشر بعد.')}</b><p>${tr('No sample values are being shown. Run the “Build Fan Accessibility & Equity” workflow after adding ORS_API_KEY, then confirm both generated files exist in data/fan-accessibility/.','لن نعرض أرقامًا تجريبية. شغّل Workflow باسم Build Fan Accessibility & Equity بعد إضافة ORS_API_KEY، ثم تأكد من وجود الملفين الناتجين داخل data/fan-accessibility/.')}</p><p class="fae-small">${esc(err.message)}</p></div>`;
      window.__faeRender=()=>{};
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load,{once:true});else load();
})();
