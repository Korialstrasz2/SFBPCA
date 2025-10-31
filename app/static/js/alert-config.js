const AlertConfigModule = (() => {
  const listElement = document.getElementById('alert-definition-list');
  const addButton = document.getElementById('add-alert-definition');
  const form = document.getElementById('alert-definition-editor');
  const idInput = document.getElementById('alert-definition-id');
  const labelInput = document.getElementById('alert-definition-label');
  const descriptionInput = document.getElementById('alert-definition-description');
  const logicInput = document.getElementById('alert-definition-logic');
  const feedback = document.getElementById('alert-definition-feedback');
  const deleteButton = document.getElementById('delete-alert-definition');

  let definitions = [];
  let activeId = null;

  const defaultLogicTemplate = [
    'def run(data_store, helpers, definition):',
    '    """Return a list of alerts."""',
    '    alerts = []',
    '    return alerts',
  ].join('\n');

  const showFeedback = (message, isError = false) => {
    if (!feedback) return;
    feedback.textContent = message;
    feedback.classList.toggle('error', isError);
    if (message) {
      feedback.classList.add('visible');
    } else {
      feedback.classList.remove('visible');
    }
  };

  const renderEmptyListState = () => {
    if (!listElement) return;
    const emptyItem = document.createElement('li');
    emptyItem.textContent = 'No alerts configured yet. Add one to get started.';
    emptyItem.classList.add('alert-definition-empty');
    listElement.innerHTML = '';
    listElement.appendChild(emptyItem);
    if (form) {
      form.setAttribute('hidden', '');
    }
  };

  const renderList = () => {
    if (!listElement) return;
    if (!definitions.length) {
      renderEmptyListState();
      return;
    }

    const fragment = document.createDocumentFragment();
    definitions.forEach((definition) => {
      const item = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = definition.label || definition.id;
      if (definition.id === activeId) {
        button.classList.add('active');
      }
      button.addEventListener('click', () => {
        selectDefinition(definition.id);
      });
      item.appendChild(button);
      fragment.appendChild(item);
    });

    listElement.innerHTML = '';
    listElement.appendChild(fragment);
  };

  const populateForm = (definition) => {
    if (!form) return;
    form.removeAttribute('hidden');
    idInput.value = definition.id;
    labelInput.value = definition.label || '';
    descriptionInput.value = definition.description || '';
    logicInput.value = definition.logic || defaultLogicTemplate;
  };

  const selectDefinition = (id) => {
    activeId = id;
    const definition = definitions.find((entry) => entry.id === id);
    renderList();
    if (definition) {
      populateForm(definition);
    } else if (form) {
      form.setAttribute('hidden', '');
    }
  };

  const generateId = () => `custom_${Date.now()}`;

  const addDefinition = () => {
    const newDefinition = {
      id: generateId(),
      label: 'New alert',
      description: '',
      logic: defaultLogicTemplate,
    };
    definitions.push(newDefinition);
    selectDefinition(newDefinition.id);
    showFeedback('New alert created. Remember to save your changes.');
  };

  const persistDefinitions = async (successMessage) => {
    try {
      const response = await fetch('/alert-definitions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alerts: definitions }),
      });
      const payload = await response.json();
      if (!response.ok) {
        const errorMessage = payload && payload.error ? payload.error : 'Failed to save alert definitions';
        throw new Error(errorMessage);
      }
      definitions = Array.isArray(payload.alerts) ? payload.alerts : [];
      renderList();
      if (activeId && !definitions.some((entry) => entry.id === activeId)) {
        activeId = definitions.length ? definitions[0].id : null;
      }
      if (activeId) {
        selectDefinition(activeId);
      } else if (form) {
        form.setAttribute('hidden', '');
      }
      showFeedback(successMessage || 'Alert definitions saved');
      document.dispatchEvent(new CustomEvent('alerts:refresh'));
    } catch (error) {
      showFeedback(error.message || 'Failed to save alert definitions', true);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form) return;

    const id = idInput.value || generateId();
    const label = labelInput.value.trim();
    if (!label) {
      showFeedback('Alert label is required.', true);
      labelInput.focus();
      return;
    }
    const logic = logicInput.value.trim();
    if (!logic) {
      showFeedback('Alert logic cannot be empty.', true);
      logicInput.focus();
      return;
    }

    let definition = definitions.find((entry) => entry.id === id);
    if (!definition) {
      definition = { id };
      definitions.push(definition);
    }
    definition.label = label;
    definition.description = descriptionInput.value.trim();
    definition.logic = logic;
    activeId = id;

    await persistDefinitions('Alert saved successfully.');
  };

  const handleDelete = async () => {
    if (!activeId) {
      showFeedback('Select an alert to delete first.', true);
      return;
    }
    const definition = definitions.find((entry) => entry.id === activeId);
    const label = definition ? definition.label || definition.id : activeId;
    if (!window.confirm(`Delete alert "${label}"? This cannot be undone.`)) {
      return;
    }
    definitions = definitions.filter((entry) => entry.id !== activeId);
    activeId = definitions.length ? definitions[0].id : null;
    await persistDefinitions('Alert deleted.');
  };

  const fetchDefinitions = async () => {
    if (!listElement) return;
    try {
      const response = await fetch('/alert-definitions');
      if (!response.ok) {
        throw new Error('Unable to load alert definitions');
      }
      const payload = await response.json();
      definitions = Array.isArray(payload.alerts) ? payload.alerts : [];
      if (definitions.length) {
        activeId = definitions[0].id;
        renderList();
        selectDefinition(activeId);
        showFeedback('Loaded alert definitions.');
      } else {
        renderList();
        showFeedback('No alerts defined yet. Create one to begin.');
      }
    } catch (error) {
      renderEmptyListState();
      showFeedback(error.message || 'Failed to load alert definitions', true);
    }
  };

  if (form) {
    form.addEventListener('submit', handleSubmit);
  }
  if (addButton) {
    addButton.addEventListener('click', addDefinition);
  }
  if (deleteButton) {
    deleteButton.addEventListener('click', handleDelete);
  }

  fetchDefinitions();

  return {
    fetchDefinitions,
  };
})();

window.AlertConfigModule = AlertConfigModule;
