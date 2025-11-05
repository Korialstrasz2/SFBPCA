// query_helper.js

const QueryHelper = (() => {
  const form = document.getElementById('query-generator-form');
  const accountInput = document.getElementById('account-ids');
  const results = document.getElementById('query-results');
  const clearButton = document.getElementById('clear-queries');


const SOQL_BUILDERS = {
  accounts: (ids) =>
    `SELECT Id, Name
     FROM Account
     WHERE Id IN (${formatIds(ids)})
     ORDER BY Name`,

  // Contacts linked to those accounts through AccountContactRelation
  contacts: (ids) =>
    `SELECT Id, FirstName, LastName, IndividualId, AccountId, FiscalCode__c,
            VATNumber__c, MobilePhone, HomePhone, Email
     FROM Contact
     WHERE Id IN (
       SELECT ContactId FROM AccountContactRelation
       WHERE AccountId IN (${formatIds(ids)})
     )
     ORDER BY LastName, FirstName`,

    individuals: (ids) =>
      `SELECT Id, FirstName, LastName
      FROM Individual
      WHERE Id IN (SELECT IndividualId FROM Contact WHERE AccountId IN (${formatIds(
        ids,
      )})) ORDER BY LastName, FirstName`,

  // AccountContactRelation stays the same
  account_contact_relations: (ids) =>
    `SELECT Id, AccountId, ContactId, Roles
     FROM AccountContactRelation
     WHERE AccountId IN (${formatIds(ids)})
     ORDER BY AccountId`,

    contact_point_phones: (ids) =>
      `SELECT Id, ParentId, TelephoneNumber
      FROM ContactPointPhone
      WHERE ParentId IN (SELECT IndividualId FROM Contact WHERE IndividualId != null AND AccountId IN (${formatIds(
        ids,
      )})) ORDER BY ParentId`,
    contact_point_emails: (ids) =>
      `SELECT Id, ParentId, EmailAddress, Type__c
      FROM ContactPointEmail
      WHERE ParentId IN (SELECT IndividualId FROM Contact WHERE IndividualId != null AND AccountId IN (${formatIds(
        ids,
      )})) ORDER BY ParentId`,
};

  const TITLES = {
    accounts: 'Account',
    contacts: 'Contact',
    individuals: 'Individual',
    account_contact_relations: 'AccountContactRelation',
    contact_point_phones: 'ContactPointPhone',
    contact_point_emails: 'ContactPointEmail',
  };

  const escapeHtml = (value) =>
    value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  function formatIds(ids) {
    return ids.map((id) => `'${id}'`).join(', ');
  }

  function parseAccountIds() {
    if (!accountInput) {
      return [];
    }
    const raw = accountInput.value || '';
    const tokens = raw
      .split(/[\s,;]+/)
      .map((token) => token.trim())
      .filter(Boolean);
    return Array.from(new Set(tokens));
  }

  function renderInitialMessage() {
    if (!results) return;
    results.innerHTML =
      '<p class="query-empty">Enter one or more Account IDs above to generate SOQL queries for every supported object.</p>';
  }

  function buildQueries(ids) {
    return Object.entries(SOQL_BUILDERS).map(([key, builder]) => ({
      key,
      title: TITLES[key] || key,
      query: builder(ids),
    }));
  }

  function renderQueries(items) {
    if (!results) return;
    if (items.length === 0) {
      renderInitialMessage();
      return;
    }

    const markup = items
      .map(
        ({ key, title, query }) => `
        <article class="query-card" data-entity="${key}">
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

    results.innerHTML = markup;
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

  function handleSubmit(event) {
    event.preventDefault();
    const ids = parseAccountIds();
    if (ids.length === 0) {
      renderQueries([]);
      return;
    }
    const queries = buildQueries(ids);
    renderQueries(queries);
  }

  function handleReset(event) {
    if (!form || event.target !== clearButton) {
      return;
    }
    setTimeout(() => {
      renderInitialMessage();
    }, 0);
  }

  if (form) {
    form.addEventListener('submit', handleSubmit);
    form.addEventListener('reset', handleReset);
  }

  if (results) {
    results.addEventListener('click', (event) => {
      const button = event.target.closest('button.copy-query');
      if (button) {
        copyQuery(button);
      }
    });
  }

  renderInitialMessage();

  return {
    parseAccountIds,
    buildQueries,
  };
})();

window.QueryHelper = QueryHelper;
