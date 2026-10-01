const viewer = document.getElementById('record-viewer');
const recordObject = document.getElementById('record-object');
const sleeve = document.getElementById('record-sleeve');
const viewerFront = document.getElementById('viewer-front');
const viewerBack = document.getElementById('viewer-back');
const rotateButton = document.getElementById('rotate-record');
const viewerTitle = document.getElementById('viewer-title');
const viewerArtist = document.getElementById('viewer-artist');
const viewerYear = document.getElementById('viewer-year');
const ART_ENDPOINT_VERSION = '20260930-live-discogs';

function placeholder(record) {
  const title = record.title.replace(/[&<>"']/g, '').slice(0, 32);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600"><rect width="600" height="600" fill="#110d0a"/><circle cx="300" cy="280" r="210" fill="#251a12" stroke="#956c40" stroke-width="3"/><circle cx="300" cy="280" r="52" fill="#b78a50"/><text x="300" y="548" text-anchor="middle" fill="#d5bb91" font-family="Georgia" font-size="26">${title}</text></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function openViewer(record, art) {
  viewerTitle.textContent = record.title;
  viewerArtist.textContent = record.artist;
  viewerYear.textContent = record.year ?? 'Date pending';
  viewerFront.src = art.front_url || placeholder(record);
  viewerFront.alt = `Cover of ${record.title} by ${record.artist}`;
  viewerBack.src = art.back_url || art.front_url || placeholder(record);
  viewerBack.alt = art.back_url ? `Back cover of ${record.title} by ${record.artist}` : viewerFront.alt;
  const source = document.getElementById('viewer-source');
  source.hidden = !art.source_url; source.href = art.source_url || '#'; source.textContent = art.attribution || '';
  recordObject.classList.remove('is-flipped', 'is-expanded');
  rotateButton.hidden = !art.back_url; rotateButton.textContent = 'Show back';
  viewer.showModal();
}

rotateButton.addEventListener('click', () => {
  const flipped = recordObject.classList.toggle('is-flipped');
  rotateButton.textContent = flipped ? 'Show cover' : 'Show back';
});
sleeve.addEventListener('click', () => recordObject.classList.toggle('is-expanded'));
document.getElementById('close-record-viewer').addEventListener('click', () => viewer.close());
viewer.addEventListener('click', event => { if (event.target === viewer) viewer.close(); });
viewer.addEventListener('close', () => recordObject.classList.remove('is-flipped', 'is-expanded'));

async function start() {
  requestAnimationFrame(() => document.body.classList.remove('records-entering'));
  const status = document.getElementById('records-status');
  const list = document.getElementById('records-list');
  const genreId = new URLSearchParams(location.search).get('genre');
  try {
    const recordsResponse = await fetch('/data/genre_records.json');
    if (!recordsResponse.ok) throw Error('Records data could not be loaded.');
    const records = (await recordsResponse.json()).genres?.[genreId]?.records || [];
    if (!records.length) { status.classList.remove('visually-hidden'); status.textContent = 'No saved chart records have been selected for this genre yet.'; return; }
    status.textContent = `${records.length} selected records`;
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
        if (resolved.front_url) image.src = resolved.front_url; return resolved;
      });
      button.addEventListener('click', async () => openViewer(record, await artPromise));
    });
  } catch (error) { status.classList.remove('visually-hidden'); status.textContent = error.message; }
}

start();
