(() => {
    const input = document.getElementById('id_picture');
    const canvas = document.getElementById('picture-canvas');
    if (!input || !canvas || !window.DataTransfer || !canvas.toBlob) return;
    const context = canvas.getContext('2d');
    if (!context) return;
    const editor = document.getElementById('picture-editor');
    const preview = document.getElementById('picture-preview');
    const status = document.getElementById('picture-status');
    const placeholder = document.getElementById('picture-placeholder');
    const action = document.getElementById('picture-action');
    const zoom = document.getElementById('picture-zoom');
    const x = document.getElementById('picture-x');
    const y = document.getElementById('picture-y');
    const apply = document.getElementById('picture-apply');
    let image = null;
    let revision = 0;
    let previewURL = null;
    let drag = null;
    let confirmedFile = null;
    const cropStatus = document.getElementById('picture-crop-status');
    function setStatus(message) {
        status.textContent = message;
        cropStatus.textContent = message;
    }
    function restoreConfirmedPhoto() {
        const transfer = new DataTransfer();
        if (confirmedFile) transfer.items.add(confirmedFile);
        input.files = transfer.files;
        input.setCustomValidity('');
        preview.hidden = !confirmedFile;
        placeholder.hidden = Boolean(confirmedFile);
        action.textContent = confirmedFile ? 'Change photo' : '+ Add photo';
        if (confirmedFile) preview.src = previewURL;
        setStatus(confirmedFile ? `Photo ready · ${Math.ceil(confirmedFile.size / 1024)} KB.` : 'Tap the photo box to upload.');
    }
    document.getElementById('picture-cancel').addEventListener('click', () => editor.close());
    editor.addEventListener('close', () => {
        revision++;
        drag = null;
        restoreConfirmedPhoto();
        document.body.classList.remove('photo-crop-open');
        input.focus();
    });

    function crop() {
        const scale = Math.max(canvas.width / image.width, canvas.height / image.height) * Number(zoom.value);
        const width = canvas.width / scale;
        const height = canvas.height / scale;
        return { width, height, left: (image.width - width) * Number(x.value), top: (image.height - height) * Number(y.value) };
    }
    function draw() {
        if (!image) return;
        const box = crop();
        context.fillStyle = '#fff';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, box.left, box.top, box.width, box.height, 0, 0, canvas.width, canvas.height);
    }
    function changed() {
        revision++;
        input.setCustomValidity('Choose “Use this crop” to confirm your photograph.');
        setStatus('Adjust your photo, then choose “Use this crop”.');
        draw();
    }
    function reset() {
        zoom.value = '1';
        x.value = y.value = '0.5';
        changed();
    }
    input.addEventListener('change', async () => {
        const current = ++revision;
        const file = input.files[0];
        image = null;

        input.setCustomValidity('');
        if (!file) { restoreConfirmedPhoto(); return; }
        const reject = message => {
            restoreConfirmedPhoto();
            setStatus(message);
            input.reportValidity();
        };
        if (file.size > 3 * 1024 * 1024) {
            reject('Choose a photograph no larger than 3 MB.');
            return;
        }
        if (!/\.(jpe?g|png|webp)$/i.test(file.name) ||
            (file.type && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type))) {
            reject('Choose a JPG, PNG or WebP photograph.');
            return;
        }
        input.setCustomValidity('Wait for the photograph to load, then confirm your crop.');
        setStatus('Loading your photograph…');
        const url = URL.createObjectURL(file);
        try {
            const loaded = new Image();
            loaded.src = url;
            await loaded.decode();
            if (current !== revision) return;
            image = loaded;
            editor.showModal();
            document.body.classList.add('photo-crop-open');
            reset();
            zoom.focus();
        } catch {
            if (current === revision) reject('This photograph could not be opened. Choose another image.');
        } finally {
            URL.revokeObjectURL(url);
        }
    });
    [zoom, x, y].forEach(control => control.addEventListener('input', changed));
    document.getElementById('picture-reset').addEventListener('click', reset);
    canvas.addEventListener('pointerdown', event => {
        if (!image) return;
        drag = { x: event.clientX, y: event.clientY, left: Number(x.value), top: Number(y.value) };
        canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', event => {
        if (!drag || !image) return;
        const box = crop();
        const rect = canvas.getBoundingClientRect();
        const horizontal = image.width - box.width;
        const vertical = image.height - box.height;
        const clamp = value => Math.max(0, Math.min(1, value));
        if (horizontal > 0) x.value = clamp(drag.left - (event.clientX - drag.x) * box.width / rect.width / horizontal);
        if (vertical > 0) y.value = clamp(drag.top - (event.clientY - drag.y) * box.height / rect.height / vertical);
        changed();
    });
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(name => canvas.addEventListener(name, () => { drag = null; }));
    apply.addEventListener('click', () => {
        if (!image) return;
        const current = revision;
        apply.disabled = true;
        canvas.toBlob(blob => {
            apply.disabled = false;
            if (current !== revision) return;
            if (!blob) {
                setStatus('Could not prepare this crop. Please try again.');
                return;
            }
            try {
                const transfer = new DataTransfer();
                confirmedFile = new File([blob], 'passport.jpg', { type: 'image/jpeg' });
                transfer.items.add(confirmedFile);
                input.files = transfer.files;
                input.setCustomValidity('');
                if (previewURL) URL.revokeObjectURL(previewURL);
                previewURL = URL.createObjectURL(blob);
                preview.src = previewURL;
                preview.hidden = false;
                editor.close();
            } catch {
                setStatus('Your browser could not prepare the upload. Please try a newer browser.');
            }
        }, 'image/jpeg', 0.82);
    });
})();
