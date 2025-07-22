// Create a new JS file for consultation functionality
document.addEventListener('DOMContentLoaded', function() {
    const scheduleButtons = document.querySelectorAll('.schedule-btn');
    const appointmentModal = new bootstrap.Modal(document.getElementById('appointmentModal'));
    
    scheduleButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const doctorId = this.dataset.doctorId;
            const doctorName = this.dataset.doctorName;
            const doctorSpecialty = this.dataset.doctorSpecialty;
            
            // Update modal information
            document.querySelector('.modal-doctor-info .doctor-name').textContent = `Dr. ${doctorName}`;
            document.querySelector('.modal-doctor-info .doctor-spec').textContent = doctorSpecialty;
            
            try {
                // Fetch doctor's schedule
                const response = await fetch(`/api/doctor/schedule/${doctorId}`);
                const data = await response.json();
                
                if (data.success) {
                    // Display weekly schedule
                    displayWeeklySchedule(data.schedule);
                    
                    // Initialize date picker
                    initializeDatePicker(data.schedule, data.booked_slots);
                    
                    // Show modal
                    appointmentModal.show();
                }
            } catch (error) {
                console.error('Error fetching doctor schedule:', error);
                alert('Failed to load doctor\'s schedule. Please try again.');
            }
        });
    });
    
    function displayWeeklySchedule(schedule) {
        const scheduleTable = document.querySelector('.schedule-table');
        const tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Day</th>
                        <th>Hours</th>
                    </tr>
                </thead>
                <tbody>
                    ${schedule.map(slot => `
                        <tr>
                            <td>${slot.day_of_week}</td>
                            <td>${slot.start_time} - ${slot.end_time}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        scheduleTable.innerHTML = tableHTML;
    }
    
    function initializeDatePicker(schedule, bookedSlots) {
        const dateInput = document.getElementById('appointmentDate');
        const today = new Date().toISOString().split('T')[0];
        
        dateInput.min = today;
        dateInput.max = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        
        dateInput.addEventListener('change', function() {
            const selectedDate = this.value;
            const dayOfWeek = new Date(selectedDate).toLocaleDateString('en-US', { weekday: 'long' });
            
            // Find schedule for selected day
            const daySchedule = schedule.find(s => s.day_of_week === dayOfWeek);
            if (daySchedule) {
                displayTimeSlots(daySchedule, selectedDate, bookedSlots);
            }
        });
    }
    
    function displayTimeSlots(daySchedule, selectedDate, bookedSlots) {
        const timeSlotsContainer = document.querySelector('.time-slots');
        const slots = generateTimeSlots(daySchedule.start_time, daySchedule.end_time);
        
        const slotsHTML = slots.map(slot => {
            const isBooked = bookedSlots.some(bookedSlot => 
                bookedSlot.date === selectedDate && bookedSlot.time === slot
            );
            
            return `
                <div class="time-slot ${isBooked ? 'booked' : ''}" 
                     data-time="${slot}" 
                     ${isBooked ? 'disabled' : ''}>
                    ${formatTime(slot)}
                </div>
            `;
        }).join('');
        
        timeSlotsContainer.innerHTML = slotsHTML;
        
        // Add click handlers for time slots
        document.querySelectorAll('.time-slot:not(.booked)').forEach(slot => {
            slot.addEventListener('click', function() {
                document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
                this.classList.add('selected');
            });
        });
    }
    
    // Handle appointment booking
    document.querySelector('.book-appointment').addEventListener('click', async function() {
        const doctorId = document.querySelector('.schedule-btn').dataset.doctorId;
        const selectedDate = document.getElementById('appointmentDate').value;
        const selectedSlot = document.querySelector('.time-slot.selected');
        const reason = document.getElementById('visitReason').value;
        
        if (!selectedDate || !selectedSlot || !reason) {
            alert('Please select a date, time slot, and provide a reason for the visit');
            return;
        }
        
        try {
            const response = await fetch('/api/book-appointment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    doctor_id: doctorId,
                    appointment_date: selectedDate,
                    appointment_time: selectedSlot.dataset.time,
                    reason: reason
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert('Appointment booked successfully!');
                appointmentModal.hide();
                location.reload();
            } else {
                throw new Error(data.message || 'Failed to book appointment');
            }
        } catch (error) {
            console.error('Error booking appointment:', error);
            alert(error.message || 'Failed to book appointment. Please try again.');
        }
    });
});

// Helper functions
function generateTimeSlots(start, end) {
    const slots = [];
    let current = start;
    
    while (current < end) {
        slots.push(current);
        current = incrementTime(current, 30);
    }
    
    return slots;
}

function incrementTime(time, minutes) {
    const [hours, mins] = time.split(':').map(Number);
    const date = new Date();
    date.setHours(hours, mins + minutes);
    return date.toTimeString().slice(0, 5);
}

function formatTime(time) {
    const [hours, minutes] = time.split(':');
    const date = new Date();
    date.setHours(hours, minutes);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
} 