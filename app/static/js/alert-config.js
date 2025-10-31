const AlertConfigModule = (() => {
  const listElement = document.getElementById('alert-definition-list');
  const form = document.getElementById('alert-definition-form');
  const formTitle = document.getElementById('alert-definition-form-title');
  const newButton = document.getElementById('new-alert-definition');
  const deleteButton = document.getElementById('delete-alert-definition');
  const feedback = document.getElementById('alert-definition-feedback');
  const idInput = document.getElementById('alert-id');
  const nameInput = document.getElementById('alert-name');
  const descriptionInput = document.getElementById('alert-description');
  const enabledInput = document.getElementById('alert-enabled');
  const logicTypeSelect = document.getElementById('alert-logic-type');
  const logicHelp = document.getElementById('alert-logic-help');
  const parameterFieldsContainer = document.getElementById('alert-parameter-fields');
  const logicPreview = document.getElementById('alert-logic-preview');

  const state = {
    definitions: [],
    blueprints: {},
    selectedId: null,
  };

  const getBlueprint = (logicType) => state.blueprints[logicType] || { parameters: {} };

  const resetFeedback = () => {
    if (!feedback) return;
    feedback.textContent = '';
    feedback.classList.remove('error', 'visible');
  };

  const showFeedback = (message, isError = false) => {
    if (!feedback) return;
    feedback.textContent = message;
    feedback.classList.toggle('error', isError);
    feedback.classList.add('visible');
  };

  const convertParameterValue = (meta = {}, rawValue) => {
    if (meta.type === 'number') {
      const numeric = Number(rawValue);
      if (Number.isNaN(numeric)) {
        return rawValue;
      }
      return numeric;
    }
    return rawValue;
  };

  const mergeWithDefaults = (logicType, values) => {
    const blueprint = getBlueprint(logicType);
    const merged = {};
    const parameters = blueprint.parameters || {};

    Object.entries(parameters).forEach(([key, meta]) => {
      const rawValue = values[key];
      if (rawValue !== undefined && rawValue !== '') {
        merged[key] = convertParameterValue(meta, rawValue);
      } else if (meta.default !== undefined) {
        merged[key] = meta.default;
      }
    });

    Object.entries(values).forEach(([key, rawValue]) => {
      if (merged[key] !== undefined) return;
      if (rawValue === '' || rawValue === undefined) return;
      merged[key] = convertParameterValue(parameters[key], rawValue);
    });

    return merged;
  };

  const collectParameterValues = ({ includeEmpty = false } = {}) => {
    const values = {};
    if (!parameterFieldsContainer) {
      return values;
    }

    parameterFieldsContainer.querySelectorAll('[data-parameter-key]').forEach((wrapper) => {
      const key = wrapper.dataset.parameterKey;
      const input = wrapper.querySelector('input, select, textarea');
      if (!key || !input) {
        return;
      }

      const rawValue = input.value;
      if (!includeEmpty && (rawValue === '' || rawValue === undefined)) {
        return;
      }

      const blueprint = getBlueprint(logicTypeSelect?.value || '');
      const meta = (blueprint.parameters || {})[key] || {};
      if (meta.type === 'number') {
        const numeric = Number(rawValue);
        if (rawValue === '' && !includeEmpty) {
          return;
        }
        if (!Number.isNaN(numeric)) {
          values[key] = numeric;
          return;
        }
      }

      values[key] = rawValue;
    });

    return values;
  };

  const updateLogicPreview = () => {
    if (!logicPreview || !logicTypeSelect) return;
    const logicType = logicTypeSelect.value;
    if (!logicType) {
      logicPreview.value = '';
      return;
    }
    const rawValues = collectParameterValues({ includeEmpty: true });
    const parameters = mergeWithDefaults(logicType, rawValues);
    const logic = {
      type: logicType,
      parameters,
    };
    logicPreview.value = JSON.stringify(logic, null, 2);
  };

  const createParameterField = (key, meta, value) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'form-field';
    wrapper.dataset.parameterKey = key;

    const label = document.createElement('label');
    label.htmlFor = `parameter-${key}`;
    label.textContent = meta.label || key;
    wrapper.appendChild(label);

    let input;
    if (meta.type === 'select' && Array.isArray(meta.options)) {
      input = document.createElement('select');
      meta.options.forEach((option) => {
        const opt = document.createElement('option');
        opt.value = option.value;
        opt.textContent = option.label || option.value;
        input.appendChild(opt);
      });
      if (value === undefined || value === '') {
        input.value = meta.default ?? (meta.options[0] ? meta.options[0].value : '');
      }
    } else {
      input = document.createElement('input');
      input.type = meta.type === 'number' ? 'number' : 'text';
      if (meta.min !== undefined) {
        input.min = meta.min;
      }
    }

    input.id = `parameter-${key}`;
    const stringValue = value !== undefined ? value : meta.default;
    if (stringValue !== undefined && stringValue !== null) {
      input.value = String(stringValue);
    }

    input.addEventListener('input', updateLogicPreview);
    input.addEventListener('change', updateLogicPreview);
    wrapper.appendChild(input);

    if (meta.help) {
      const help = document.createElement('p');
      help.className = 'field-hint';
      help.textContent = meta.help;
      wrapper.appendChild(help);
    }

    return wrapper;
  };

  const renderParameterFields = (logicType, values = {}) => {
    if (!parameterFieldsContainer) return;
    parameterFieldsContainer.innerHTML = '';
    const blueprint = getBlueprint(logicType);
    if (logicHelp) {
      logicHelp.textContent = blueprint.description || '';
    }

    const parameters = blueprint.parameters || {};
    const keys = Object.keys(parameters);
    if (keys.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'field-hint';
      empty.textContent = 'This logic does not require additional parameters.';
      parameterFieldsContainer.appendChild(empty);
      updateLogicPreview();
      return;
    }

    keys.forEach((key) => {
      const meta = parameters[key] || {};
      const field = createParameterField(key, meta, values[key]);
      parameterFieldsContainer.appendChild(field);
    });

    updateLogicPreview();
  };

  const populateLogicTypes = () => {
    if (!logicTypeSelect) return;
    const previousValue = logicTypeSelect.value;
    logicTypeSelect.innerHTML = '';

    const entries = Object.entries(state.blueprints).sort((a, b) => {
      const labelA = (a[1].label || a[0]).toLowerCase();
      const labelB = (b[1].label || b[0]).toLowerCase();
      return labelA.localeCompare(labelB);
    });

    entries.forEach(([value, meta]) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = meta.label || value;
      logicTypeSelect.appendChild(option);
    });

    const targetValue = entries.some(([value]) => value === previousValue)
      ? previousValue
      : entries[0]?.[0] || '';
    logicTypeSelect.value = targetValue;
    renderParameterFields(targetValue);
  };

  const renderDefinitionList = () => {
    if (!listElement) return;
    listElement.innerHTML = '';

    if (!state.definitions.length) {
      const empty = document.createElement('li');
      empty.className = 'empty-state';
      empty.textContent = 'No alert definitions found. Create one to get started.';
      listElement.appendChild(empty);
      return;
    }

    const fragment = document.createDocumentFragment();
    state.definitions.forEach((definition) => {
      const item = document.createElement('li');
      item.className = 'definition-card';
      if (definition.enabled === false) {
        item.classList.add('disabled');
      }
      if (state.selectedId === definition.id) {
        item.classList.add('active');
      }
      item.dataset.id = definition.id;

      const header = document.createElement('header');
      const title = document.createElement('h4');
      title.textContent = definition.name || definition.id;
      const identifier = document.createElement('small');
      identifier.textContent = `ID: ${definition.id}`;
      title.appendChild(identifier);
      header.appendChild(title);

      const actions = document.createElement('div');
      actions.className = 'card-actions';
      const status = document.createElement('span');
      status.className = 'status-badge';
      status.textContent = definition.enabled === false ? 'Disabled' : 'Enabled';
      actions.appendChild(status);

      const editButton = document.createElement('button');
      editButton.type = 'button';
      editButton.className = 'link-button';
      editButton.textContent = 'Edit';
      editButton.addEventListener('click', (event) => {
        event.preventDefault();
        setFormMode('edit', definition.id);
      });
      actions.appendChild(editButton);
      header.appendChild(actions);
      item.appendChild(header);

      if (definition.description) {
        const description = document.createElement('p');
        description.textContent = definition.description;
        item.appendChild(description);
      }

      const logicSummary = document.createElement('pre');
      logicSummary.textContent = JSON.stringify(definition.logic || {}, null, 2);
      item.appendChild(logicSummary);

      item.addEventListener('click', (event) => {
        if (event.target === editButton) return;
        event.preventDefault();
        setFormMode('edit', definition.id);
      });

      fragment.appendChild(item);
    });

    listElement.appendChild(fragment);
  };

  const setFormMode = (mode, definitionId = null) => {
    resetFeedback();
    state.selectedId = mode === 'edit' ? definitionId : null;

    if (mode === 'edit') {
      const definition = state.definitions.find((item) => item.id === definitionId);
      if (!definition) {
        return;
      }
      formTitle.textContent = `Edit alert: ${definition.name || definition.id}`;
      idInput.value = definition.id || '';
      idInput.readOnly = true;
      nameInput.value = definition.name || '';
      descriptionInput.value = definition.description || '';
      enabledInput.checked = definition.enabled !== false;
      logicTypeSelect.value = definition.logic?.type || logicTypeSelect.value;
      renderParameterFields(definition.logic?.type || logicTypeSelect.value, definition.logic?.parameters || {});
      deleteButton.hidden = false;
    } else {
      formTitle.textContent = 'Create alert definition';
      idInput.value = '';
      idInput.readOnly = false;
      nameInput.value = '';
      descriptionInput.value = '';
      enabledInput.checked = true;
      populateLogicTypes();
      deleteButton.hidden = true;
    }

    renderDefinitionList();
    updateLogicPreview();
  };

  const buildPayload = () => {
    const id = idInput.value.trim();
    const name = nameInput.value.trim();
    const logicType = logicTypeSelect.value;
    if (!id || !name || !logicType) {
      throw new Error('Identifier, name, and logic type are required.');
    }
    const description = descriptionInput.value.trim();
    const parameters = mergeWithDefaults(logicType, collectParameterValues({ includeEmpty: true }));
    return {
      id,
      name,
      description,
      enabled: enabledInput.checked,
      logic: {
        type: logicType,
        parameters,
      },
    };
  };

  const fetchDefinitions = async () => {
    if (!listElement) return;
    try {
      const response = await fetch('/alert-definitions');
      if (!response.ok) {
        throw new Error('Unable to load alert definitions');
      }
      const payload = await response.json();
      state.definitions = payload.definitions || [];
      state.blueprints = payload.blueprints || {};
      populateLogicTypes();
      renderDefinitionList();
      if (state.selectedId) {
        setFormMode('edit', state.selectedId);
      } else {
        updateLogicPreview();
      }
    } catch (error) {
      showFeedback(error.message || 'Failed to load alert definitions', true);
    }
  };

  const submitDefinition = async (event) => {
    if (!form) return;
    event.preventDefault();
    try {
      const payload = buildPayload();
      const isEdit = Boolean(state.selectedId);
      const endpoint = isEdit ? `/alert-definitions/${encodeURIComponent(state.selectedId)}` : '/alert-definitions';
      const method = isEdit ? 'PUT' : 'POST';
      const response = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        const message = errorPayload.description || errorPayload.message || 'Unable to save alert definition';
        throw new Error(message);
      }
      await fetchDefinitions();
      setFormMode('edit', payload.id);
      showFeedback('Alert definition saved');
    } catch (error) {
      showFeedback(error.message || 'Unable to save alert definition', true);
    }
  };

  const deleteDefinition = async () => {
    if (!state.selectedId) return;
    const confirmation = window.confirm('Delete this alert definition? This action cannot be undone.');
    if (!confirmation) {
      return;
    }
    try {
      const response = await fetch(`/alert-definitions/${encodeURIComponent(state.selectedId)}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        const message = errorPayload.description || errorPayload.message || 'Unable to delete alert definition';
        throw new Error(message);
      }
      state.selectedId = null;
      await fetchDefinitions();
      setFormMode('create');
      showFeedback('Alert definition deleted');
    } catch (error) {
      showFeedback(error.message || 'Unable to delete alert definition', true);
    }
  };

  const attachEventListeners = () => {
    if (logicTypeSelect) {
      logicTypeSelect.addEventListener('change', () => {
        renderParameterFields(logicTypeSelect.value);
      });
    }

    if (form) {
      form.addEventListener('submit', submitDefinition);
    }

    if (newButton) {
      newButton.addEventListener('click', (event) => {
        event.preventDefault();
        setFormMode('create');
      });
    }

    if (deleteButton) {
      deleteButton.addEventListener('click', (event) => {
        event.preventDefault();
        deleteDefinition();
      });
    }
  };

  const init = () => {
    if (!listElement || !form) {
      return;
    }
    attachEventListeners();
    fetchDefinitions();
  };

  init();

  return {
    refresh: fetchDefinitions,
  };
})();

window.AlertConfigModule = AlertConfigModule;
