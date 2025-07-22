document.addEventListener('DOMContentLoaded', function() {
    const scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));
    
    // Load appointments for each tab
    loadAppointments('pending');
    loadAppointments('confirmed');
    loadAppointments('completed');
    
    // Handle tab changes
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            const status = e.target.id.split('-')[0];
            loadAppointments(status);
        });
    });
    
    // View schedule button
    document.getElementById('viewScheduleBtn').addEventListener('click', () => {
        scheduleModal.show();
    });
    
    async function loadAppointments(status) {
        const container = document.getElementById(`${status}Appointments`);
        container.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';
        
        try {
            const response = await fetch(`/api/doctor/appointments?status=${status}`);
            const appointments = await response.json();
            
            if (appointments.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-4 text-muted">
                        <p>No ${status} appointments</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = appointments.map(appointment => `
                <div class="appointment-card" data-id="${appointment.id}">
                    <div class="appointment-header">
                        <div>
                            <h5 class="mb-1">${appointment.patient_name}</h5>
                            <p class="text-muted mb-0">${appointment.patient_email}</p>
                        </div>
                        <span class="status-badge ${appointment.status}">
                            ${appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1)}
                        </span>
                    </div>
                    
                    <div class="appointment-details">
                        <p class="mb-2">
                            <i class="far fa-calendar me-2"></i>
                            ${formatDate(appointment.appointment_date)}
                        </p>
                        <p class="mb-2">
                            <i class="far fa-clock me-2"></i>
                            ${formatTime(appointment.appointment_time)}
                        </p>
                    </div>
                    
                    ${getActionButtons(appointment)}
                </div>
            `).join('');
            
            // Update counts
            const count = appointments.length;
            document.getElementById(`${status}Count`).textContent = count;
            
            // Add event listeners to action buttons
            addActionButtonListeners();
            
        } catch (error) {
            console.error('Error loading appointments:', error);
            container.innerHTML = `
                <div class="text-center py-4 text-danger">
                    <p>Error loading appointments</p>
                </div>
            `;
        }
    }
    
    function getActionButtons(appointment) {
        if (appointment.status === 'pending') {
            return `
                <div class="appointment-actions">
                    <button class="btn btn-success btn-sm confirm-btn">
                        <i class="fas fa-check me-1"></i> Confirm
                    </button>
                    <button class="btn btn-danger btn-sm cancel-btn">
                        <i class="fas fa-times me-1"></i> Cancel
                    </button>
                </div>
            `;
        } else if (appointment.status === 'confirmed') {
            return `
                <div class="appointment-actions">
                    <button class="btn btn-info btn-sm complete-btn">
                        <i class="fas fa-check-double me-1"></i> Mark Complete
                    </button>
                    <button class="btn btn-danger btn-sm cancel-btn">
                        <i class="fas fa-times me-1"></i> Cancel
                    </button>
                </div>
            `;
        }
        return '';
    }
    
    function addActionButtonListeners() {
        // Confirm appointment
        document.querySelectorAll('.confirm-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                const appointmentId = this.closest('.appointment-card').dataset.id;
                await updateAppointmentStatus(appointmentId, 'confirmed');
            });
        });
        
        // Complete appointment
        document.querySelectorAll('.complete-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                const appointmentId = this.closest('.appointment-card').dataset.id;
                await updateAppointmentStatus(appointmentId, 'completed');
            });
        });
        
        // Cancel appointment
        document.querySelectorAll('.cancel-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                const appointmentId = this.closest('.appointment-card').dataset.id;
                if (confirm('Are you sure you want to cancel this appointment?')) {
                    await updateAppointmentStatus(appointmentId, 'cancelled');
                }
            });
        });
    }
    
    async function updateAppointmentStatus(appointmentId, status) {
        try {
            const response = await fetch(`/api/doctor/appointments/${appointmentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                // Reload all appointments to update counts
                loadAppointments('pending');
                loadAppointments('confirmed');
                loadAppointments('completed');
            } else {
                alert(result.error || 'Error updating appointment');
            }
            
        } catch (error) {
            console.error('Error updating appointment:', error);
            alert('Error updating appointment');
        }
    }
    
    function formatDate(dateStr) {
        return new Date(dateStr).toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
    
    function formatTime(timeStr) {
        return new Date(`2000-01-01T${timeStr}`).toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }
});