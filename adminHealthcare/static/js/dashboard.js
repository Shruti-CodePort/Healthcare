document.addEventListener('DOMContentLoaded', function() {
    // Close alert messages
    document.querySelectorAll('.close-alert').forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.remove();
        });
    });

    // Search functionality with debounce
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }
});

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function handleSearch(e) {
    const searchTerm = e.target.value;
    if (searchTerm.length >= 2) {
        fetch(`/search_doctors?term=${encodeURIComponent(searchTerm)}`)
            .then(response => response.json())
            .then(updateDoctorsGrid)
            .catch(error => console.error('Search error:', error));
    }
}

function updateDoctorsGrid(doctors) {
    const grid = document.getElementById('doctorsGrid');
    grid.innerHTML = doctors.map(doctor => `
        <div class="doctor-card">
            <div class="card-header">
                <h3>${doctor.name}</h3>
                <div class="status-badge ${doctor.is_verified ? 'verified' : 'unverified'}">
                    ${doctor.is_verified ? 'Verified' : 'Unverified'}
                </div>
            </div>
            <div class="card-body">
                <p><strong>Specialty:</strong> ${doctor.specialty || 'Not specified'}</p>
                <p><strong>Email:</strong> ${doctor.email}</p>
            </div>
            <div class="card-actions">
                <a href="/view_documents/${doctor.id}" class="btn btn-primary">View Documents</a>
                <button onclick="showDoctorDetails(${doctor.id})" class="btn btn-secondary">Details</button>
            </div>
        </div>
    `).join('');
}

let currentDoctorId = null;

function showDoctorDetails(doctorId) {
    currentDoctorId = doctorId;
    fetch(`/get_doctor_details/${doctorId}`)
        .then(response => response.json())
        .then(displayDoctorDetails)
        .catch(error => console.error('Error fetching doctor details:', error));
}

function displayDoctorDetails(doctor) {
    const detailsDiv = document.getElementById('doctorDetails');
    detailsDiv.innerHTML = `
        <div class="details-grid">
            <p><strong>Name:</strong> ${doctor.name}</p>
            <p><strong>Email:</strong> ${doctor.email}</p>
            <p><strong>Specialty:</strong> ${doctor.specialty || 'Not specified'}</p>
            <p><strong>License:</strong> ${doctor.license_number || 'Not provided'}</p>
            <p><strong>Experience:</strong> ${doctor.experience_years || 0} years</p>
            <p><strong>Qualification:</strong> ${doctor.qualification || 'Not provided'}</p>
            <p><strong>Status:</strong> ${doctor.is_verified ? 'Verified' : 'Unverified'}</p>
        </div>
    `;
    document.getElementById('doctorModal').style.display = 'block';
}

function verifyDoctor() {
    updateDoctorVerification(true);
}

function unverifyDoctor() {
    updateDoctorVerification(false);
}

function updateDoctorVerification(verify) {
    if (!currentDoctorId) return;

    const notes = document.getElementById('verificationNotes').value;
    const url = verify ? 
        `/verify_doctor/${currentDoctorId}` : 
        `/unverify_doctor/${currentDoctorId}`;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ verification_notes: notes })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Error updating verification status: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while updating verification status');
    });
}

// Modal control
const modal = document.getElementById('doctorModal');
const closeBtn = document.querySelector('.modal .close');

closeBtn.onclick = function() {
    modal.style.display = 'none';
    currentDoctorId = null;
    document.getElementById('verificationNotes').value = '';
}

window.onclick = function(event) {
    if (event.target === modal) {
        modal.style.display = 'none';
        currentDoctorId = null;
        document.getElementById('verificationNotes').value = '';
    }
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    // Optionally show user-friendly error message
    // alert('An error occurred. Please try again or contact support if the problem persists.');
});