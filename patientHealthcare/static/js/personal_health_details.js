document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-tab');

            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });

    const radioButtons = document.querySelectorAll('input[type="radio"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', function() {
            const textarea = this.closest('.form-group').querySelector('textarea');
            if (this.value === 'no') {
                textarea.value = 'No';
                textarea.disabled = true;
            } else {
                textarea.value = '';
                textarea.disabled = false;
            }
        });
    });
});
// Add this to your personal_health_details.js file
document.addEventListener('DOMContentLoaded', function() {
    const surgeryYes = document.getElementById('surgeryYes');
    const surgeryNo = document.getElementById('surgeryNo');
    const surgeryDetailsSection = document.getElementById('surgeryDetailsSection');
    
    // Function to toggle surgery details section
    function toggleSurgeryDetails(show) {
        surgeryDetailsSection.style.display = show ? 'block' : 'none';
        
        // Clear file input and textarea when hiding the section
        if (!show) {
            const fileInput = document.getElementById('surgeryFiles');
            const textarea = document.getElementById('previousSurgeries');
            if (fileInput) fileInput.value = '';
            if (textarea) textarea.value = '';
        }
    }
    
    // Add event listeners to radio buttons
    if (surgeryYes && surgeryNo && surgeryDetailsSection) {
        surgeryYes.addEventListener('change', () => toggleSurgeryDetails(true));
        surgeryNo.addEventListener('change', () => toggleSurgeryDetails(false));
        
        // Set initial state based on loaded data
        if (surgeryYes.checked) {
            toggleSurgeryDetails(true);
        } else if (surgeryNo.checked) {
            toggleSurgeryDetails(false);
        }
    }
});