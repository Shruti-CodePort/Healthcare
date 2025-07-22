document.addEventListener('DOMContentLoaded', function() {
    const flashContainer = document.getElementById('flash-message-container');
    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(function(message) {
        // Show the message with a slight delay
        setTimeout(() => {
            message.classList.add('show');
        }, 100);

        // Set a timeout to remove the message after 3 seconds
        setTimeout(function() {
            hideFlashMessage(message);
        }, 3000);

        // Add click event listener to close button
        const closeButton = message.querySelector('.flash-close');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                hideFlashMessage(message);
            });
        }
    });

    function hideFlashMessage(message) {
        message.classList.remove('show');
        message.addEventListener('transitionend', function() {
            message.remove();
            if (flashContainer.children.length === 0) {
                flashContainer.style.display = 'none';
            }
        });
    }
});