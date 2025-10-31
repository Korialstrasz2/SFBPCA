const AlertsModule = (() => {
  const alertList = document.getElementById('alert-list');
  const alertCount = document.getElementById('alert-count');
  const refreshButton = document.getElementById('refresh-alerts');

  const renderEmptyState = () => {
    if (!alertList) return;
    alertList.innerHTML = '<li>No alerts generated yet. Import data to begin the review.</li>';
    if (alertCount) {
      alertCount.textContent = '0 alerts';
    }
  };

  const renderAlerts = (alerts) => {
    if (!alertList) return;
    if (!alerts || alerts.length === 0) {
      renderEmptyState();
      return;
    }

    const fragment = document.createDocumentFragment();
    alerts.forEach((alert) => {
      const item = document.createElement('li');

      const type = document.createElement('div');
      type.className = 'alert-type';
      type.textContent = alert.type || 'Alert';

      const message = document.createElement('div');
      message.className = 'alert-message';
      message.textContent = alert.message || '';

      const meta = document.createElement('div');
      meta.className = 'alert-meta';
      const ruleName = alert.name || alert.logic_id || 'Custom alert';
      const logicId = alert.logic_id ? ` (${alert.logic_id})` : '';
      meta.textContent = `Rule: ${ruleName}${logicId}`;

      item.appendChild(type);
      item.appendChild(message);
      item.appendChild(meta);

      if (alert.context && Object.keys(alert.context).length > 0) {
        const details = document.createElement('details');
        details.className = 'alert-context';
        const summary = document.createElement('summary');
        summary.textContent = 'View data context';
        const contextPre = document.createElement('pre');
        contextPre.textContent = JSON.stringify(alert.context, null, 2);
        details.appendChild(summary);
        details.appendChild(contextPre);
        item.appendChild(details);
      }

      fragment.appendChild(item);
    });

    alertList.innerHTML = '';
    alertList.appendChild(fragment);

    if (alertCount) {
      const label = alerts.length === 1 ? 'alert' : 'alerts';
      alertCount.textContent = `${alerts.length} ${label}`;
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await fetch('/alerts');
      if (!response.ok) {
        throw new Error('Failed to load alerts');
      }
      const payload = await response.json();
      renderAlerts(payload.alerts || []);
    } catch (error) {
      if (alertList) {
        alertList.innerHTML = `<li class="error">${error.message}</li>`;
      }
      if (alertCount) {
        alertCount.textContent = '';
      }
    }
  };

  if (refreshButton) {
    refreshButton.addEventListener('click', (event) => {
      event.preventDefault();
      fetchAlerts();
    });
  }

  document.addEventListener('alerts:refresh', fetchAlerts);
  renderEmptyState();

  return {
    fetchAlerts,
  };
})();

window.AlertsModule = AlertsModule;
