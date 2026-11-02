(() => {
    const button = document.getElementById('share-photo');
    const status = document.getElementById('share-status');
    if (!button || !navigator.share || !navigator.canShare || !window.File) return;
    if (!navigator.canShare({ files: [new File([''], 'card.png', { type: 'image/png' })] })) return;

    // Prepare the photo before the click so the share call keeps its user gesture.
    fetch(button.dataset.imageUrl, { referrerPolicy: 'no-referrer' })
        .then(response => {
            if (!response.ok) throw new Error('Photo unavailable');
            return response.blob();
        })
        .then(blob => {
            const file = new File([blob], 'biin_ambassador_card.png', { type: 'image/png' });
            if (!navigator.canShare({ files: [file] })) return;
            button.hidden = false;
            button.addEventListener('click', async () => {
                status.textContent = '';
                try {
                    await navigator.share({ files: [file], title: 'BIIN Campus Ambassador' });
                } catch (error) {
                    if (error.name !== 'AbortError') {
                        status.textContent = 'Download your photo and upload it in your preferred app.';
                    }
                }
            });
        })
        .catch(() => { /* The download link remains available. */ });
})();
