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
  const filterAccount = document.getElementById('filter-account');
  const filterAlertType = document.getElementById('filter-alert-type');
  const filterContactRole = document.getElementById('filter-contact-role');
  const summaryTabsContainer = document.querySelector('.alert-summary-tabs');
  const summaryTabs = document.querySelectorAll('.summary-tab');
  const summaryTabPanels = document.querySelectorAll('.summary-tab-panel');
  const summaryStatsContent = document.getElementById('summary-stats-content');
  const summaryStatsEmpty = document.getElementById('summary-stats-empty');
  const summaryStatsPerTypeBody = document.getElementById('summary-stats-per-type');
  const summaryStatsTopAccountsBody = document.getElementById('summary-stats-top-accounts');
  const statElements = {
    totalAlerts: document.getElementById('stat-total-alerts'),
    totalAccounts: document.getElementById('stat-total-accounts'),
    accountsWithAlerts: document.getElementById('stat-accounts-with-alerts'),
    uniqueContacts: document.getElementById('stat-unique-contacts'),
    uniqueAlertTypes: document.getElementById('stat-unique-alert-types'),
    alertsWithoutContact: document.getElementById('stat-alerts-without-contact'),
    averageAlerts: document.getElementById('stat-average-alerts'),
  };
  const stepButtons = document.querySelectorAll('.step-button');
  const panels = document.querySelectorAll('.panel');
  const bulkFileInput = document.getElementById('bulk-file-input');
  const bulkSelectButton = document.getElementById('select-all-files');
  const bulkModal = document.getElementById('bulk-mapping-modal');
  const bulkModalList = document.getElementById('bulk-mapping-list');
  const bulkModalClose = document.getElementById('bulk-modal-close');

  let sectionIdCounter = 0;
  let currentSummaryRows = [];
  let lastFocusedElement = null;

  const integerFormatter = new Intl.NumberFormat('it-IT');
  const averageFormatter = new Intl.NumberFormat('it-IT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  if (bulkModal) {
    bulkModal.setAttribute('aria-hidden', 'true');
  }

  const SOQL_BUILDERS = {
    accounts: (ids) =>
      `SELECT Id, Name\nFROM Account\nWHERE Id IN (${formatIds(ids)})\nORDER BY Name`,
    contacts: (ids) =>
      `SELECT Id, FirstName, LastName, IndividualId, AccountId, FiscalCode__c, VATNumber__c, MobilePhone, Phone, Email,Company__c\nFROM Contact\nWHERE Id IN (\n  SELECT ContactId FROM AccountContactRelation\n  WHERE AccountId IN (${formatIds(ids)})\n)\nORDER BY LastName, FirstName`,
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

  const SUPPORTED_ENTITIES = [
    'accounts',
    'contacts',
    'individuals',
    'account_contact_relations',
    'contact_point_phones',
    'contact_point_emails',
  ];

  const ENTITY_LABELS = {
    accounts: 'Account',
    contacts: 'Contatti',
    individuals: 'Individual',
    account_contact_relations: 'Relazioni Account-Contact',
    contact_point_phones: 'Contact Point Phone',
    contact_point_emails: 'Contact Point Email',
  };

  const EXPECTED_COLUMNS = {
    accounts: ['Id', 'Name'],
    contacts: [
      'Id',
      'FirstName',
      'LastName',
      'IndividualId',
      'FiscalCode__c',
      'VATNumber__c',
      'MobilePhone',
      'Phone',
      'Email',
      'Company__c'
    ],
    individuals: ['Id', 'FirstName', 'LastName'],
    account_contact_relations: ['Id', 'AccountId', 'ContactId', 'Roles'],
    contact_point_phones: ['Id', 'ParentId', 'TelephoneNumber'],
    contact_point_emails: ['Id', 'ParentId', 'EmailAddress', 'Type__c'],
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
            <span>Titolo sezione</span>
            <input type="text" name="section_name" value="${escapeHtml(name)}" placeholder="Esempio: Clienti privati" required />
          </label>
        </div>
        <button type="button" class="icon-button remove-section" aria-label="Rimuovi sezione">&times;</button>
      </header>
      <label>
        <span>ID Account</span>
        <textarea name="section_account_ids" rows="4" placeholder="001XXXXXXXXXXXX\n001YYYYYYYYYYYY">${escapeHtml(accountIds)}</textarea>
      </label>
      <p class="form-hint">Separa gli ID con virgole, spazi o nuove righe.</p>
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
    createSection({ name: 'Sezione predefinita' });
  }

  function escapeHtml(value) {
    return (value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function normaliseHeaderValue(value) {
    return (value || '')
      .replace(/^\ufeff/, '')
      .replace(/^"|"$/g, '')
      .trim();
  }

  function extractCsvHeaderColumns(text) {
    if (!text) {
      throw new Error('File vuoto.');
    }
    const match = text.match(/^(.*?)(?:\r?\n|$)/);
    const headerLine = match ? match[1] : '';
    if (!headerLine) {
      throw new Error('Intestazione non trovata nel file CSV.');
    }
    return headerLine
      .split(',')
      .map(normaliseHeaderValue)
      .filter(Boolean);
  }

  async function readCsvColumns(file) {
    const source = typeof file.slice === 'function' ? file.slice(0, 4096) : file;
    const text = typeof source.text === 'function' ? await source.text() : await file.text();
    return extractCsvHeaderColumns(text);
  }

  function getMatchingEntities(columns) {
    return SUPPORTED_ENTITIES.filter((entity) => {
      const expected = EXPECTED_COLUMNS[entity] || [];
      return expected.every((column) => columns.includes(column));
    });
  }

  async function classifyFiles(files) {
    const matched = [];
    const unmatched = [];
    const usedEntities = new Set();

    for (const file of files) {
      try {
        const columns = await readCsvColumns(file);
        const matches = getMatchingEntities(columns);
        if (!matches.length) {
          unmatched.push({ file, reason: 'Intestazioni non riconosciute.' });
          continue;
        }
        const available = matches.find((entity) => !usedEntities.has(entity));
        if (available) {
          usedEntities.add(available);
          matched.push({ entity: available, file });
        } else {
          const label = ENTITY_LABELS[matches[0]] || matches[0];
          unmatched.push({ file, reason: `File duplicato per ${label}.` });
        }
      } catch (error) {
        unmatched.push({ file, reason: error.message || 'File non leggibile.' });
      }
    }

    return { matched, unmatched };
  }

  function assignFileToInput(entity, file) {
    if (!importForm) return;
    const input = importForm.querySelector(`input[name="${entity}"]`);
    if (!input) return;
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    input.files = dataTransfer.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function applyBulkAssignments(result) {
    result.matched.forEach(({ entity, file }) => {
      assignFileToInput(entity, file);
    });
  }

  function buildModalListMarkup(result) {
    const items = [];

    result.matched.forEach(({ entity, file }) => {
      const label = ENTITY_LABELS[entity] || entity;
      const fileName = file && file.name ? file.name : 'File sconosciuto';
      items.push(
        `<li class="matched"><strong>${escapeHtml(fileName)}</strong><span>Assegnato a ${escapeHtml(label)}</span></li>`
      );
    });

    result.unmatched.forEach(({ file, reason }) => {
      const detail = reason || 'File non riconosciuto.';
      const fileName = file && file.name ? file.name : 'File sconosciuto';
      items.push(
        `<li class="unmatched"><strong>${escapeHtml(fileName)}</strong><span>${escapeHtml(detail)}</span></li>`
      );
    });

    if (!items.length) {
      items.push('<li class="matched"><strong>Nessun file elaborato.</strong></li>');
    }

    return items.join('');
  }

  function showBulkModal(result) {
    if (!bulkModal || !bulkModalList) return;
    bulkModalList.innerHTML = buildModalListMarkup(result);
    bulkModal.removeAttribute('hidden');
    bulkModal.setAttribute('aria-hidden', 'false');
    lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusTarget = bulkModal.querySelector('[data-modal-focus]');
    if (focusTarget && typeof focusTarget.focus === 'function') {
      focusTarget.focus();
    }
  }

  function hideBulkModal() {
    if (!bulkModal) return;
    bulkModal.setAttribute('hidden', '');
    bulkModal.setAttribute('aria-hidden', 'true');
    if (bulkModalList) {
      bulkModalList.innerHTML = '';
    }
    if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
      lastFocusedElement.focus();
    }
    lastFocusedElement = null;
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
        name: nameInput.value.trim() || 'Sezione senza titolo',
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
      queryOutput.innerHTML = '<p class="query-empty">Aggiungi almeno una sezione con ID Account per generare le query.</p>';
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
                <button type="button" class="copy-query" data-query="${escapeHtml(query)}">Copia negli appunti</button>
              </article>
            `,
          )
          .join('');
        return `
          <section class="query-card-group" aria-label="Query per ${escapeHtml(section.name)}">
            <header>
              <h3>${escapeHtml(section.name)}</h3>
              <p class="form-hint">${section.accountIds.length} ID Account</p>
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
      button.textContent = 'Appunti non disponibili';
      setTimeout(() => {
        button.textContent = previous;
      }, 2000);
      return;
    }
    try {
      await navigator.clipboard.writeText(query);
      button.textContent = 'Copiato!';
    } catch (error) {
      button.textContent = 'Copia non riuscita';
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
    setFeedback('Caricamento dei file in corso...', 'pending');
    try {
      const response = await fetch('/api/import', { method: 'POST', body: formData });
      if (!response.ok) {
        throw new Error(`Import non riuscito: stato ${response.status}`);
      }
      const payload = await response.json();
      const imported = Object.entries(payload.summary || {})
        .map(([entity, count]) => `${entity.replace(/_/g, ' ')}: ${count}`)
        .join(', ');
      setFeedback(imported ? `Import eseguito per ${imported}.` : 'Nessun file elaborato.', 'success');
    } catch (error) {
      setFeedback(error.message || 'Import non riuscito.', 'error');
    }
  }

  function handleImportReset() {
    setFeedback('Selezioni azzerate.', 'info');
  }

  async function handleBulkFileSelection(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) {
      return;
    }

    let result;
    try {
      result = await classifyFiles(files);
      applyBulkAssignments(result);
      const matchedCount = result.matched.length;
      const unmatchedCount = result.unmatched.length;
      if (matchedCount && !unmatchedCount) {
        setFeedback(`Abbinati automaticamente ${matchedCount} file CSV.`, 'success');
      } else if (matchedCount && unmatchedCount) {
        setFeedback(
          `Abbinati ${matchedCount} file, ${unmatchedCount} non riconosciuti. Controlla il riepilogo.`,
          'warning'
        );
      } else {
        setFeedback('Nessun file riconosciuto. Controlla le intestazioni dei CSV.', 'error');
      }
    } catch (error) {
      setFeedback(error.message || 'Impossibile analizzare i file selezionati.', 'error');
      result = {
        matched: [],
        unmatched: files.map((file) => ({ file, reason: 'Analisi non riuscita.' })),
      };
    } finally {
      if (result) {
        showBulkModal(result);
      }
      event.target.value = '';
    }
  }

  function setFeedback(message, variant) {
    if (!importFeedback) return;
    importFeedback.textContent = message;
    if (variant) {
      importFeedback.dataset.variant = variant;
    } else {
      delete importFeedback.dataset.variant;
    }
  }

  async function runAlerts() {
    if (!alertButton) return;
    alertButton.disabled = true;
    alertButton.textContent = 'Analisi in corso...';
    try {
      const response = await fetch('/api/alerts/run', { method: 'POST' });
      if (!response.ok) {
        throw new Error(`Esecuzione allerte non riuscita: stato ${response.status}`);
      }
      const payload = await response.json();
      renderAlerts(payload.details || []);
      renderSummary(payload.summary || [], payload.statistics || null);
    } catch (error) {
      renderAlerts([]);
      renderSummary([], null);
      if (alertList) {
        alertList.innerHTML = `<li class="alert-item error">${escapeHtml(error.message || 'Errore durante le allerte.')}</li>`;
      }
    } finally {
      alertButton.disabled = false;
      alertButton.textContent = 'Esegui il ciclo allerte';
    }
  }

  function formatMultiline(text) {
    return escapeHtml(text || '').replace(/\n/g, '<br />');
  }

  function renderAlerts(alerts) {
    if (!alertList) return;
    if (!alerts.length) {
      alertList.innerHTML = '<li class="alert-item">Nessuna allerta generata.</li>';
    } else {
      const markup = alerts
        .map(
          (alert) => `
            <li class="alert-item">
              <h3>${escapeHtml(alert.alert_type || 'Allerta')}</h3>
              <p>${formatMultiline(alert.message || '')}</p>
              <dl class="alert-meta">
                <div><dt>Account</dt><dd>${escapeHtml(alert.account_name || alert.account_id || 'Sconosciuto')}</dd></div>
                <div><dt>Contatti</dt><dd>${escapeHtml(alert.contact_name || alert.contact_id || 'N/D')}</dd></div>
              </dl>
            </li>
          `,
        )
        .join('');
      alertList.innerHTML = markup;
    }
    if (alertCount) {
      alertCount.textContent = alerts.length ? `${alerts.length} allerte` : '';
    }
  }

  function normaliseFilterValue(value) {
    return (value || '').trim();
  }

  function getAccountLabel(row) {
    return normaliseFilterValue(row.account_name || row.account_id || 'Sconosciuto');
  }

  function getRoleList(row) {
    return (row.contact_roles || '')
      .split(/[,;]+/)
      .map((role) => normaliseFilterValue(role))
      .filter(Boolean);
  }

  function populateFilter(select, values, placeholder) {
    if (!select) return;
    const previous = select.value;
    const options = [`<option value="">${escapeHtml(placeholder)}</option>`];
    values.forEach((value) => {
      options.push(`<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`);
    });
    select.innerHTML = options.join('');
    if (values.includes(previous)) {
      select.value = previous;
    } else {
      select.value = '';
    }
  }

  function toSortedArray(set) {
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'it', { sensitivity: 'base' }));
  }

  function populateSummaryFilters(rows) {
    const accountValues = new Set();
    const alertTypes = new Set();
    const roleValues = new Set();

    rows.forEach((row) => {
      const account = getAccountLabel(row);
      if (account) accountValues.add(account);
      const alertType = normaliseFilterValue(row.alert_type);
      if (alertType) alertTypes.add(alertType);
      getRoleList(row).forEach((role) => roleValues.add(role));
    });

    populateFilter(filterAccount, toSortedArray(accountValues), 'Tutti');
    populateFilter(filterAlertType, toSortedArray(alertTypes), 'Tutti');
    populateFilter(filterContactRole, toSortedArray(roleValues), 'Tutti');
  }

  function resetSummaryFilters() {
    populateFilter(filterAccount, [], 'Tutti');
    populateFilter(filterAlertType, [], 'Tutti');
    populateFilter(filterContactRole, [], 'Tutti');
  }

  function renderSummaryTable(rows) {
    if (!summaryTable || !summaryTableBody || !summaryEmpty) return;
    if (!rows.length) {
      summaryTableBody.innerHTML =
        '<tr class="empty"><td colspan="6">Nessuna riga corrispondente ai filtri selezionati.</td></tr>';
    } else {
      const markup = rows
        .map(
          (row) => `
            <tr>
              <td>${escapeHtml(row.alert_type)}</td>
              <td>${escapeHtml(getAccountLabel(row))}</td>
              <td>${escapeHtml(row.contact_name || row.contact_id || 'N/D')}</td>
              <td>${escapeHtml(row.contact_roles || 'N/D')}</td>
              <td>${escapeHtml(row.data_focus || 'N/D')}</td>
              <td>${escapeHtml(row.details || '')}</td>
            </tr>
          `,
        )
        .join('');
      summaryTableBody.innerHTML = markup;
    }
    summaryTable.hidden = false;
    summaryEmpty.hidden = true;
  }

  function applySummaryFilters() {
    if (!summaryTable || !summaryTableBody || !summaryEmpty) return;
    if (!currentSummaryRows.length) {
      summaryTable.hidden = true;
      summaryEmpty.hidden = false;
      summaryTableBody.innerHTML = '';
      return;
    }

    const filters = {
      account: filterAccount ? filterAccount.value : '',
      alertType: filterAlertType ? filterAlertType.value : '',
      contactRole: filterContactRole ? filterContactRole.value : '',
    };

    const filtered = currentSummaryRows.filter((row) => {
      if (filters.account && getAccountLabel(row) !== filters.account) {
        return false;
      }
      if (filters.alertType && normaliseFilterValue(row.alert_type) !== filters.alertType) {
        return false;
      }
      if (filters.contactRole) {
        const roles = getRoleList(row);
        if (!roles.includes(filters.contactRole)) {
          return false;
        }
      }
      return true;
    });

    renderSummaryTable(filtered);
  }

  function formatInteger(value) {
    if (typeof value !== 'number' || Number.isNaN(value)) {
      return '0';
    }
    return integerFormatter.format(Math.trunc(value));
  }

  function formatAverage(value) {
    if (typeof value !== 'number' || Number.isNaN(value)) {
      return '0,00';
    }
    return averageFormatter.format(value);
  }

  function renderSummaryStatistics(statistics) {
    if (!summaryStatsContent || !summaryStatsEmpty) return;

    if (!statistics || !statistics.totals) {
      summaryStatsContent.hidden = true;
      summaryStatsEmpty.hidden = false;
      Object.values(statElements).forEach((element) => {
        if (element) element.textContent = '0';
      });
      if (summaryStatsPerTypeBody) {
        summaryStatsPerTypeBody.innerHTML =
          '<tr class="empty"><td colspan="5">Nessun dato disponibile.</td></tr>';
      }
      if (summaryStatsTopAccountsBody) {
        summaryStatsTopAccountsBody.innerHTML =
          '<tr class="empty"><td colspan="2">Nessun dato disponibile.</td></tr>';
      }
      return;
    }

    summaryStatsEmpty.hidden = true;
    summaryStatsContent.hidden = false;

    const totals = statistics.totals || {};
    if (statElements.totalAlerts)
      statElements.totalAlerts.textContent = formatInteger(totals.total_alerts || 0);
    if (statElements.totalAccounts)
      statElements.totalAccounts.textContent = formatInteger(totals.total_accounts || 0);
    if (statElements.accountsWithAlerts)
      statElements.accountsWithAlerts.textContent = formatInteger(totals.accounts_with_alerts || 0);
    if (statElements.uniqueContacts)
      statElements.uniqueContacts.textContent = formatInteger(totals.unique_contacts || 0);
    if (statElements.uniqueAlertTypes)
      statElements.uniqueAlertTypes.textContent = formatInteger(totals.unique_alert_types || 0);
    if (statElements.alertsWithoutContact)
      statElements.alertsWithoutContact.textContent = formatInteger(totals.alerts_without_contact || 0);
    if (statElements.averageAlerts)
      statElements.averageAlerts.textContent = formatAverage(totals.average_alerts_per_account || 0);

    const perType = Array.isArray(statistics.per_type) ? statistics.per_type : [];
    if (summaryStatsPerTypeBody) {
      if (!perType.length) {
        summaryStatsPerTypeBody.innerHTML =
          '<tr class="empty"><td colspan="5">Nessun dato disponibile.</td></tr>';
      } else {
        const perTypeMarkup = perType
          .map(
            (row) => `
              <tr>
                <td>${escapeHtml(row.alert_type || 'N/D')}</td>
                <td>${formatInteger(row.alert_count || 0)}</td>
                <td>${formatInteger(row.unique_accounts || 0)}</td>
                <td>${formatInteger(row.unique_contacts || 0)}</td>
                <td>${formatInteger(row.alerts_without_contact || 0)}</td>
              </tr>
            `,
          )
          .join('');
        summaryStatsPerTypeBody.innerHTML = perTypeMarkup;
      }
    }

    const topAccounts = Array.isArray(statistics.top_accounts) ? statistics.top_accounts : [];
    if (summaryStatsTopAccountsBody) {
      if (!topAccounts.length) {
        summaryStatsTopAccountsBody.innerHTML =
          '<tr class="empty"><td colspan="2">Nessun dato disponibile.</td></tr>';
      } else {
        const topMarkup = topAccounts
          .map((account) => {
            const label = account.account_name || account.account_id || 'Sconosciuto';
            return `
              <tr>
                <td>${escapeHtml(label)}</td>
                <td>${formatInteger(account.alert_count || 0)}</td>
              </tr>
            `;
          })
          .join('');
        summaryStatsTopAccountsBody.innerHTML = topMarkup;
      }
    }
  }

  function renderSummary(rows, statistics) {
    if (
      !downloadButton ||
      !summaryTable ||
      !summaryTableBody ||
      !summaryEmpty ||
      !summaryStatsEmpty ||
      !summaryStatsContent
    ) {
      return;
    }

    currentSummaryRows = Array.isArray(rows) ? rows : [];
    const statsPayload = statistics && typeof statistics === 'object' ? statistics : null;

    if (!currentSummaryRows.length) {
      summaryTable.hidden = true;
      summaryEmpty.hidden = false;
      downloadButton.disabled = true;
      summaryTableBody.innerHTML = '';
      resetSummaryFilters();
    } else {
      downloadButton.disabled = false;
      populateSummaryFilters(currentSummaryRows);
      applySummaryFilters();
    }

    renderSummaryStatistics(statsPayload);
  }

  async function downloadAlerts() {
    try {
      const response = await fetch('/api/alerts/download');
      if (!response.ok) {
        throw new Error('Impossibile scaricare il file Excel.');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'riepilogo_allerte.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert(error.message || 'Download non riuscito.');
    }
  }

  function handleSummaryTabClick(event) {
    const tab = event.target.closest('.summary-tab');
    if (!tab) return;
    const targetId = tab.dataset.target;
    if (!targetId) return;

    summaryTabs.forEach((button) => {
      const isActive = button === tab;
      button.classList.toggle('active', isActive);
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    summaryTabPanels.forEach((panel) => {
      const isActive = panel.id === targetId;
      panel.classList.toggle('active', isActive);
      panel.hidden = !isActive;
    });
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

  if (bulkSelectButton && bulkFileInput) {
    bulkSelectButton.addEventListener('click', () => {
      bulkFileInput.click();
    });
  }

  if (bulkFileInput) {
    bulkFileInput.addEventListener('change', handleBulkFileSelection);
  }

  if (bulkModalClose) {
    bulkModalClose.addEventListener('click', hideBulkModal);
  }

  if (bulkModal) {
    bulkModal.addEventListener('click', (event) => {
      if (event.target === bulkModal) {
        hideBulkModal();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !bulkModal.hasAttribute('hidden')) {
        hideBulkModal();
      }
    });
  }

  if (alertButton) {
    alertButton.addEventListener('click', runAlerts);
  }

  if (downloadButton) {
    downloadButton.addEventListener('click', downloadAlerts);
  }

  if (summaryTabsContainer) {
    summaryTabsContainer.addEventListener('click', handleSummaryTabClick);
  }

  [filterAccount, filterAlertType, filterContactRole].forEach((element) => {
    if (element) {
      element.addEventListener('change', applySummaryFilters);
    }
  });

  if (stepButtons.length) {
    document.querySelector('.steps').addEventListener('click', handleStepClick);
  }

  addInitialSection();
  renderQueryResults([]);
})();
