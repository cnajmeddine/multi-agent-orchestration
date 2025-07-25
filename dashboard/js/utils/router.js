// Simple router utility 
class Router {
    constructor() {
        this.routes = {};
        this.currentRoute = null;
        this.init();
    }

    init() {
        window.addEventListener('hashchange', () => this.handleRouteChange());
        this.handleRouteChange();
    }

    register(path, handler) {
        this.routes[path] = handler;
    }

    navigate(path) {
        window.location.hash = path;
    }

    handleRouteChange() {
        const hash = window.location.hash.slice(1) || 'dashboard';
        this.currentRoute = hash;
        
        // Hide all pages
        document.querySelectorAll('.page').forEach(page => {
            page.style.display = 'none';
        });

        // Show current page
        const currentPage = document.getElementById(`${hash}-page`);
        if (currentPage) {
            currentPage.style.display = 'block';
        }

        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.page === hash) {
                item.classList.add('active');
            }
        });

        // Call route handler if exists
        if (this.routes[hash]) {
            this.routes[hash]();
        }
    }
}

// Global router instance
window.router = new Router();