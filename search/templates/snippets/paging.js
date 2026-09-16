document.addEventListener('DOMContentLoaded', () => {
    const paginationContainer = document.getElementById('search-pagination-list');
    if (paginationContainer) {
        paginationContainer.addEventListener('click', (event) => {
            const button = event.target.closest('button[data-page]');
            if (button && !button.hasAttribute('disabled')) {
                const pageNumber = button.getAttribute('data-page');
                if (pageNumber) {
                    const currentUrl = new URL(window.location.href);
                    currentUrl.searchParams.set('page', pageNumber);
                    window.location.href = currentUrl.toString();
                }
            }
        });
    }
});
