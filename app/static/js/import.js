const ImportModule = (() => {
  const form = document.getElementById('import-form');
  const feedback = document.getElementById('import-feedback');
  const stepButtons = document.querySelectorAll('.step-button');
  const panels = document.querySelectorAll('.panel');
  const bulkTrigger = document.getElementById('bulk-file-trigger');
  const bulkInput = document.getElementById('bulk-file-input');
  const matchModal = document.getElementById('bulk-match-modal');
  const matchSummary = document.getElementById('bulk-match-summary');
  const assignedGroup = document.getElementById('bulk-match-assigned-group');
  const assignedList = document.getElementById('bulk-match-assigned');
  const unmatchedGroup = document.getElementById('bulk-match-unmatched-group');
  const unmatchedList = document.getElementById('bulk-match-unmatched');
  const modalCloseButton = document.getElementById('bulk-match-close');

  const appConfig = window.APP_CONFIG || {};
  const entityFields = appConfig.entityFields || {};
  const normalizedEntityFields = Object.fromEntries(
    Object.entries(entityFields).map(([key, fields]) => [
      key,
      Array.isArray(fields) ? fields.map((field) => field.toLowerCase()) : [],
    ])
  );

  const entityInputs = new Map();
  if (form) {
    form.querySelectorAll('.file-input input[type="file"]').forEach((input) => {
      const container = input.closest('.file-input');
      const labelText = container?.querySelector('.label-text')?.textContent?.trim();
      entityInputs.set(input.name, {
        input,
        label: labelText || input.name.replaceAll('_', ' '),
      });
    });
  }

  const getEntityLabel = (entity) => entityInputs.get(entity)?.label || entity.replaceAll('_', ' ');

  const splitWithDelimiter = (line, delimiter) => {
    const fields = [];
    let current = '';
    let insideQuotes = false;
    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      if (char === '"') {
        if (insideQuotes && line[index + 1] === '"') {
          current += '"';
          index += 1;
        } else {
          insideQuotes = !insideQuotes;
        }
      } else if (!insideQuotes && char === delimiter) {
        fields.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    fields.push(current.trim());
    return fields
      .map((field) => field.replace(/^"|"$/g, '').trim())
      .filter((field) => field.length > 0);
  };

  const detectDelimiter = (line) => {
    const candidates = [',', ';', '\t', '|'];
    let bestDelimiter = candidates[0];
    let bestScore = -1;
    candidates.forEach((delimiter) => {
      const parts = splitWithDelimiter(line, delimiter);
      if (parts.length > bestScore) {
        bestScore = parts.length;
        bestDelimiter = delimiter;
      }
    });
    return bestDelimiter;
  };

  const parseHeaders = (text) => {
    if (!text) return [];
    const firstLine = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find((line) => line.length > 0);
    if (!firstLine) return [];
    const delimiter = detectDelimiter(firstLine);
    return splitWithDelimiter(firstLine, delimiter);
  };

  const readFilePreview = (file) =>
    new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => {
        resolve(typeof reader.result === 'string' ? reader.result : '');
      };
      reader.onerror = () => resolve('');
      reader.readAsText(file.slice(0, 4096));
    });

  const matchHeadersToEntity = (headers) => {
    if (!headers || headers.length === 0) {
      return null;
    }
    const normalizedHeaders = new Set(headers.map((header) => header.toLowerCase()));
    let bestMatch = null;
    let bestScore = 0;
    Object.entries(normalizedEntityFields).forEach(([entity, fields]) => {
      if (!fields.length) {
        return;
      }
      const score = fields.reduce(
        (total, field) => (normalizedHeaders.has(field) ? total + 1 : total),
        0
      );
      if (score === fields.length && score >= bestScore) {
        bestMatch = entity;
        bestScore = score;
      }
    });
    return bestMatch;
  };

  const describeHeaders = (headers) => {
    if (!headers || headers.length === 0) {
      return 'Intestazioni non disponibili';
    }
    const preview = headers.slice(0, 5).join(', ');
    return headers.length > 5 ? `${preview}…` : preview;
  };

  let lastFocusedElement = null;

  const closeMatchModal = () => {
    if (!matchModal) {
      return;
    }
    matchModal.setAttribute('hidden', '');
    if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
      lastFocusedElement.focus();
    }
  };

  const openMatchModal = (matches, unmatched, totalFiles) => {
    if (!matchModal) {
      return;
    }
    const assignedCount = matches.length;
    const unmatchedCount = unmatched.length;
    if (matchSummary) {
      const parts = [`Abbiamo associato ${assignedCount} file su ${totalFiles}.`];
      if (unmatchedCount > 0) {
        parts.push(`${unmatchedCount} file richiedono una verifica manuale.`);
      }
      matchSummary.textContent = parts.join(' ');
    }

    if (assignedGroup && assignedList) {
      assignedGroup.hidden = assignedCount === 0;
      assignedList.innerHTML = '';
      matches.forEach(({ entity, file }) => {
        const item = document.createElement('li');
        const entityName = document.createElement('strong');
        entityName.textContent = getEntityLabel(entity);
        const fileName = document.createElement('span');
        fileName.textContent = file.name;
        item.append(entityName, fileName);
        assignedList.appendChild(item);
      });
    }

    if (unmatchedGroup && unmatchedList) {
      unmatchedGroup.hidden = unmatchedCount === 0;
      unmatchedList.innerHTML = '';
      unmatched.forEach((detail) => {
        const item = document.createElement('li');
        const fileName = document.createElement('strong');
        fileName.textContent = detail.file.name;
        const description = document.createElement('span');
        if (detail.reason === 'duplicate') {
          description.textContent = `Duplicato per ${getEntityLabel(
            detail.entity
          )} (già associato a ${detail.existingFileName})`;
        } else if (detail.reason === 'no-headers') {
          description.textContent = 'Intestazioni non trovate nel file';
        } else {
          description.textContent = `Formato non riconosciuto (campi: ${describeHeaders(
            detail.headers
          )})`;
        }
        item.append(fileName, description);
        unmatchedList.appendChild(item);
      });
    }

    lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    matchModal.removeAttribute('hidden');
    if (modalCloseButton) {
      modalCloseButton.focus();
    }
  };

  const setActiveStep = (targetId) => {
    stepButtons.forEach((button) => {
      const isActive = button.dataset.target === targetId;
      button.classList.toggle('active', isActive);
    });
    panels.forEach((panel) => {
      const isActive = panel.id === targetId;
      panel.classList.toggle('active', isActive);
    });
  };

  stepButtons.forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      setActiveStep(button.dataset.target);
    });
  });

  const renderFeedback = (message, isError = false, summary = {}) => {
    if (!feedback) return;
    feedback.textContent = message;
    if (Object.keys(summary).length > 0) {
      const details = Object.entries(summary)
        .map(([key, count]) => `${key.replaceAll('_', ' ')}: ${count}`)
        .join(' | ');
      feedback.textContent = `${message}. Imported => ${details}`;
    }
    feedback.classList.toggle('error', isError);
    feedback.classList.add('visible');
  };

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        const response = await fetch('/import', {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) {
          throw new Error(`Import failed with status ${response.status}`);
        }
        const payload = await response.json();
        renderFeedback('Import successful', false, payload.summary || {});
        document.dispatchEvent(new CustomEvent('alerts:refresh'));
        setActiveStep('alerts-step');
      } catch (error) {
        renderFeedback(error.message || 'Import failed', true);
      }
    });

    form.addEventListener('reset', () => {
      if (bulkInput) {
        bulkInput.value = '';
      }
    });
  }

  if (bulkTrigger && bulkInput) {
    bulkTrigger.addEventListener('click', () => {
      bulkInput.click();
    });

    bulkInput.addEventListener('change', async () => {
      const files = Array.from(bulkInput.files || []);
      if (files.length === 0) {
        return;
      }

      const matches = [];
      const unmatched = [];
      const assignments = new Map();

      for (const file of files) {
        // eslint-disable-next-line no-await-in-loop
        const preview = await readFilePreview(file);
        const headers = parseHeaders(preview);
        if (!headers.length) {
          unmatched.push({ file, reason: 'no-headers' });
          continue;
        }
        const entity = matchHeadersToEntity(headers);
        if (entity) {
          if (!assignments.has(entity)) {
            assignments.set(entity, { file, headers });
            matches.push({ entity, file });
          } else {
            const existing = assignments.get(entity);
            unmatched.push({
              file,
              reason: 'duplicate',
              entity,
              existingFileName: existing.file.name,
            });
          }
        } else {
          unmatched.push({ file, reason: 'no-match', headers });
        }
      }

      entityInputs.forEach(({ input }) => {
        // Clear previous selections to avoid mixing legacy and automatic uploads.
        input.value = '';
      });

      assignments.forEach(({ file }, entity) => {
        const config = entityInputs.get(entity);
        if (!config) {
          return;
        }
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        config.input.files = dataTransfer.files;
        config.input.dispatchEvent(new Event('change', { bubbles: true }));
      });

      openMatchModal(matches, unmatched, files.length);
      bulkInput.value = '';
    });
  }

  if (modalCloseButton) {
    modalCloseButton.addEventListener('click', closeMatchModal);
  }

  if (matchModal) {
    matchModal.addEventListener('click', (event) => {
      if (event.target === matchModal) {
        closeMatchModal();
      }
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && matchModal && !matchModal.hasAttribute('hidden')) {
      closeMatchModal();
    }
  });

  return {
    setActiveStep,
  };
})();

window.ImportModule = ImportModule;
