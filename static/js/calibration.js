const canvas = document.getElementById('stampCanvas');
const ctx = canvas.getContext('2d');
const stampSelect = document.getElementById('stampSelect');
const coordX = document.getElementById('coordX');
const coordY = document.getElementById('coordY');
const fontFamily = document.getElementById('fontFamily');
const fontSize = document.getElementById('fontSize');
const fontColor = document.getElementById('fontColor');
const previewText = document.getElementById('previewText');
const saveBtn = document.getElementById('saveBtn');
const statusMessage = document.getElementById('statusMessage');

let currentImage = null;
let allConfigs = {};

// Initialize
async function init() {
    await loadStamps();
    await loadConfig();
    if (stampSelect.options.length > 0) {
        loadStampImage(stampSelect.value);
    }
}

// Load list of stamps
async function loadStamps() {
    const response = await fetch('/api/stamps');
    const stamps = await response.json();
    stampSelect.innerHTML = '';
    stamps.forEach(stamp => {
        const option = document.createElement('option');
        option.value = stamp;
        option.textContent = stamp;
        stampSelect.appendChild(option);
    });
}

// Load existing configuration
async function loadConfig() {
    const response = await fetch('/api/config');
    allConfigs = await response.json();
}

// Load selected stamp image
function loadStampImage(filename) {
    const img = new Image();
    img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        currentImage = img;
        
        // Apply existing config if available
        if (allConfigs[filename]) {
            const conf = allConfigs[filename];
            coordX.value = conf.x || 0;
            coordY.value = conf.y || 0;
            fontFamily.value = conf.font || 'Arial';
            fontSize.value = conf.size || 24;
            fontColor.value = conf.color || '#000000';
        } else {
            // Defaults
            coordX.value = Math.floor(img.width / 2);
            coordY.value = Math.floor(img.height / 2);
        }
        draw();
    };
    img.src = `/images/${filename}`;
}

// Draw everything
function draw() {
    if (!currentImage) return;

    // Clear and draw image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(currentImage, 0, 0);

    // Draw text
    const text = previewText.value;
    const x = parseInt(coordX.value) || 0;
    const y = parseInt(coordY.value) || 0;
    const size = parseInt(fontSize.value) || 24;
    const family = fontFamily.value;
    const color = fontColor.value;

    ctx.font = `${size}px ${family}`;
    ctx.fillStyle = color;
    ctx.textAlign = 'center'; // Center text horizontally at the point
    ctx.textBaseline = 'middle'; // Center text vertically at the point
    ctx.fillText(text, x, y);

    // Draw a small crosshair to show exact point
    ctx.strokeStyle = 'rgba(0, 255, 0, 0.7)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x - 10, y);
    ctx.lineTo(x + 10, y);
    ctx.moveTo(x, y - 10);
    ctx.lineTo(x, y + 10);
    ctx.stroke();
}

// Event Listeners
stampSelect.addEventListener('change', (e) => loadStampImage(e.target.value));

[coordX, coordY, fontFamily, fontSize, fontColor, previewText].forEach(el => {
    el.addEventListener('input', () => {
        // Update config object in memory
        const filename = stampSelect.value;
        if (!allConfigs[filename]) allConfigs[filename] = {};
        allConfigs[filename].x = parseInt(coordX.value);
        allConfigs[filename].y = parseInt(coordY.value);
        allConfigs[filename].font = fontFamily.value;
        allConfigs[filename].size = parseInt(fontSize.value);
        allConfigs[filename].color = fontColor.value;
        
        draw();
    });
});

canvas.addEventListener('mousedown', (e) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const x = Math.round((e.clientX - rect.left) * scaleX);
    const y = Math.round((e.clientY - rect.top) * scaleY);

    coordX.value = x;
    coordY.value = y;
    
    // Trigger input event to update config and redraw
    coordX.dispatchEvent(new Event('input'));
});

saveBtn.addEventListener('click', async () => {
    // Ensure current values are saved to the object
    const filename = stampSelect.value;
    allConfigs[filename] = {
        x: parseInt(coordX.value),
        y: parseInt(coordY.value),
        font: fontFamily.value,
        size: parseInt(fontSize.value),
        color: fontColor.value
    };

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(allConfigs)
        });
        const result = await response.json();
        if (result.status === 'success') {
            statusMessage.textContent = 'Configuration Saved!';
            statusMessage.className = 'success';
            setTimeout(() => statusMessage.textContent = '', 3000);
        } else {
            throw new Error('Save failed');
        }
    } catch (err) {
        statusMessage.textContent = 'Error saving configuration.';
        statusMessage.className = 'error';
    }
});

// Start
init();
