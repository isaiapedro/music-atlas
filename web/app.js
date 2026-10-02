const svg = document.getElementById('map');
const mapPanel = document.querySelector('.map-panel');
const countriesLayer = document.getElementById('country-layer');
const regionsLayer = document.getElementById('region-layer');
const capitalLayer = document.getElementById('capital-layer');
const mapStage = document.querySelector('.map-stage');
const genrePanel = document.getElementById('genre-panel');
const genreScene = document.getElementById('genre-scene');
const genreMapLayer = document.getElementById('genre-map-layer');
const selectedGenreMapLayer = document.getElementById('selected-genre-map-layer');
const genreHitLayer = document.getElementById('genre-hit-layer');
const geographyLayer = document.getElementById('geography-layer');
const naturalEarthDensityLayer = document.getElementById('natural-earth-density-layer');
const naturalEarthLayer = document.getElementById('natural-earth-layer');
const baseLabelLayer = document.getElementById('base-label-layer');
const decadePoints = document.getElementById('timeline-decades');
const headerCountry = document.getElementById('header-country');
const detail = document.getElementById('detail-content');
const timeline = document.getElementById('timeline');
const periodSlider = document.getElementById('period-slider');
const periodLabel = document.getElementById('period-label');
const periodEnd = document.querySelector('.timeline-ends span:last-child');
const periodStart = document.querySelector('.timeline-ends span:first-child');
const timelineSpans = document.getElementById('timeline-spans');
const tooltip = document.getElementById('map-tooltip');
const geographyLegend = document.getElementById('geography-legend');
const overlay = document.getElementById('detail-overlay');
const closeDetail = document.getElementById('close-detail');
const imageLightbox = document.getElementById('image-lightbox');
const imageLightboxAsset = document.getElementById('image-lightbox-asset');
const imageLightboxCaption = document.getElementById('image-lightbox-caption');
const closeImageLightboxButton = document.getElementById('close-image-lightbox');
const status = document.getElementById('map-status');
const fullscreenButton = document.getElementById('fullscreen');
const NS = 'http://www.w3.org/2000/svg';
let initialView = '0 0 1000 580';
let countries = [];
let regions = [];
let capitals = [];
let genres = [];
let instrumentImages = {};
let naturalEarth = {populated_places: [], urban_areas: [], rivers_lake_centerlines: [], lakes: [], geography_regions_elevation_points: []};
let articles = {countries: {}, regions: {}, genres: {}};
let genreRecords = {genres: {}};
let selectedPath = null;
let selectedCountry = null;
let selectedGenre = null;
let geographyPinned = false;
let overviewBounds = null;
let drag = null;
let suppressClick = false;
let selectionTimer = null;
let viewFrame = 0;
const capitalCityCodes = new Set();

// ISO 3166-1 alpha-3 to alpha-2, kept here so flags work offline with the
// bundled map data (including the map's few area-specific codes).
const countryFlagCodes = {
  AFG:'AF', AGO:'AO', DZA:'DZ', ARM:'AM', AZE:'AZ', BGD:'BD', BHR:'BH', BEN:'BJ', BTN:'BT', BWA:'BW',
  BFA:'BF', BDI:'BI', KHM:'KH', CMR:'CM', CPV:'CV', CAF:'CF', TCD:'TD', CHN:'CN', COM:'KM',
  COD:'CD', COG:'CG', CIV:'CI', CYP:'CY', DJI:'DJ', EGY:'EG', GNQ:'GQ', ERI:'ER', ETH:'ET',
  SWZ:'SZ', GAB:'GA', GMB:'GM', GEO:'GE', GHA:'GH', GIN:'GN', GNB:'GW', KEN:'KE', KAS:'IN',
  PRK:'KP', KOR:'KR', KWT:'KW', KGZ:'KG', LAO:'LA', LBN:'LB', LSO:'LS', LBR:'LR', LBY:'LY',
  MDG:'MG', MWI:'MW', MYS:'MY', MLI:'ML', MRT:'MR', MAR:'MA', MOZ:'MZ', MMR:'MM', NAM:'NA',
  NPL:'NP', NER:'NE', NGA:'NG', OMN:'OM', PAK:'PK', PSX:'PS', PHL:'PH', QAT:'QA', RWA:'RW',
  SAU:'SA', SEN:'SN', SLE:'SL', SGP:'SG', SOM:'SO', SOL:'SO', ZAF:'ZA', SDS:'SS', LKA:'LK',
  SDN:'SD', SYR:'SY', TWN:'TW', TJK:'TJ', TZA:'TZ', THA:'TH', TLS:'TL', TGO:'TG', TUN:'TN',
  TUR:'TR', TKM:'TM', UGA:'UG', ARE:'AE', UZB:'UZ', VNM:'VN', YEM:'YE', ZMB:'ZM', ZWE:'ZW',
  ISR:'IL', IRQ:'IQ', IRN:'IR', IDN:'ID', IND:'IN', JPN:'JP', JOR:'JO', KAZ:'KZ', MNG:'MN',
  MYS:'MY', STP:'ST', TON:'TO', CYN:'CY', MAC:'MO', HKG:'HK', IOA:'AU', SAH:'EH', CPV:'CV',
  BRN:'BN', TON:'TO', TKM:'TM', XKX:'XK'
};
function countryFlag(code) {
  const alpha2 = countryFlagCodes[code];
  if (!alpha2) return '⚑';
  return [...alpha2].map(letter => String.fromCodePoint(0x1f1e6 + letter.charCodeAt(0) - 65)).join('');
}
function openImageLightbox(image) {
  imageLightboxAsset.src = image.currentSrc || image.src;
  imageLightboxAsset.alt = image.alt;
  imageLightboxCaption.textContent = image.alt;
  imageLightbox.showModal();
}
function appendEnlargeableFigure(parent, {src, alt, title, note, sourcePage}) {
  const figure = document.createElement('figure');
  if (title) figure.className = 'instrument-card';
  const asset = document.createElement('img');
  asset.src = src;
  asset.alt = title ? `${title}. ${note}` : alt;
  asset.loading = 'lazy';
  asset.referrerPolicy = 'no-referrer';
  asset.tabIndex = 0;
  asset.setAttribute('role', 'button');
  asset.setAttribute('aria-label', `Enlarge image: ${asset.alt}`);
  const open = () => openImageLightbox(asset);
  asset.addEventListener('click', open);
  asset.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); }
  });
  const caption = document.createElement('figcaption');
  if (title) {
    const heading = document.createElement('strong');
    heading.textContent = title;
    caption.append(heading);
  }
  const source = document.createElement('a');
  source.href = sourcePage;
  source.target = '_blank';
  source.rel = 'noopener noreferrer';
  source.textContent = 'Source';
  caption.append(`${title ? note : alt} `, source);
  figure.append(asset, caption);
  parent.append(figure);
}
function citationLabel(url) {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    if (host === 'folkways.si.edu') return 'Smithsonian Folkways';
    if (host === 'theworld.org') return 'The World';
    if (host === 'daily.bandcamp.com') return 'Bandcamp Daily';
    if (host.endsWith('wikipedia.org')) return 'Wikipedia';
    return host;
  } catch { return url; }
}
function closeImageLightbox() {
  if (imageLightbox.open) imageLightbox.close();
}
const currentYear = new Date().getFullYear();
const currentDecade = Math.floor(currentYear / 10) * 10;
// This is a display-only historical bucket; it is not a claim about 1930s
// origins. It gathers every documented period before the first decade point.
const before1940Period = 1930;
function periodDisplayLabel(period) {
  return period === before1940Period ? 'Before 1940s' : `${period}s`;
}
periodSlider.max = String(currentDecade);
periodSlider.value = String(currentDecade);
periodLabel.textContent = periodDisplayLabel(currentDecade);
periodEnd.textContent = String(currentDecade);
function selectDecade(decade, options = {}) {
  periodSlider.value = String(decade);
  periodLabel.textContent = periodDisplayLabel(decade);
  const first = Number(periodSlider.min);
  const count = Math.floor((currentDecade - first) / 10) + 1;
  periodLabel.style.left = `${(((decade - first) / 10 + .5) / count) * 100}%`;
  decadePoints.querySelectorAll('button').forEach(button => {
    const active = Number(button.dataset.decade) === decade;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  renderGenrePanel();
  if (options.refit !== false && selectedCountry) setView(...viewForCountry(selectedCountry.geometry).split(/\s+/).map(Number), Boolean(options.animate));
  renderTimelineSpans();
}
function renderDecadePoints(options = {}) {
  decadePoints.replaceChildren();
  const start = Number(periodSlider.min);
  decadePoints.style.setProperty('--timeline-edge', `${100 / (2 * (Math.floor((currentDecade - start) / 10) + 1))}%`);
  for (let decade = Math.floor(start / 10) * 10; decade <= currentDecade; decade += 10) {
    const button = document.createElement('button');
    button.type = 'button'; button.dataset.decade = String(decade);
    button.setAttribute('aria-label', periodDisplayLabel(decade));
    const dot = document.createElement('span'); dot.className = 'decade-dot'; dot.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span'); label.className = 'decade-year'; label.textContent = periodDisplayLabel(decade);
    button.append(dot, label);
    button.addEventListener('click', event => { if (suppressDecadeClick && event.detail) return; selectDecade(decade); });
    decadePoints.append(button);
  }
  selectDecade(Number(periodSlider.value), options);
}

// Equal Earth forward projection, centered at 75°E for this Africa/Asia atlas.
// Šavrič, Patterson & Jenny (2018); equations also used by PROJ.
function point([lon, lat]) {
  const radians = Math.PI / 180;
  const lambda = (lon - 75) * radians;
  const phi = lat * radians;
  const theta = Math.asin(Math.sqrt(3) * Math.sin(phi) / 2);
  const theta2 = theta * theta;
  const theta6 = theta2 * theta2 * theta2;
  const a1 = 1.340264, a2 = -0.081106, a3 = 0.000893, a4 = 0.003796;
  const denominator = a1 + 3 * a2 * theta2 + theta6 * (7 * a3 + 9 * a4 * theta2);
  const x = (2 * Math.sqrt(3) / 3) * lambda * Math.cos(theta) / denominator;
  const y = theta * (a1 + a2 * theta2 + theta6 * (a3 + a4 * theta2));
  return [x * 300, -y * 300];
}
function ringPath(ring) {
  const parts = [];
  for (let i = 0; i < ring.length; i++) {
    const start = ring[i];
    const end = ring[(i + 1) % ring.length];
    const steps = Math.max(1, Math.ceil(Math.max(Math.abs(end[0] - start[0]), Math.abs(end[1] - start[1])) / 2));
    for (let step = 0; step < steps; step++) {
      const fraction = step / steps;
      const coordinate = [start[0] + (end[0] - start[0]) * fraction, start[1] + (end[1] - start[1]) * fraction];
      parts.push(`${parts.length ? 'L' : 'M'}${point(coordinate).map(n => n.toFixed(2)).join(' ')}`);
    }
  }
  return parts.join('') + 'Z';
}
function geometryPath(geometry) {
  if (geometry.type === 'LineString' || geometry.type === 'MultiLineString') {
    const lines = geometry.type === 'LineString' ? [geometry.coordinates] : geometry.coordinates;
    return lines.map(line => line.map((coordinate, index) => `${index ? 'L' : 'M'}${point(coordinate).map(n => n.toFixed(2)).join(' ')}`).join('')).join('');
  }
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  return polygons.map(polygon => polygon.map(ringPath).join('')).join('');
}
function bounds(geometry) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  function walk(value) {
    if (typeof value[0] === 'number') { const [x, y] = point(value); minX = Math.min(x, minX); maxX = Math.max(x, maxX); minY = Math.min(y, minY); maxY = Math.max(y, maxY); }
    else value.forEach(walk);
  }
  walk(geometry.coordinates);
  return [minX, minY, maxX, maxY];
}
function coordinateBounds(geometry) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  function walk(value) {
    if (typeof value[0] === 'number') {
      const [x, y] = value;
      minX = Math.min(x, minX); maxX = Math.max(x, maxX);
      minY = Math.min(y, minY); maxY = Math.max(y, maxY);
    } else value.forEach(walk);
  }
  walk(geometry.coordinates);
  return [minX, minY, maxX, maxY];
}
function viewForBounds([minX, minY, maxX, maxY], margin) {
  const aspect = svg.clientWidth / svg.clientHeight || 1.72;
  const width = Math.max(1, (maxX - minX) * (1 + margin * 2));
  const height = Math.max(1, (maxY - minY) * (1 + margin * 2));
  const viewWidth = Math.max(width, height * aspect);
  const viewHeight = viewWidth / aspect;
  return `${(minX + maxX - viewWidth) / 2} ${(minY + maxY - viewHeight) / 2} ${viewWidth} ${viewHeight}`;
}
function viewForCountry(geometry) {
  let [minX, minY, maxX, maxY] = bounds(geometry);
  const box = sceneBounds(geometry);
  [minX, minY, maxX, maxY] = box;
  // Labels live in a reserved screen gutter and must never expand the geographic
  // bounds. Including their boxes here made small or multipart countries shrink
  // and slide away from the center of the map.
  minY -= (maxY-minY)*.025;
  const fullWidth = svg.clientWidth || 1000;
  const fullHeight = svg.clientHeight || 600;
  const mobile = fullWidth <= 800;
  const panelWidth = fullWidth <= 1000 ? 380 : Math.min(560, Math.max(390, window.innerWidth * .34));
  // Use the full country-view height now that the bottom navigation strip is gone.
  // Keep a clear left-side gutter for the fixed map navigation and label rail.
  const left = mobile ? 22 : 180;
  const top = mobile ? 102 : 122;
  const right = mobile ? fullWidth - 22 : fullWidth - panelWidth - 30;
  const bottom = mobile ? fullHeight * .52 - 45 : fullHeight - 62;
  // Preserve the established framing while making the scene exactly 20% larger.
  const units = Math.max((maxX - minX) / Math.max(60, right - left), (maxY - minY) / Math.max(60, bottom - top)) * (1.12 / 1.20);
  return `${(minX + maxX) / 2 - (left + right) / 2 * units} ${(minY + maxY) / 2 - (top + bottom) / 2 * units} ${fullWidth * units} ${fullHeight * units}`;
}
function viewBox() { return svg.getAttribute('viewBox').split(/\s+/).map(Number); }
function setView(x, y, width, height, animate = false) {
  cancelAnimationFrame(viewFrame);
  const next = [x, y, width, height];
  const apply = values => {
    svg.setAttribute('viewBox', values.join(' '));
    updateCapitalScale();
  };
  if (!animate || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    apply(next);
    return;
  }
  const start = viewBox();
  const began = performance.now();
  const duration = 800;
  const step = now => {
    const progress = Math.min(1, (now - began) / duration);
    const eased = progress < .5 ? 2 * progress * progress : 1 - ((-2 * progress + 2) ** 2) / 2;
    apply(start.map((value, index) => value + (next[index] - value) * eased));
    if (progress < 1) viewFrame = requestAnimationFrame(step);
  };
  viewFrame = requestAnimationFrame(step);
}
function updateCapitalScale() {
  const unitsPerPixel = viewBox()[2] / (svg.clientWidth || 1000);
  capitalLayer.querySelectorAll('circle').forEach(circle => {
    circle.setAttribute('r', String(Number(circle.dataset.sizeTier || 4.5) * unitsPerPixel));
  });
  naturalEarthLayer.querySelectorAll('.region-city-dot').forEach(circle => {
    circle.setAttribute('r', String(Number(circle.dataset.sizeTier || 4) * unitsPerPixel));
  });
}
function showTooltip(name, clientX, clientY) {
  const rect = svg.getBoundingClientRect();
  const stageRect = mapStage.getBoundingClientRect();
  tooltip.textContent = name;
  tooltip.hidden = false;
  tooltip.style.left = `${rect.left - stageRect.left + Math.max(8, Math.min(Math.max(8, rect.width - 180), clientX - rect.left + 14))}px`;
  tooltip.style.top = `${rect.top - stageRect.top + Math.max(8, Math.min(Math.max(8, rect.height - 44), clientY - rect.top + 14))}px`;
}
function hideTooltip() { tooltip.hidden = true; }
function showCapitals(code) {
  capitalLayer.querySelectorAll('g').forEach(marker => {
    const selected = Boolean(code) && marker.dataset.code === code;
    marker.style.display = selected ? '' : 'none';
    marker.querySelector('circle').classList.toggle('selected', selected);
  });
}
function naturalEarthLabel(kind, properties) {
  const labels = {
    populated_places: 'Urban place', urban_areas: 'Urban area', rivers_lake_centerlines: 'River or lake centerline',
    lakes: 'Lake or reservoir', geography_regions_elevation_points: 'Elevation point'
  };
  const name = properties.name;
  if (kind === 'lakes') {
    const type = properties.feature || 'Lake';
    return name ? `${name} · ${type}` : `Unnamed ${type.toLowerCase()}`;
  }
  if (kind === 'rivers_lake_centerlines') {
    const type = properties.feature === 'River (Intermittent)' ? 'Intermittent river' : 'River';
    return name ? `${name} · ${type}` : `Unnamed ${type.toLowerCase()}`;
  }
  const displayName = name || labels[kind];
  const elevation = properties.elevation_m ? ` · ${Math.round(properties.elevation_m)} m` : '';
  return `${displayName} · ${labels[kind]}${elevation}`;
}
function regionNameAtMapPoint(code, event) {
  const candidate = inverseScenePoint(mapPoint(event));
  return regions.find(region => region.properties.code === code && pointInProjectedGeometry(candidate, region.geometry))?.properties.name || null;
}
function selectRegion(name) {
  if (!geographyPinned || !name) return;
  hideTooltip();
  selectedGenre = null;
  setDetailContext('region', name);
}
function isolateWaterFeature(element = null) {
  naturalEarthLayer.classList.add('water-feature-isolated');
  naturalEarthLayer.querySelectorAll('.water-feature-hovered').forEach(item => item.classList.remove('water-feature-hovered'));
  element?.classList.add('water-feature-hovered');
}
function clearWaterFeatureIsolation() {
  naturalEarthLayer.classList.remove('water-feature-isolated');
  naturalEarthLayer.querySelectorAll('.water-feature-hovered').forEach(item => item.classList.remove('water-feature-hovered'));
}
function cityMarkerRadius(population, countryMaximum) {
  if (population === countryMaximum && population > 0) return 10;
  if (population > 10_000_000) return 8;
  if (population > 1_000_000) return 6.5;
  if (population > 100_000) return 5;
  if (population >= 50_000) return 4;
  return 3;
}
function renderRegionCities(regionName) {
  naturalEarthLayer.querySelector('.region-city-layer')?.remove();
  if (!regionName || !selectedCountry || !geographyPinned) return;
  const code = selectedCountry.properties.code;
  const region = regions.find(item => item.properties.code === code && item.properties.name === regionName);
  if (!region) return;
  const unitsPerPixel = viewBox()[2] / (svg.clientWidth || 1000);
  const countryMaximum = Math.max(0, ...naturalEarth.populated_places
    .filter(feature => feature.properties.code === code && feature.properties.reported_population)
    .map(feature => Number(feature.properties.reported_population.population || 0)));
  const layer = svgElement('g', {class:'region-city-layer','clip-path':`url(#natural-earth-${code})`,'aria-label':`Populous places in ${regionName}`});
  naturalEarth.populated_places
    .filter(feature => feature.properties.code === code
      && feature.properties.reported_population
      && !capitalCityCodes.has(feature.properties.un_city_code)
      && pointInProjectedGeometry(point(feature.geometry.coordinates), region.geometry))
    .sort((left, right) => Number(right.properties.population || 0) - Number(left.properties.population || 0))
    .forEach(feature => {
      const [cx,cy] = point(feature.geometry.coordinates);
      const population = Number(feature.properties.population || 0);
      const reported = feature.properties.reported_population;
      const label = reported
        ? `${feature.properties.name} · Population ${Number(reported.population).toLocaleString('en-US')}${reported.year ? ` (${reported.year})` : ''}`
        : feature.properties.name;
      const marker = svgElement('g',{class:'region-city-marker',tabindex:'0','aria-label':label});
      const markerPopulation = Number(reported.population || 0);
      const radius = cityMarkerRadius(markerPopulation, countryMaximum);
      const circle = svgElement('circle',{cx,cy,r:radius*unitsPerPixel,class:'region-city-dot','data-size-tier':radius});
      marker.append(circle);
      marker.addEventListener('pointermove', event => { if (!drag?.moved) showTooltip(label,event.clientX,event.clientY); isolateWaterFeature(); });
      marker.addEventListener('pointerleave',()=>{ hideTooltip(); clearWaterFeatureIsolation(); });
      marker.addEventListener('click', event => { event.stopPropagation(); selectRegion(regionName); });
      marker.addEventListener('focus',()=>{ const rect=circle.getBoundingClientRect(); showTooltip(label,rect.left+rect.width/2,rect.top+rect.height/2); });
      marker.addEventListener('blur',hideTooltip);
      layer.append(marker);
    });
  naturalEarthLayer.append(layer);
}
function elevationContours(features) {
  if (!features.length) return [];
  const [minX, minY, maxX, maxY] = bounds(selectedCountry.geometry);
  const width = maxX - minX, height = maxY - minY;
  const points = features.map(feature => ({point: point(feature.geometry.coordinates), elevation: Math.max(0, Number(feature.properties.elevation_m || 0))}));
  const maxElevation = Math.max(...points.map(item => item.elevation));
  if (!maxElevation) return [];
  const anchors = [[minX,minY],[maxX,minY],[maxX,maxY],[minX,maxY],[(minX+maxX)/2,minY],[maxX,(minY+maxY)/2],[(minX+maxX)/2,maxY],[minX,(minY+maxY)/2]].map(coordinate => ({point:coordinate,elevation:0}));
  const samples = [...points, ...anchors];
  const columns = 38, rows = Math.max(22, Math.min(54, Math.round(columns * height / Math.max(width, 1))));
  const smoothing = Math.max(width, height) * .07;
  const values = Array.from({length: rows + 1}, (_, row) => Array.from({length: columns + 1}, (_, column) => {
    const x = minX + width * column / columns, y = minY + height * row / rows;
    let weighted = 0, weights = 0;
    samples.forEach(sample => {
      const distance2 = (x-sample.point[0])**2 + (y-sample.point[1])**2 + smoothing**2;
      const weight = 1 / distance2;
      weighted += sample.elevation * weight; weights += weight;
    });
    return weighted / weights;
  }));
  const interpolate = (a, b, va, vb, level) => {
    const ratio = va === vb ? .5 : (level - va) / (vb - va);
    return [a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio];
  };
  return [.18,.34,.52,.72,.88].map((fraction, index) => {
    const level = maxElevation * fraction;
    let d = '', labelPoint = null;
    for (let row = 0; row < rows; row++) for (let column = 0; column < columns; column++) {
      const x0=minX+width*column/columns, x1=minX+width*(column+1)/columns;
      const y0=minY+height*row/rows, y1=minY+height*(row+1)/rows;
      const corners=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]];
      const cell=[values[row][column],values[row][column+1],values[row+1][column+1],values[row+1][column]];
      const crossings=[];
      [[0,1],[1,2],[2,3],[3,0]].forEach(([a,b]) => {
        if ((cell[a] < level) !== (cell[b] < level)) crossings.push(interpolate(corners[a],corners[b],cell[a],cell[b],level));
      });
      if (crossings.length === 2) d += `M${crossings[0][0].toFixed(2)} ${crossings[0][1].toFixed(2)}L${crossings[1][0].toFixed(2)} ${crossings[1][1].toFixed(2)}`;
      else if (crossings.length === 4) d += `M${crossings[0][0].toFixed(2)} ${crossings[0][1].toFixed(2)}L${crossings[1][0].toFixed(2)} ${crossings[1][1].toFixed(2)}M${crossings[2][0].toFixed(2)} ${crossings[2][1].toFixed(2)}L${crossings[3][0].toFixed(2)} ${crossings[3][1].toFixed(2)}`;
      if (!labelPoint && crossings.length) labelPoint = crossings.find(candidate => pointInProjectedGeometry(candidate, selectedCountry.geometry)) || null;
    }
    return {d, level: Math.round(level), index, labelPoint};
  }).filter(contour => contour.d);
}
function renderNaturalEarthLayers(code) {
  naturalEarthDensityLayer.replaceChildren();
  naturalEarthLayer.replaceChildren();
  naturalEarthDensityLayer.setAttribute('transform', `matrix(${sceneMatrix().join(' ')})`);
  naturalEarthLayer.setAttribute('transform', `matrix(${sceneMatrix().join(' ')})`);
  const clipId = `natural-earth-${code}`;
  svg.querySelectorAll('defs [data-natural-earth-clip]').forEach(node => node.remove());
  const clip = svgElement('clipPath', {id: clipId, 'data-natural-earth-clip': ''});
  clip.append(svgElement('path', {d: geometryPath(selectedCountry.geometry)}));
  svg.querySelector('defs').append(clip);
  const [countryMinX,,countryMaxX] = bounds(selectedCountry.geometry);
  const countrySpan = Math.max(1, countryMaxX - countryMinX);
  const places = naturalEarth.populated_places.filter(feature => feature.properties.code === code);
  const populationLayer = svgElement('g', {class:'natural-earth-population-heat', 'clip-path':`url(#${clipId})`});
  const peaks = svgElement('g', {class:'population-heat-peaks'});
  const populations = places.map(feature => Number(feature.properties.population || 0));
  const maxPopulation = Math.max(1, ...populations);
  places.forEach(feature => {
    const [cx,cy] = point(feature.geometry.coordinates);
    // Brightness is the place's percentage of the largest population center
    // in this country, so every country retains meaningful local contrast.
    const relativePopulation = Math.max(0, Number(feature.properties.population || 0)) / maxPopulation;
    const radiusStrength = Math.sqrt(relativePopulation);
    const luminosity = 30 + relativePopulation * 45;
    peaks.append(svgElement('circle', {cx,cy,r:countrySpan*(.018+radiusStrength*.065),fill:`hsl(198 20% ${luminosity.toFixed(1)}%)`,opacity:(.18+relativePopulation*.62).toFixed(2),'data-concentration-percent':(relativePopulation*100).toFixed(1)}));
  });
  populationLayer.append(peaks); naturalEarthDensityLayer.append(populationLayer);
  const elevationFeatures = naturalEarth.geography_regions_elevation_points.filter(feature => feature.properties.code === code);
  const contourLayer = svgElement('g', {class:'natural-earth-elevation-contours','clip-path':`url(#${clipId})`});
  const unitsPerPixel = viewBox()[2] / (svg.clientWidth || 1000);
  elevationContours(elevationFeatures).forEach(contour => {
    contourLayer.append(svgElement('path',{d:contour.d,class:'elevation-contour','data-elevation':contour.level,'data-level':contour.index}));
    if (contour.labelPoint) {
      const labelGroup = svgElement('g',{transform:`translate(${contour.labelPoint[0]} ${contour.labelPoint[1]}) scale(${unitsPerPixel})`,class:'elevation-label-group','data-level':contour.index});
      const label = svgElement('text',{x:0,y:0,class:'elevation-label','text-anchor':'middle','dominant-baseline':'middle'});
      label.textContent = `${contour.level} m`; labelGroup.append(label); contourLayer.append(labelGroup);
    }
  });
  for (const [kind, features] of Object.entries(naturalEarth)) {
    if (kind === 'populated_places' || kind === 'urban_areas' || kind === 'geography_regions_elevation_points') continue;
    const group = svgElement('g', {class: `natural-earth-${kind}`, 'data-kind': kind, 'clip-path': `url(#${clipId})`});
    features.filter(feature => feature.properties.code === code).forEach(feature => {
      // Lake polygons already carry the visible lake geometry and type. Natural
      // Earth's separate lake-centerline records are cartographic construction
      // lines, so do not duplicate them as ambiguous water features.
      if (kind === 'rivers_lake_centerlines' && feature.properties.feature === 'Lake Centerline') return;
      const label = naturalEarthLabel(kind, feature.properties);
      const geometry = feature.geometry;
      const element = svgElement('path', {d: geometryPath(geometry), class: 'natural-earth-shape'});
      element.dataset.kind = kind;
      element.setAttribute('aria-label', label);
      element.addEventListener('pointermove', event => {
        if (!drag?.moved) showTooltip(label, event.clientX, event.clientY);
        isolateWaterFeature(element);
      });
      element.addEventListener('pointerleave', () => { hideTooltip(); clearWaterFeatureIsolation(); });
      element.addEventListener('click', event => {
        event.stopPropagation();
        selectRegion(regionNameAtMapPoint(code, event));
      });
      group.append(element);
    });
    naturalEarthLayer.append(group);
  }
  naturalEarthLayer.append(contourLayer);
}
// This palette is deliberately high contrast on the Atlas background.  Colors are
// assigned within the country currently being explored, so visiting genres remain
// distinct from the local layers they appear beside.
const genreColors = ['#ffb638', '#00dec5', '#35b9ff', '#d98aff', '#ff729a', '#c5e86c', '#ff8754', '#a9d8ff', '#ff9fc2', '#9ae6b4', '#f8d46b', '#c4a8ff'];
const genreColorOverrides = {'nga-afrobeat': '#ffb638', 'nga-juju': '#00dec5', 'nga-fuji': '#d98aff', 'nga-highlife': '#2589ff'};
function genreArea(genre, code = selectedCountry?.properties.code) {
  if (!genre || !code) return null;
  if (genre.country === code) return genre;
  return genre.associated_areas?.find(area => area.country === code) || null;
}
function genreIsCountryWide(area) {
  return area?.map_scope === 'country';
}
function genreIsApproximate(area) {
  return area?.map_scope === 'approximate';
}
function approximateRegionLabel(area) {
  return `Approx. ${area.approximate_region.replace('-', ' ')}`;
}
function genreCoverageTokens(area) {
  if (genreIsCountryWide(area)) return ['*'];
  if (genreIsApproximate(area)) return [`approx:${area.approximate_region}`];
  return [...new Set(area?.regions || [])].map(region => `region:${region}`);
}
function genreCoverageFraction(area, regionCount) {
  if (genreIsCountryWide(area)) return 1;
  if (genreIsApproximate(area)) return area.approximate_region === 'central' ? .25
    : area.approximate_region.includes('-') ? .25 : .5;
  return Math.max(.01, genreCoverageTokens(area).length / Math.max(1, regionCount));
}
function genreCoveragesOverlap(left, right) {
  if (left.includes('*') || right.includes('*')) return true;
  const rightSet = new Set(right);
  return left.some(token => rightSet.has(token));
}
function approximateRegionGeometry(geometry, direction) {
  // Directional slices are GeoJSON and therefore must be built from geographic
  // coordinates. Using already-projected SVG bounds here caused a second
  // projection and sent some genre layers far outside their countries.
  const [x0, y0, x1, y1] = coordinateBounds(geometry);
  const xMid = (x0 + x1) / 2, yMid = (y0 + y1) / 2;
  const parts = {
    north: [x0, y0, x1, yMid], 'north-east': [xMid, y0, x1, yMid], east: [xMid, y0, x1, y1],
    'south-east': [xMid, yMid, x1, y1], south: [x0, yMid, x1, y1], 'south-west': [x0, yMid, xMid, y1],
    west: [x0, y0, xMid, y1], 'north-west': [x0, y0, xMid, yMid],
    central: [x0 + (x1 - x0) * .25, y0 + (y1 - y0) * .25, x0 + (x1 - x0) * .75, y0 + (y1 - y0) * .75],
  };
  const [left, top, right, bottom] = parts[direction];
  return {type: 'Polygon', coordinates: [[[left, top], [right, top], [right, bottom], [left, bottom], [left, top]]]};
}
function svgElement(tag, attributes = {}) {
  const node = document.createElementNS(NS, tag);
  Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, String(value)));
  return node;
}
function sceneMatrix() {
  if (!selectedCountry) return [1, 0, 0, 1, 0, 0];
  const [x0, y0, x1, y1] = bounds(selectedCountry.geometry);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  // Keep a restrained perspective cue without materially distorting the
  // country's recognizable proportions. The translation holds its center.
  return [1, -.07, .12, .86, -.12 * cy, .07 * cx + .14 * cy];
}
function scenePoint(x, y) {
  const [a,b,c,d,e,f] = sceneMatrix();
  return [a*x+c*y+e, b*x+d*y+f];
}
function inverseScenePoint([x, y]) {
  const [a,b,c,d,e,f] = sceneMatrix();
  const determinant = a*d - b*c;
  return [((x-e)*d - (y-f)*c) / determinant, ((y-f)*a - (x-e)*b) / determinant];
}
function sceneBounds(geometry) {
  const [x0,y0,x1,y1] = bounds(geometry);
  const corners = [[x0,y0],[x1,y0],[x0,y1],[x1,y1]].map(([x,y])=>scenePoint(x,y));
  return [Math.min(...corners.map(p=>p[0])),Math.min(...corners.map(p=>p[1])),Math.max(...corners.map(p=>p[0])),Math.max(...corners.map(p=>p[1]))];
}
function projectedPolygons(geometry) {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  return polygons.map(polygon => polygon.map(ring => ring.map(point)));
}
function pointInRing([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if (((yi > y) !== (yj > y)) && x < (xj - xi) * (y - yi) / ((yj - yi) || Number.EPSILON) + xi) inside = !inside;
  }
  return inside;
}
function pointInProjectedGeometry(candidate, geometry) {
  return projectedPolygons(geometry).some(polygon => pointInRing(candidate, polygon[0]) && !polygon.slice(1).some(hole => pointInRing(candidate, hole)));
}
function interiorAnchor(geometries, clipGeometry = null) {
  const ranked = geometries.map(geometry => {
    const box = bounds(geometry);
    return {geometry, box, area: Math.max(0, box[2] - box[0]) * Math.max(0, box[3] - box[1])};
  }).sort((a, b) => b.area - a.area);
  for (const {geometry, box} of ranked) {
    const [x0, y0, x1, y1] = box;
    const center = [(x0 + x1) / 2, (y0 + y1) / 2];
    const valid = candidate => pointInProjectedGeometry(candidate, geometry)
      && (!clipGeometry || pointInProjectedGeometry(candidate, clipGeometry));
    if (valid(center)) return scenePoint(...center);
    let best = null, bestDistance = Infinity;
    for (let yi = 1; yi < 20; yi++) for (let xi = 1; xi < 20; xi++) {
      const candidate = [x0 + (x1 - x0) * xi / 20, y0 + (y1 - y0) * yi / 20];
      if (!valid(candidate)) continue;
      const distance = (candidate[0] - center[0]) ** 2 + (candidate[1] - center[1]) ** 2;
      if (distance < bestDistance) { best = candidate; bestDistance = distance; }
    }
    if (best) return scenePoint(...best);
  }
  const fallback = ranked[0]?.box || sceneBounds(selectedCountry.geometry);
  return scenePoint((fallback[0] + fallback[2]) / 2, (fallback[1] + fallback[3]) / 2);
}
function restoreGenreHitOrder() {
  [...genreHitLayer.children].sort((a, b) => Number(a.dataset.order) - Number(b.dataset.order)).forEach(hit => genreHitLayer.append(hit));
}
function restoreGenreLayerOrder() {
  while (selectedGenreMapLayer.firstElementChild) genreMapLayer.append(selectedGenreMapLayer.firstElementChild);
  svg.insertBefore(genreMapLayer, selectedGenreMapLayer);
  restoreGenreHitOrder();
}
function raiseSelectedGenreLayer(id) {
  restoreGenreLayerOrder();
  const active = [...genreMapLayer.children].find(layer => layer.dataset.genre === id);
  if (!active) return;
  // The selected genre remains topmost; the geographic map becomes the layer
  // immediately beneath it, with the other genre slices below the map.
  svg.insertBefore(genreMapLayer, geographyLayer);
  selectedGenreMapLayer.append(active);
  const activeHit = [...genreHitLayer.children].find(hit => hit.dataset.genre === id);
  if (activeHit) genreHitLayer.append(activeHit);
}
function emphasizeGenre(id) {
  const isolated = Boolean(id);
  geographyLayer.classList.toggle('stack-muted', isolated && id !== 'geography');
  svg.classList.toggle('isolating-layer', isolated);
  const baseLabel = baseLabelLayer.querySelector('.base-map-label');
  baseLabel?.classList.toggle('emphasized', id === 'geography');
  baseLabel?.classList.toggle('dimmed', isolated && id !== 'geography');
  const territoryLayers = [...genreMapLayer.querySelectorAll('.genre-territory'), ...selectedGenreMapLayer.querySelectorAll('.genre-territory')];
  territoryLayers.forEach(layer => {
    const active = layer.dataset.genre === id;
    layer.classList.toggle('emphasized', active);
    layer.classList.toggle('subdued', isolated && !active);
    // Genre geometry stays registered to the base map in every interaction state.
    layer.removeAttribute('transform');
  });
  genreScene.querySelectorAll('.genre-choice').forEach(button => {
    button.classList.toggle('previewing', button.dataset.genre === id);
  });
  if (!isolated) {
    [...genreMapLayer.children].sort((a, b) => Number(a.dataset.order) - Number(b.dataset.order)).forEach(layer => genreMapLayer.append(layer));
    if (!selectedGenre) restoreGenreHitOrder();
  }
}
function renderGenreTerritory(genre, area, localRegions, index, count, stackLevel = 0) {
  const approximate = genreIsApproximate(area);
  const shapes = genreIsCountryWide(area) ? [selectedCountry] : approximate
    ? [{geometry: approximateRegionGeometry(selectedCountry.geometry, area.approximate_region), properties: {name: approximateRegionLabel(area)}}]
    : localRegions.filter(region => area.regions.includes(region.properties.name));
  const layer = svgElement('g', {class: 'genre-territory', 'data-genre': genre.id});
  const [minX, minY, maxX, maxY] = sceneBounds(selectedCountry.geometry);
  const span = maxX - minX;
  const sceneHeight = maxY - minY;
  const [, , countryViewWidth] = viewForCountry(selectedCountry.geometry).split(/\s+/).map(Number);
  const unitsPerPixel = countryViewWidth / (svg.clientWidth || 1000);
  const lift = stackLevel * 12 * unitsPerPixel;
  layer.dataset.order = index;
  layer.dataset.lift = lift;
  layer.classList.toggle('country-association', genreIsCountryWide(area));
  layer.classList.toggle('approximate-association', approximate);
  layer.style.setProperty('--genre-color', genreColor(genre));
  layer.style.setProperty('--edge-width', '3px');
  const liftedMatrix = sceneMatrix();
  liftedMatrix[5] -= lift;
  const surfaceGroup = svgElement('g', {transform: `matrix(${liftedMatrix.join(' ')})`});
  layer.append(surfaceGroup);
  const focusNames = new Set(area.focus_regions || []);
  const hit = svgElement('g', {class: 'genre-hit', 'data-genre': genre.id, tabindex: '0', role: 'button', 'aria-label': `Explore ${genre.name} map layer`});
  hit.dataset.order = index;
  const hoverThisGenre = () => {
    if (selectedGenre && selectedGenre.id !== genre.id) return;
    emphasizeGenre(genre.id);
  };
  hit.addEventListener('pointerenter', hoverThisGenre);
  hit.addEventListener('pointerleave', () => { hideTooltip(); emphasizeGenre(selectedGenre?.id); });
  hit.addEventListener('focus', hoverThisGenre);
  hit.addEventListener('blur', () => emphasizeGenre(selectedGenre?.id));
  hit.addEventListener('click', () => selectGenre(genre));
  hit.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectGenre(genre); }
  });
  const hitSurface = svgElement('g', {transform: `matrix(${liftedMatrix.join(' ')})`}); hit.append(hitSurface);
  const clipId = approximate ? `approximate-${selectedCountry.properties.code}-${genre.id}`.replace(/[^a-z0-9_-]/gi, '-') : null;
  if (clipId) {
    svg.querySelector('defs').append(svgElement('clipPath', {id: clipId, 'data-approximate-clip': ''}));
    svg.querySelector(`#${CSS.escape(clipId)}`).append(svgElement('path', {d: geometryPath(selectedCountry.geometry)}));
  }
  function paintShape(feature, surface, hits) {
    const d = geometryPath(feature.geometry);
    const clipped = clipId ? {'clip-path': `url(#${clipId})`} : {};
    const primary = focusNames.has(feature.properties.name);
    surface.append(svgElement('path', {d, class: primary ? 'territory-surface territory-flat territory-primary' : 'territory-surface territory-flat', ...clipped}));
    const target = svgElement('path', {d, ...clipped});
    const territoryLabel = genre.name;
    target.setAttribute('aria-label', territoryLabel);
    target.addEventListener('pointermove', event => {
      if (selectedGenre && selectedGenre.id !== genre.id) return;
      if (!drag?.moved) showTooltip(territoryLabel, event.clientX, event.clientY);
    });
    hits.append(target);
  }
  for (const feature of shapes) paintShape(feature, surfaceGroup, hitSurface);
  if (shapes.length) {
    // Bounding-box centers can fall in the sea, a hole, or outside a concave
    // country. Sample an actual interior point, including the country clip used
    // by directional approximate regions, before drawing the label pin.
    const [ax,baseAnchorY] = interiorAnchor(shapes.map(shape => shape.geometry), approximate ? selectedCountry.geometry : null);
    const ay = baseAnchorY - lift;
    // Labels use an independent rail, so compact map layers never overlap text.
    const labelScreenCenter = maxY - sceneHeight * (.20 + index * .19);
    const labelCenter = labelScreenCenter;
    const [viewX,,viewWidth] = viewForCountry(selectedCountry.geometry).split(/\s+/).map(Number);
    const labelUnitsPerPixel = viewWidth / (svg.clientWidth || 1000);
    const labelWidth = 230 * labelUnitsPerPixel;
    const labelHeight = 64 * labelUnitsPerPixel;
    const desiredLabelX = minX - span * .29;
    const labelX = Math.max(viewX + 12 * labelUnitsPerPixel, Math.min(desiredLabelX, viewX + viewWidth - labelWidth - 12 * labelUnitsPerPixel));
    const labelY = labelCenter - labelHeight / 2;
    const label = svgElement('g', {class:'stack-label'});
    const line = svgElement('path', {d:`M${labelX+labelWidth} ${labelCenter}H${minX-8*labelUnitsPerPixel}L${ax} ${ay}`,class:'stack-leader'});
    label.append(line,svgElement('circle',{cx:ax,cy:ay,r:4*labelUnitsPerPixel,class:'stack-pin'}),svgElement('rect',{x:labelX,y:labelY,width:labelWidth,height:labelHeight,rx:8*labelUnitsPerPixel}));
    const words = genre.name.split(/\s+/);
    const nameLines = [];
    words.forEach(word => {
      const current = nameLines.at(-1);
      if (!current || ((current + ' ' + word).length > 18 && nameLines.length < 2)) nameLines.push(word);
      else nameLines[nameLines.length - 1] += ` ${word}`;
    });
    // SVG font sizes are expressed in viewBox units. Scale a local text group by
    // units-per-screen-pixel so the global 19px type contract renders as 19px
    // instead of growing when a country is tightly zoomed.
    const textGroup=svgElement('g',{transform:`translate(${labelX} ${labelY}) scale(${labelUnitsPerPixel})`,class:'stack-label-copy'});
    const name=svgElement('text',{x:12,y:25});
    nameLines.forEach((line,rowIndex) => {
      const row=svgElement('tspan',{x:12,dy:rowIndex ? 22 : 0});
      row.textContent=line; name.append(row);
    });
    textGroup.append(name);
    label.append(textGroup);layer.append(label);
    const labeledRegions = new Set();
    for (const feature of shapes) {
      if (!focusNames.has(feature.properties.name) || labeledRegions.has(feature.properties.name)) continue;
      labeledRegions.add(feature.properties.name);
      const [regionX, regionY] = interiorAnchor([feature.geometry]);
      const regionLabel = svgElement('g', {class: 'territory-region-label', transform: `translate(${regionX} ${regionY - lift}) scale(${labelUnitsPerPixel})`});
      const regionText = svgElement('text', {'text-anchor': 'middle', y: 5});
      regionText.textContent = feature.properties.name;
      regionLabel.append(regionText);
      layer.append(regionLabel);
    }
    const labelHit=svgElement('rect',{x:labelX,y:labelY,width:labelWidth,height:labelHeight,fill:'transparent','pointer-events':'all'});hit.append(labelHit);
  }
  genreMapLayer.append(layer);
  genreHitLayer.append(hit);
}
function selectGeography() {
  selectedGenre = null;
  svg.classList.add('has-label-selection');
  restoreGenreLayerOrder();
  pinGeography();
  setDetailContext('country');
  emphasizeGenre('geography');
}
function setRegionInteraction(enabled) {
  regionsLayer.querySelectorAll('.region').forEach(path => {
    path.classList.toggle('selectable', enabled);
    path.setAttribute('tabindex', enabled ? '0' : '-1');
    path.setAttribute('aria-disabled', String(!enabled));
  });
}
function pinGeography() {
  if (!selectedCountry || geographyPinned) return;
  geographyPinned = true;
  svg.classList.add('geography-active');
  geographyLegend.hidden = false;
  geographyLayer.classList.add('pinned');
  renderNaturalEarthLayers(selectedCountry.properties.code);
  showCapitals(selectedCountry.properties.code);
  svg.append(naturalEarthDensityLayer);
  svg.append(geographyLayer);
  // Keep rivers, lakes, and elevation above the colored regions while density
  // remains below them as a demographic underlay.
  svg.append(naturalEarthLayer);
  setRegionInteraction(true);
  status.textContent = `${selectedCountry.properties.name} map raised. Select a region.`;
}
function resetGeographyLayer() {
  geographyPinned = false;
  svg.classList.remove('geography-active');
  geographyLegend.hidden = true;
  geographyLayer.classList.remove('pinned');
  clear(naturalEarthDensityLayer);
  clear(naturalEarthLayer);
  baseLabelLayer.querySelector('.base-map-label')?.classList.remove('active');
  showCapitals(null);
  svg.insertBefore(geographyLayer, baseLabelLayer);
  setRegionInteraction(false);
}
function unpinGeography() {
  if (!geographyPinned) return;
  resetGeographyLayer();
  emphasizeGenre(selectedGenre?.id);
  if (document.getElementById('detail-title')) setDetailContext('country');
  status.textContent = `${selectedCountry.properties.name} genre stack restored.`;
}
function clearMapLabelSelection() {
  if (geographyPinned) unpinGeography();
  svg.classList.remove('has-label-selection');
  if (!selectedGenre) return;
  selectedGenre = null;
  restoreGenreLayerOrder();
  genreScene.querySelectorAll('.genre-choice').forEach(button => button.setAttribute('aria-pressed', 'false'));
  emphasizeGenre(null);
  if (document.getElementById('detail-title')) setDetailContext('country');
}
function genreActiveInYear(genre, year, area = genreArea(genre)) {
  if (!area) return false;
  const localAssociation = area !== genre;
  const earliestShown = localAssociation ? area.active_from : genre.active_from;
  const latestShown = (localAssociation ? area.active_to : genre.active_to) ?? currentYear;
  // An unknown start is not a 2020s start. Keep the layer discoverable while
  // labelling its time range as unresolved; the research plan still leaves
  // unsupported historical decade cells open.
  if (earliestShown == null) return year <= latestShown;
  return earliestShown <= Math.min(year + 9, currentYear) && year <= latestShown;
}
function genreDisplayKey(name) {
  const normalized = name.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    .replace(/\s+in\s+.+$/, ' ')
    .replace(/\b(music|dance|song|songs|chant|chants|tradition|traditions|style|genre|the)\b/g, ' ');
  const tokens = normalized.match(/[a-z0-9]+/g) || [];
  return [...new Set(tokens)].join(' ');
}
function genreDisplayPriority(genre, countryCode) {
  return Number(genre.country === countryCode) * 1000
    + Number(Boolean(genre.wikipedia_title)) * 50
    + (genre.sources?.length || 0) * 10
    + Number(Boolean(genre.image)) * 5
    + (genre.youtube_examples?.length || 0)
    + (genre.artists?.length || 0);
}
function dedupeGenreEntries(entries, countryCode) {
  const chosen = new Map();
  entries.forEach(entry => {
    const key = genreDisplayKey(entry.genre.name);
    const previous = chosen.get(key);
    const score = genreDisplayPriority(entry.genre, countryCode);
    const previousScore = previous ? genreDisplayPriority(previous.genre, countryCode) : -1;
    if (!previous || score > previousScore || (score === previousScore && entry.genre.id.localeCompare(previous.genre.id) < 0)) chosen.set(key, entry);
  });
  return [...chosen.values()];
}
function sharedGenreFamily(genre) {
  const key = genreDisplayKey(genre.name);
  const linkedCountries = new Set([genre.country, ...(genre.associated_areas || []).map(area => area.country)]);
  return genres.filter(candidate => genreDisplayKey(candidate.name) === key && (
    candidate.id === genre.id
    || linkedCountries.has(candidate.country)
    || (candidate.associated_areas || []).some(area => area.country === genre.country)
  ));
}
function sharedGenreContent(genre) {
  const family = sharedGenreFamily(genre);
  if (family.length < 2) return genre;
  const ranked = [...family].sort((left, right) => {
    const score = item => Number(Boolean(articles.genres?.[item.id]?.extract)) * 10000
      + (item.note?.length || 0)
      + (item.sources?.length || 0) * 20;
    return score(right) - score(left) || left.id.localeCompare(right.id);
  });
  const descriptionRecord = ranked[0];
  const imageRecord = ranked.find(item => item.image);
  const videos = [];
  const seenVideos = new Set();
  [...family].sort((a, b) => a.id.localeCompare(b.id)).forEach(item => {
    (item.youtube_examples || []).forEach(example => {
      if (seenVideos.has(example.youtube_url)) return;
      seenVideos.add(example.youtube_url);
      videos.push(example);
    });
  });
  const artists = [...new Set([
    ...family.flatMap(item => item.artists || []),
    ...videos.map(example => example.artist),
  ])];
  return {
    ...descriptionRecord,
    image: imageRecord?.image || null,
    artists,
    youtube_examples: videos,
  };
}
function renderTimelineSpans() {
  timelineSpans.replaceChildren();
  if (!selectedCountry) return;
  const countryCode = selectedCountry.properties.code;
  const localGenres = dedupeGenreEntries(
    genres.map(genre => ({genre, area: genreArea(genre, countryCode)})).filter(entry => entry.area),
    countryCode,
  ).map(entry => entry.genre);
  if (!localGenres.length) return;
  const firstYear = Number(periodSlider.min);
  const lastYear = Number(periodSlider.max);
  const selectedYear = Number(periodSlider.value);
  localGenres.forEach((genre, index) => {
    const row = document.createElement('div'); row.className = 'timeline-span-row';
    const area = genreArea(genre);
    row.classList.toggle('active', genreActiveInYear(genre, selectedYear, area));
    const name = document.createElement('span'); name.textContent = genre.name;
    const track = document.createElement('div'); track.className = 'timeline-span-track';
    const span = document.createElement('div'); span.className = 'timeline-span-fill';
    span.style.backgroundColor = genreColor(genre);
    const localAssociation = area !== genre;
    const areaStart = localAssociation ? area.active_from : genre.active_from;
    const areaEnd = (localAssociation ? area.active_to : genre.active_to) ?? lastYear;
    const undatedStart = areaStart == null;
    const firstDecade = Math.floor(areaStart / 10) * 10;
    const finalDecade = Math.floor(areaEnd / 10) * 10;
    const timelineWidth = lastYear + 10 - firstYear;
    span.style.left = `${undatedStart ? 0 : Math.max(0, (firstDecade - firstYear) / timelineWidth) * 100}%`;
    span.style.right = `${Math.max(0, (lastYear - finalDecade) / timelineWidth) * 100}%`;
    span.classList.toggle('undated', undatedStart);
    const endStatus = localAssociation ? area.timeline_end_status : genre.timeline_end_status;
    const endLabel = areaEnd < lastYear ? areaEnd : endStatus === 'present' ? 'present' : 'last prominence unresolved';
    span.title = undatedStart
      ? `${genre.name}: start decade unresolved; full-width dashed bar is not a continuity claim`
      : `${genre.name}: ${area.start_label}–${endLabel}`;
    track.append(span); row.append(name, track); timelineSpans.append(row);
  });
}
function renderGenrePanel() {
  if (!selectedCountry) return;
  geographyLayer.setAttribute('transform', `matrix(${sceneMatrix().join(' ')})`);
  const year = Number(periodSlider.value);
  genreScene.replaceChildren();
  svg.querySelectorAll('defs [data-approximate-clip]').forEach(node => node.remove());
  restoreGenreLayerOrder();
  genreMapLayer.replaceChildren();
  genreHitLayer.replaceChildren();
  geographyLayer.classList.remove('stack-muted');
  svg.classList.remove('isolating-layer', 'has-label-selection');
  const countryCode = selectedCountry.properties.code;
  const localRegions = regions.filter(region => region.properties.code === countryCode);
  const available = dedupeGenreEntries(
    genres.map(genre => ({genre, area: genreArea(genre, countryCode)}))
      .filter(({genre, area}) => area && genreActiveInYear(genre, year, area)),
    countryCode,
  )
    .map(entry => ({...entry, coverage: genreCoverageTokens(entry.area), coverageSize: genreCoverageFraction(entry.area, localRegions.length), stackLevel: 0}))
    .sort((a, b) => b.coverageSize - a.coverageSize || a.genre.name.localeCompare(b.genre.name));
  available.forEach(entry => { entry.stackLevel = 0; });
  if (selectedGenre && !available.some(({genre}) => genre.id === selectedGenre.id)) {
    selectedGenre = null;
    if (document.getElementById('detail-title')) setDetailContext('country');
  }
  if (!available.length) {
    const message = document.createElement('p'); message.className = 'genre-gap';
    message.textContent = 'No reviewed genre layers for this place and year yet.';
    genreScene.append(message);
    return;
  }
  available.forEach(({genre, area, stackLevel}, index) => {
    renderGenreTerritory(genre, area, localRegions, index, available.length, stackLevel);
  });
  if (selectedGenre) raiseSelectedGenreLayer(selectedGenre.id);
  emphasizeGenre(selectedGenre?.id);
}
function genreColor(genre, countryCode = selectedCountry?.properties.code) {
  const localGenres = countryCode
    ? genres.filter(item => genreArea(item, countryCode))
    : genres.filter(item => item.country === genre.country);
  const overrides = localGenres.map(item => genreColorOverrides[item.id]).filter(Boolean);
  const claimedOverride = genreColorOverrides[genre.id];
  // Overrides preserve the signature Nigerian colors, provided another layer in
  // the same view has not already claimed that swatch.
  if (claimedOverride && overrides.indexOf(claimedOverride) === overrides.lastIndexOf(claimedOverride)) return claimedOverride;
  const reserved = new Set(overrides);
  const palette = genreColors.filter(color => !reserved.has(color));
  const unassigned = localGenres.filter(item => !genreColorOverrides[item.id] || overrides.indexOf(genreColorOverrides[item.id]) !== overrides.lastIndexOf(genreColorOverrides[item.id]));
  const index = unassigned.findIndex(item => item.id === genre.id);
  return palette[index] || `hsl(${(index * 137.508 + 17) % 360} 72% 56%)`;
}
function highlightGenreRegions(genre) {
  emphasizeGenre(genre?.id);
  overlay.style.setProperty('--selected-genre-color', genre ? genreColor(genre) : '#ddb26c');
}
function selectGenre(genre) {
  if (geographyPinned) resetGeographyLayer();
  selectedGenre = genre;
  svg.classList.add('has-label-selection');
  raiseSelectedGenreLayer(genre.id);
  genreScene.querySelectorAll('.genre-choice').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.genre === genre.id)));
  setDetailContext('genre', genre);
}
function showArticle(kind, value) {
  const code = selectedCountry.properties.code;
  const article = kind === 'genre' ? articles.genres?.[value.id]
    : kind === 'region' ? articles.regions?.[code + '|' + value]
    : articles.countries?.[code];
  const body = document.getElementById('wiki-body');
  const source = document.getElementById('wiki-source');
  const facts = document.getElementById('geo-facts');
  if (!body || !source || !facts) return;
  source.replaceChildren();
  facts.replaceChildren();
  facts.hidden = true;
  const preferLocalNote = kind === 'genre' && value?.prefer_local_note && value.note;
  const usedExtract = !preferLocalNote && Boolean(article?.english_extract || article?.extract);
  body.textContent = preferLocalNote ? value.note : article?.english_extract || article?.extract || (kind === 'genre' && value.note) || 'A saved description is not available for this selection yet.';
  const citations = document.getElementById('text-citations');
  if (citations) {
    citations.replaceChildren();
    citations.hidden = true;
    if (code !== 'AFG') {
      const items = [];
      const shown = body.textContent;
      if (usedExtract && article?.url) items.push({url: article.url, label: article.title || 'Wikipedia'});
      if (kind === 'genre' && Array.isArray(value.sources)) {
        value.sources.forEach(item => {
          const url = typeof item === 'string' ? item : item?.url;
          if (!url || items.some(existing => existing.url === url)) return;
          const label = citationLabel(url);
          if (shown.includes(label)) items.push({url, label});
        });
      }
      if (items.length) {
        const heading = document.createElement('p');
        heading.className = 'cited-from';
        heading.textContent = 'Cited from';
        citations.append(heading);
        items.forEach(item => {
          const line = document.createElement('p');
          if (item.url) {
            const link = document.createElement('a');
            link.href = item.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = item.label;
            line.append(link);
          } else line.textContent = item.label;
          citations.append(line);
        });
      }
      citations.hidden = !items.length;
    }
  }
  if (kind !== 'genre') {
    if (kind === 'country' && article.population?.value) {
      const item = document.createElement('p');
      item.textContent = 'Population: ' + Math.round(article.population.value).toLocaleString('en-US') + (article.population.year ? ' (' + article.population.year + ')' : '');
      facts.append(item);
    }
    if (article.area_km2) {
      const item = document.createElement('p');
      item.textContent = 'Area: ' + article.area_km2.toLocaleString('en-US', {maximumFractionDigits: 2}) + ' km²';
      facts.append(item);
    }
    facts.hidden = !facts.childElementCount;
  }
  const links = !preferLocalNote && article?.url ? [{url: article.url, label: 'Read full wikipedia article'}] : [];
  const sourceUrl = item => typeof item === 'string' ? item : item?.url;
  const referenceCandidates = [];
  if (kind === 'genre' && Array.isArray(value.sources)) referenceCandidates.push(...value.sources);
  const area = kind === 'genre' ? genreArea(value, code) : null;
  if (area && area !== value && Array.isArray(area.sources)) referenceCandidates.push(...area.sources);
  if (kind !== 'genre' && article?.wikidata_url) referenceCandidates.push(article.wikidata_url);
  const referenceUrl = referenceCandidates.map(sourceUrl).find(Boolean);
  if (referenceUrl) links.push({url: referenceUrl, label: preferLocalNote || code === 'AFG' ? 'Read full article' : 'Reference'});
  if (links.length) {
    const list = document.createElement('div'); list.className = 'reference-links';
    links.forEach(item => {
      const reference = document.createElement(item.url ? 'a' : 'span');
      if (item.url) { reference.href = item.url; reference.target = '_blank'; reference.rel = 'noopener noreferrer'; }
      reference.textContent = item.label;
      list.append(reference);
    });
    source.append(list);
  }
}
function setDetailContext(kind, value) {
  if (!selectedCountry) return;
  const contentValue = kind === 'genre' ? sharedGenreContent(value) : value;
  const regionSelected = kind === 'region';
  svg.classList.toggle('has-region-selection', regionSelected);
  regionsLayer.querySelectorAll('.region').forEach(path => {
    path.classList.toggle('selected-region', regionSelected && path.dataset.name === value);
  });
  renderRegionCities(regionSelected ? value : null);
  const countryName = selectedCountry.properties.name;
  const context = document.getElementById('detail-context');
  context.hidden = kind !== 'country';
  context.textContent = selectedCountry.properties.continent.toUpperCase();
  const countryPrefix = `${countryFlag(selectedCountry.properties.code)} ${countryName}`;
  document.getElementById('detail-title').textContent = kind === 'region' ? `${countryPrefix} · ${value}` : kind === 'genre' ? `${countryPrefix} · ${value.name}` : countryPrefix;
  const meta = document.getElementById('detail-meta');
  meta.replaceChildren();
  meta.hidden = true;
  const artists = document.getElementById('genre-artists');
  const player = document.getElementById('genre-player');
  const image = document.getElementById('genre-image');
  const records = document.getElementById('genre-records');
  artists.replaceChildren();
  player.replaceChildren();
  image.replaceChildren();
  records.replaceChildren();
  artists.hidden = kind !== 'genre' || !contentValue?.instruments?.length;
  player.hidden = kind !== 'genre' || !contentValue?.youtube_examples?.length;
  image.hidden = kind !== 'genre' || !contentValue?.image;
  const recordCount = genreRecords.genres?.[value?.id]?.records?.length || 0;
  records.hidden = kind !== 'genre' || !recordCount;
  highlightGenreRegions(kind === 'genre' ? value : null);
  document.querySelector('.detail-scroll').scrollTop = 0;
  if (kind === 'genre') {
    if (contentValue.image) {
      appendEnlargeableFigure(image, {
        src: contentValue.image.image_url,
        alt: contentValue.image.depicts,
        sourcePage: contentValue.image.source_page_url
      });
    }
    if (contentValue.instruments?.length) {
      const instrumentsHeading = document.createElement('h3'); instrumentsHeading.textContent = 'Instruments';
      const instrumentList = document.createElement('div'); instrumentList.className = 'instrument-list';
      contentValue.instruments.forEach(name => {
        const photo = instrumentImages[name];
        if (photo) {
          appendEnlargeableFigure(instrumentList, {
            src: photo.image_url,
            title: name,
            note: photo.note,
            sourcePage: photo.source_page_url
          });
        } else {
          const card = document.createElement('figure'); card.className = 'instrument-card';
          const caption = document.createElement('figcaption'); caption.textContent = name;
          card.append(caption); instrumentList.append(card);
        }
      });
      artists.append(instrumentsHeading, instrumentList);
    }
    if (contentValue.youtube_examples?.length) {
      const sampleHeading = document.createElement('h3'); sampleHeading.textContent = 'Watch examples';
      player.append(sampleHeading);
      contentValue.youtube_examples.forEach(example => {
        const card = document.createElement('div'); card.className = 'sample-track';
        const row = document.createElement('div'); row.className = 'sample-track-row';
        const play = document.createElement('button'); play.type = 'button'; play.textContent = '▶';
        play.setAttribute('aria-label', `Load YouTube player for ${example.title} by ${example.artist}`);
        const label = document.createElement('div'); label.className = 'sample-track-label';
        const artist = document.createElement('strong'); artist.textContent = example.artist;
        const title = document.createElement('span'); title.textContent = example.title;
        label.append(artist, title);
        const recording = document.createElement('a'); recording.href = example.youtube_url;
        recording.target = '_blank'; recording.rel = 'noopener noreferrer';
        recording.textContent = '↗'; recording.setAttribute('aria-label', `Open ${example.title} on YouTube`);
        row.append(play, label, recording);
        play.addEventListener('click', () => {
          const iframe = document.createElement('iframe');
          iframe.title = `${example.title} by ${example.artist} on YouTube`;
          const videoId = new URL(example.youtube_url).searchParams.get('v');
          iframe.src = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`;
          iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
          iframe.allowFullscreen = true; iframe.loading = 'lazy';
          iframe.referrerPolicy = 'strict-origin-when-cross-origin';
          card.append(iframe); play.remove();
        }, {once: true});
        card.append(row); player.append(card);
      });
    }
    if (recordCount) {
      const link = document.createElement('a');
      link.className = 'genre-records-link';
      const countryCode = selectedCountry.properties.code;
      const countryName = selectedCountry.properties.name;
      link.href = `/records.html?genre=${encodeURIComponent(value.id)}&country=${encodeURIComponent(countryCode)}&name=${encodeURIComponent(countryName)}`;
      link.textContent = 'Listening Room';
      link.addEventListener('click', event => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        const target = link.href;
        if (matchMedia('(prefers-reduced-motion: reduce)').matches) { location.href = target; return; }
        document.body.classList.add('page-leaving');
        setTimeout(() => { location.href = target; }, 1100);
      });
      records.append(link);
    }
    showArticle('genre', contentValue);
  } else if (kind === 'region') {
    showArticle('region', value);
  } else {
    showArticle('country');
  }
}
function zoom(factor, anchor) {
  const [x, y, width, height] = viewBox();
  const overviewWidth = Number(initialView.split(/\s+/)[2]);
  // Country view is an inspection mode: allow roughly 25x the fitted country
  // framing so urban polygons, waterways and elevation points can be examined.
  // Overview remains bounded to avoid losing the continental map.
  const countryWidth = selectedCountry ? Number(viewForCountry(selectedCountry.geometry).split(/\s+/)[2]) : overviewWidth;
  const maxWidth = selectedCountry ? countryWidth * 1.2 : overviewWidth * 2;
  const minWidth = selectedCountry ? countryWidth / 32 : overviewWidth / 24;
  const nextWidth = Math.min(maxWidth, Math.max(minWidth, width * factor));
  const ratio = nextWidth / width;
  const center = anchor || [x + width / 2, y + height / 2];
  setView(center[0] - (center[0] - x) * ratio, center[1] - (center[1] - y) * ratio, nextWidth, height * ratio);
}
function mapPoint(event) {
  const point = svg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  const result = point.matrixTransform(svg.getScreenCTM().inverse());
  return [result.x, result.y];
}
function clear(node) { node.replaceChildren(); }
function reset() {
  clearTimeout(selectionTimer);
  timeline.hidden = true;
  genrePanel.hidden = true;
  mapStage.classList.remove('has-genre-panel');
  genreScene.replaceChildren();
  restoreGenreLayerOrder();
  genreMapLayer.replaceChildren();
  selectedGenreMapLayer.replaceChildren();
  genreHitLayer.replaceChildren();
  svg.querySelectorAll('defs [data-approximate-clip]').forEach(node => node.remove());
  resetGeographyLayer();
  geographyLayer.classList.remove('stack-muted');
  svg.classList.remove('isolating-layer');
  timelineSpans.replaceChildren();
  selectedGenre = null;
  svg.classList.remove('has-region-selection');
  hideTooltip();
  if (overviewBounds) initialView = viewForBounds(overviewBounds, .04);
  setView(...initialView.split(/\s+/).map(Number), true);
  clear(regionsLayer);
  clear(naturalEarthDensityLayer);
  clear(naturalEarthLayer);
  clear(baseLabelLayer);
  showCapitals(null);
  countriesLayer.querySelectorAll('path').forEach(path => {
    path.classList.remove('selected', 'dim', 'genre-origin');
    path.style.removeProperty('--genre-color');
    path.setAttribute('tabindex', '0');
    path.removeAttribute('aria-disabled');
  });
  overlay.hidden = true;
  detail.replaceChildren();
  status.textContent = 'Showing Africa and Asia.';
  document.querySelector('.brand').focus({preventScroll:true});
  selectedPath = null;
  selectedCountry = null;
  geographyLayer.removeAttribute('transform');
  naturalEarthDensityLayer.removeAttribute('transform');
  naturalEarthLayer.removeAttribute('transform');
  mapPanel.classList.remove('country-view');
  headerCountry.hidden = true;
  headerCountry.textContent = '';
}
function choose(feature) {
  const {code, name, continent} = feature.properties;
  selectedCountry = feature;
  headerCountry.textContent = `/ ${name}`;
  headerCountry.hidden = false;
  selectedGenre = null;
  mapPanel.classList.add('country-view');
  periodSlider.min = String(before1940Period);
  periodSlider.value = String(currentDecade);
  periodStart.textContent = periodDisplayLabel(Number(periodSlider.min));
  renderDecadePoints({refit: false});
  selectedPath = countriesLayer.querySelector(`[data-code="${code}"]`);
  genrePanel.hidden = false;
  mapStage.classList.add('has-genre-panel');
  timeline.hidden = false;
  showCapitals(null);
  countriesLayer.querySelectorAll('path').forEach(path => { path.classList.toggle('selected', path.dataset.code === code); path.classList.toggle('dim', path.dataset.code !== code); path.setAttribute('tabindex', '-1'); path.setAttribute('aria-disabled', 'true'); });
  clear(regionsLayer);
  hideTooltip();
  const localRegions = regions.filter(region => region.properties.code === code);
  for (const region of localRegions) {
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', geometryPath(region.geometry)); path.setAttribute('class', 'region'); path.setAttribute('tabindex', '-1');
    path.setAttribute('aria-disabled', 'true');
    path.dataset.name = region.properties.name;
    path.setAttribute('aria-label', `${region.properties.name} region; open Wikipedia overview`);
    // The custom map tooltip is the sole hover label. A native SVG <title>
    // here would appear after a delay and duplicate it when the pointer rests.
    regionsLayer.append(path);
    path.addEventListener('pointermove', event => { if (geographyPinned && !drag?.moved) showTooltip(region.properties.name, event.clientX, event.clientY); });
    path.addEventListener('pointerleave', hideTooltip);
    path.addEventListener('focus', () => { const rect = path.getBoundingClientRect(); showTooltip(region.properties.name, rect.left + rect.width / 2, rect.top + rect.height / 2); });
    path.addEventListener('blur', hideTooltip);
    path.addEventListener('click', event => { if (!geographyPinned) return; event.stopPropagation(); hideTooltip(); selectedGenre = null; setDetailContext('region', region.properties.name); });
    path.addEventListener('keydown', event => { if (geographyPinned && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); event.stopPropagation(); selectedGenre = null; setDetailContext('region', region.properties.name); } });
  }
  const [sceneMinX, sceneMinY, sceneMaxX, sceneMaxY] = sceneBounds(feature.geometry);
  const sceneWidth = sceneMaxX - sceneMinX;
  const sceneHeight = sceneMaxY - sceneMinY;
  // Continue the label rail at the same 19%-of-scene-height interval used by
  // every genre label above it.
  const labelCenter = sceneMaxY - sceneHeight * .01;
  const [countryViewX,,countryViewWidth] = viewForCountry(feature.geometry).split(/\s+/).map(Number);
  const baseUnitsPerPixel = countryViewWidth / (svg.clientWidth || 1000);
  const baseLabelWidth = 230 * baseUnitsPerPixel;
  const baseName = `Explore ${name}`;
  const baseNameLines = [];
  baseName.split(/\s+/).forEach(word => {
    const current = baseNameLines.at(-1);
    if (!current || (current + ' ' + word).length > 18) baseNameLines.push(word);
    else baseNameLines[baseNameLines.length - 1] += ` ${word}`;
  });
  const baseLabelHeightPixels = Math.max(64, 48 + (baseNameLines.length - 1) * 22);
  const baseLabelHeight = baseLabelHeightPixels * baseUnitsPerPixel;
  const desiredLabelX = sceneMinX - sceneWidth * .29;
  const labelX = Math.max(countryViewX + 12 * baseUnitsPerPixel, Math.min(desiredLabelX, countryViewX + countryViewWidth - baseLabelWidth - 12 * baseUnitsPerPixel));
  // Use a verified point inside the actual country geometry. A bounding-box
  // coordinate can fall in the sea or beyond a concave/multipart country.
  const [anchorX, anchorY] = interiorAnchor([feature.geometry]);
  const baseLabel = svgElement('g', {class: 'stack-label base-map-label'});
  baseLabel.style.setProperty('--genre-color', '#9bb7c4');
  baseLabel.setAttribute('tabindex', '0');
  baseLabel.setAttribute('role', 'button');
  baseLabel.setAttribute('aria-label', `Explore ${name} base map and select a region`);
  const baseTextGroup = svgElement('g', {transform: `translate(${labelX} ${labelCenter - baseLabelHeight / 2}) scale(${baseUnitsPerPixel})`, class: 'stack-label-copy'});
  const baseText = svgElement('text', {x: 12, y: 25});
  baseNameLines.forEach((line, rowIndex) => {
    const row = svgElement('tspan', {x: 12, dy: rowIndex ? 22 : 0});
    row.textContent = line;
    baseText.append(row);
  });
  baseTextGroup.append(baseText);
  baseLabel.append(
    svgElement('path', {d: `M${labelX + baseLabelWidth} ${labelCenter}H${sceneMinX - 8 * baseUnitsPerPixel}L${anchorX} ${anchorY}`, class: 'stack-leader'}),
    svgElement('circle', {cx: anchorX, cy: anchorY, r: 4 * baseUnitsPerPixel, class: 'stack-pin'}),
    svgElement('rect', {x: labelX, y: labelCenter - baseLabelHeight / 2, width: baseLabelWidth, height: baseLabelHeight, rx: 8 * baseUnitsPerPixel}),
    baseTextGroup
  );
  const activateBaseMap = event => {
    event?.preventDefault();
    event?.stopPropagation();
    selectGeography();
  };
  baseLabel.addEventListener('click', activateBaseMap);
  baseLabel.addEventListener('pointerenter', () => emphasizeGenre('geography'));
  baseLabel.addEventListener('pointerleave', () => emphasizeGenre(geographyPinned ? 'geography' : selectedGenre?.id));
  baseLabel.addEventListener('focus', () => emphasizeGenre('geography'));
  baseLabel.addEventListener('blur', () => emphasizeGenre(geographyPinned ? 'geography' : selectedGenre?.id));
  baseLabel.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') activateBaseMap(event);
  });
  baseLabelLayer.replaceChildren(baseLabel);
  setView(...viewForCountry(feature.geometry).split(/\s+/).map(Number), true);
  detail.replaceChildren(closeDetail);
  const scroll = document.createElement('div'); scroll.className = 'detail-scroll'; detail.append(scroll);
  const label = document.createElement('p'); label.id = 'detail-context'; label.className = 'eyebrow'; label.textContent = continent.toUpperCase();
  const title = document.createElement('h2'); title.id = 'detail-title'; title.textContent = `${countryFlag(code)} ${name}`;
  const meta = document.createElement('div'); meta.id = 'detail-meta'; meta.className = 'detail-meta'; meta.hidden = true;
  const facts = document.createElement('div'); facts.id = 'geo-facts'; facts.className = 'geo-facts'; facts.hidden = true;
  const body = document.createElement('p'); body.id = 'wiki-body'; body.className = 'wiki-body';
  const citations = document.createElement('div'); citations.id = 'text-citations'; citations.className = 'text-citations'; citations.hidden = true;
  const source = document.createElement('div'); source.id = 'wiki-source'; source.className = 'wiki-source';
  const image = document.createElement('section'); image.id = 'genre-image'; image.className = 'genre-image'; image.hidden = true;
  const artists = document.createElement('section'); artists.id = 'genre-artists'; artists.className = 'genre-artists'; artists.hidden = true;
  const player = document.createElement('section'); player.id = 'genre-player'; player.className = 'genre-player'; player.hidden = true;
  const records = document.createElement('section'); records.id = 'genre-records'; records.className = 'genre-records'; records.hidden = true;
  scroll.append(label, title, meta, facts, image, body, citations, artists, player);
  detail.append(records, source);
  overlay.hidden = false;
  closeDetail.focus();
  renderGenrePanel();
  setDetailContext('country');
  status.textContent = `${name} selected, ${localRegions.length} mapped regions.`;
}
async function start() {
  try {
    const dataVersion = '20261002-145936';
    const [countryResponse, regionResponse, capitalResponse, genreResponse, articleResponse, placesResponse, urbanResponse, riversResponse, lakesResponse, elevationResponse, populationOverrideResponse, recordResponse, instrumentResponse] = await Promise.all([fetch(`/data/countries.geojson?v=${dataVersion}`), fetch(`/data/regions.geojson?v=${dataVersion}`), fetch(`/data/capitals.json?v=${dataVersion}`), fetch(`/data/genres.json?v=${dataVersion}`), fetch(`/data/articles.json?v=${dataVersion}`), fetch(`/data/populated_places.geojson?v=${dataVersion}`), fetch(`/data/urban_areas.geojson?v=${dataVersion}`), fetch(`/data/rivers_lake_centerlines.geojson?v=${dataVersion}`), fetch(`/data/lakes.geojson?v=${dataVersion}`), fetch(`/data/geography_regions_elevation_points.geojson?v=${dataVersion}`), fetch(`/data/place_population_overrides.json?v=${dataVersion}`), fetch(`/data/genre_records.json?v=${dataVersion}`), fetch(`/data/instrument_images.json?v=${dataVersion}`)]);
    if ([countryResponse, regionResponse, capitalResponse, genreResponse, articleResponse, placesResponse, urbanResponse, riversResponse, lakesResponse, elevationResponse, populationOverrideResponse, recordResponse, instrumentResponse].some(response => !response.ok)) throw Error('Map assets could not be loaded.');
    countries = (await countryResponse.json()).features;
    regions = (await regionResponse.json()).features;
    capitals = await capitalResponse.json();
    genres = (await genreResponse.json()).genres;
    articles = await articleResponse.json();
    genreRecords = await recordResponse.json();
    instrumentImages = (await instrumentResponse.json()).instruments;
    const populationOverrides = await populationOverrideResponse.json();
    const populatedPlaces = (await placesResponse.json()).features;
    populatedPlaces.forEach(feature => {
      const override = populationOverrides[feature.properties.population_key || `${feature.properties.code}|${feature.properties.name}`];
      if (override && override.year) feature.properties.reported_population = override;
    });
    naturalEarth = {
      populated_places: populatedPlaces,
      urban_areas: (await urbanResponse.json()).features,
      rivers_lake_centerlines: (await riversResponse.json()).features,
      lakes: (await lakesResponse.json()).features,
      geography_regions_elevation_points: (await elevationResponse.json()).features
    };
    overviewBounds = countries.map(feature => bounds(feature.geometry)).reduce((all, box) => [Math.min(all[0], box[0]), Math.min(all[1], box[1]), Math.max(all[2], box[2]), Math.max(all[3], box[3])], [Infinity, Infinity, -Infinity, -Infinity]);
    initialView = viewForBounds(overviewBounds, .04);
    setView(...initialView.split(/\s+/).map(Number));
    for (const feature of countries) {
      const path = document.createElementNS(NS, 'path');
      path.setAttribute('d', geometryPath(feature.geometry)); path.setAttribute('class', 'country');
      path.setAttribute('tabindex', '0'); path.setAttribute('role', 'button');
      path.setAttribute('aria-label', `Explore ${feature.properties.name}`); path.dataset.code = feature.properties.code;
      path.addEventListener('pointermove', event => { if (!selectedCountry && !drag?.moved) showTooltip(feature.properties.name, event.clientX, event.clientY); });
      path.addEventListener('pointerleave', hideTooltip);
      path.addEventListener('focus', () => { if (!selectedCountry) { const rect = path.getBoundingClientRect(); showTooltip(feature.properties.name, rect.left + rect.width / 2, rect.top + rect.height / 2); } });
      path.addEventListener('blur', hideTooltip);
      path.addEventListener('click', event => {
        if (selectedCountry) return;
        clearTimeout(selectionTimer);
        if (event.detail > 1) return;
        selectionTimer = setTimeout(() => choose(feature), 450);
      });
      path.addEventListener('keydown', event => { if (!selectedCountry && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); choose(feature); } });
      countriesLayer.append(path);
    }
    for (const capital of capitals) {
      const [x, y] = point(capital.coordinates);
      const marker = document.createElementNS(NS, 'g'); marker.dataset.code = capital.code; marker.setAttribute('tabindex', '0');
      const circle = document.createElementNS(NS, 'circle'); circle.setAttribute('cx', String(x)); circle.setAttribute('cy', String(y)); circle.setAttribute('class', 'capital-dot');
      const countryCities = naturalEarth.populated_places.filter(feature => feature.properties.code === capital.code);
      const maximum = Math.max(0, ...countryCities.map(feature => Number(feature.properties.reported_population?.population || 0)));
      const namedCapital = countryCities.find(feature => feature.properties.name.toLocaleLowerCase() === capital.name.toLocaleLowerCase());
      const capitalCity = namedCapital || countryCities
        .filter(feature => feature.properties.feature === 'Admin-0 capital')
        .sort((left, right) => {
          const [leftX,leftY] = left.geometry.coordinates, [rightX,rightY] = right.geometry.coordinates;
          return (leftX-capital.coordinates[0])**2+(leftY-capital.coordinates[1])**2
            - ((rightX-capital.coordinates[0])**2+(rightY-capital.coordinates[1])**2);
        })[0];
      if (capitalCity) capitalCityCodes.add(capitalCity.properties.un_city_code);
      const capitalPopulation = Number(capitalCity?.properties.reported_population?.population || 0);
      const capitalYear = capitalCity?.properties.reported_population?.year;
      const capitalLabel = capitalPopulation
        ? `${capital.name} · Population ${capitalPopulation.toLocaleString('en-US')}${capitalYear ? ` (${capitalYear})` : ''}`
        : capital.name;
      marker.setAttribute('aria-label', capitalLabel);
      circle.dataset.sizeTier = String(cityMarkerRadius(capitalPopulation, maximum));
      marker.append(circle);
      marker.addEventListener('pointermove', event => { showTooltip(capitalLabel, event.clientX, event.clientY); isolateWaterFeature(); });
      marker.addEventListener('pointerleave', () => { hideTooltip(); clearWaterFeatureIsolation(); });
      marker.addEventListener('focus', () => { const rect = circle.getBoundingClientRect(); showTooltip(capitalLabel, rect.left + rect.width / 2, rect.top + rect.height / 2); });
      marker.addEventListener('blur', hideTooltip);
      capitalLayer.append(marker);
    }
    updateCapitalScale();
    showCapitals(null);
    status.textContent = `${countries.length} countries loaded. Select a country.`;
    const requestedCountry = new URLSearchParams(location.search).get('country');
    const requestedFeature = requestedCountry && countries.find(feature => feature.properties.code === requestedCountry);
    if (requestedFeature) choose(requestedFeature);
  } catch (error) { status.textContent = error.message; }
}
geographyLayer.addEventListener('click', event => {
  if (!selectedCountry || drag?.moved) return;
  event.stopPropagation();
  if (!geographyPinned) selectGeography();
});
svg.addEventListener('click', event => {
  const keptSelection = event.target.closest?.('.genre-hit,.base-map-label,#geography-layer');
  if (!keptSelection) clearMapLabelSelection();
});
closeDetail.addEventListener('click', reset);
overlay.addEventListener('click', event => { if (event.target === overlay) reset(); });
closeImageLightboxButton.addEventListener('click', closeImageLightbox);
imageLightbox.addEventListener('click', event => { if (event.target === imageLightbox) closeImageLightbox(); });
imageLightbox.addEventListener('close', () => {
  imageLightboxAsset.removeAttribute('src');
  imageLightboxAsset.alt = '';
  imageLightboxCaption.textContent = '';
});
periodSlider.addEventListener('input', () => {
  selectDecade(Number(periodSlider.value));
});
let draggingDecade = false;
let decadePointerStart = 0;
let suppressDecadeClick = false;
function selectDecadeAt(clientX) {
  const buttons = [...decadePoints.querySelectorAll('button')];
  if (!buttons.length) return;
  const nearest = buttons.reduce((best, button) => {
    const rect = button.getBoundingClientRect();
    const distance = Math.abs(clientX - rect.left - rect.width / 2);
    return distance < best.distance ? {button, distance} : best;
  }, {button: buttons[0], distance: Infinity}).button;
  selectDecade(Number(nearest.dataset.decade));
}
decadePoints.addEventListener('pointerdown', event => {
  if (event.button !== 0) return;
  draggingDecade = true;
  decadePointerStart = event.clientX;
  decadePoints.setPointerCapture(event.pointerId);
  selectDecadeAt(event.clientX);
});
decadePoints.addEventListener('pointermove', event => { if (draggingDecade) selectDecadeAt(event.clientX); });
decadePoints.addEventListener('pointerup', event => {
  if (Math.abs(event.clientX - decadePointerStart) > 5) {
    suppressDecadeClick = true;
    setTimeout(() => { suppressDecadeClick = false; }, 0);
  }
  draggingDecade = false;
});
decadePoints.addEventListener('pointercancel', () => { draggingDecade = false; });
document.getElementById('zoom-in').addEventListener('click', () => zoom(.75));
document.getElementById('zoom-out').addEventListener('click', () => zoom(1 / .75));
svg.addEventListener('wheel', event => {
  // Ctrl + wheel is normally claimed by the browser for page zoom.  While the
  // pointer is on the map, retain that familiar gesture for geographic zoom.
  if (!event.ctrlKey) return;
  event.preventDefault();
  hideTooltip();
  const direction = event.deltaY < 0 ? .86 : 1 / .86;
  zoom(direction, mapPoint(event));
}, {passive: false});
svg.addEventListener('pointerdown', event => {
  if (event.button !== 0 || drag) return;
  clearTimeout(selectionTimer);
  suppressClick = false;
  drag = { id: event.pointerId, x: event.clientX, y: event.clientY, view: viewBox(), inverse: svg.getScreenCTM().inverse(), moved: false };
});
svg.addEventListener('pointermove', event => {
  if (!drag || event.pointerId !== drag.id) return;
  const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
  if (!drag.moved && Math.hypot(dx, dy) < 5) return;
  if (!drag.moved) { drag.moved = true; hideTooltip(); svg.setPointerCapture(event.pointerId); svg.classList.add('dragging'); }
  const { a, b, c, d } = drag.inverse;
  setView(drag.view[0] - a * dx - c * dy, drag.view[1] - b * dx - d * dy, drag.view[2], drag.view[3]);
  event.preventDefault();
});
function endDrag(event) {
  if (!drag || event.pointerId !== drag.id) return;
  if (drag.moved) {
    suppressClick = true;
    setTimeout(() => { suppressClick = false; }, 100);
    if (svg.hasPointerCapture(event.pointerId)) svg.releasePointerCapture(event.pointerId);
  }
  svg.classList.remove('dragging');
  drag = null;
}
svg.addEventListener('pointerup', endDrag);
svg.addEventListener('pointercancel', endDrag);
window.addEventListener('pointerup', endDrag);
window.addEventListener('pointercancel', endDrag);
svg.addEventListener('click', event => {
  if (!suppressClick) return;
  event.preventDefault();
  event.stopPropagation();
  suppressClick = false;
}, true);
svg.addEventListener('dblclick', event => {
  event.preventDefault();
  clearTimeout(selectionTimer);
  zoom(.5, mapPoint(event));
});
fullscreenButton.addEventListener('click', async () => {
  try {
    if (document.fullscreenElement === mapPanel) await document.exitFullscreen();
    else await mapPanel.requestFullscreen();
  } catch { status.textContent = 'Fullscreen is unavailable in this browser.'; }
});
document.addEventListener('fullscreenchange', () => {
  const active = document.fullscreenElement === mapPanel;
  fullscreenButton.setAttribute('aria-label', active ? 'Exit fullscreen' : 'Enter fullscreen');
  fullscreenButton.title = active ? 'Exit fullscreen' : 'Enter fullscreen';
  requestAnimationFrame(() => {
    if (selectedCountry) {
      setView(...viewForCountry(selectedCountry.geometry).split(/\s+/).map(Number));
    } else if (overviewBounds) {
      initialView = viewForBounds(overviewBounds, .04);
      setView(...initialView.split(/\s+/).map(Number));
    }
  });
});
new ResizeObserver(() => {
  if (!overviewBounds) return;
  if (selectedCountry) setView(...viewForCountry(selectedCountry.geometry).split(/\s+/).map(Number));
  else {
    initialView = viewForBounds(overviewBounds, .04);
    setView(...initialView.split(/\s+/).map(Number));
  }
}).observe(svg);
document.addEventListener('keydown', event => {
  if (imageLightbox.open) return;
  if (!overlay.hidden && event.key === 'Escape') { reset(); return; }
  if (!selectedCountry || timeline.hidden || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
  if (event.target.closest?.('a,button,input,select,textarea,[contenteditable="true"]')) return;
  const direction = event.key === 'ArrowRight' ? 10 : -10;
  const nextDecade = Math.max(Number(periodSlider.min), Math.min(Number(periodSlider.max), Number(periodSlider.value) + direction));
  if (nextDecade === Number(periodSlider.value)) return;
  event.preventDefault();
  selectDecade(nextDecade);
});
start();
