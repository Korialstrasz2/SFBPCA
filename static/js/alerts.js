(function () {
  const form = document.getElementById('alerts-form');
  const runButton = document.getElementById('run-alerts');
  const results = document.getElementById('alerts-results');

  if (!form || !runButton || !results) {
    return;
  }

  const renderResults = (alerts) => {
    if (!alerts || alerts.length === 0) {
      results.innerHTML = '<p class="empty-state">No alerts were selected.</p>';
      return;
    }

    const fragments = alerts.map((alert) => {
      const wrapper = document.createElement('section');
      wrapper.className = 'alert-result';

      const heading = document.createElement('h3');
      heading.textContent = alert.description;
      wrapper.appendChild(heading);

      if (!alert.matches || alert.matches.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-state';
        empty.textContent = 'No matches found.';
        wrapper.appendChild(empty);
        return wrapper;
      }

      const list = document.createElement('ul');
      alert.matches.forEach((match) => {
        const item = document.createElement('li');
        const pre = document.createElement('pre');
        pre.textContent = JSON.stringify(match, null, 2);
        item.appendChild(pre);
        list.appendChild(item);
      });

      wrapper.appendChild(list);
      return wrapper;
    });

    results.innerHTML = '';
    fragments.forEach((node) => results.appendChild(node));
  };

  runButton.addEventListener('click', async () => {
    const selectedAlerts = Array.from(
      form.querySelectorAll('input[name="alerts"]:checked'),
    ).map((input) => input.value);

    results.classList.remove('error');
    results.textContent = 'Evaluating alerts…';

    try {
      const response = await fetch('/api/alerts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ alerts: selectedAlerts }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to evaluate alerts.');
      }

      renderResults(data.alerts || []);
    } catch (error) {
      results.classList.add('error');
      results.textContent = `Alert evaluation error: ${error.message}`;
    }
  });
})();
