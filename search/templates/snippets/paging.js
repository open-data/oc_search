document.addEventListener('DOMContentLoaded', () => {
    const paginationContainer = document.getElementById('search-pagination-list');
    if (paginationContainer) {
        paginationContainer.addEventListener('click', (event) => {
            const button = event.target.closest('button[data-url]');
            if (button) {
                const targetUrl = button.getAttribute('data-url');
                if (targetUrl) {
                    window.location.href = targetUrl;
                }
            }
        });
    }
});
