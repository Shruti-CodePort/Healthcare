// Navigation and Interaction Management
document.addEventListener('DOMContentLoaded', () => {
    // Navigation Function
    function navigateTo(page) {
        // Secure navigation mapping
        const navigationMap = {
            'dashboard': 'dashboard.html',
            'login': 'login.html',
            'signup': 'signup.html',
            'profile': 'profile.html',
            'services': 'services.html',
            'home': 'index.html'
        };

        // Validate and navigate
        if (navigationMap[page]) {
            window.location.href = navigationMap[page];
        } else {
            console.warn(`Invalid navigation target: ${page}`);
            window.location.href = 'dashboard.html'; // Default fallback
        }
    }

    // Smooth Scroll Implementation
    function smoothScroll(target) {
        const element = document.querySelector(target);
        if (element) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }

    // Dynamic Header Background
    function handleHeaderBackground() {
        const header = document.querySelector('.header');
        const scrollThreshold = 50;

        window.addEventListener('scroll', () => {
            if (window.scrollY > scrollThreshold) {
                header.classList.add('scrolled');
                header.style.backgroundColor = '#1a2632';
            } else {
                header.classList.remove('scrolled');
                header.style.backgroundColor = '#ffffff';
            }
        });
    }

    // Interactive Button Handlers
    function setupButtonInteractions() {
        // Navigation Buttons
        const navigationButtons = document.querySelectorAll('[data-navigate]');
        navigationButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const targetPage = button.getAttribute('data-navigate');
                navigateTo(targetPage);
            });
        });

        // Scroll Buttons
        const scrollButtons = document.querySelectorAll('[data-scroll]');
        scrollButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const targetSection = button.getAttribute('data-scroll');
                smoothScroll(targetSection);
            });
        });
    }

    // Feature Card Hover Effects
    function setupFeatureCardHovers() {
        const featureCards = document.querySelectorAll('.feature-card');
        featureCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.classList.add('hover-active');
            });

            card.addEventListener('mouseleave', () => {
                card.classList.remove('hover-active');
            });
        });
    }

    // Modal Interaction
    function setupModalInteractions() {
        const modalTriggers = document.querySelectorAll('[data-modal-trigger]');
        const modals = document.querySelectorAll('.modal');

        modalTriggers.forEach(trigger => {
            trigger.addEventListener('click', () => {
                const modalId = trigger.getAttribute('data-modal-trigger');
                const modal = document.getElementById(modalId);
                
                if (modal) {
                    modal.style.display = 'block';
                }
            });
        });

        // Close modal functionality
        const closeModalButtons = document.querySelectorAll('.modal-close');
        closeModalButtons.forEach(button => {
            button.addEventListener('click', () => {
                const modal = button.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                }
            });
        });
    }

    // Form Validation Utility
    function setupFormValidation() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    form.classList.add('was-validated');
                }
            });
        });
    }

    // Initialize All Interactions
    function initializeInteractions() {
        handleHeaderBackground();
        setupButtonInteractions();
        setupFeatureCardHovers();
        setupModalInteractions();
        setupFormValidation();
    }

    // Error Tracking
    function setupErrorTracking() {
        window.addEventListener('error', (event) => {
            console.error('Unhandled error:', event.error);
            // Optional: Send error to logging service
        });
    }

    // Main Initialization
    function init() {
        initializeInteractions();
        setupErrorTracking();
    }

    // Start the application
    init();
});