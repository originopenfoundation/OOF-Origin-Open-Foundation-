'use strict';

const button = document.getElementById('run');
const statusLine = document.getElementById('status');
const results = document.getElementById('results');

button.addEventListener('click', async () => {
  button.disabled = true;
  statusLine.textContent = 'Running sample tests…';
  results.textContent = '';
  try {
    const response = await fetch('/_lara/engine-demo', {signal: AbortSignal.timeout(15000)});
    if (response.status === 404) {
      statusLine.textContent = 'Public engine testing is disabled.';
      return;
    }
    const payload = await response.json();
    if (payload.cases) results.textContent = JSON.stringify(payload.cases, null, 2);
    statusLine.textContent = response.ok ? 'All three sample requests completed.' :
      response.status === 429 ? 'Rate limit reached. Try again in a minute.' : 'Sample tests failed.';
  } catch {
    statusLine.textContent = 'The server could not complete the request. Try again.';
  } finally {
    button.disabled = false;
  }
});
