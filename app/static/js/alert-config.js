const AlertConfigModule = (() => {
  const listContainer = document.getElementById('alert-config-list');
  const statusContainer = document.getElementById('alert-config-status');
  const addButton = document.getElementById('add-alert');
  const form = document.getElementById('alert-config-form');

  let configEntries = [];

  const setStatus = (message, isError = false) => {
    if (!statusContainer) {
      return;
    }
    statusContainer.textContent = message;
    statusContainer.classList.toggle('error', isError);
    if (message) {
      statusContainer.classList.add('visible');
    } else {
      statusContainer.classList.remove('visible');
    }
  };

  const createInputGroup = (labelText, inputElement, helperText) => {
    const wrapper = document.createElement('label');
    wrapper.className = 'config-field';

    const label = document.createElement('span');
    label.className = 'field-label';
    label.textContent = labelText;
    wrapper.append(label, inputElement);

    if (helperText) {
      const helper = document.createElement('span');
      helper.className = 'field-helper';
      helper.textContent = helperText;
      wrapper.appendChild(helper);
    }

    return wrapper;
  };

  const renderEmptyState = () => {
    if (!listContainer) {
      return;
    }
    listContainer.innerHTML = '';
    const empty = document.createElement('p');
    empty.className = 'config-empty';
    empty.textContent = 'No alerts configured yet.';
    listContainer.appendChild(empty);
  };

  const renderConfig = () => {
    if (!listContainer) {
      return;
    }

    if (!configEntries.length) {
      renderEmptyState();
      return;
    }

    listContainer.innerHTML = '';

    configEntries.forEach((entry) => {
      const card = document.createElement('article');
      card.className = 'config-card';
      card.dataset.id = entry.id;
      card.dataset.kind = entry.kind || 'system';

      const header = document.createElement('div');
      header.className = 'config-card-header';

      const toggleLabel = document.createElement('label');
      toggleLabel.className = 'config-toggle';
      const toggle = document.createElement('input');
      toggle.type = 'checkbox';
      toggle.className = 'config-enabled';
      toggle.checked = entry.enabled !== false;
      const toggleText = document.createElement('span');
      toggleText.textContent = 'Enabled';
      toggleLabel.append(toggle, toggleText);

      header.appendChild(toggleLabel);

      if (entry.kind === 'custom') {
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'ghost';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
          configEntries = configEntries.filter((item) => item.id !== entry.id);
          renderConfig();
        });
        header.appendChild(removeButton);
      }

      card.appendChild(header);

      const nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.className = 'config-label';
      nameInput.value = entry.label || '';
      nameInput.required = true;
      card.appendChild(createInputGroup('Display name', nameInput));

      const descriptionArea = document.createElement('textarea');
      descriptionArea.className = 'config-description';
      descriptionArea.value = entry.description || '';
      descriptionArea.rows = 2;
      card.appendChild(createInputGroup('Description', descriptionArea));

      if (entry.kind === 'custom') {
        const messageArea = document.createElement('textarea');
        messageArea.className = 'config-message';
        messageArea.value = entry.message || '';
        messageArea.rows = 3;
        card.appendChild(
          createInputGroup('Alert message', messageArea, 'This message will appear in the alerts list when enabled.')
        );
      } else {
        const helper = document.createElement('p');
        helper.className = 'config-helper';
        helper.textContent = 'System-generated alerts run automatically after each import.';
        card.appendChild(helper);
      }

      listContainer.appendChild(card);
    });
  };

  const fetchConfig = async () => {
    if (!listContainer) {
      return;
    }
    try {
      const response = await fetch('/alerts/config');
      if (!response.ok) {
        throw new Error('Failed to load alert configuration');
      }
      const payload = await response.json();
      configEntries = Array.isArray(payload.config) ? payload.config : [];
      renderConfig();
    } catch (error) {
      renderEmptyState();
      setStatus(error.message || 'Unable to load alert configuration', true);
    }
  };

  const serialiseForm = () => {
    if (!listContainer) {
      return [];
    }
    const cards = Array.from(listContainer.querySelectorAll('.config-card'));
    return cards.map((card) => {
      const id = card.dataset.id;
      const kind = card.dataset.kind || 'system';
      const label = card.querySelector('.config-label');
      const description = card.querySelector('.config-description');
      const message = card.querySelector('.config-message');
      const enabled = card.querySelector('.config-enabled');
      return {
        id,
        kind,
        label: label ? label.value : '',
        description: description ? description.value : '',
        message: message ? message.value : '',
        enabled: enabled ? enabled.checked : true,
      };
    });
  };

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      setStatus('Saving configuration…');
      try {
        const payload = { config: serialiseForm() };
        const response = await fetch('/alerts/config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error('Failed to save configuration');
        }
        const data = await response.json();
        configEntries = Array.isArray(data.config) ? data.config : [];
        renderConfig();
        setStatus('Alert configuration saved successfully.');
        document.dispatchEvent(new CustomEvent('alerts:refresh'));
      } catch (error) {
        setStatus(error.message || 'Unable to save configuration', true);
      }
    });
  }

  if (addButton) {
    addButton.addEventListener('click', () => {
      const newEntry = {
        id: `custom-${Date.now()}`,
        label: 'New custom alert',
        description: '',
        message: '',
        enabled: true,
        kind: 'custom',
      };
      configEntries = [...configEntries, newEntry];
      renderConfig();
      setStatus('');
    });
  }

  fetchConfig();

  return {
    fetchConfig,
  };
})();

window.AlertConfigModule = AlertConfigModule;
