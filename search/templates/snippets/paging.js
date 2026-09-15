document.querySelectorAll('.pagination .pg-btn').forEach(button => {
    button.addEventListener('click', function() {
        const targetUrl = this.getAttribute('data-url');
        if (targetUrl) {
            window.location.href = targetUrl;
        }
    });
});
