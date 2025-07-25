// Entry point for dashboard JS 
class App {
    constructor() {
        this.init();
    }

    init() {
        this.setupSidebar();
        this.setupNavigation();
        this.loadInitialPage();
    }

    setupSidebar() {
        const toggleBtn = document.getElementById('sidebarToggle');
        const app = document.querySelector('.app');
        
        if (toggleBtn && app) {
            toggleBtn.addEventListener('click', () => {
                app.classList.toggle('sidebar-collapsed');
            });
        }
    }

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.dataset.page;
                router.navigate(page);
            });
        });
    }

    loadInitialPage() {
        // Load dashboard by default
        if (!window.location.hash) {
            router.navigate('dashboard');
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});