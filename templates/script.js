document.addEventListener('DOMContentLoaded', () => {
    const imageUpload = document.getElementById('imageUpload');
    const wishesText = document.getElementById('wishesText');
    const nameText = document.getElementById('nameText');
    const textLines = document.getElementById('textLines');
    
    const wishesFontSizeSlider = document.getElementById('wishesFontSizeSlider');
    const wishesFontSizeValue = document.getElementById('wishesFontSizeValue');
    const nameFontSizeSlider = document.getElementById('nameFontSizeSlider');
    const nameFontSizeValue = document.getElementById('nameFontSizeValue');

    const generateButton = document.getElementById('generateButton');
    const regenerateButton = document.getElementById('regenerateButton');
    const outputImage = document.getElementById('outputImage');
    const downloadLink = document.getElementById('downloadLink');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const originalPreview = document.getElementById('originalPreview');

    let currentImageFile = null;

    // Update slider value display
    wishesFontSizeSlider.addEventListener('input', (e) => {
        wishesFontSizeValue.textContent = e.target.value;
    });
    nameFontSizeSlider.addEventListener('input', (e) => {
        nameFontSizeValue.textContent = e.target.value;
    });

    imageUpload.addEventListener('change', (event) => {
        currentImageFile = event.target.files[0];
        if (currentImageFile) {
            const reader = new FileReader();
            reader.onload = (e) => {
                originalPreview.src = e.target.result;
                originalPreview.style.display = 'block';
            }
            reader.readAsDataURL(currentImageFile);
            // Reset output if new image is uploaded
            outputImage.style.display = 'none';
            downloadLink.style.display = 'none';
            regenerateButton.style.display = 'none';
            generateButton.style.display = 'inline-block'; // Or 'block' depending on layout
            generateButton.disabled = false; // Re-enable generate button
        } else {
            originalPreview.style.display = 'none';
        }
    });

    function processCardRequest() {
        if (!currentImageFile) {
            alert('Oops! Please upload an image first.');
            return;
        }
        if (!wishesText.value.trim()) {
            alert('Please enter some wishes text (e.g., Happy Birthday).');
            return;
        }
        if (!nameText.value.trim()) {
            alert('Who is this card for? Please enter a name.');
            return;
        }

        loadingIndicator.style.display = 'flex'; // Use flex for spinner alignment
        outputImage.style.display = 'none';
        downloadLink.style.display = 'none';
        generateButton.disabled = true;
        regenerateButton.disabled = true;

        const formData = new FormData();
        formData.append('image', currentImageFile);
        formData.append('wishes_text', wishesText.value);
        formData.append('name_text', nameText.value);
        formData.append('text_lines', textLines.value);
        // Send font size multipliers (value / 100)
        formData.append('wishes_font_size_multiplier', parseFloat(wishesFontSizeSlider.value) / 100);
        formData.append('name_font_size_multiplier', parseFloat(nameFontSizeSlider.value) / 100);
        // The backend will now always apply its randomization logic, so no explicit 'regenerate' flag is strictly needed
        // unless you want different logic paths for initial generation vs. regeneration.
        // For this setup, every call is a "new style" generation.

        fetch('http://127.0.0.1:5000/process-image', {
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) {
                // Try to parse JSON error from backend first
                return response.json().then(errData => {
                    throw new Error(errData.error || `Server error: ${response.status}`);
                }).catch(() => {
                    // If backend didn't send JSON or it was malformed
                    throw new Error(`Image processing failed. Status: ${response.status}`);
                });
            }
            return response.blob();
        })
        .then(blob => {
            const objectURL = URL.createObjectURL(blob);
            outputImage.src = objectURL;
            outputImage.style.display = 'block';
            
            downloadLink.href = objectURL;
            const safeName = nameText.value.trim().toLowerCase().replace(/\s+/g, '_') || 'custom';
            downloadLink.download = `${safeName}_card.jpg`;
            downloadLink.style.display = 'inline-block';
            
            generateButton.style.display = 'none'; // Hide initial generate
            regenerateButton.style.display = 'inline-block'; // Show regenerate
        })
        .catch(error => {
            console.error('Processing Error:', error);
            alert('Failed to create card: ' + error.message);
            // Show generate button again if it was the initial attempt, or keep regenerate visible
            if (!regenerateButton.style.display || regenerateButton.style.display === 'none'){
                generateButton.style.display = 'inline-block';
            }
        })
        .finally(() => {
            loadingIndicator.style.display = 'none';
            generateButton.disabled = false; // Always re-enable buttons
            regenerateButton.disabled = false;
        });
    }

    generateButton.addEventListener('click', processCardRequest);
    regenerateButton.addEventListener('click', processCardRequest); // Regenerate uses the same enhanced function
});