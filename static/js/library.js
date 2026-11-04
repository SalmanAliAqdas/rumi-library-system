document.getElementById('display-toggle')?.addEventListener('click', () => {
  const url = new URL(location.href);
  if (url.searchParams.get('display') === '1') url.searchParams.delete('display');
  else url.searchParams.set('display', '1');
  location.assign(url);
});
const fullscreen = document.getElementById('fullscreen');
if (fullscreen && document.fullscreenEnabled && document.body.classList.contains('display-mode')) {
  fullscreen.hidden = false;
  fullscreen.addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch { fullscreen.hidden = true; }
  });
}
document.querySelectorAll('.book-art img').forEach(img => {
  const ready = () => { if (img.naturalWidth) img.parentElement.classList.add('has-cover'); };
  img.addEventListener('load', ready);
  img.addEventListener('error', () => img.remove());
  if (img.complete) ready();
});

document.getElementById('print-labels')?.addEventListener('click', () => window.print());

document.querySelectorAll('[data-suggestion]').forEach(button => {
  button.addEventListener('click', () => {
    document.getElementById('metadata-suggestion').value = button.dataset.suggestion;
    // Only selected fields in the chosen result are submitted.
    document.querySelectorAll('[name=approve], [name=replace_confirm]').forEach(input => {
      input.disabled = !button.closest('fieldset').contains(input);
    });
  });
});
