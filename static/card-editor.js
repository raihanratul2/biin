(() => {
    const preview = document.getElementById('card-preview');
    if (!preview) return;

    const svg = preview.querySelector('svg');
    const photo = svg.querySelector('#ambassador-photo');
    const form = document.getElementById('card-position-form');
    const controls = document.getElementById('card-position-controls');
    const save = document.getElementById('card-save');
    const download = document.getElementById('card-download');
    const status = document.getElementById('card-save-status');
    const inputs = {
        x: document.getElementById('card-photo-x'),
        y: document.getElementById('card-photo-y'),
        scale: document.getElementById('card-photo-scale'),
    };
    let saved = JSON.parse(document.getElementById('card-position').textContent);
    let position = { ...saved };
    let drag = null;
    let saving = false;
    const hasPhoto = photo.hasAttribute('href') || photo.hasAttributeNS('http://www.w3.org/1999/xlink', 'href');
    const dirty = () => Object.keys(position).some(key => position[key] !== saved[key]);
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    const frame = {
        x: Number(photo.getAttribute('width')),
        y: Number(photo.getAttribute('height')),
    };

    function constrainPosition() {
        position.scale = clamp(position.scale, Number(inputs.scale.min), Number(inputs.scale.max));
        for (const axis of ['x', 'y']) {
            // Only the extra space created by zooming is available for movement.
            const limit = Math.floor(frame[axis] * (position.scale - 1) / 2 * 10 + 1e-9) / 10;
            inputs[axis].min = -limit;
            inputs[axis].max = limit;
            position[axis] = clamp(position[axis], -limit, limit);
        }
    }

    function render(message) {
        constrainPosition();
        photo.setAttribute('transform',
            `translate(${position.x} ${position.y}) translate(760.62 587.4) scale(${position.scale}) translate(-760.62 -587.4)`);
        for (const key of Object.keys(inputs)) inputs[key].value = position[key];
        document.getElementById('card-scale-value').textContent = `${Math.round(position.scale * 100)}%`;
        document.getElementById('card-x-value').textContent = Math.round(position.x);
        document.getElementById('card-y-value').textContent = Math.round(position.y);
        save.disabled = !hasPhoto || !dirty() || saving;
        download.setAttribute('aria-disabled', String(dirty() || saving));
        download.tabIndex = dirty() || saving ? -1 : 0;
        status.classList.remove('is-error');
        status.textContent = message || (dirty() ? 'Unsaved changes — save before downloading.' : 'Saved position');
    }

    function svgPoint(event) {
        const point = svg.createSVGPoint();
        point.x = event.clientX;
        point.y = event.clientY;
        return point.matrixTransform(svg.getScreenCTM().inverse());
    }

    svg.addEventListener('pointerdown', event => {
        if (!hasPhoto || saving || event.button !== 0 || !event.isPrimary || drag) return;
        if (!event.target.closest('#ambassador-portrait')) return;
        const point = svgPoint(event);
        drag = { id: event.pointerId, start: point, x: position.x, y: position.y };
        svg.setPointerCapture(event.pointerId);
        preview.classList.add('is-dragging');
        event.preventDefault();
    });

    svg.addEventListener('pointermove', event => {
        if (!drag || saving || event.pointerId !== drag.id) return;
        const point = svgPoint(event);
        position.x = Math.round((drag.x + point.x - drag.start.x) * 10) / 10;
        position.y = Math.round((drag.y + point.y - drag.start.y) * 10) / 10;
        render();
    });

    function endDrag(event) {
        if (!drag || event.pointerId !== drag.id) return;
        drag = null;
        preview.classList.remove('is-dragging');
    }
    svg.addEventListener('pointerup', endDrag);
    svg.addEventListener('pointercancel', endDrag);
    svg.addEventListener('lostpointercapture', endDrag);

    for (const [key, input] of Object.entries(inputs)) {
        input.addEventListener('input', () => {
            position[key] = Number(input.value);
            render();
        });
    }
    document.getElementById('card-reset').addEventListener('click', () => {
        position = { x: 0, y: 0, scale: 1 };
        render();
    });

    download.addEventListener('click', event => {
        if (dirty() || saving) event.preventDefault();
    });
    window.addEventListener('beforeunload', event => {
        if (dirty()) {
            event.preventDefault();
            event.returnValue = '';
        }
    });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (saving || !hasPhoto || !dirty()) return;
        // Capture values before disabling the controls during the request.
        const body = new FormData(form);
        saving = true;
        controls.disabled = true;
        render('Saving position…');
        try {
            const response = await fetch(form.action, {
                method: 'POST', body, credentials: 'same-origin',
                headers: { 'Accept': 'application/json' },
            });
            const result = await response.json();
            if (!response.ok || result.saved !== true) throw new Error('Save failed');
            saved = { ...result.position };
            position = { ...saved };
            render('Position saved');
        } catch {
            status.textContent = 'Could not save the position. Please try again.';
            status.classList.add('is-error');
        } finally {
            saving = false;
            controls.disabled = !hasPhoto;
            save.disabled = !hasPhoto || !dirty();
            download.setAttribute('aria-disabled', String(dirty()));
            download.tabIndex = dirty() ? -1 : 0;
        }
    });

    controls.disabled = !hasPhoto;
    render(hasPhoto ? undefined : 'No photo available for this applicant.');
})();
