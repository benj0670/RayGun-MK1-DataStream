const potValueEl = document.getElementById('pot_value');
const hallStateEl = document.getElementById('hall_state');
const photoStateEl = document.getElementById('photo_state');
const accelXEl = document.getElementById('accel_x');
const accelYEl = document.getElementById('accel_y');
const accelZEl = document.getElementById('accel_z');
const batteryStatusEl = document.getElementById('battery_status');
const batteryLevelEl = document.getElementById('battery_level');
const connectButton = document.getElementById('connectButton');
const needlePositionEl = document.getElementById('needle_position');
const ammoLeftEl = document.getElementById('ammo');
const data = {};
var barrel = "";

async function readSerialData() {
    try {
        // 1. Request access to a serial port
        const serialPort = await navigator.serial.requestPort();
        
        // 2. Open the serial port with the correct baud rate (must match CircuitPython settings, typically 115200)
        await serialPort.open({ baudRate: 115200 });
        
        console.log("Serial port opened successfully.");

        const reader = serialPort.readable.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // 3. Start continuous reading loop
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true});

            // Process data line by line (assuming data is sent as newline-delimited custom strings)
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep the partial line if there is one

            for (const line of lines) {
                if (line.trim()) {
                    
                    // Custom parsing logic: Split by comma to get individual pairs
                    const pairs = line.split(',');
                    
                    for (const pair of pairs) {
                        if (pair.includes(':')) {
                            const parts = pair.split(':');
                            if (parts.length === 2) {
                                const key = parts[0].trim().replace(/[{}]/g, '');
                                const value = parts[1].trim().replace(/[{}]/g, '');
                                //console.log("Found key: " + key + "   and value: " + value)
                                // Store the parsed key-value pair
                                data[key] = value;
                            }
                        }
                    }

                    // Display the extracted data
                    hallStateEl.textContent = data["'barrel_open'"].replace(/[']/g, '') || '--';
                    potValueEl.textContent = data["'pot_value'"] || '--';
                    photoStateEl.textContent = data["'photo_state'"] || '--';
                    accelXEl.textContent = data["'accel_x'"] || '--';
                    accelYEl.textContent = data["'accel_y'"] || '--';
                    accelZEl.textContent = data["'accel_z'"] || '--';
                    batteryStatusEl.textContent = data["'battery_status'"].replace(/[']/g, '') || '--';
                    needlePositionEl.textContent = data["'needle_position'"];
                    ammoLeftEl.textContent = 20 - data["'ammo'"];
                }
            }
        }
        
        await serialPort.close();
        console.log("Serial port closed.");

    } catch (error) {
        console.error("Error accessing serial port or reading data:", error);
        hallStateEl.textContent = "Connection Failed";
        photoStateEl.textContent = "Connection Failed";
        alert("Failed to connect to serial device. Check permissions and device selection.");
    }
}

// Attach the function to the button click event
connectButton.addEventListener('click', readSerialData);
