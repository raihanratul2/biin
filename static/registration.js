(() => {
    const form = document.getElementById('ambassador-form');
    if (!form) return;

    const steps = [...form.querySelectorAll('.registration-step')];
    const stepButtons = [...form.querySelectorAll('.step-button')];
    const previous = document.getElementById('previous-step');
    const next = document.getElementById('next-step');
    const submit = document.getElementById('submit-registration');
    const status = document.getElementById('step-status');
    const review = document.getElementById('application-review');
    const hint = document.getElementById('action-hint');
    let current = 0;
    let furthest = 0;

    function buildReview() {
        review.replaceChildren();
        steps.slice(0, -1).forEach((step, index) => {
            const section = document.createElement('div');
            section.className = 'review-section';
            const heading = document.createElement('div');
            heading.className = 'review-heading';
            const title = document.createElement('h3');
            title.textContent = step.querySelector('h2').textContent;
            const edit = document.createElement('button');
            edit.type = 'button';
            edit.textContent = 'Edit';
            edit.setAttribute('aria-label', `Edit ${title.textContent}`);
            edit.addEventListener('click', () => showStep(index));
            heading.append(title, edit);
            const list = document.createElement('dl');
            step.querySelectorAll('.field').forEach(field => {
                const controls = [...field.querySelectorAll('input, select, textarea')];
                const label = field.querySelector('legend, label');
                if (!label || !controls.length) return;
                const term = document.createElement('dt');
                term.textContent = label.textContent;
                const detail = document.createElement('dd');
                detail.textContent = controls.filter(control => control.type !== 'checkbox' || control.checked)
                    .map(control => control.tagName === 'SELECT' ? control.selectedOptions[0]?.textContent : control.value)
                    .filter(Boolean).join(', ') || 'Not provided';
                list.append(term, detail);
            });
            section.append(heading, list);
            review.append(section);
        });
        review.hidden = false;
    }

    function showStep(index, focus = true) {
        current = index;
        furthest = Math.max(furthest, index);
        steps.forEach((step, i) => { step.hidden = i !== index; });
        stepButtons.forEach((button, i) => {
            button.disabled = i > furthest;
            button.parentElement.classList.toggle('is-complete', i < index);
            button.querySelector('.step-number').textContent = i < index ? '✓' : i + 1;
            if (i === index) button.setAttribute('aria-current', 'step');
            else button.removeAttribute('aria-current');
        });
        previous.hidden = index === 0;
        next.hidden = index === steps.length - 1;
        submit.hidden = index !== steps.length - 1;
        hint.hidden = index !== 0;
        status.textContent = `STEP ${index + 1} OF ${steps.length}`;
        if (index === steps.length - 1) buildReview();
        if (focus) steps[index].querySelector('h2').focus();
    }

    function validateStep(index) {
        const invalid = [...steps[index].querySelectorAll('input, select, textarea')]
            .find(control => !control.checkValidity());
        if (!invalid) return true;
        if (current !== index) showStep(index, false);
        invalid.reportValidity();
        invalid.focus();
        return false;
    }

    function goForward(target) {
        for (let i = 0; i < target; i++) {
            if (!validateStep(i)) return;
        }
        showStep(target);
    }

    previous.addEventListener('click', () => showStep(current - 1));
    next.addEventListener('click', () => goForward(current + 1));
    stepButtons.forEach((button, index) => button.addEventListener('click', () => {
        if (index > current) goForward(index);
        else showStep(index);
    }));
    form.addEventListener('submit', event => {
        if (current < steps.length - 1) {
            event.preventDefault();
            goForward(current + 1);
            return;
        }
        for (let i = 0; i < steps.length; i++) {
            if (!validateStep(i)) {
                event.preventDefault();
                return;
            }
        }
        submit.disabled = true;
        submit.textContent = 'Submitting…';
    });

    // Keep the full form usable when JavaScript is unavailable. Validation is
    // handled here only after initialization, so hidden fields can be revealed.
    form.noValidate = true;
    form.classList.add('wizard-ready');
    form.querySelector('.registration-progress').hidden = false;
    const firstError = steps.findIndex(step => step.querySelector('.field-error'));
    showStep(firstError < 0 ? 0 : firstError, firstError >= 0);
})();
