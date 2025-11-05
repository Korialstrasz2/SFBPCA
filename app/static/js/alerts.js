const AlertsModule = (() => {
  const alertList = document.getElementById('alert-list');
  const alertCount = document.getElementById('alert-count');
  const refreshButton = document.getElementById('refresh-alerts');
  const summaryTable = document.getElementById('alert-summary-table');
  const summaryBody = document.getElementById('alert-summary-body');
  const summaryEmpty = document.getElementById('alert-summary-empty');
  const downloadButton = document.getElementById('download-alerts-csv');
  const tabButtons = Array.from(document.querySelectorAll('[data-alert-tab]'));

  let currentAlerts = [];

  const setActiveTab = (tabName) => {
    tabButtons.forEach((button) => {
      const isActive = button.dataset.alertTab === tabName;
      button.classList.toggle('active', isActive);
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
      const panelId = button.getAttribute('aria-controls');
      if (!panelId) return;
      const panel = document.getElementById(panelId);
      if (!panel) return;
      if (isActive) {
        panel.removeAttribute('hidden');
      } else {
        panel.setAttribute('hidden', '');
      }
    });
  };

  const initializeTabs = () => {
    tabButtons.forEach((button) => {
      button.addEventListener('click', () => {
        setActiveTab(button.dataset.alertTab);
      });
    });
    if (tabButtons.length) {
      setActiveTab(tabButtons[0].dataset.alertTab);
    }
  };

  const renderEmptySummary = () => {
    if (summaryBody) {
      summaryBody.innerHTML = '';
    }
    if (summaryTable) {
      summaryTable.hidden = true;
    }
    if (summaryEmpty) {
      summaryEmpty.hidden = false;
    }
    if (downloadButton) {
      downloadButton.disabled = true;
    }
  };

  const renderEmptyState = () => {
    if (alertList) {
      alertList.innerHTML = '';
      const item = document.createElement('li');
      item.textContent = 'No alerts generated yet. Import data to begin the review.';
      alertList.appendChild(item);
    }
    if (alertCount) {
      alertCount.textContent = '0 alerts';
    }
    renderEmptySummary();
  };

  const createObjectDetails = (objects) => {
    if (!objects || typeof objects !== 'object') {
      return null;
    }
    const keys = Object.keys(objects).sort((a, b) => a.localeCompare(b));
    if (!keys.length) {
      return null;
    }
    const details = document.createElement('details');
    details.className = 'alert-objects';
    const summary = document.createElement('summary');
    summary.textContent = 'Object IDs';
    details.appendChild(summary);

    const list = document.createElement('ul');
    list.className = 'alert-objects-list';
    keys.forEach((key) => {
      const values = Array.isArray(objects[key]) ? objects[key] : [objects[key]];
      if (!values.length) {
        return;
      }
      const filteredValues = values.filter((value) => value !== undefined && value !== null && value !== '');
      if (!filteredValues.length) {
        return;
      }
      const item = document.createElement('li');
      const term = document.createElement('span');
      term.className = 'alert-objects-term';
      term.textContent = key;
      const value = document.createElement('span');
      value.textContent = filteredValues.join(', ');
      item.appendChild(term);
      item.appendChild(value);
      list.appendChild(item);
    });

    if (!list.childElementCount) {
      return null;
    }

    details.appendChild(list);
    return details;
  };

  const renderDetails = (alerts) => {
    if (!alertList) return;
    const fragment = document.createDocumentFragment();
    alerts.forEach((alert) => {
      const item = document.createElement('li');

      const type = document.createElement('div');
      type.className = 'alert-type';
      type.textContent = alert.type || 'Alert';
      item.appendChild(type);

      const message = document.createElement('p');
      message.className = 'alert-message';
      message.textContent = alert.message || '';
      item.appendChild(message);

      const details = createObjectDetails(alert.objects);
      if (details) {
        item.appendChild(details);
      }

      fragment.appendChild(item);
    });

    alertList.innerHTML = '';
    alertList.appendChild(fragment);
  };

  const renderSummary = (alerts) => {
    if (!summaryBody || !summaryTable || !summaryEmpty) {
      return;
    }

    if (!alerts.length) {
      renderEmptySummary();
      return;
    }

    const grouped = new Map();
    alerts.forEach((alert) => {
      const key = alert.definition_id || alert.type || 'Alert';
      if (!grouped.has(key)) {
        grouped.set(key, {
          type: alert.type || 'Alert',
          description: alert.description || '',
          count: 0,
        });
      }
      const entry = grouped.get(key);
      entry.count += 1;
    });

    summaryBody.innerHTML = '';
    grouped.forEach((entry) => {
      const row = document.createElement('tr');
      const typeCell = document.createElement('th');
      typeCell.scope = 'row';
      typeCell.textContent = entry.type;
      const descriptionCell = document.createElement('td');
      descriptionCell.textContent = entry.description;
      const countCell = document.createElement('td');
      countCell.textContent = String(entry.count);
      row.appendChild(typeCell);
      row.appendChild(descriptionCell);
      row.appendChild(countCell);
      summaryBody.appendChild(row);
    });

    summaryTable.hidden = false;
    summaryEmpty.hidden = true;
    if (downloadButton) {
      downloadButton.disabled = false;
    }
  };

  const updateCount = (alerts) => {
    if (!alertCount) return;
    const label = alerts.length === 1 ? 'alert' : 'alerts';
    alertCount.textContent = `${alerts.length} ${label}`;
  };

  const collectObjectKeys = (alerts) => {
    const keys = new Set();
    alerts.forEach((alert) => {
      if (alert.objects && typeof alert.objects === 'object') {
        Object.keys(alert.objects).forEach((key) => keys.add(key));
      }
    });
    return Array.from(keys).sort((a, b) => a.localeCompare(b));
  };

  const escapeCsvValue = (value) => {
    const needsEscaping = /[",\n]/.test(value);
    if (!needsEscaping) {
      return value;
    }
    return `"${value.replace(/"/g, '""')}"`;
  };

  const buildCsv = (alerts) => {
    if (!alerts.length) {
      return '';
    }
    const objectKeys = collectObjectKeys(alerts);
    const header = ['number', 'alert type name', 'alert description', 'summary', ...objectKeys];
    const rows = [header.join(',')];
    alerts.forEach((alert, index) => {
      const base = [
        String(index + 1),
        alert.type || 'Alert',
        alert.description || '',
        alert.summary || alert.message || '',
      ];
      const values = objectKeys.map((key) => {
        const entries = alert.objects && alert.objects[key];
        if (!entries || (Array.isArray(entries) && !entries.length)) {
          return 'NA';
        }
        if (Array.isArray(entries)) {
          return entries.length ? entries.join(' | ') : 'NA';
        }
        return String(entries);
      });
      const row = [...base, ...values].map((value) => escapeCsvValue(String(value)));
      rows.push(row.join(','));
    });
    return rows.join('\n');
  };

  const downloadCsv = () => {
    if (!currentAlerts.length) {
      return;
    }
    const csv = buildCsv(currentAlerts);
    if (!csv) {
      return;
    }
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'alerts-summary.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const renderAlerts = (alerts) => {
    currentAlerts = Array.isArray(alerts) ? alerts : [];
    if (!currentAlerts.length) {
      renderEmptyState();
      return;
    }
    renderDetails(currentAlerts);
    renderSummary(currentAlerts);
    updateCount(currentAlerts);
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
      currentAlerts = [];
      if (alertList) {
        alertList.innerHTML = '';
        const item = document.createElement('li');
        item.className = 'error';
        item.textContent = error.message;
        alertList.appendChild(item);
      }
      if (alertCount) {
        alertCount.textContent = '';
      }
      renderEmptySummary();
    }
  };

  if (refreshButton) {
    refreshButton.addEventListener('click', (event) => {
      event.preventDefault();
      fetchAlerts();
    });
  }

  if (downloadButton) {
    downloadButton.addEventListener('click', downloadCsv);
  }

  document.addEventListener('alerts:refresh', fetchAlerts);

  initializeTabs();
  renderEmptyState();

  return {
    fetchAlerts,
  };
})();

window.AlertsModule = AlertsModule;
