// Event-specific theme configurations
const EVENT_THEMES = {
    'Birthday': [
        { name: 'Neon Party', emoji: '⚡', value: 'Neon Party' },
        { name: 'Balloon Fest', emoji: '🎈', value: 'Balloon Fest' },
        { name: 'Confetti Pop', emoji: '🎊', value: 'Confetti Pop' },
        { name: 'Cake Dreams', emoji: '🎂', value: 'Cake Dreams' }
    ],
    'Wedding': [
        { name: 'Royal Elegance', emoji: '👑', value: 'Royal Elegance' },
        { name: 'Floral Romance', emoji: '🌸', value: 'Floral Romance' },
        { name: 'Classic White', emoji: '🤍', value: 'Classic White' },
        { name: 'Garden Dream', emoji: '🌿', value: 'Garden Dream' }
    ],
    'Party': [
        { name: 'Disco Lights', emoji: '🪩', value: 'Disco Lights' },
        { name: 'Beach Vibes', emoji: '🏖️', value: 'Beach Vibes' },
        { name: 'Retro Funk', emoji: '🕺', value: 'Retro Funk' },
        { name: 'Glow Party', emoji: '💫', value: 'Glow Party' }
    ],
    'Corporate': [
        { name: 'Professional', emoji: '💼', value: 'Professional' },
        { name: 'Modern Tech', emoji: '💻', value: 'Modern Tech' },
        { name: 'Luxury Gold', emoji: '✨', value: 'Luxury Gold' },
        { name: 'Minimal Clean', emoji: '⚪', value: 'Minimal Clean' }
    ],
    'Anniversary': [
        { name: 'Romantic Rose', emoji: '🌹', value: 'Romantic Rose' },
        { name: 'Golden Years', emoji: '💛', value: 'Golden Years' },
        { name: 'Champagne', emoji: '🥂', value: 'Champagne' },
        { name: 'Starry Night', emoji: '⭐', value: 'Starry Night' }
    ],
    'Baby Shower': [
        { name: 'Baby Blue', emoji: '💙', value: 'Baby Blue' },
        { name: 'Soft Pink', emoji: '💗', value: 'Soft Pink' },
        { name: 'Pastel Rainbow', emoji: '🌈', value: 'Pastel Rainbow' },
        { name: 'Teddy Bear', emoji: '🧸', value: 'Teddy Bear' }
    ]
};

document.addEventListener('DOMContentLoaded', () => {
    // State
    let state = {
        eventType: 'Birthday',
        vibe: null,
        familyName: '',
        celebrantName: '',
        eventDate: '',
        eventTime: '',
        eventVenue: '',
        eventMessage: '',
        userPhotoUrl: null,
        generatedData: null,
        selectedMusic: null
    };

    // Elements
    const vibeSelector = document.getElementById('vibeSelector');
    const generateBtn = document.getElementById('generateBtn');
    const resultSection = document.getElementById('resultSection');
    const inputForm = document.getElementById('inputForm');
    const cardTitle = document.getElementById('cardTitle');
    const cardBody = document.getElementById('cardBody');
    const generatedImage = document.getElementById('generatedImage');
    const skeletonLoader = document.getElementById('skeletonLoader');
    const regenerateBtn = document.getElementById('regenerateBtn');

    // Initialize Uploadcare
    const widget = uploadcare.Widget('[role=uploadcare-uploader]');

    // Custom validator for max size 40MB
    widget.validators.push(function (fileInfo) {
        if (fileInfo.size !== null && fileInfo.size > 40 * 1024 * 1024) {
            throw new Error('File is too large. Maximum size is 40MB.');
        }
    });

    widget.onUploadComplete(info => {
        state.userPhotoUrl = info.cdnUrl;
        console.log('Photo uploaded:', state.userPhotoUrl);
        alert('Photo uploaded successfully!');
    });

    // Function to render themes based on event type
    function renderThemes(eventType) {
        const themes = EVENT_THEMES[eventType] || EVENT_THEMES['Birthday'];
        vibeSelector.innerHTML = themes.map(theme => `
            <div class="vibe-card" data-vibe="${theme.value}">
                <div class="glass-card rounded-xl p-6 md:p-8 border-2 border-white/20 hover:border-purple-400/50 transition-all duration-300 h-32 md:h-40 flex flex-col justify-center items-center touch-manipulation cursor-pointer">
                    <div class="text-3xl md:text-5xl mb-2 md:mb-3">${theme.emoji}</div>
                    <span class="text-xs md:text-sm font-semibold text-white">${theme.name}</span>
                </div>
            </div>
        `).join('');

        // Re-attach click listeners
        attachVibeListeners();

        // Auto-select first theme
        const firstCard = vibeSelector.querySelector('.vibe-card');
        if (firstCard) {
            firstCard.click();
        }
    }

    // Attach vibe selection listeners
    function attachVibeListeners() {
        vibeSelector.querySelectorAll('.vibe-card').forEach(card => {
            card.addEventListener('click', () => {
                // Remove selected class from all
                document.querySelectorAll('.vibe-card').forEach(c => c.classList.remove('selected'));

                // Add to clicked
                card.classList.add('selected');
                state.vibe = card.dataset.vibe;
            });
        });
    }

    // Event type button handlers
    const eventTypeSelector = document.getElementById('eventTypeSelector');
    eventTypeSelector.addEventListener('click', (e) => {
        const btn = e.target.closest('.event-type-btn');
        if (!btn) return;

        // Remove selected from all buttons
        document.querySelectorAll('.event-type-btn').forEach(b => b.classList.remove('selected'));

        // Add selected to clicked button
        btn.classList.add('selected');

        // Update state and render themes
        state.eventType = btn.dataset.event;
        renderThemes(state.eventType);
    });

    // Initialize with Birthday themes
    renderThemes('Birthday');

    // Generate Handler
    generateBtn.addEventListener('click', async () => {
        // Get all input values
        state.familyName = document.getElementById('familyName').value.trim();
        state.celebrantName = document.getElementById('celebrantName').value.trim();
        state.eventDate = document.getElementById('eventDate').value.trim();
        state.eventTime = document.getElementById('eventTime').value.trim();
        state.eventVenue = document.getElementById('eventVenue').value.trim();
        state.eventMessage = document.getElementById('eventMessage').value.trim();

        // Validation
        if (!state.familyName) {
            alert('Please enter the family name!');
            return;
        }

        if (!state.celebrantName) {
            alert('Please enter the celebrant name!');
            return;
        }

        if (!state.eventDate) {
            alert('Please enter the event date!');
            return;
        }

        if (!state.eventTime) {
            alert('Please enter the event time!');
            return;
        }

        if (!state.eventVenue) {
            alert('Please enter the event venue!');
            return;
        }

        if (!state.vibe) {
            alert('Please select a theme!');
            return;
        }

        if (!state.userPhotoUrl) {
            alert('Please upload a photo to continue!');
            return;
        }

        setButtonLoading(generateBtn, true);

        try {
            // Build detailed prompt
            const details = `Join us for ${state.celebrantName}'s ${state.eventType} celebration! ${state.eventDate} at ${state.eventTime} at ${state.eventVenue}. ${state.eventMessage}`;

            // Step 1: Refine Prompt with Enhanced Details (Gemini)
            const refineResponse = await fetch('/api/refine-prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    eventType: state.eventType,
                    vibe: state.vibe,
                    details: details,
                    familyName: state.familyName,
                    celebrantName: state.celebrantName
                })
            });

            if (refineResponse.status === 401) {
                alert('Please login to generate invitations!');
                window.location.href = '/login';
                return;
            }

            const refineResult = await refineResponse.json();
            if (!refineResult.success) throw new Error(refineResult.error);

            state.generatedData = refineResult.data;

            // Step 2: Generate Image
            const imageResponse = await fetch('/api/generate-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_prompt: state.generatedData.image_prompt,
                    user_photo_url: state.userPhotoUrl,
                    title: state.generatedData.card_title,
                    body: state.generatedData.card_body,
                    eventType: state.eventType,
                    vibe: state.vibe,
                    familyName: state.familyName,
                    celebrantName: state.celebrantName,
                    eventDate: state.eventDate,
                    eventTime: state.eventTime,
                    eventVenue: state.eventVenue,
                    eventMessage: state.eventMessage,
                    location_name: state.eventVenue
                })
            });

            const imageResult = await imageResponse.json();
            if (!imageResult.success) throw new Error(imageResult.error);

            // Store invitation data FIRST (before displaying)
            if (imageResult.invitation_id) {
                state.invitation_id = imageResult.invitation_id;
                state.share_link = imageResult.share_link;
                console.log('Invitation created with ID:', state.invitation_id);
            }

            // Display results (now state.invitation_id is available)
            displayResults(imageResult.image_url);

        } catch (error) {
            console.error('Generation error:', error);
            alert(`Error: ${error.message}`);
        } finally {
            setButtonLoading(generateBtn, false);
        }
    });

    function displayResults(imageUrl) {
        // Show result section
        resultSection.classList.remove('hidden');
        inputForm.scrollIntoView({ behavior: 'smooth' });

        // Set background image
        generatedImage.src = imageUrl;
        generatedImage.style.display = 'block';
        skeletonLoader.style.display = 'none';

        // Display family name
        const familyNameText = document.getElementById('familyNameText');
        if (familyNameText) {
            familyNameText.textContent = state.familyName;
        }

        // Display user photo
        const userPhotoContainer = document.getElementById('userPhotoContainer');
        const userPhotoOverlay = document.getElementById('userPhotoOverlay');
        if (state.userPhotoUrl && userPhotoContainer && userPhotoOverlay) {
            userPhotoOverlay.src = state.userPhotoUrl;
            userPhotoContainer.classList.remove('hidden');
        }

        // Display celebrant name
        if (cardTitle) {
            cardTitle.textContent = state.celebrantName;
        }

        // Display event details
        const dateText = document.getElementById('dateText');
        const timeText = document.getElementById('timeText');
        const venueText = document.getElementById('venueText');

        if (dateText) dateText.textContent = state.eventDate;
        if (timeText) timeText.textContent = state.eventTime;
        if (venueText) venueText.textContent = state.eventVenue;

        // Display message
        if (cardBody && state.eventMessage) {
            cardBody.textContent = state.eventMessage;
        } else if (cardBody) {
            cardBody.textContent = state.generatedData?.card_body || 'Join us for this special celebration!';
        }

        // Setup public link
        if (state.share_link) {
            const publicLinkBtn = document.getElementById('publicLinkBtn');
            if (publicLinkBtn) {
                publicLinkBtn.href = `/invite/${state.share_link}`;
            }
        }

        // Store invitation_id globally for video generation
        if (state.invitation_id) {
            window.currentInvitationId = state.invitation_id;
            // Also store in a data attribute on the result section
            resultSection.dataset.invitationId = state.invitation_id;
            console.log('Invitation ID stored:', state.invitation_id);
        }

        // Reinitialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Scroll to results
        setTimeout(() => {
            resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 500);
    }

    // Video Generation with Music Selection
    const generateVideoBtn = document.getElementById('generateVideoBtn');
    if (generateVideoBtn) {
        generateVideoBtn.addEventListener('click', async () => {
            // Check both state and global variable
            let invitationId = state.invitation_id || window.currentInvitationId || resultSection?.dataset?.invitationId;
            
            // If still not found, try to get it from the share link
            if (!invitationId) {
                const publicLinkBtn = document.getElementById('publicLinkBtn');
                if (publicLinkBtn && publicLinkBtn.href) {
                    const shareLink = publicLinkBtn.href.split('/invite/')[1];
                    if (shareLink) {
                        console.log('Fetching invitation ID from share link:', shareLink);
                        try {
                            const response = await fetch(`/api/get-invitation-id-by-link/${shareLink}`);
                            const result = await response.json();
                            if (result.success) {
                                invitationId = result.invitation_id;
                                state.invitation_id = invitationId;
                                window.currentInvitationId = invitationId;
                                console.log('Retrieved invitation ID:', invitationId);
                            }
                        } catch (error) {
                            console.error('Error fetching invitation ID:', error);
                        }
                    }
                }
            }
            
            if (!invitationId) {
                alert('Please generate an invitation first!');
                return;
            }

            // Store in state if found in global/dataset
            if (!state.invitation_id && invitationId) {
                state.invitation_id = invitationId;
                window.currentInvitationId = invitationId;
            }

            console.log('Starting video generation for invitation:', invitationId);

            // Show music modal
            openMusicModal();
        });
    }

    // Regenerate button
    if (regenerateBtn) {
        regenerateBtn.addEventListener('click', () => {
            resultSection.classList.add('hidden');
            inputForm.scrollIntoView({ behavior: 'smooth' });
            
            // Reset state
            state.generatedData = null;
            state.invitation_id = null;
            state.share_link = null;
        });
    }

    // Helper functions
    function setButtonLoading(button, loading) {
        if (loading) {
            button.dataset.originalText = button.innerHTML;
            button.innerHTML = '<div class="spinner-border spinner-border-sm"></div> Generating...';
            button.disabled = true;
        } else {
            button.innerHTML = button.dataset.originalText || button.innerHTML;
            button.disabled = false;
        }
    }
});

// Music Modal Functions (Global scope for onclick handlers)
function openMusicModal() {
    const modal = document.getElementById('musicModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

function closeMusicModal() {
    const modal = document.getElementById('musicModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

async function generateVideoWithMusic(musicChoice) {
    closeMusicModal();

    const generateVideoBtn = document.getElementById('generateVideoBtn');
    const originalHTML = generateVideoBtn.innerHTML;
    generateVideoBtn.innerHTML = '<div class="spinner"></div> Generating Video (30-60s)...';
    generateVideoBtn.disabled = true;

    try {
        // Get invitation_id from multiple possible sources
        const resultSection = document.getElementById('resultSection');
        const invitation_id = window.currentInvitationId || 
                              resultSection?.dataset?.invitationId || 
                              document.querySelector('[data-invitation-id]')?.dataset.invitationId;

        console.log('🎬 Starting video generation...');
        console.log('Invitation ID:', invitation_id);
        console.log('Music choice:', musicChoice);

        if (!invitation_id) {
            throw new Error('No invitation found. Please generate an invitation first.');
        }

        console.log('Sending request to /api/generate-video...');

        const response = await fetch('/api/generate-video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                invitation_id: invitation_id,
                music: musicChoice,
                duration: 10 // 10 seconds as requested
            })
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server error:', errorText);
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        console.log('Response data:', result);

        if (!result.success) {
            throw new Error(result.error || 'Failed to generate video');
        }

        console.log('✅ Video generated successfully!');
        console.log('Video URL:', result.video_url);

        // Show download button
        const downloadVideoBtn = document.getElementById('downloadVideoBtn');
        if (downloadVideoBtn) {
            downloadVideoBtn.href = result.video_url;
            downloadVideoBtn.classList.remove('hidden');
            console.log('Download button shown');
        }

        alert('🎉 Video generated successfully! Click the "Download Video" button to save it.');

    } catch (error) {
        console.error('❌ Video generation error:', error);
        console.error('Error details:', error.message);
        alert(`Error generating video:\n${error.message}\n\nCheck browser console (F12) for details.`);
    } finally {
        generateVideoBtn.innerHTML = originalHTML;
        generateVideoBtn.disabled = false;
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

// Close modal on outside click
document.getElementById('musicModal')?.addEventListener('click', function(e) {
    if (e.target === this) {
        closeMusicModal();
    }
});

// Initialize Lucide icons
if (typeof lucide !== 'undefined') {
    lucide.createIcons();
}

