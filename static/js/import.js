(function () {
  const form = document.getElementById('import-form');
  const status = document.getElementById('import-status');

  if (!form) {
    return;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    status.classList.remove('error');
    status.textContent = 'Uploading files…';

    const formData = new FormData(form);

    try {
      const response = await fetch('/api/import', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Import failed.');
      }

      const parts = Object.entries(data.counts || {})
        .map(([key, value]) => `${value} ${key.replace(/_/g, ' ')}`)
        .join(', ');

      status.textContent = `Import complete. ${parts}`;
    } catch (error) {
      status.classList.add('error');
      status.textContent = `Import error: ${error.message}`;
    }
  });
})();
