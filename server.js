const express = require('express');
const csv = require('csv-parser');
const fs = require('fs');
const cors = require('cors');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

let sensorData = [];
let allDataLoaded = false;
let realtimeConnections = new Set();
let currentDataIndex = 0;

function loadAllCSVData() {
    const csvFilePath = 'sensor_data.csv';
    
    if (!fs.existsSync(csvFilePath)) {
        console.error('CSV file not found:', csvFilePath);
        return;
    }

    sensorData = [];
    console.log('📁 Loading ALL data from CSV...');
    
    fs.createReadStream(csvFilePath)
        .pipe(csv())
        .on('data', (row) => {
            const processedRow = {
                timestamp: row.time || row.timestamp || row.date || new Date().toISOString(),
                battery_voltage: parseFloat(row.battery_voltage) || parseFloat(row.battery) || parseFloat(row.voltage) || 0,
                humidity: parseFloat(row.humidity) || parseFloat(row.hum) || 0,
                motion: parseInt(row.motion) || parseFloat(row.motion) || 0,
                temperature: parseFloat(row.temperature) || parseFloat(row.temp) || 0,
                id: Math.random().toString(36).substr(2, 9) // Unique ID for each record
            };
            
            if (!isNaN(processedRow.temperature) && !isNaN(processedRow.humidity)) {
                sensorData.push(processedRow);
            }
        })
        .on('end', () => {
            console.log(`✅ Loaded ALL ${sensorData.length} records from CSV`);
            allDataLoaded = true;
            
            startRealtimeSimulation();
        })
        .on('error', (error) => {
            console.error('❌ Error reading CSV:', error);
        });
}

function startRealtimeSimulation() {
    setInterval(() => {
        if (sensorData.length === 0) return;
        
        currentDataIndex = (currentDataIndex + 1) % sensorData.length;
        const currentData = sensorData[currentDataIndex];
        
        const realtimeData = {
            ...currentData,
            realtime_timestamp: new Date().toISOString(),
            current_index: currentDataIndex,
            total_records: sensorData.length
        };
        
        broadcastRealtimeData(realtimeData);
        
    }, 2000); // Update every 2 seconds
}

function broadcastRealtimeData(data) {
    const message = JSON.stringify({
        type: 'realtime_update',
        data: data
    });
    
    realtimeConnections.forEach(client => {
        client.res.write(`data: ${message}\n\n`);
    });
}

app.get('/api/all-data', (req, res) => {
    if (sensorData.length === 0) {
        return res.status(404).json({ error: 'No data available' });
    }
    res.json(sensorData);
});

app.get('/api/current-data', (req, res) => {
    if (sensorData.length === 0) {
        return res.status(404).json({ error: 'No data available' });
    }
    
    const currentData = sensorData[currentDataIndex];
    res.json({
        ...currentData,
        realtime_timestamp: new Date().toISOString(),
        current_index: currentDataIndex,
        total_records: sensorData.length
    });
});

app.get('/api/statistics', (req, res) => {
    if (sensorData.length === 0) {
        return res.json({ error: 'No data available' });
    }
    
    const tempData = sensorData.map(d => d.temperature);
    const humidityData = sensorData.map(d => d.humidity);
    const batteryData = sensorData.map(d => d.battery_voltage);
    const motionData = sensorData.map(d => d.motion);
    
    const stats = {
        total_records: sensorData.length,
        data_range: {
            start: sensorData[0]?.timestamp,
            end: sensorData[sensorData.length - 1]?.timestamp
        },
        temperature: {
            min: Math.min(...tempData),
            max: Math.max(...tempData),
            avg: tempData.reduce((sum, val) => sum + val, 0) / tempData.length,
            std: Math.sqrt(tempData.reduce((sq, n) => sq + Math.pow(n - tempData.reduce((a, b) => a + b) / tempData.length, 2), 0) / tempData.length)
        },
        humidity: {
            min: Math.min(...humidityData),
            max: Math.max(...humidityData),
            avg: humidityData.reduce((sum, val) => sum + val, 0) / humidityData.length,
            std: Math.sqrt(humidityData.reduce((sq, n) => sq + Math.pow(n - humidityData.reduce((a, b) => a + b) / humidityData.length, 2), 0) / humidityData.length)
        },
        battery_voltage: {
            min: Math.min(...batteryData),
            max: Math.max(...batteryData),
            avg: batteryData.reduce((sum, val) => sum + val, 0) / batteryData.length,
            trend: batteryData[batteryData.length - 1] - batteryData[0]
        },
        motion: {
            total_detections: motionData.filter(val => val > 0).length,
            detection_rate: (motionData.filter(val => val > 0).length / motionData.length * 100).toFixed(1),
            longest_activation: findLongestActivation(motionData)
        },
        correlations: {
            temp_humidity: calculateCorrelation(tempData, humidityData),
            temp_battery: calculateCorrelation(tempData, batteryData)
        }
    };
    
    res.json(stats);
});

app.get('/api/realtime-stream', (req, res) => {
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    });
    
    const client = {
        id: Date.now(),
        res
    };
    
    realtimeConnections.add(client);
    
    console.log(`🔗 New real-time client connected: ${client.id}`);
    
    if (sensorData.length > 0) {
        const currentData = sensorData[currentDataIndex];
        const initialData = JSON.stringify({
            type: 'initial_data',
            data: {
                ...currentData,
                realtime_timestamp: new Date().toISOString(),
                current_index: currentDataIndex,
                total_records: sensorData.length
            }
        });
        res.write(`data: ${initialData}\n\n`);
    }
    
    req.on('close', () => {
        realtimeConnections.delete(client);
        console.log(`🔌 Real-time client disconnected: ${client.id}`);
    });
});

app.get('/api/recent-data/:limit', (req, res) => {
    const limit = parseInt(req.params.limit) || 50;
    const recentData = sensorData.slice(-limit);
    res.json(recentData);
});

app.post('/api/realtime-control', (req, res) => {
    const { action, speed } = req.body;
    
    console.log(`🎮 Real-time control: ${action} at speed ${speed}`);
    
    res.json({
        status: 'success',
        action: action,
        speed: speed,
        message: `Real-time simulation ${action}`
    });
});

function findLongestActivation(motionData) {
    let maxLength = 0;
    let currentLength = 0;
    
    for (const motion of motionData) {
        if (motion > 0) {
            currentLength++;
            maxLength = Math.max(maxLength, currentLength);
        } else {
            currentLength = 0;
        }
    }
    return maxLength;
}

function calculateCorrelation(x, y) {
    const n = x.length;
    const sum_x = x.reduce((a, b) => a + b, 0);
    const sum_y = y.reduce((a, b) => a + b, 0);
    const sum_xy = x.reduce((sum, val, i) => sum + val * y[i], 0);
    const sum_x2 = x.reduce((sum, val) => sum + val * val, 0);
    const sum_y2 = y.reduce((sum, val) => sum + val * val, 0);
    
    const numerator = n * sum_xy - sum_x * sum_y;
    const denominator = Math.sqrt((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y));
    
    return denominator === 0 ? 0 : (numerator / denominator).toFixed(3);
}

app.listen(PORT, () => {
    console.log(`🚀 Server running on http://localhost:${PORT}`);
    console.log(`📊 API Endpoints:`);
    console.log(`   GET /api/all-data - Get ALL sensor data`);
    console.log(`   GET /api/current-data - Get current real-time data`);
    console.log(`   GET /api/realtime-stream - Real-time SSE stream`);
    console.log(`   GET /api/recent-data/:limit - Get recent data`);
    console.log(`   GET /api/statistics - Get comprehensive statistics`);
    console.log(`   POST /api/realtime-control - Control real-time simulation`);
    loadAllCSVData();
});