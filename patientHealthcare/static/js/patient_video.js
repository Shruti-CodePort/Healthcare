// Patient Video Consultation JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(`${tabId}-consultations`).classList.add('active');
        });
    });
    
    // Modal handling for prescriptions
    const prescriptionModal = document.getElementById('prescription-modal');
    const prescriptionButtons = document.querySelectorAll('.view-prescription-btn');
    const closePrescriptionModal = prescriptionModal.querySelector('.close-modal');
    
    prescriptionButtons.forEach(button => {
        button.addEventListener('click', () => {
            const appointmentId = button.getAttribute('data-appointment-id');
            loadPrescription(appointmentId);
            prescriptionModal.style.display = 'block';
        });
    });
    
    closePrescriptionModal.addEventListener('click', () => {
        prescriptionModal.style.display = 'none';
    });
    
    // Modal handling for chat history
    const chatModal = document.getElementById('chat-modal');
    const chatButtons = document.querySelectorAll('.view-chat-btn');
    const closeChatModal = chatModal.querySelector('.close-modal');
    
    chatButtons.forEach(button => {
        button.addEventListener('click', () => {
            const appointmentId = button.getAttribute('data-appointment-id');
            loadChatHistory(appointmentId);
            chatModal.style.display = 'block';
        });
    });
    
    closeChatModal.addEventListener('click', () => {
        chatModal.style.display = 'none';
    });
    
    // Close modals when clicking outside
    window.addEventListener('click', (event) => {
        if (event.target === prescriptionModal) {
            prescriptionModal.style.display = 'none';
        }
        if (event.target === chatModal) {
            chatModal.style.display = 'none';
        }
    });
    
    // Print prescription functionality
    const printButton = document.getElementById('print-prescription');
    if (printButton) {
        printButton.addEventListener('click', () => {
            const prescriptionContent = document.getElementById('prescription-content').innerHTML;
            const printWindow = window.open('', '_blank');
            
            printWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Prescription</title>
                    <style>
                        body { font-family: Arial, sans-serif; padding: 20px; }
                        .prescription-header { text-align: center; margin-bottom: 20px; }
                        .prescription-content { border: 1px solid #ddd; padding: 15px; }
                    </style>
                </head>
                <body>
                    <div class="prescription-header">
                        <h2>Medical Prescription</h2>
                    </div>
                    <div class="prescription-content">
                        ${prescriptionContent}
                    </div>
                </body>
                </html>
            `);
            
            printWindow.document.close();
            printWindow.focus();
            
            // Wait for content to load before printing
            setTimeout(() => {
                printWindow.print();
                printWindow.close();
            }, 500);
        });
    }

    // Function to load prescription data
    function loadPrescription(appointmentId) {
        const prescriptionContent = document.getElementById('prescription-content');
        prescriptionContent.innerHTML = '<div class="loading">Loading prescription...</div>';
        
        // Fetch prescription data from server
        fetch(`/api/prescription/${appointmentId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load prescription');
                }
                return response.json();
            })
            .then(data => {
                if (data.prescription) {
                    let htmlContent = `
                        <div class="prescription-header">
                            <p><strong>Doctor:</strong> Dr. ${data.doctor_name}</p>
                            <p><strong>Date:</strong> ${data.date}</p>
                        </div>
                        <div class="prescription-items">
                    `;
                    
                    // Parse prescription content - assuming it's stored with some structure
                    // This would depend on how you're formatting prescriptions in the chat
                    data.prescription.forEach(item => {
                        htmlContent += `
                            <div class="prescription-item">
                                <p><strong>${item.medication}</strong></p>
                                <p>Dosage: ${item.dosage}</p>
                                <p>Instructions: ${item.instructions}</p>
                            </div>
                        `;
                    });
                    
                    htmlContent += `
                        </div>
                        <div class="prescription-notes">
                            <p><strong>Additional Notes:</strong></p>
                            <p>${data.notes || 'None'}</p>
                        </div>
                    `;
                    
                    prescriptionContent.innerHTML = htmlContent;
                } else {
                    prescriptionContent.innerHTML = '<p>No prescription found for this consultation.</p>';
                }
            })
            .catch(error => {
                prescriptionContent.innerHTML = `<p class="error">Error: ${error.message}</p>`;
            });
    }

    // Function to load chat history
    function loadChatHistory(appointmentId) {
        const chatHistoryContent = document.getElementById('chat-history-content');
        chatHistoryContent.innerHTML = '<div class="loading">Loading chat history...</div>';
        
        // Fetch chat history from server
        fetch(`/api/chat-history/${appointmentId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load chat history');
                }
                return response.json();
            })
            .then(data => {
                if (data.messages && data.messages.length > 0) {
                    let htmlContent = '';
                    
                    data.messages.forEach(message => {
                        const messageClass = message.sender_type === 'doctor' ? 'doctor' : 'patient';
                        const formattedTime = new Date(message.timestamp).toLocaleTimeString();
                        
                        htmlContent += `
                            <div class="chat-message ${messageClass}">
                                <div class="message-header">
                                    <span>${message.sender_name}</span>
                                    <span>${formattedTime}</span>
                                </div>
                                <div class="message-content">
                                    ${message.content}
                                </div>
                                ${message.is_prescription ? '<div class="prescription-message"><i class="fas fa-prescription"></i> Prescription</div>' : ''}
                            </div>
                        `;
                    });
                    
                    chatHistoryContent.innerHTML = htmlContent;
                } else {
                    chatHistoryContent.innerHTML = '<p>No chat messages found for this consultation.</p>';
                }
            })
            .catch(error => {
                chatHistoryContent.innerHTML = `<p class="error">Error: ${error.message}</p>`;
            });
    }
    
    // Update countdown timer for upcoming consultations
    function updateCountdowns() {
        const joinButtons = document.querySelectorAll('.join-btn.disabled');
        
        joinButtons.forEach(button => {
            const minutesText = button.innerText.match(/\d+/);
            if (minutesText) {
                let minutes = parseInt(minutesText[0]);
                
                if (minutes <= 1) {
                    // Refresh the page to update joinable status when time is up
                    location.reload();
                } else {
                    minutes--;
                    button.innerHTML = `<i class="fas fa-video"></i> Join (${minutes} min)`;
                }
            }
        });
    }
    
    // Update countdown every minute
    setInterval(updateCountdowns, 60000);
});