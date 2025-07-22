document.addEventListener('DOMContentLoaded', function() {
    // Handle navigation between sections
    const navLinks = document.querySelectorAll('.nav-link[data-frame]');
    const contentFrames = document.querySelectorAll('.content-frame');
    const userInfoSection = document.getElementById('userInfoSection');
    const personalDetailsFrame = document.getElementById('personalDetails');
    const consultButtons = document.querySelectorAll('.consult-btn');
    consultButtons.forEach(button => {
        button.addEventListener('click', function() {
            const doctorId = this.getAttribute('data-doctor-id');
            
            if (!this.disabled) {
                // Here you would typically initiate a video call
                // For now, we'll just show an alert
                alert(`Starting consultation with doctor ID: ${doctorId}`);
                
                // In a real application, you might redirect to a video chat room:
                // window.location.href = `/video-chat/${doctorId}`;
            }
        });
    });
    
    // Handle schedule appointment buttons
    const scheduleButtons = document.querySelectorAll('.schedule-btn');
    
    scheduleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const doctorCard = this.closest('.doctor-card');
            const doctorName = doctorCard.querySelector('h3').textContent;
            
            alert(`Opening scheduling calendar for ${doctorName}`);
            // In a real app, you might open a modal with a calendar
        });
    });

    // Function to show personal details
    function showPersonalDetails() {
        contentFrames.forEach(frame => frame.classList.remove('active'));
        navLinks.forEach(link => link.classList.remove('active'));
        personalDetailsFrame.classList.add('active');
        userInfoSection.classList.add('active');
    }

    // Add click event to user info section
    userInfoSection.addEventListener('click', showPersonalDetails);

    // Handle navigation link clicks
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Only handle navigation for non-logout links
            if (!this.href || !this.href.endsWith('/logout')) {
                e.preventDefault();
                
                userInfoSection.classList.remove('active');
                navLinks.forEach(navLink => navLink.classList.remove('active'));
                this.classList.add('active');

                contentFrames.forEach(frame => frame.classList.remove('active'));
                const frameId = this.getAttribute('data-frame');
                const selectedFrame = document.getElementById(frameId);
                if (selectedFrame) {
                    selectedFrame.classList.add('active');
                }
            }
        });
    });

    // Handle health metrics radio buttons
    const metrics = ['bp', 'sugar', 'temp', 'glucose'];
    metrics.forEach(metric => {
        const radioYes = document.querySelector(`input[name="${metric}-monitor"][value="yes"]`);
        const radioNo = document.querySelector(`input[name="${metric}-monitor"][value="no"]`);
        const inputs = document.getElementById(`${metric}-inputs`);

        if (radioYes && radioNo && inputs) {
            radioYes.addEventListener('change', () => {
                inputs.style.display = radioYes.checked ? 'block' : 'none';
            });

            radioNo.addEventListener('change', () => {
                inputs.style.display = 'none';
            });
        }
    });
    
    // Show personal details by default when page loads
    showPersonalDetails();
});
// Add this to your existing dashboard.js file

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modal
    const appointmentModal = new bootstrap.Modal(document.getElementById('appointmentModal'));
    
    // Handle schedule button clicks
    document.querySelectorAll('.schedule-btn').forEach(button => {
        button.addEventListener('click', function() {
            const doctorId = this.dataset.doctorId;
            const doctorName = this.dataset.doctorName;
            const doctorSpecialty = this.dataset.doctorSpecialty;

            // Set minimum date to today
            const dateInput = document.getElementById('appointment-date');
            if (dateInput) {
                const today = new Date().toISOString().split('T')[0];
                dateInput.min = today;
            }

            // Update modal information
            document.getElementById('modal-doctor-name').textContent = `Dr. ${doctorName}`;
            document.getElementById('modal-doctor-specialty').textContent = doctorSpecialty || 'Not specified';

            // Show schedule modal
            const scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));
            scheduleModal.show();

            // Function to group slots by date
            function groupSlotsByDate(slots) {
                return slots.reduce((groups, slot) => {
                    if (!groups[slot.date]) {
                        groups[slot.date] = [];
                    }
                    groups[slot.date].push(slot);
                    return groups;
                }, {});
            }

            // Handle date selection
            dateInput.addEventListener('change', async function() {
                const selectedDate = this.value;
                const timeSlotsContainer = document.getElementById('time-slots');
                
                try {
                    const response = await fetch(`/api/doctor/availability/${doctorId}`);
                    const data = await response.json();
                    
                    if (data.success) {
                        // Filter slots for selected date
                        const dateSlots = data.availability.filter(slot => slot.date === selectedDate);
                        
                        if (dateSlots.length === 0) {
                            timeSlotsContainer.innerHTML = '<p class="text-info">No available slots for this date</p>';
                            return;
                        }

                        // Display time slots
                        timeSlotsContainer.innerHTML = dateSlots.map(slot => `
                            <button type="button" class="btn btn-outline-primary time-slot m-1"
                                    data-time="${slot.time}">
                                ${slot.formatted_time}
                            </button>
                        `).join('');

                        // Handle time slot selection
                        document.querySelectorAll('.time-slot').forEach(slot => {
                            slot.addEventListener('click', function() {
                                // Remove previous selection
                                document.querySelectorAll('.time-slot').forEach(s => 
                                    s.classList.remove('selected', 'btn-primary'));
                                
                                // Add selection to current slot
                                this.classList.remove('btn-outline-primary');
                                this.classList.add('selected', 'btn-primary');
                            });
                        });
                    } else {
                        throw new Error(data.error || 'Failed to load time slots');
                    }
                } catch (error) {
                    console.error('Error fetching time slots:', error);
                    timeSlotsContainer.innerHTML = '<p class="text-danger">Failed to load available time slots</p>';
                }
            });
        });
    });

    // Update the appointment confirmation handler
    const confirmAppointmentBtn = document.getElementById('confirm-appointment');
    if (confirmAppointmentBtn) {
        confirmAppointmentBtn.addEventListener('click', async function() {
            const doctorId = document.querySelector('.schedule-btn').dataset.doctorId;
            const selectedDate = document.getElementById('appointment-date').value;
            const selectedTimeSlot = document.querySelector('.time-slot.selected');
            const reason = document.getElementById('appointment-reason').value;

            if (!selectedDate || !selectedTimeSlot || !reason) {
                alert('Please select a date, time slot, and provide a reason for the appointment');
                return;
            }

            try {
                const response = await fetch('/schedule-appointment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        doctor_id: doctorId,
                        appointment_date: selectedDate,
                        appointment_time: selectedTimeSlot.dataset.time,
                        reason: reason
                    })
                });

                const data = await response.json();
                if (response.ok) {
                    alert('Appointment scheduled successfully!');
                    location.reload();
                } else {
                    throw new Error(data.error || 'Failed to schedule appointment');
                }
            } catch (error) {
                console.error('Error scheduling appointment:', error);
                alert(error.message || 'Failed to schedule appointment. Please try again.');
            }
        });
    }
});