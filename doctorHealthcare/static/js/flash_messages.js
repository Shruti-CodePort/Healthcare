document.addEventListener('DOMContentLoaded', function() {
    // Get all flash messages
    const flashMessages = document.querySelectorAll('.flash-message');
    
    // Add close functionality
    flashMessages.forEach(message => {
        const closeButton = message.querySelector('.flash-close');
        
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                message.style.animation = 'fadeOut 0.3s forwards';
                setTimeout(() => {
                    message.remove();
                }, 300);
            });
        }
        
        // Auto close after 5 seconds
        setTimeout(() => {
            if (message.parentNode) {
                message.style.animation = 'fadeOut 0.3s forwards';
                setTimeout(() => {
                    if (message.parentNode) {
                        message.remove();
                    }
                }, 300);
            }
        }, 5000);
    });
});