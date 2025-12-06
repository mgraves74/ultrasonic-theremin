// dashboard.js
// Client-side JavaScript for theremin dashboard

// ===== SOCKET.IO CONNECTION =====
const socket = io();

// ===== GLOBAL STATE =====
let frequencyChart = null;
const frequencyHistory = {
    timestamps: [],
    values: []
};
const MAX_HISTORY_SECONDS = 20;  // 20 second window

// ===== SOCKET EVENT HANDLERS =====

// Connection established
socket.on('connect', () => {
    console.log('Connected to server');
    document.getElementById('connection-dot').classList.add('connected');
    document.getElementById('connection-text').textContent = 'Connected';
});

// Connection lost
socket.on('disconnect', () => {
    console.log('Disconnected from server');
    document.getElementById('connection-dot').classList.remove('connected');
    document.getElementById('connection-text').textContent = 'Disconnected';
});

// Audio state update (frequency, volume, playing status)
socket.on('audio_state', (data) => {
    // update frequency display
    const freq_display = document.getElementById('frequency-display');
    if (data.frequency > 0) {
        freq_display.textContent = Math.round(data.frequency) + ' Hz';
    } else {
        freq_display.textContent = '0 Hz';
    }
    
    // update note display
    const note_display = document.getElementById('note-display');
    note_display.textContent = frequency_to_note(data.frequency);
    
    // update volume display
    const volume_display = document.getElementById('volume-display');
    volume_display.textContent = Math.round(data.volume * 100) + '%';
    
    // update playing status
    const status_dot = document.getElementById('status-dot');
    const status_text = document.getElementById('status-text');
    if (data.playing) {
        status_dot.classList.add('playing');
        status_text.textContent = 'PLAYING';
    } else {
        status_dot.classList.remove('playing');
        status_text.textContent = 'SILENT';
    }
    
    // add frequency to history for chart
    add_frequency_point(data.frequency);
});

// Sensor update (distance, volume with timestamp)
socket.on('sensor_update', (data) => {
    // update distance display
    const distance_display = document.getElementById('distance-display');
    distance_display.textContent = data.distance.toFixed(1) + ' cm';
});

// Waveform data
socket.on('waveform_data', (data) => {
    draw_waveform(data.samples);
});

// ===== HELPER FUNCTIONS =====

// Convert frequency to musical note name (A432 tuning)
function frequency_to_note(freq) {
    if (freq === 0 || freq === null) {
        return '—';
    }
    
    const A4 = 432.0;  // A432 tuning
    const C0 = A4 * Math.pow(2, -4.75);  // C0 reference
    
    const h = Math.round(12 * Math.log2(freq / C0));
    const octave = Math.floor(h / 12);
    const n = h % 12;
    
    const note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    
    return note_names[n] + octave;
}

// Add new frequency point to history and update chart
function add_frequency_point(frequency) {
    const current_time = Date.now() / 1000;  // convert to seconds
    
    // add new point
    frequencyHistory.timestamps.push(current_time);
    frequencyHistory.values.push(frequency);
    
    // remove old points outside time window
    const cutoff_time = current_time - MAX_HISTORY_SECONDS;
    while (frequencyHistory.timestamps.length > 0 && 
           frequencyHistory.timestamps[0] < cutoff_time) {
        frequencyHistory.timestamps.shift();
        frequencyHistory.values.shift();
    }
    
    // update chart
    update_frequency_chart();
}

// Update frequency chart with current history
function update_frequency_chart() {
    if (!frequencyChart) return;
    
    // convert timestamps to relative time (seconds ago)
    const current_time = Date.now() / 1000;
    const labels = frequencyHistory.timestamps.map(ts => {
        return -(current_time - ts);  // negative for "seconds ago"
    });
    
    frequencyChart.data.labels = labels;
    frequencyChart.data.datasets[0].data = frequencyHistory.values;
    frequencyChart.update('none');  // update without animation for smoothness
}

// Draw waveform on canvas
function draw_waveform(samples) {
    const canvas = document.getElementById('waveform-canvas');
    const ctx = canvas.getContext('2d');
    
    // set canvas size to match display size
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
    // clear canvas (dark grey background)
    ctx.fillStyle = '#2c3e50';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    if (!samples || samples.length === 0) return;
    
    // draw waveform
    const center_y = canvas.height / 2;
    const amplitude = canvas.height * 0.4;  // use 80% of height for waveform
    
    // green waveform line
    ctx.strokeStyle = '#28a745';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    for (let i = 0; i < samples.length; i++) {
        const x = (i / samples.length) * canvas.width;
        const y = center_y - (samples[i] * amplitude);
        
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    
    ctx.stroke();
    
    // draw center line (white, semi-transparent)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, center_y);
    ctx.lineTo(canvas.width, center_y);
    ctx.stroke();
}

// ===== INITIALIZATION =====

// Initialize frequency chart with Chart.js
function init_frequency_chart() {
    const ctx = document.getElementById('frequency-chart').getContext('2d');
    
    frequencyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Frequency (Hz)',
                data: [],
                borderColor: '#5b9bd5',
                backgroundColor: 'rgba(91, 155, 213, 0.2)',
                borderWidth: 2,
                pointRadius: 0,  // no points, just line
                tension: 0.4,  // smooth curves
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,  // disable for real-time performance
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Time (seconds ago)',
                        color: '#ffffff'
                    },
                    ticks: {
                        color: '#ffffff',
                        callback: function(value) {
                            return Math.abs(Math.round(value));
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    min: -MAX_HISTORY_SECONDS,
                    max: 0
                },
                y: {
                    title: {
                        display: true,
                        text: 'Frequency (Hz)',
                        color: '#ffffff'
                    },
                    ticks: {
                        color: '#ffffff'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    min: 0,
                    max: 1200
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
    
    console.log('Dashboard initialized');
}

// Initialize chart when page loads
window.addEventListener('load', () => {
    init_frequency_chart();
});

// Handle window resize for canvas
window.addEventListener('resize', () => {
    const canvas = document.getElementById('waveform-canvas');
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
});