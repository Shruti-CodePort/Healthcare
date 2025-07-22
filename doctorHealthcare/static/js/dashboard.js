document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar on mobile
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
        });
    }

    // Notifications dropdown
    const notificationBell = document.querySelector('.notifications');
    if (notificationBell) {
        notificationBell.addEventListener('click', (e) => {
            e.stopPropagation();
            notificationBell.classList.toggle('active');
        });
    }

    // Search functionality
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            // Add your search logic here
        });
    }

    // Appointment actions
    const appointmentButtons = document.querySelectorAll('.btn-action');
    appointmentButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const action = this.classList.contains('start') ? 'start' :
                          this.classList.contains('reschedule') ? 'reschedule' :
                          'cancel';
            const appointmentCard = this.closest('.appointment-card');
            const patientName = appointmentCard.querySelector('.patient-info h3').textContent;
            
            switch(action) {
                case 'start':
                    startAppointment(patientName);
                    break;
                case 'reschedule':
                    rescheduleAppointment(patientName);
                    break;
                case 'cancel':
                    cancelAppointment(patientName);
                    break;
            }
        });
    });

    // Example functions for appointment actions
    function startAppointment(patientName) {
        console.log(`Starting appointment with ${patientName}`);
        // Add your video call logic here
    }

    function rescheduleAppointment(patientName) {
        console.log(`Rescheduling appointment with ${patientName}`);
        // Add your rescheduling logic here
    }

    function cancelAppointment(patientName) {
        if (confirm(`Are you sure you want to cancel the appointment with ${patientName}?`)) {
            console.log(`Cancelling appointment with ${patientName}`);
            // Add your cancellation logic here
        }
    }

    // Quick actions
    const quickActions = document.querySelectorAll('.action-btn');
    quickActions.forEach(action => {
        action.addEventListener('click', function() {
            const actionType = this.querySelector('span').textContent;
            console.log(`Quick action clicked: ${actionType}`);
            // Add your quick action logic here
        });
    });

    // Update time
    function updateTime() {
        const timeElements = document.querySelectorAll('.time');
        timeElements.forEach(element => {
            const time = element.getAttribute('data-time');
            if (time) {
                const formattedTime = new Date(time).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                });
                element.textContent = formattedTime;
            }
        });
    }

    // Update status dots
    function updateStatusDots() {
        const appointments = document.querySelectorAll('.appointment-card');
        appointments.forEach(appointment => {
            const time = appointment.querySelector('.time').getAttribute('data-time');
            const statusDot = appointment.querySelector('.status-dot');
            
            if (time) {
                const appointmentTime = new Date(time);
                const now = new Date();
                
                if (now > appointmentTime) {
                    statusDot.className = 'status-dot completed';
                } else if (Math.abs(now - appointmentTime) <= 30 * 60 * 1000) {
                    statusDot.className = 'status-dot ongoing';
                }
            }
        });
    }

    // Initial calls
    updateTime();
    updateStatusDots();

    // Update every minute
    setInterval(() => {
        updateTime();
        updateStatusDots();
    }, 60000);
}); 