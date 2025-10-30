const AlertConfigModule = (() => {
  const list = document.getElementById('alert-config-list');
  const form = document.getElementById('alert-config-form');
  const feedback = document.getElementById('alert-config-feedback');
  const resetButton = document.getElementById('reset-alert-config');

  const setStatusText = (input, statusElement, toggleText) => {
    const enabled = Boolean(input?.checked);
    const statusLabel = enabled ? 'Enabled' : 'Disabled';
    if (statusElement) {
      statusElement.textContent = statusLabel;
      statusElement.dataset.status = enabled ? 'enabled' : 'disabled';
    }
    if (toggleText) {
      toggleText.textContent = statusLabel;
    }
  };

  const clearFeedback = () => {
    if (!feedback) return;
    feedback.textContent = '';
    feedback.classList.remove('error');
    feedback.classList.remove('visible');
  };

  const showFeedback = (message, isError = false) => {
    if (!feedback) return;
    feedback.textContent = message;
    feedback.classList.toggle('error', Boolean(isError));
    feedback.classList.add('visible');
  };

  const renderRules = (rules) => {
    const safeRules = Array.isArray(rules) ? rules : [];
    if (!list) return;

    list.innerHTML = '';

    if (safeRules.length === 0) {
      const emptyState = document.createElement('p');
      emptyState.className = 'alert-config-empty';
      emptyState.textContent = 'No alert rules are currently available.';
      emptyState.setAttribute('role', 'note');
      list.appendChild(emptyState);
      return;
    }

    const fragment = document.createDocumentFragment();

    safeRules.forEach((rule) => {
      const item = document.createElement('article');
      item.className = 'alert-config-item';
      item.setAttribute('role', 'listitem');

      const header = document.createElement('div');
      header.className = 'alert-config-header';

      const title = document.createElement('h3');
      title.className = 'alert-config-title';
      title.textContent = rule.label;

      const status = document.createElement('span');
      status.className = 'alert-config-status';

      const toggleWrapper = document.createElement('div');
      toggleWrapper.className = 'alert-config-toggle-wrapper';

      const inputId = `alert-rule-${rule.id}`;
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.id = inputId;
      input.className = 'alert-config-checkbox';
      input.dataset.ruleId = rule.id;
      input.dataset.defaultEnabled = String(Boolean(rule.default_enabled));
      input.checked = Boolean(rule.enabled);

      const toggleLabel = document.createElement('label');
      toggleLabel.className = 'alert-config-toggle';
      toggleLabel.setAttribute('for', inputId);

      const toggleIndicator = document.createElement('span');
      toggleIndicator.className = 'alert-config-toggle-indicator';
      toggleIndicator.setAttribute('aria-hidden', 'true');

      const toggleText = document.createElement('span');
      toggleText.className = 'alert-config-toggle-text';

      toggleLabel.appendChild(toggleIndicator);
      toggleLabel.appendChild(toggleText);

      toggleWrapper.appendChild(input);
      toggleWrapper.appendChild(toggleLabel);

      input.addEventListener('change', () => {
        setStatusText(input, status, toggleText);
        clearFeedback();
      });

      const description = document.createElement('p');
      description.className = 'alert-config-description';
      description.textContent = rule.description;
      description.id = `${inputId}-description`;

      title.id = `${inputId}-label`;
      input.setAttribute('aria-labelledby', title.id);
      input.setAttribute('aria-describedby', description.id);

      header.appendChild(title);
      header.appendChild(status);
      header.appendChild(toggleWrapper);

      item.appendChild(header);
      item.appendChild(description);

      setStatusText(input, status, toggleText);

      fragment.appendChild(item);
    });

    list.appendChild(fragment);
  };

  const gatherRuleUpdates = () => {
    if (!form) return [];
    const inputs = form.querySelectorAll('input.alert-config-checkbox[data-rule-id]');
    return Array.from(inputs).map((input) => ({
      id: input.dataset.ruleId,
      enabled: Boolean(input.checked),
    }));
  };

  const fetchConfiguration = async () => {
    if (!list) return;
    try {
      const response = await fetch('/alerts/config');
      if (!response.ok) {
        throw new Error('Failed to load alert configuration.');
      }
      const payload = await response.json();
      renderRules(payload.rules || []);
      clearFeedback();
    } catch (error) {
      list.innerHTML = '';
      const errorMessage = document.createElement('p');
      errorMessage.className = 'alert-config-error';
      errorMessage.textContent = error.message;
      list.appendChild(errorMessage);
      showFeedback(error.message, true);
    }
  };

  const submitConfiguration = async () => {
    const rules = gatherRuleUpdates();
    try {
      const response = await fetch('/alerts/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || 'Failed to update alert configuration.');
      }
      const payload = await response.json();
      renderRules(payload.rules || []);
      showFeedback('Alert configuration saved.', false);
      document.dispatchEvent(new CustomEvent('alerts:refresh'));
    } catch (error) {
      showFeedback(error.message, true);
    }
  };

  const resetConfiguration = async () => {
    try {
      const response = await fetch('/alerts/config/reset', { method: 'POST' });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || 'Failed to reset alert configuration.');
      }
      const payload = await response.json();
      renderRules(payload.rules || []);
      showFeedback('Alert configuration reset to defaults.', false);
      document.dispatchEvent(new CustomEvent('alerts:refresh'));
    } catch (error) {
      showFeedback(error.message, true);
    }
  };

  if (form) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      submitConfiguration();
    });
  }

  if (resetButton) {
    resetButton.addEventListener('click', (event) => {
      event.preventDefault();
      resetConfiguration();
    });
  }

  fetchConfiguration();

  return {
    fetchConfiguration,
    renderRules,
  };
})();

window.AlertConfigModule = AlertConfigModule;
