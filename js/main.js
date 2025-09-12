document.addEventListener('DOMContentLoaded', () => {
    console.log('termAI website loaded');

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            // Prevent default for all but the download button
            if (!this.id || this.id !== 'download-script-btn') {
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Force file download for termAI.py
    const downloadBtn = document.getElementById('download-script-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const filePath = 'termAI.py';

            fetch(filePath)
                .then(response => response.text())
                .then(text => {
                    const blob = new Blob([text], { type: 'text/plain' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'termAI.py';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                })
                .catch(err => console.error('Error al descargar el archivo:', err));
        });
    }
});
