const viewer = document.getElementById('record-viewer');
const recordObject = document.getElementById('record-object');
const sleeve = document.getElementById('record-sleeve');
const viewerFront = document.getElementById('viewer-front');
const viewerBack = document.getElementById('viewer-back');
const rotateButton = document.getElementById('rotate-record');
const viewerTitle = document.getElementById('viewer-title');
const viewerArtist = document.getElementById('viewer-artist');
const viewerYear = document.getElementById('viewer-year');
const viewerRecordId = document.getElementById('viewer-record-id');
const ART_ENDPOINT_VERSION = '20261002-spotify-embed';
const SPOTIFY_MARK = '<svg viewBox="0 0 168 168"><path fill="#fff" d="M83.996.277C37.747.277.253 37.77.253 84.019c0 46.251 37.494 83.741 83.743 83.741 46.254 0 83.744-37.49 83.744-83.741 0-46.246-37.49-83.738-83.745-83.738l.001-.004zm38.404 120.78a5.217 5.217 0 0 1-7.18 1.73c-19.662-12.01-44.414-14.73-73.564-8.07a5.222 5.222 0 0 1-6.249-3.93 5.21 5.21 0 0 1 3.926-6.25c31.9-7.291 59.263-4.15 81.337 9.34a5.222 5.222 0 0 1 1.73 7.18zm10.25-22.805c-1.89 3.075-5.91 4.045-8.98 2.155-22.51-13.839-56.823-17.846-83.448-9.764-3.453 1.043-7.1-.903-8.148-4.35a6.538 6.538 0 0 1 4.354-8.143c30.413-9.228 68.222-4.758 94.072 11.127a6.53 6.53 0 0 1 2.15 8.975zm.88-23.744c-26.99-16.031-71.52-17.505-97.289-9.684-4.138 1.255-8.514-1.081-9.768-5.219a7.835 7.835 0 0 1 5.221-9.771c29.581-8.98 78.756-7.245 109.83 11.202a7.823 7.823 0 0 1 2.74 10.733c-2.2 3.722-7.02 4.949-10.73 2.739z"/></svg>';
const listenServicesBox = document.getElementById('listen-services');
const listenPlayerHost = document.getElementById('listen-player-host');
let openRecord = null;
const listenServices = [
  {id: 'youtube', label: 'Watch on YouTube', color: '#ff0000', fields: ['youtube_url', 'youtube'], hosts: ['youtube.com', 'youtu.be', 'm.youtube.com']},
  {id: 'spotify', label: 'Listen on Spotify', color: '#1db954', fields: ['spotify_url', 'spotify'], hosts: ['open.spotify.com', 'spotify.com']},
  {id: 'apple', label: 'Listen on Apple Music', color: '#111111', fields: ['apple_music_url', 'apple_url', 'apple'], hosts: ['music.apple.com']}
];
const listenLogos = {
  youtube: '<svg viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="12" rx="3" fill="#fff"/><path d="M10 9.2v5.6l5.4-2.8z" fill="var(--listen-color)"/></svg>',
  spotify: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="#fff" stroke-width="1.6"/><path d="M7 10c3-1.1 6.4-.6 8.8.8M7.6 13c2.3-.8 4.9-.4 6.8.8M8.2 15.7c1.6-.5 3.4-.2 4.7.5" fill="none" stroke="#fff" stroke-width="1.4" stroke-linecap="round"/></svg>',
  amazon: '<svg viewBox="0 0 24 24"><path d="M5 14.2c2.4 2.2 5.4 3.2 8 3.2 2.4 0 4.6-.8 6.4-2.3" fill="none" stroke="#fff" stroke-width="1.7" stroke-linecap="round"/><path d="M16.6 13.4l3.1 1.4-.6 2.8" fill="none" stroke="#fff" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  apple: '<svg viewBox="0 0 24 24"><path fill="#fff" d="M16.4 12.6c0-1.8 1.5-2.7 1.5-2.8-1-1.4-2.4-1.5-2.9-1.5-1.2-.2-2.4.7-3 .7s-1.6-.7-2.7-.7c-1.4 0-2.7.8-3.4 2.1-1.5 2.6-.4 6.4 1.1 8.5.7 1 1.5 2.1 2.6 2.1 1 0 1.4-.7 2.7-.7s1.6.7 2.7.7 1.8-1 2.5-2c.8-1.2 1.1-2.3 1.1-2.3s-2.2-.8-2.2-3.1zM14.7 7.3c.6-.7 1-1.7.9-2.7-1 0-2.1.6-2.8 1.4-.6.7-1.1 1.7-1 2.7 1.1.1 2.2-.6 2.9-1.4z"/></svg>',
  deezer: '<svg viewBox="0 0 24 24"><rect x="4" y="14" width="3" height="4" fill="#fff"/><rect x="8.5" y="11" width="3" height="7" fill="#fff"/><rect x="13" y="8" width="3" height="10" fill="#fff"/><rect x="17.5" y="5" width="3" height="13" fill="#fff"/></svg>',
  soundcloud: '<svg viewBox="0 0 24 24"><path fill="#fff" d="M8 15.5v-3h1.1v3zm2 0v-4h1.1v4zm2 0V10h1.1v5.5zm2 0V11h1.1v4.5zm3.2.1c1.4-.2 2.4-1.4 2.4-2.8 0-1.6-1.3-2.8-2.9-2.8-.3 0-.6 0-.9.1-.4-1.7-1.9-3-3.8-3-.4 0-.7 0-1.1.1v8.3h6.3z"/></svg>',
  tidal: '<svg viewBox="0 0 24 24"><path fill="#fff" d="M4 12l4-4 4 4-4 4zm8 0l4-4 4 4-4 4z"/></svg>',
  pandora: '<svg viewBox="0 0 24 24"><path fill="#fff" d="M8 4h6.2c3.1 0 5.1 1.9 5.1 4.7 0 2.9-2 4.8-5.2 4.8H11v6.5H8z"/></svg>',
  bandcamp: '<svg viewBox="0 0 24 24"><path fill="#fff" d="M7 17l6.5-10H17L10.5 17z"/></svg>',
  'youtube-music': '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8" fill="none" stroke="#fff" stroke-width="1.6"/><path d="M10 9.2v5.6l5-2.8z" fill="#fff"/></svg>'
};

function httpsUrl(value) {
  if (typeof value !== 'string' || !value.startsWith('https://')) return '';
  try { return new URL(value).href; } catch { return ''; }
}
function hostMatches(url, hosts) {
  const host = new URL(url).hostname.replace(/^www\./, '');
  if (host === 'music.youtube.com' || host.endsWith('.music.youtube.com')) {
    return hosts.some(item => item.replace(/^www\./, '') === 'music.youtube.com');
  }
  return hosts.some(item => {
    const expected = item.replace(/^www\./, '');
    return host === expected || host.endsWith(`.${expected}`);
  });
}
function youtubeVideoId(url) {
  const parsed = new URL(url);
  const host = parsed.hostname.replace(/^www\./, '');
  if (host === 'music.youtube.com') return '';
  if (host === 'youtu.be') return parsed.pathname.split('/').filter(Boolean)[0] || '';
  const watch = parsed.searchParams.get('v');
  if (watch) return watch;
  const parts = parsed.pathname.split('/').filter(Boolean);
  const marker = parts.findIndex(part => part === 'embed' || part === 'shorts');
  return marker >= 0 ? parts[marker + 1] || '' : '';
}
function serviceUrl(record, service) {
  const bags = [record, record.links, record.listen, record.streaming].filter(item => item && typeof item === 'object' && !Array.isArray(item));
  for (const bag of bags) {
    for (const field of service.fields) {
      const url = httpsUrl(bag[field]);
      if (url && hostMatches(url, service.hosts)) return url;
    }
  }
  const lists = [record.streams, record.links, record.listen, record.streaming].filter(Array.isArray);
  for (const list of lists) {
    for (const item of list) {
      if (!item || typeof item !== 'object') continue;
      const name = String(item.service || item.provider || item.platform || '').toLowerCase().replace(/[\s_-]+/g, '');
      const url = httpsUrl(item.url || item.href);
      if (!url || !hostMatches(url, service.hosts)) continue;
      const accepted = new Set([service.id.replace(/-/g, ''), ...service.fields.map(field => field.replace(/_url$/, '').replace(/_/g, ''))]);
      if (accepted.has(name)) return url;
    }
  }
  return '';
}
function verifiedListenLinks(record) {
  const chosen = [];
  for (const service of listenServices) {
    const url = serviceUrl(record, service);
    if (!url) continue;
    if (service.id === 'youtube' && !youtubeVideoId(url)) continue;
    chosen.push({...service, url});
    if (chosen.length === 3) break;
  }
  return chosen;
}
function clearListenPlayer() {
  listenPlayerHost.replaceChildren();
  listenPlayerHost.hidden = true;
  listenPlayerHost.classList.remove('spotify-embed', 'spotify-track');
}
function spotifyEmbed(url) {
  const parsed = new URL(url);
  let parts = parsed.pathname.split('/').filter(Boolean);
  if (parts[0] && parts[0].startsWith('intl-')) parts = parts.slice(1);
  if (parts[0] === 'embed') parts = parts.slice(1);
  if (parts.length < 2 || (parts[0] !== 'album' && parts[0] !== 'track')) return null;
  if (!/^[A-Za-z0-9]{22}$/.test(parts[1])) return null;
  return {kind: parts[0], src: `https://open.spotify.com/embed/${parts[0]}/${parts[1]}?theme=0`};
}
function renderListenLinks() {
  listenServicesBox.replaceChildren();
  clearListenPlayer();
  const links = recordObject.classList.contains('is-expanded') && openRecord ? verifiedListenLinks(openRecord) : [];
  listenServicesBox.hidden = !links.length;
  links.forEach(link => {
    const control = link.id === 'youtube' || link.id === 'spotify' ? document.createElement('button') : document.createElement('a');
    control.className = `listen-service listen-${link.id}`;
    control.style.setProperty('--listen-color', link.color);
    if (link.id === 'youtube') {
      control.type = 'button';
      control.addEventListener('click', event => {
        event.stopPropagation();
        const videoId = youtubeVideoId(link.url);
        const iframe = document.createElement('iframe');
        iframe.title = `${openRecord.title} by ${openRecord.artist} on YouTube`;
        iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?rel=0`;
        iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
        iframe.allowFullscreen = true;
        iframe.referrerPolicy = 'strict-origin-when-cross-origin';
        listenPlayerHost.classList.remove('spotify-embed', 'spotify-track');
        listenPlayerHost.replaceChildren(iframe);
        listenPlayerHost.hidden = false;
      });
    } else if (link.id === 'spotify') {
      control.type = 'button';
      control.addEventListener('click', event => {
        event.stopPropagation();
        const embed = spotifyEmbed(link.url);
        if (!embed) return;
        const iframe = document.createElement('iframe');
        iframe.title = `${openRecord.title} by ${openRecord.artist} on Spotify`;
        iframe.src = embed.src;
        iframe.allow = 'autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture';
        iframe.allowFullscreen = true;
        iframe.referrerPolicy = 'strict-origin-when-cross-origin';
        listenPlayerHost.classList.add('spotify-embed');
        listenPlayerHost.classList.toggle('spotify-track', embed.kind === 'track');
        listenPlayerHost.replaceChildren(iframe);
        listenPlayerHost.hidden = false;
      });
    } else {
      control.href = link.url;
      control.target = '_blank';
      control.rel = 'noopener noreferrer';
    }
    const logo = document.createElement('span');
    logo.className = 'listen-logo';
    logo.setAttribute('aria-hidden', 'true');
    logo.innerHTML = listenLogos[link.id];
    const text = document.createElement('span');
    text.textContent = link.label;
    control.append(logo, text);
    listenServicesBox.append(control);
  });
}

function placeholder(record) {
  const title = record.title.replace(/[&<>"']/g, '').slice(0, 32);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600"><rect width="600" height="600" fill="#110d0a"/><circle cx="300" cy="280" r="210" fill="#251a12" stroke="#956c40" stroke-width="3"/><circle cx="300" cy="280" r="52" fill="#b78a50"/><text x="300" y="548" text-anchor="middle" fill="#d5bb91" font-family="Georgia" font-size="26">${title}</text></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function markSpotifyArtwork(image, enabled) {
  image.classList.toggle('spotify-artwork', Boolean(enabled));
}
function renderArtCredit(art) {
  const source = document.getElementById('viewer-source');
  const spotify = art.provider === 'Spotify' && art.source_url;
  source.classList.toggle('spotify-credit', Boolean(spotify));
  source.replaceChildren();
  source.hidden = !art.source_url;
  source.href = art.source_url || '#';
  if (spotify) {
    const mark = document.createElement('span');
    mark.className = 'spotify-mark';
    mark.setAttribute('aria-hidden', 'true');
    mark.innerHTML = SPOTIFY_MARK;
    const label = document.createElement('span');
    label.textContent = 'Listen on Spotify';
    source.append(mark, label);
    return;
  }
  source.textContent = art.attribution || '';
}

function openViewer(record, art) {
  openRecord = record;
  viewerTitle.textContent = record.title;
  viewerArtist.textContent = record.artist;
  viewerYear.textContent = record.year ?? 'Date pending';
  viewerRecordId.textContent = record.id;
  viewerFront.src = art.front_url || placeholder(record);
  viewerFront.alt = `Cover of ${record.title} by ${record.artist}`;
  viewerBack.src = art.back_url || art.front_url || placeholder(record);
  viewerBack.alt = art.back_url ? `Back cover of ${record.title} by ${record.artist}` : viewerFront.alt;
  markSpotifyArtwork(viewerFront, art.provider === 'Spotify');
  markSpotifyArtwork(viewerBack, art.provider === 'Spotify');
  renderArtCredit(art);
  recordObject.classList.remove('is-flipped', 'is-expanded');
  renderListenLinks();
  rotateButton.hidden = !art.back_url; rotateButton.textContent = 'Show back';
  viewer.showModal();
}

rotateButton.addEventListener('click', () => {
  const flipped = recordObject.classList.toggle('is-flipped');
  rotateButton.textContent = flipped ? 'Show cover' : 'Show back';
});
sleeve.addEventListener('click', () => {
  recordObject.classList.toggle('is-expanded');
  renderListenLinks();
});
document.getElementById('close-record-viewer').addEventListener('click', () => viewer.close());
viewer.addEventListener('click', event => { if (event.target === viewer) viewer.close(); });
viewer.addEventListener('close', () => {
  openRecord = null;
  viewerRecordId.textContent = '';
  recordObject.classList.remove('is-flipped', 'is-expanded');
  renderListenLinks();
});

function leaveAtlas(event) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  const target = event.currentTarget.href;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    location.href = target;
    return;
  }
  try { sessionStorage.setItem('atlas-fade', '1'); } catch (error) {}
  document.body.classList.add('page-leaving');
  setTimeout(() => { location.href = target; }, 1100);
}
document.querySelector('.records-back').addEventListener('click', leaveAtlas);
document.querySelector('.brand').addEventListener('click', leaveAtlas);

async function start() {
  const reveal = () => document.body.classList.remove('records-entering', 'page-arriving');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) reveal();
  else requestAnimationFrame(() => requestAnimationFrame(reveal));
  const status = document.getElementById('records-status');
  const list = document.getElementById('records-list');
  const params = new URLSearchParams(location.search);
  const genreId = params.get('genre');
  const countryCode = params.get('country');
  const countryName = params.get('name');
  const back = document.querySelector('.records-back');
  if (countryCode) {
    back.href = `/?country=${encodeURIComponent(countryCode)}`;
    back.textContent = countryName ? `← Back to ${countryName}` : '← Back to country';
  }
  try {
    const recordsResponse = await fetch('/data/genre_records.json?v=20261002-popular-yt');
    if (!recordsResponse.ok) throw Error('Records data could not be loaded.');
    const records = (await recordsResponse.json()).genres?.[genreId]?.records || [];
    if (!records.length) { status.classList.remove('visually-hidden'); status.textContent = 'No saved chart records have been selected for this genre yet.'; return; }
    status.textContent = `${records.length} selected records`;
    list.classList.toggle('single-bin', records.length <= 9);
    let bucketRecords;
    records.forEach((record, index) => {
      if (index % 9 === 0) {
        const bucket = document.createElement('section');
        const rowCount = Math.ceil(Math.min(9, records.length - index) / 3);
        bucket.className = `record-bucket bucket-rows-${rowCount}`;
        bucket.setAttribute('aria-label', `Records ${index + 1}–${Math.min(index + 9, records.length)}`);
        bucketRecords = document.createElement('ol');
        bucketRecords.className = 'bucket-records';
        bucketRecords.start = index + 1;
        bucket.append(bucketRecords); list.append(bucket);
      }
      const item = document.createElement('li'); item.className = 'bucket-record';
      item.style.setProperty('--row', Math.floor((index % 9) / 3));
      item.style.setProperty('--column', index % 3);
      const button = document.createElement('button'); button.className = 'shelf-record-button'; button.type = 'button';
      const image = document.createElement('img'); image.src = placeholder(record); image.alt = ''; image.loading = 'lazy';
      const label = document.createElement('span'); label.className = 'shelf-record-label';
      const album = document.createElement('strong'); album.textContent = record.title;
      const artist = document.createElement('span'); artist.textContent = record.artist;
      const year = document.createElement('time'); year.textContent = record.year ?? 'Date pending';
      label.append(album, artist, year); button.append(image, label); item.append(button); bucketRecords.append(item);
      const artPromise = fetch(`/api/record-art?record=${encodeURIComponent(record.id)}&v=${ART_ENDPOINT_VERSION}`).then(response => response.ok ? response.json() : null).catch(() => null).then(art => {
        const resolved = art?.available ? art : {available:false, front_url:placeholder(record), back_url:null};
        if (resolved.front_url) image.src = resolved.front_url;
        markSpotifyArtwork(image, resolved.provider === 'Spotify');
        return resolved;
      });
      button.addEventListener('click', async () => openViewer(record, await artPromise));
    });
  } catch (error) { status.classList.remove('visually-hidden'); status.textContent = error.message; }
}

start();
