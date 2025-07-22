// schedule.js
document.addEventListener('DOMContentLoaded', function() {
    const scheduleButtons = document.querySelectorAll('.schedule-btn');
    const scheduleForm = document.getElementById('scheduleForm');
    const appointmentDate = document.getElementById('appointmentDate');
    const appointmentTime = document.getElementById('appointmentTime');
    const doctorId = document.getElementById('doctorId');
    const doctorName = document.getElementById('doctorName');
    const confirmSchedule = document.getElementById('confirmSchedule');

    // Set minimum date to today
    const today = new Date().toISOString().split('T')[0];
    appointmentDate.setAttribute('min', today);

    scheduleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const doctor_id = this.dataset.doctorId;
            const doctor_name = this.dataset.doctorName;
            
            doctorId.value = doctor_id;
            doctorName.textContent = doctor_name;
            
            // Clear previous selections
            appointmentDate.value = '';
            appointmentTime.innerHTML = '<option value="">Select a date first</option>';
            
            // Show the modal
            const scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));
            scheduleModal.show();
        });
    });

    // When date is selected, fetch available time slots
    appointmentDate.addEventListener('change', function() {
        const selected_date = this.value;
        const doctor_id = doctorId.value;

        if (selected_date) {
            // Show loading state
            appointmentTime.innerHTML = '<option value="">Loading available slots...</option>';

            // Fetch available time slots from server
            fetch(`/doctor-availability/${doctor_id}?date=${selected_date}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }

                    // Update time slots dropdown
                    appointmentTime.innerHTML = '';
                    if (data.available_slots && data.available_slots.length > 0) {
                        appointmentTime.innerHTML = '<option value="">Select a time slot</option>';
                        data.available_slots.forEach(slot => {
                            // Convert 24-hour format to 12-hour format
                            const [hours, minutes] = slot.split(':');
                            const time = new Date(2000, 0, 1, hours, minutes);
                            const timeString = time.toLocaleTimeString('en-US', {
                                hour: 'numeric',
                                minute: '2-digit',
                                hour12: true
                            });
                            
                            appointmentTime.innerHTML += `
                                <option value="${slot}">${timeString}</option>
                            `;
                        });
                    } else {
                        appointmentTime.innerHTML = '<option value="">No available slots</option>';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    appointmentTime.innerHTML = '<option value="">Error loading time slots</option>';
                });
        }
    });

    // Handle form submission
    confirmSchedule.addEventListener('click', function(e) {
        e.preventDefault();
        
        const formData = {
            doctor_id: doctorId.value,
            appointment_date: appointmentDate.value,
            appointment_time: appointmentTime.value,
            symptoms: document.getElementById('symptoms').value,
            notes: document.getElementById('notes').value
        };

        // Validate form
        if (!formData.appointment_date || !formData.appointment_time) {
            alert('Please select both date and time');
            return;
        }

        // Submit appointment request
        fetch('/schedule-appointment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('scheduleModal')).hide();
            
            // Show success message
            alert('Appointment scheduled successfully!');
            
            // Refresh appointments list
            if (typeof refreshAppointments === 'function') {
                refreshAppointments();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to schedule appointment: ' + error.message);
        });
    });
});