(function () {
  const sectionContainer = document.getElementById('account-sections');
  const queryForm = document.getElementById('query-config-form');
  const addSectionButton = document.getElementById('add-account-section');
  const queryOutput = document.getElementById('query-output');
  const importForm = document.getElementById('import-form');
  const importFeedback = document.getElementById('import-feedback');
  const alertButton = document.getElementById('run-alerts');
  const alertList = document.getElementById('alert-list');
  const alertCount = document.getElementById('alert-count');
  const downloadButton = document.getElementById('download-alerts');
  const summaryTable = document.getElementById('alert-summary-table');
  const summaryTableBody = summaryTable ? summaryTable.querySelector('tbody') : null;
  const summaryEmpty = document.getElementById('alert-summary-empty');
  const stepButtons = document.querySelectorAll('.step-button');
  const panels = document.querySelectorAll('.panel');

  let sectionIdCounter = 0;

  const SOQL_BUILDERS = {
    accounts: (ids) =>
      `SELECT Id, Name\nFROM Account\nWHERE Id IN (${formatIds(ids)})\nORDER BY Name`,
    contacts: (ids) =>
      `SELECT Id, FirstName, LastName, IndividualId, AccountId, FiscalCode__c, VATNumber__c, MobilePhone, HomePhone, Email\nFROM Contact\nWHERE Id IN (\n  SELECT ContactId FROM AccountContactRelation\n  WHERE AccountId IN (${formatIds(ids)})\n)\nORDER BY LastName, FirstName`,
    individuals: (ids) =>
      `SELECT Id, FirstName, LastName\nFROM Individual\nWHERE Id IN (\n  SELECT IndividualId FROM Contact\n  WHERE AccountId IN (${formatIds(ids)}) AND IndividualId != null\n)\nORDER BY LastName, FirstName`,
    account_contact_relations: (ids) =>
      `SELECT Id, AccountId, ContactId, Roles\nFROM AccountContactRelation\nWHERE AccountId IN (${formatIds(ids)})\nORDER BY AccountId`,
    contact_point_phones: (ids) =>
      `SELECT Id, ParentId, TelephoneNumber\nFROM ContactPointPhone\nWHERE ParentId IN (\n  SELECT IndividualId FROM Contact\n  WHERE AccountId IN (${formatIds(ids)}) AND IndividualId != null\n)\nORDER BY ParentId`,
    contact_point_emails: (ids) =>
      `SELECT Id, ParentId, EmailAddress, Type__c\nFROM ContactPointEmail\nWHERE ParentId IN (\n  SELECT IndividualId FROM Contact\n  WHERE AccountId IN (${formatIds(ids)}) AND IndividualId != null\n)\nORDER BY ParentId`,
  };

  const TITLES = {
    accounts: 'Account',
    contacts: 'Contact',
    individuals: 'Individual',
    account_contact_relations: 'AccountContactRelation',
    contact_point_phones: 'ContactPointPhone',
    contact_point_emails: 'ContactPointEmail',
  };

  function formatIds(ids) {
    return ids.map((value) => `'${value}'`).join(', ');
  }

  function createSection({ name = '', accountIds = '' } = {}) {
    sectionIdCounter += 1;
    const wrapper = document.createElement('article');
    wrapper.className = 'query-card';
    wrapper.dataset.sectionId = String(sectionIdCounter);
    wrapper.innerHTML = `
      <header>
        <div>
          <label class="inline-label">
            <span>Section title</span>
            <input type="text" name="section_name" value="${escapeHtml(name)}" placeholder="Example: Private clients" required />
          </label>
        </div>
        <button type="button" class="icon-button remove-section" aria-label="Remove section">&times;</button>
      </header>
      <label>
        <span>Account IDs</span>
        <textarea name="section_account_ids" rows="4" placeholder="001XXXXXXXXXXXX\n001YYYYYYYYYYYY">${escapeHtml(accountIds)}</textarea>
      </label>
      <p class="form-hint">Separate IDs with commas, spaces, or new lines.</p>
    `;

    wrapper.querySelector('.remove-section').addEventListener('click', () => {
      wrapper.remove();
      if (sectionContainer && sectionContainer.children.length === 0) {
        addInitialSection();
      }
    });

    sectionContainer.appendChild(wrapper);
  }

  function addInitialSection() {
    if (!sectionContainer) return;
    sectionContainer.innerHTML = '';
    createSection({ name: 'Default section' });
  }

  function escapeHtml(value) {
    return (value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function parseSections() {
    if (!sectionContainer) return [];
    return Array.from(sectionContainer.querySelectorAll('article.query-card')).map((section) => {
      const nameInput = section.querySelector('input[name="section_name"]');
      const textArea = section.querySelector('textarea[name="section_account_ids"]');
      const tokens = (textArea.value || '')
        .split(/[\s,;]+/)
        .map((token) => token.trim())
        .filter(Boolean);
      return {
        name: nameInput.value.trim() || 'Untitled section',
        accountIds: Array.from(new Set(tokens)),
      };
    });
  }

  function buildQueriesForSection(section) {
    const { accountIds } = section;
    if (!accountIds.length) {
      return [];
    }
    return Object.entries(SOQL_BUILDERS).map(([key, builder]) => ({
      key,
      title: TITLES[key] || key,
      query: builder(accountIds),
    }));
  }

  function renderQueryResults(sectionResults) {
    if (!queryOutput) return;
    if (!sectionResults.length) {
      queryOutput.innerHTML = '<p class="query-empty">Add at least one section with Account IDs to generate queries.</p>';
      return;
    }

    const markup = sectionResults
      .map(({ section, queries }) => {
        const cards = queries
          .map(
            ({ key, title, query }) => `
              <article class="query-snippet" data-entity="${key}">
                <header>
                  <h3>${escapeHtml(title)} query</h3>
                  <span class="badge">${escapeHtml(`${title}.csv`)}</span>
                </header>
                <pre><code>${escapeHtml(query)}</code></pre>
                <button type="button" class="copy-query" data-query="${escapeHtml(query)}">Copy to clipboard</button>
              </article>
            `,
          )
          .join('');
        return `
          <section class="query-card-group" aria-label="${escapeHtml(section.name)} queries">
            <header>
              <h3>${escapeHtml(section.name)}</h3>
              <p class="form-hint">${section.accountIds.length} Account IDs</p>
            </header>
            <div class="query-grid">${cards}</div>
          </section>
        `;
      })
      .join('');

    queryOutput.innerHTML = markup;
  }

  async function copyQuery(button) {
    const query = button.dataset.query;
    if (!query) return;
    const previous = button.textContent;
    if (!navigator.clipboard || typeof navigator.clipboard.writeText !== 'function') {
      button.textContent = 'Clipboard unavailable';
      setTimeout(() => {
        button.textContent = previous;
      }, 2000);
      return;
    }
    try {
      await navigator.clipboard.writeText(query);
      button.textContent = 'Copied!';
    } catch (error) {
      button.textContent = 'Copy failed';
    } finally {
      setTimeout(() => {
        button.textContent = previous;
      }, 2000);
    }
  }

  function handleQuerySubmit(event) {
    event.preventDefault();
    const sections = parseSections().filter((section) => section.accountIds.length);
    const sectionResults = sections.map((section) => ({
      section,
      queries: buildQueriesForSection(section),
    }));
    renderQueryResults(sectionResults.filter((result) => result.queries.length));
  }

  async function handleImport(event) {
    event.preventDefault();
    if (!importForm) return;
    const formData = new FormData(importForm);
    setFeedback('Uploading files...', 'pending');
    try {
      const response = await fetch('/api/import', { method: 'POST', body: formData });
      if (!response.ok) {
        throw new Error(`Import failed with status ${response.status}`);
      }
      const payload = await response.json();
      const imported = Object.entries(payload.summary || {})
        .map(([entity, count]) => `${entity.replace(/_/g, ' ')}: ${count}`)
        .join(', ');
      setFeedback(imported ? `Imported ${imported}.` : 'No files processed.', 'success');
    } catch (error) {
      setFeedback(error.message || 'Import failed.', 'error');
    }
  }

  function handleImportReset() {
    setFeedback('Selections cleared.', 'info');
  }

  function setFeedback(message, variant) {
    if (!importFeedback) return;
    importFeedback.textContent = message;
    importFeedback.dataset.variant = variant;
  }

  async function runAlerts() {
    if (!alertButton) return;
    alertButton.disabled = true;
    alertButton.textContent = 'Running...';
    try {
      const response = await fetch('/api/alerts/run', { method: 'POST' });
      if (!response.ok) {
        throw new Error(`Alert loop failed with status ${response.status}`);
      }
      const payload = await response.json();
      renderAlerts(payload.details || []);
      renderSummary(payload.summary || []);
    } catch (error) {
      renderAlerts([]);
      renderSummary([]);
      if (alertList) {
        alertList.innerHTML = `<li class="alert-item error">${escapeHtml(error.message || 'Alert loop failed.')}</li>`;
      }
    } finally {
      alertButton.disabled = false;
      alertButton.textContent = 'Run alert loop';
    }
  }

  function renderAlerts(alerts) {
    if (!alertList) return;
    if (!alerts.length) {
      alertList.innerHTML = '<li class="alert-item">No alerts generated.</li>';
    } else {
      const markup = alerts
        .map(
          (alert) => `
            <li class="alert-item">
              <h3>${escapeHtml(alert.alert_type || 'Alert')}</h3>
              <p>${escapeHtml(alert.message || '')}</p>
              <dl class="alert-meta">
                <div><dt>Account</dt><dd>${escapeHtml(alert.account_name || alert.account_id || 'Unknown')}</dd></div>
                <div><dt>Contact</dt><dd>${escapeHtml(alert.contact_name || alert.contact_id || 'N/A')}</dd></div>
                <div><dt>Triggered</dt><dd>${escapeHtml(alert.triggered_at || '')}</dd></div>
              </dl>
            </li>
          `,
        )
        .join('');
      alertList.innerHTML = markup;
    }
    if (alertCount) {
      alertCount.textContent = alerts.length ? `${alerts.length} alerts` : '';
    }
  }

  function renderSummary(rows) {
    if (!downloadButton || !summaryTable || !summaryTableBody || !summaryEmpty) return;
    if (!rows.length) {
      summaryTable.hidden = true;
      summaryEmpty.hidden = false;
      downloadButton.disabled = true;
      summaryTableBody.innerHTML = '';
      return;
    }
    const markup = rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.alert_type)}</td>
            <td>${escapeHtml(row.account_name || row.account_id || 'Unknown')}</td>
            <td>${escapeHtml(row.contact_name || row.contact_id || 'N/A')}</td>
            <td>${escapeHtml(row.details || '')}</td>
            <td>${escapeHtml(row.triggered_at)}</td>
          </tr>
        `,
      )
      .join('');
    summaryTableBody.innerHTML = markup;
    summaryTable.hidden = false;
    summaryEmpty.hidden = true;
    downloadButton.disabled = false;
  }

  async function downloadAlerts() {
    try {
      const response = await fetch('/api/alerts/download');
      if (!response.ok) {
        throw new Error('Unable to download CSV');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'alert_summary.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert(error.message || 'Download failed.');
    }
  }

  function handleStepClick(event) {
    const button = event.target.closest('.step-button');
    if (!button) return;
    const targetId = button.dataset.target;
    if (!targetId) return;

    stepButtons.forEach((step) => step.classList.toggle('active', step === button));
    panels.forEach((panel) => {
      panel.classList.toggle('active', panel.id === targetId);
    });
  }

  if (addSectionButton) {
    addSectionButton.addEventListener('click', () => createSection());
  }

  if (queryForm) {
    queryForm.addEventListener('submit', handleQuerySubmit);
  }

  if (queryOutput) {
    queryOutput.addEventListener('click', (event) => {
      const button = event.target.closest('button.copy-query');
      if (button) {
        copyQuery(button);
      }
    });
  }

  if (importForm) {
    importForm.addEventListener('submit', handleImport);
    importForm.addEventListener('reset', handleImportReset);
  }

  if (alertButton) {
    alertButton.addEventListener('click', runAlerts);
  }

  if (downloadButton) {
    downloadButton.addEventListener('click', downloadAlerts);
  }

  if (stepButtons.length) {
    document.querySelector('.steps').addEventListener('click', handleStepClick);
  }

  addInitialSection();
  renderQueryResults([]);
})();
