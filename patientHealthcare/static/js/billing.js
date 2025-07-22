// Add this to your patient_dashboard.js file or create a new JS file
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the billing tab
    const billingDiv = document.getElementById('billing');
    if (billingDiv) {
        loadPaymentRequests();
    }
    
    // Event delegation for dynamic content
    document.body.addEventListener('click', function(event) {
        if (event.target.classList.contains('pay-now-btn')) {
            const paymentRequestId = event.target.dataset.id;
            showPaymentModal(paymentRequestId, event.target.dataset.upiId, event.target.dataset.amount);
        }
    });
});

function loadPaymentRequests() {
    fetch('/api/patient/payment-requests')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            displayPaymentRequests(data.payment_requests);
        })
        .catch(error => {
            console.error('Error loading payment requests:', error);
            document.getElementById('billing').innerHTML = `
                <div class="alert alert-danger">
                    Failed to load payment requests. Please try again later.
                </div>
            `;
        });
}

// Update the displayPaymentRequests function to use the correct doctor fields
function displayPaymentRequests(paymentRequests) {
    const billingDiv = document.getElementById('billing');
    
    if (paymentRequests.length === 0) {
        billingDiv.innerHTML = `
            <div class="alert alert-info">
                You don't have any payment requests at this time.
            </div>
        `;
        return;
    }
    
    let html = `
        <h3>Payment Requests</h3>
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Doctor</th>
                        <th>Amount</th>
                        <th>Appointment Date</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    paymentRequests.forEach(request => {
        // Fix date parsing to avoid time zone issues
        // Split the date string to get components
        const dateParts = request.appointment_date.split('-');
        
        // Create date using YYYY, MM-1, DD format (months are 0-indexed in JavaScript)
        // This ensures we're creating the date in local time without time zone conversion
        const appointmentDate = new Date(
            parseInt(dateParts[0]),        // Year
            parseInt(dateParts[1]) - 1,    // Month (0-indexed)
            parseInt(dateParts[2])         // Day
        );
        
        // Format the date properly for display
        const formattedDate = appointmentDate.toLocaleDateString();
        
        // For time window calculation
        // First extract hours and minutes from time string (assuming format like "14:30:00")
        const timeParts = request.appointment_time.split(':');
        const hours = parseInt(timeParts[0]);
        const minutes = parseInt(timeParts[1]);
        
        // Create a new date object for appointment with correct hours and minutes
        const appointmentDateTime = new Date(appointmentDate);
        appointmentDateTime.setHours(hours, minutes, 0, 0);
        
        // Get appointment time for display (format HH:MM)
        const appointmentTime = request.appointment_time.substring(0, 5);
        
        let statusDisplay = '';
        let actionButton = '';
        
        if (request.status === 'pending') {
            statusDisplay = `<span class="badge bg-warning text-dark">Pending Payment</span>`;
            actionButton = `<button class="btn btn-primary btn-sm pay-now-btn" 
                data-id="${request.id}" 
                data-upi-id="${request.upi_id}"
                data-amount="${request.amount}">Pay Now</button>`;
        } else if (request.status === 'paid') {
            if (request.is_verified) {
                statusDisplay = `<span class="badge bg-success">Verified</span>`;
                
                // Calculate time windows based on correct appointment date and time
                const now = new Date();
                
                // Allow video consultation 10 minutes before and 30 minutes after appointment time
                const startWindow = new Date(appointmentDateTime);
                startWindow.setMinutes(startWindow.getMinutes() - 10);
                
                const endWindow = new Date(appointmentDateTime);
                endWindow.setMinutes(endWindow.getMinutes() + 30);
                
                // Debug logs
                console.log("Original appointment date from API:", request.appointment_date);
                console.log("Original appointment time from API:", request.appointment_time);
                console.log("Parsed appointment date-time:", appointmentDateTime);
                console.log("Current time:", now);
                console.log("Start window:", startWindow);
                console.log("End window:", endWindow);
                
                if (now >= startWindow && now <= endWindow) {
                    actionButton = `<button class="btn btn-success btn-sm video-consult-btn" 
                        data-appointment-id="${request.appointment_id}">
                        <i class="fas fa-video"></i> Join Consultation
                    </button>`;
                } else if (now < startWindow) {
                    // Calculate time until consultation
                    const diffMs = startWindow - now;
                    const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
                    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
                    
                    actionButton = `<span class="badge bg-info">
                        Consultation in ${diffHrs}h ${diffMins}m
                    </span>`;
                } else {
                    // After consultation window
                    actionButton = `<span class="badge bg-secondary">Consultation ended</span>`;
                }
            } else {
                statusDisplay = `<span class="badge bg-info">Paid (Awaiting Verification)</span>`;
                actionButton = `<span class="badge bg-secondary">Waiting for doctor to verify</span>`;
            }
        } else if (request.status === 'failed') {
            statusDisplay = `<span class="badge bg-danger">Failed</span>`;
        } else if (request.status === 'cancelled') {
            statusDisplay = `<span class="badge bg-secondary">Cancelled</span>`;
        }
        
        html += `
            <tr>
                <td>Dr. ${request.doctor_name} (${request.specialty})</td>
                <td>₹${request.amount}</td>
                <td>${formattedDate} at ${appointmentTime}</td>
                <td>${statusDisplay}</td>
                <td>${actionButton}</td>
            </tr>
        `;
    });
    
    // Rest of the function remains the same
    html += `
                </tbody>
            </table>
        </div>
        
        <!-- Payment Modal -->
        <div class="modal fade" id="paymentModal" tabindex="-1" aria-labelledby="paymentModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="paymentModalLabel">Complete Payment</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="payment-details">
                            <p>Amount: <span id="modal-amount"></span></p>
                            <p>UPI ID: <span id="modal-upi-id"></span></p>
                            <div class="text-center mb-3">
                                <div id="qrcode-container"></div>
                                <p class="mt-2">Scan QR code to pay</p>
                            </div>
                        </div>
                        <form id="payment-form" enctype="multipart/form-data">
                            <input type="hidden" id="payment-request-id">
                            <div class="mb-3">
                                <label for="transaction-id" class="form-label">Transaction ID</label>
                                <input type="text" class="form-control" id="transaction-id" required>
                            </div>
                            <div class="mb-3">
                                <label for="payment-proof" class="form-label">Payment Screenshot</label>
                                <input type="file" class="form-control" id="payment-proof" accept="image/png, image/jpeg, image/jpg, application/pdf" required>
                                <div class="form-text">Upload a screenshot or receipt of your payment (PNG, JPG, PDF)</div>
                            </div>
                            <div class="d-grid">
                                <button type="submit" class="btn btn-success">Submit Payment</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

         <!-- Video Consultation Modal -->
        <div class="modal fade" id="videoConsultModal" tabindex="-1" aria-labelledby="videoConsultModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="videoConsultModalLabel">Video Consultation</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div id="video-container" class="text-center">
                            <p>Video consultation will be implemented later.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    billingDiv.innerHTML = html;
    
    // Initialize Bootstrap components if needed
    if (typeof bootstrap !== 'undefined') {
        const paymentModalEl = document.getElementById('paymentModal');
        if (paymentModalEl) {
            new bootstrap.Modal(paymentModalEl);
        }
        const videoModalEl = document.getElementById('videoConsultModal');
        if (videoModalEl) {
            new bootstrap.Modal(videoModalEl);
        }
    }
    document.querySelectorAll('.video-consult-btn').forEach(button => {
        button.addEventListener('click', function() {
            const appointmentId = this.getAttribute('data-appointment-id');
            // Show video modal (empty implementation for now)
            const videoModal = new bootstrap.Modal(document.getElementById('videoConsultModal'));
            videoModal.show();
        });
    });
}

function showPaymentModal(paymentRequestId, upiId, amount) {
    document.getElementById('payment-request-id').value = paymentRequestId;
    document.getElementById('modal-amount').textContent = `₹${amount}`;
    document.getElementById('modal-upi-id').textContent = upiId;
    
    // Generate QR code for UPI payment
    const qrContainer = document.getElementById('qrcode-container');
    qrContainer.innerHTML = ''; // Clear previous QR code
    
    // Create UPI payment URL
    // Format: upi://pay?pa=UPI_ID&pn=NAME&am=AMOUNT&cu=CURRENCY&tn=MESSAGE
    const upiPaymentString = `upi://pay?pa=${upiId}&am=${amount}&cu=INR&tn=DoctorConsultation`;
    
    // Create QR code
    try {
        new QRCode(qrContainer, {
            text: upiPaymentString,
            width: 200,
            height: 200,
            colorDark: "#000000",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.H
        });
        console.log("QR Code generated successfully");
    } catch (error) {
        console.error("Error generating QR code:", error);
        qrContainer.innerHTML = `
            <div class="alert alert-info">
                <p>Please manually pay to UPI ID: <strong>${upiId}</strong></p>
                <p>Amount: <strong>₹${amount}</strong></p>
            </div>
        `;
    }
    
    // Initialize and show modal
    const paymentModal = new bootstrap.Modal(document.getElementById('paymentModal'));
    paymentModal.show();
    
    // Set up form submission
    const form = document.getElementById('payment-form');
    // Remove previous event listeners
    const newForm = form.cloneNode(true);
    form.parentNode.replaceChild(newForm, form);
    
    newForm.addEventListener('submit', function(event) {
        event.preventDefault();
        submitPaymentForm();
    });
}

function submitPaymentForm() {
    const paymentRequestId = document.getElementById('payment-request-id').value;
    const transactionId = document.getElementById('transaction-id').value;
    const paymentProofFile = document.getElementById('payment-proof').files[0];
    
    if (!paymentProofFile) {
        alert('Please upload a payment screenshot');
        return;
    }
    
    const formData = new FormData();
    formData.append('payment_request_id', paymentRequestId);
    formData.append('transaction_id', transactionId);
    formData.append('payment_proof', paymentProofFile);
    
    fetch('/api/patient/submit-payment', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal
            const paymentModal = bootstrap.Modal.getInstance(document.getElementById('paymentModal'));
            paymentModal.hide();
            
            // Show success message and reload data
            alert('Payment submitted successfully!');
            loadPaymentRequests();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error submitting payment:', error);
        alert('Failed to submit payment. Please try again.');
    });
}

function getBadgeClass(status) {
    switch (status) {
        case 'paid':
            return 'bg-success';
        case 'pending':
            return 'bg-warning text-dark';
        case 'failed':
            return 'bg-danger';
        case 'cancelled':
            return 'bg-secondary';
        default:
            return 'bg-primary';
    }
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}