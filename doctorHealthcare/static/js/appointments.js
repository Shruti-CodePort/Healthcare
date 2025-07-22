document.addEventListener('DOMContentLoaded', function() {
    const addScheduleBtn = document.getElementById('addScheduleBtn');
    const scheduleForm = document.getElementById('scheduleForm');
    const availabilityForm = document.getElementById('availabilityForm');
    const cancelBtn = document.getElementById('cancelBtn');
    const dateInput = document.getElementById('schedule_date');
    const startTimeInput = document.getElementById('start_time');

    // Set min and max dates (today to next 7 days)
    const today = new Date();
    const maxDate = new Date();
    maxDate.setDate(today.getDate() + 7);
    
    dateInput.min = today.toISOString().split('T')[0];
    dateInput.max = maxDate.toISOString().split('T')[0];

    // Show/hide form
    addScheduleBtn.addEventListener('click', () => {
        scheduleForm.style.display = 'block';
    });

    cancelBtn.addEventListener('click', () => {
        scheduleForm.style.display = 'none';
        availabilityForm.reset();
    });

    // Form validation
    availabilityForm.addEventListener('submit', (e) => {
        const startTime = new Date(`${dateInput.value}T${startTimeInput.value}`);
        const now = new Date();
        
        // Validate date and time
        if (startTime < now) {
            e.preventDefault();
            alert('Cannot schedule appointments in the past');
            return false;
        }
        return true;
    });

    // Handle schedule deletion
    window.deleteSchedule = function(id) {
        if (!confirm('Are you sure you want to delete this schedule?')) return;
        
        // Create and submit a form for DELETE request
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/appointments/delete/${id}`;
        document.body.appendChild(form);
        form.submit();
    }
});
function deleteSchedule(scheduleId) {
    if (event.target.classList.contains('disabled')) {
        alert('Cannot delete this schedule as it has booked appointments');
        return;
    }
    
    if (confirm('Are you sure you want to delete this schedule?')) {
        fetch(`/appointments/delete/${scheduleId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                throw new Error('Failed to delete schedule');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to delete schedule. Please try again.');
        });
    }
}