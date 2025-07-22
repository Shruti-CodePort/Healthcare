// Video Call Functionality
document.addEventListener('DOMContentLoaded', function() {
    // WebRTC variables
    let localStream;
    let peerConnection;
    let roomId = document.querySelector('.appointment-info strong:nth-of-type(2)').nextSibling.textContent.trim();
    
    // DOM elements
    const localVideo = document.getElementById('localVideo');
    const remoteVideo = document.getElementById('remoteVideo');
    const toggleMicrophoneBtn = document.getElementById('toggleMicrophone');
    const toggleCameraBtn = document.getElementById('toggleCamera');
    const toggleScreenShareBtn = document.getElementById('toggleScreenShare');
    const endCallBtn = document.getElementById('endCall');
    const connectingOverlay = document.getElementById('connectingOverlay');
    const completeAppointmentBtn = document.getElementById('completeAppointment');
    const saveNotesBtn = document.getElementById('saveNotes');
    const consultationNotes = document.getElementById('consultationNotes');
    const callTimer = document.getElementById('callTimer');
    
    // Call timer variables
    let callDuration = 0;
    let timerInterval;
    
    // WebRTC configuration
    const configuration = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ]
    };
    
    // Initialize the call
    async function initCall() {
        try {
            // Get local media stream
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localVideo.srcObject = localStream;
            
            // Set up signaling via a WebSocket connection
            setupSignaling();
            
            // Start call timer
            startTimer();
            
        } catch (error) {
            console.error('Error accessing media devices:', error);
            alert('Error accessing camera or microphone. Please check your device permissions.');
        }
    }
    
    // Set up WebRTC signaling
    function setupSignaling() {
        // In a real application, you would use WebSockets or another signaling mechanism
        // This is a simplified example
        console.log('Setting up signaling for room:', roomId);
        
        // Simulate a connection being established after 3 seconds
        setTimeout(() => {
            // Hide the connecting overlay
            connectingOverlay.style.display = 'none';
            
            // Create a peer connection
            createPeerConnection();
            
            // For demo purposes, we're just showing the local video in both places
            // In a real application, the remote video would be from the other participant
            const remoteStream = localStream.clone();
            remoteVideo.srcObject = remoteStream;
            
        }, 3000);
    }
    
    // Create and set up the RTCPeerConnection
    function createPeerConnection() {
        peerConnection = new RTCPeerConnection(configuration);
        
        // Add local tracks to the peer connection
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
        
        // Handle ICE candidates
        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                // Send ICE candidate to the other peer through signaling
                console.log('New ICE candidate:', event.candidate);
            }
        };
        
        // Handle connection state changes
        peerConnection.onconnectionstatechange = event => {
            console.log('Connection state change:', peerConnection.connectionState);
        };
        
        // Handle receiving remote streams
        peerConnection.ontrack = event => {
            console.log('Received remote track');
            remoteVideo.srcObject = event.streams[0];
        };
    }
    
    // Start the call timer
    function startTimer() {
        timerInterval = setInterval(() => {
            callDuration++;
            updateTimerDisplay();
        }, 1000);
    }
    
    // Update the timer display
    function updateTimerDisplay() {
        const hours = Math.floor(callDuration / 3600);
        const minutes = Math.floor((callDuration % 3600) / 60);
        const seconds = callDuration % 60;
        
        callTimer.textContent = [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            seconds.toString().padStart(2, '0')
        ].join(':');
    }
    
    // Toggle microphone
    toggleMicrophoneBtn.addEventListener('click', () => {
        const audioTracks = localStream.getAudioTracks();
        if (audioTracks.length === 0) return;
        
        const enabled = !audioTracks[0].enabled;
        audioTracks[0].enabled = enabled;
        
        toggleMicrophoneBtn.innerHTML = enabled ? 
            '<i class="fas fa-microphone"></i>' : 
            '<i class="fas fa-microphone-slash"></i>';
    });
    
    // Toggle camera
    toggleCameraBtn.addEventListener('click', () => {
        const videoTracks = localStream.getVideoTracks();
        if (videoTracks.length === 0) return;
        
        const enabled = !videoTracks[0].enabled;
        videoTracks[0].enabled = enabled;
        
        toggleCameraBtn.innerHTML = enabled ? 
            '<i class="fas fa-video"></i>' : 
            '<i class="fas fa-video-slash"></i>';
    });
    
    // Toggle screen sharing
    toggleScreenShareBtn.addEventListener('click', async () => {
        const videoTracks = localStream.getVideoTracks();
        
        if (videoTracks[0].label.includes('screen')) {
            // Switch back to camera
            try {
                const cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
                const cameraTrack = cameraStream.getVideoTracks()[0];
                
                // Replace the track in the peer connection
                const senders = peerConnection.getSenders();
                const videoSender = senders.find(sender => sender.track.kind === 'video');
                videoSender.replaceTrack(cameraTrack);
                
                // Replace the track in the local stream
                videoTracks[0].stop();
                localStream.removeTrack(videoTracks[0]);
                localStream.addTrack(cameraTrack);
                
                // Update UI
                toggleScreenShareBtn.innerHTML = '<i class="fas fa-desktop"></i>';
                localVideo.srcObject = localStream;
                
            } catch (error) {
                console.error('Error switching to camera:', error);
            }
        } else {
            // Switch to screen sharing
            try {
                const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
                const screenTrack = screenStream.getVideoTracks()[0];
                
                // Listen for the user ending screen sharing
                screenTrack.onended = () => {
                    toggleScreenShareBtn.click();
                };
                
                // Replace the track in the peer connection
                const senders = peerConnection.getSenders();
                const videoSender = senders.find(sender => sender.track.kind === 'video');
                videoSender.replaceTrack(screenTrack);
                
                // Replace the track in the local stream
                videoTracks[0].stop();
                localStream.removeTrack(videoTracks[0]);
                localStream.addTrack(screenTrack);
                
                // Update UI
                toggleScreenShareBtn.innerHTML = '<i class="fas fa-stop-circle"></i>';
                localVideo.srcObject = localStream;
                
            } catch (error) {
                console.error('Error sharing screen:', error);
            }
        }
    });
    
    // End call
    endCallBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to end this consultation?')) {
            endCall();
            window.location.href = '/doctor/video_consultation';
        }
    });
    
    // Complete appointment
    completeAppointmentBtn.addEventListener('click', function() {
        const appointmentId = this.dataset.appointmentId;
        
        if (confirm('Are you sure you want to mark this appointment as completed?')) {
            fetch(`/doctor/complete_appointment/${appointmentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Appointment marked as completed. The call will now end.');
                    endCall();
                    window.location.href = '/doctor/video_consultation';
                } else {
                    alert(data.message || 'Failed to complete appointment');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while completing the appointment');
            });
        }
    });
    
    // Save consultation notes
    saveNotesBtn.addEventListener('click', () => {
        const appointmentId = completeAppointmentBtn.dataset.appointmentId;
        const notes = consultationNotes.value.trim();
        
        if (notes) {
            fetch(`/doctor/save_consultation_notes/${appointmentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ notes: notes })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Consultation notes saved successfully');
                } else {
                    alert(data.message || 'Failed to save notes');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while saving notes');
            });
        } else {
            alert('Please enter some notes before saving');
        }
    });
    
    // Clean up and end the call
    function endCall() {
        // Stop the timer
        clearInterval(timerInterval);
        
        // Close peer connection
        if (peerConnection) {
            peerConnection.close();
            peerConnection = null;
        }
        
        // Stop all tracks in the local stream
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
        }
    }
    
    // Handle page unload
    window.addEventListener('beforeunload', () => {
        endCall();
    });
    
    // Initialize the call when the page loads
    initCall();
});