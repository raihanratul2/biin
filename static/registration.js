(() => {
    const form = document.getElementById('ambassador-form');
    if (!form) return;

    const phone = form.querySelector('[name="phone_number"]');
    if (phone) {
        const limit = phone.maxLength;
        const saved = phone.value.replace(/[^0-9]/g, '');
        const group = document.createElement('div');
        group.className = 'phone-input-group';
        const code = document.createElement('input');
        code.type = 'text';
        code.id = 'phone-country-code';
        code.value = '+880';
        code.defaultValue = '+880';
        code.maxLength = 4;
        code.required = true;
        code.pattern = '\\+?[1-9][0-9]{0,2}';
        code.inputMode = 'tel';
        code.autocomplete = 'tel-country-code';
        code.setAttribute('aria-label', 'Country code');
        const number = document.createElement('input');
        number.type = 'text';
        number.id = 'phone-local-number';
        number.required = phone.required;
        number.inputMode = 'numeric';
        number.autocomplete = 'tel-national';
        number.pattern = '[0-9]+';
        number.placeholder = 'Phone number';
        number.value = saved.startsWith('880') ? saved.slice(3) : saved;
        number.defaultValue = number.value;
        number.setAttribute('aria-label', 'Phone number');
        const label = form.querySelector(`label[for="${phone.id}"]`);
        if (label) label.htmlFor = number.id;
        phone.type = 'hidden';
        phone.after(group);
        group.append(code, number);
        const counter = document.getElementById(`${phone.id}_count`);
        if (counter) {
            code.setAttribute('aria-describedby', counter.id);
            number.setAttribute('aria-describedby', counter.id);
        }
        function syncPhone() {
            const digits = code.value.replace(/[^0-9]/g, '').slice(0, 3);
            code.value = (code.value.startsWith('+') ? '+' : '') + digits;
            number.maxLength = Math.max(0, limit - digits.length);
            number.value = number.value.replace(/[^0-9]/g, '').slice(0, number.maxLength);
            phone.value = number.value ? digits + number.value : '';
            phone.dispatchEvent(new Event('input', { bubbles: true }));
        }
        code.addEventListener('input', syncPhone);
        number.addEventListener('input', syncPhone);
        code.addEventListener('change', syncPhone);
        number.addEventListener('change', syncPhone);
        form.addEventListener('reset', () => setTimeout(syncPhone, 0));
        form.addEventListener('submit', syncPhone);
        syncPhone();
    }

    form.querySelectorAll('[data-character-count]').forEach(counter => {
        const control = document.getElementById(counter.dataset.characterCount);
        if (!control) return;
        const describedBy = new Set((control.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
        describedBy.add(counter.id);
        control.setAttribute('aria-describedby', [...describedBy].join(' '));
        const updateCount = () => {
            const count = Array.from(control.value).length;
            counter.hidden = count === 0;
            counter.textContent = count ? `${count}/${control.maxLength}` : '';
        };
        control.addEventListener('input', updateCount);
        control.addEventListener('change', updateCount);
        form.addEventListener('reset', () => setTimeout(updateCount, 0));
        updateCount();
    });

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
                detail.textContent = field.contains(phone) ? phone.value || 'Not provided' : controls.filter(control => control.type !== 'checkbox' || control.checked)
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
