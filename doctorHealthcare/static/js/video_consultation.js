// Video Consultation Page Scripts
document.addEventListener('DOMContentLoaded', function() {
    // Toggle doctor online/offline status
    const toggleStatusBtn = document.getElementById('toggleStatus');
    if (toggleStatusBtn) {
        toggleStatusBtn.addEventListener('click', function() {
            const isOnline = toggleStatusBtn.classList.contains('online');
            
            // Send AJAX request to update status
            fetch('/doctor/update_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    status: isOnline ? 'offline' : 'online'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Toggle button text and class
                    toggleStatusBtn.textContent = isOnline ? 'Go Online' : 'Go Offline';
                    toggleStatusBtn.classList.toggle('online');
                    toggleStatusBtn.classList.toggle('offline');
                    
                    // Update status indicator
                    const statusIndicator = document.querySelector('.status-indicator');
                    if (statusIndicator) {
                        statusIndicator.classList.toggle('online');
                        statusIndicator.classList.toggle('offline');
                    }
                    
                    // Update status text
                    const statusText = statusIndicator.nextElementSibling;
                    if (statusText) {
                        statusText.textContent = isOnline ? 'Offline' : 'Online';
                    }
                    
                    // Update video consultation status
                    const videoStatusIndicator = document.querySelector('.video-status-indicator');
                    if (videoStatusIndicator) {
                        videoStatusIndicator.classList.toggle('available');
                        videoStatusIndicator.classList.toggle('busy');
                    }
                    
                    const videoStatusText = videoStatusIndicator.nextElementSibling;
                    if (videoStatusText) {
                        videoStatusText.textContent = isOnline ? 'Not available' : 'Available for consultation';
                    }
                    
                    // Show success message
                    showNotification(isOnline ? 'You are now offline' : 'You are now online', 'success');
                } else {
                    showNotification('Failed to update status', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred', 'error');
            });
        });
    }
    
    // Handle "Mark Complete" button clicks
    const completeButtons = document.querySelectorAll('.complete-btn');
    completeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const appointmentId = this.dataset.appointmentId;
            
            if (confirm('Are you sure you want to mark this appointment as completed?')) {
                // Send AJAX request to complete appointment
                fetch(`/doctor/complete_appointment/${appointmentId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Remove the appointment card or update UI
                        const appointmentCard = this.closest('.consultation-card');
                        if (appointmentCard) {
                            appointmentCard.style.opacity = '0.5';
                            this.disabled = true;
                            this.textContent = 'Completed';
                            
                            // Optionally remove the card after a delay
                            setTimeout(() => {
                                appointmentCard.remove();
                                
                                // If no more appointments, show "no appointments" message
                                const cardsContainer = document.querySelector('.consultation-cards');
                                if (cardsContainer && cardsContainer.children.length === 0) {
                                    cardsContainer.innerHTML = `
                                        <div class="no-appointments">
                                            <i class="fas fa-calendar-times"></i>
                                            <p>No verified consultations scheduled for today.</p>
                                        </div>
                                    `;
                                }
                            }, 1000);
                        }
                        
                        showNotification('Appointment marked as completed', 'success');
                    } else {
                        showNotification(data.message || 'Failed to complete appointment', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('An error occurred', 'error');
                });
            }
        });
    });
    
    // Helper function to show notifications
    function showNotification(message, type = 'info') {
        // If you have a notification system, use it here
        // This is a simple implementation
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
});