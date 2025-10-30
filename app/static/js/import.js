const ImportModule = (() => {
  const form = document.getElementById('import-form');
  const feedback = document.getElementById('import-feedback');
  const stepButtons = document.querySelectorAll('.step-button');
  const panels = document.querySelectorAll('.panel');

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
  }

  return {
    setActiveStep,
  };
})();

window.ImportModule = ImportModule;
