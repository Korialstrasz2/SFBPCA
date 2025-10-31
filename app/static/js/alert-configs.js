const AlertConfigModule = (() => {
  const listContainer = document.getElementById('alert-config-items');
  const form = document.getElementById('alert-config-form');
  const idField = document.getElementById('alert-config-id');
  const nameField = document.getElementById('alert-config-name');
  const descriptionField = document.getElementById('alert-config-description');
  const logicSelect = document.getElementById('alert-logic');
  const logicSummary = document.getElementById('alert-logic-summary');
  const enabledField = document.getElementById('alert-config-enabled');
  const typeTemplateField = document.getElementById('alert-type-template');
  const messageTemplateField = document.getElementById('alert-message-template');
  const parametersField = document.getElementById('alert-parameters');
  const deleteButton = document.getElementById('delete-alert-config');
  const newButton = document.getElementById('new-alert-config');
  const statusField = document.getElementById('alert-config-status');
  const logicDescription = document.getElementById('logic-description');
  const logicContextFields = document.getElementById('logic-context-fields');
  const formTitle = document.getElementById('alert-config-form-title');

  const state = {
    configs: [],
    availableLogic: [],
    selectedId: null,
  };

  const logicMap = new Map();

  const resetStatus = () => {
    if (statusField) {
      statusField.textContent = '';
      statusField.classList.remove('error', 'visible');
    }
  };

  const showStatus = (message, isError = false) => {
    if (!statusField) return;
    statusField.textContent = message;
    statusField.classList.toggle('error', isError);
    statusField.classList.add('visible');
  };

  const formatParameters = (parameters) => {
    if (!parameters || Object.keys(parameters).length === 0) {
      return '';
    }
    try {
      return JSON.stringify(parameters, null, 2);
    } catch (error) {
      return '';
    }
  };

  const parseParameters = (value) => {
    if (!value || value.trim() === '') {
      return {};
    }
    try {
      return JSON.parse(value);
    } catch (error) {
      throw new Error('Parameters must be valid JSON.');
    }
  };

  const renderLogicOptions = () => {
    if (!logicSelect) return;
    const selectedValue = logicSelect.value;
    logicSelect.innerHTML = '';
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select logic';
    logicSelect.appendChild(defaultOption);

    state.availableLogic.forEach((logic) => {
      const option = document.createElement('option');
      option.value = logic.id;
      option.textContent = logic.name || logic.id;
      logicMap.set(logic.id, logic);
      logicSelect.appendChild(option);
    });

    if (selectedValue) {
      logicSelect.value = selectedValue;
    }
  };

  const renderLogicDetails = (logicId) => {
    if (!logicSummary || !logicDescription || !logicContextFields) {
      return;
    }
    const logic = logicMap.get(logicId);
    if (!logic) {
      logicSummary.textContent = '';
      logicDescription.textContent = 'Select a logic option to see the available fields.';
      logicContextFields.textContent = '';
      return;
    }
    logicSummary.textContent = logic.description || '';
    logicDescription.textContent = logic.description || 'No description provided.';
    const contextFields = logic.context_fields || logic.contextFields;
    if (contextFields && typeof contextFields === 'object') {
      logicContextFields.textContent = JSON.stringify(contextFields, null, 2);
    } else {
      logicContextFields.textContent = 'No context fields documented.';
    }
  };

  const renderList = () => {
    if (!listContainer) return;
    listContainer.innerHTML = '';
    if (!state.configs || state.configs.length === 0) {
      const emptyItem = document.createElement('li');
      emptyItem.className = 'alert-config-item empty';
      emptyItem.textContent = 'No alerts configured yet.';
      listContainer.appendChild(emptyItem);
      return;
    }

    state.configs.forEach((config) => {
      const item = document.createElement('li');
      item.className = 'alert-config-item';
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.configId = config.id;
      button.className = 'alert-config-item__button';
      if (config.id === state.selectedId) {
        button.classList.add('active');
      }
      const name = document.createElement('span');
      name.className = 'alert-config-item__name';
      name.textContent = config.name || 'Untitled alert';
      const status = document.createElement('span');
      status.className = 'alert-config-item__status';
      status.textContent = config.enabled ? 'Enabled' : 'Disabled';
      button.appendChild(name);
      button.appendChild(status);
      button.addEventListener('click', () => {
        selectConfig(config.id);
      });
      item.appendChild(button);
      listContainer.appendChild(item);
    });
  };

  const populateForm = (config) => {
    resetStatus();
    if (!config) {
      form.reset();
      idField.value = '';
      enabledField.checked = true;
      parametersField.value = '';
      logicSelect.value = '';
      renderLogicDetails('');
      if (logicSummary) {
        logicSummary.textContent = '';
      }
      if (logicDescription) {
        logicDescription.textContent = 'Select a logic option to see the available fields.';
      }
      if (logicContextFields) {
        logicContextFields.textContent = '';
      }
      formTitle.textContent = 'Create alert';
      if (deleteButton) {
        deleteButton.disabled = true;
      }
      return;
    }

    idField.value = config.id || '';
    nameField.value = config.name || '';
    descriptionField.value = config.description || '';
    logicSelect.value = config.logic_id || '';
    enabledField.checked = config.enabled !== false;
    typeTemplateField.value = config.type_template || '';
    messageTemplateField.value = config.message_template || '';
    parametersField.value = formatParameters(config.parameters);
    formTitle.textContent = 'Edit alert';
    if (deleteButton) {
      deleteButton.disabled = false;
    }
    renderLogicDetails(config.logic_id);
  };

  const selectConfig = (configId) => {
    const config = state.configs.find((entry) => entry.id === configId);
    state.selectedId = config ? config.id : null;
    renderList();
    populateForm(config);
  };

  const startNewConfig = () => {
    state.selectedId = null;
    renderList();
    populateForm(null);
  };

  const normalizePayload = () => {
    const payload = {
      id: idField.value || undefined,
      name: nameField.value.trim(),
      description: descriptionField.value.trim(),
      logic_id: logicSelect.value,
      enabled: enabledField.checked,
      type_template: typeTemplateField.value.trim(),
      message_template: messageTemplateField.value.trim(),
      parameters: parseParameters(parametersField.value),
    };
    if (!payload.logic_id) {
      throw new Error('Please select a logic option for the alert.');
    }
    if (payload.type_template === '') {
      payload.type_template = null;
    }
    if (payload.message_template === '') {
      payload.message_template = null;
    }
    return payload;
  };

  const fetchConfigurations = async () => {
    try {
      const response = await fetch('/alert-configs');
      if (!response.ok) {
        throw new Error('Failed to load alert configurations.');
      }
      const payload = await response.json();
      state.configs = payload.configs || [];
      state.availableLogic = payload.available_logic || [];
      logicMap.clear();
      renderLogicOptions();
      renderLogicDetails(logicSelect.value);
      renderList();
      const selectedConfig = state.configs.find((entry) => entry.id === state.selectedId);
      if (selectedConfig) {
        populateForm(selectedConfig);
      } else if (state.configs.length > 0) {
        selectConfig(state.configs[0].id);
      } else {
        startNewConfig();
      }
    } catch (error) {
      showStatus(error.message || 'Unable to load alert configurations.', true);
    }
  };

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      resetStatus();
      try {
        const payload = normalizePayload();
        const isUpdate = Boolean(payload.id);
        const url = isUpdate ? `/alert-configs/${payload.id}` : '/alert-configs';
        const method = isUpdate ? 'PUT' : 'POST';
        const response = await fetch(url, {
          method,
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          const errorPayload = await response.json().catch(() => ({}));
          const message = errorPayload.message || 'Failed to save alert configuration.';
          throw new Error(message);
        }
        const data = await response.json();
        const config = data.config;
        state.selectedId = config?.id || null;
        showStatus('Alert configuration saved.');
        await fetchConfigurations();
        document.dispatchEvent(new CustomEvent('alerts:refresh'));
      } catch (error) {
        showStatus(error.message || 'Failed to save alert configuration.', true);
      }
    });
  }

  if (logicSelect) {
    logicSelect.addEventListener('change', () => {
      renderLogicDetails(logicSelect.value);
    });
  }

  if (newButton) {
    newButton.addEventListener('click', () => {
      startNewConfig();
      formTitle.textContent = 'Create alert';
    });
  }

  if (deleteButton) {
    deleteButton.addEventListener('click', async () => {
      if (!state.selectedId) {
        showStatus('Select an alert to delete.', true);
        return;
      }
      const confirmDelete = window.confirm('Delete this alert configuration?');
      if (!confirmDelete) {
        return;
      }
      try {
        const response = await fetch(`/alert-configs/${state.selectedId}`, {
          method: 'DELETE',
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.message || 'Failed to delete alert configuration.');
        }
        showStatus('Alert configuration deleted.');
        state.selectedId = null;
        await fetchConfigurations();
        document.dispatchEvent(new CustomEvent('alerts:refresh'));
      } catch (error) {
        showStatus(error.message || 'Failed to delete alert configuration.', true);
      }
    });
  }

  const init = () => {
    if (!listContainer || !form) {
      return;
    }
    fetchConfigurations();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    refresh: fetchConfigurations,
  };
})();

window.AlertConfigModule = AlertConfigModule;
