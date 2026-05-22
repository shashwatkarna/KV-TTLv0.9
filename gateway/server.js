const express = require('express');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const net = require('net');

const app = express();
app.use(express.json());
app.use(morgan('dev'));

// Rate Limiter: max 100 requests per 1 minute
const limiter = rateLimit({
    windowMs: 60 * 1000,
    max: 100,
    message: { error: 'Too many requests, please try again later.' }
});
app.use(limiter);

const DB_HOST = '127.0.0.1';
const DB_PORT = 9000;

// Helper to communicate with the Go TCP socket server
function queryDatabase(command) {
    return new Promise((resolve, reject) => {
        const client = new net.Socket();
        
        client.connect(DB_PORT, DB_HOST, () => {
            client.write(command + '\n');
        });

        client.on('data', (data) => {
            resolve(data.toString().trim());
            client.destroy();
        });

        client.on('error', (err) => {
            reject(err);
        });
    });
}

// REST endpoints
app.post('/set', async (req, res) => {
    const { key, value, ttl } = req.body;
    if (!key || value === undefined) {
        return res.status(400).json({ error: 'Missing key or value' });
    }

    const valueStr = typeof value === 'object' ? JSON.stringify(value) : String(value);
    const ttlVal = ttl && ttl > 0 ? parseInt(ttl) : 0;
    
    // Command format: SET <key> <ttl> <value>
    const cmd = `SET ${key} ${ttlVal} ${valueStr}`;
    
    try {
        const reply = await queryDatabase(cmd);
        if (reply === 'OK') {
            res.json({ status: 'success', message: `Key '${key}' set successfully.` });
        } else {
            res.status(500).json({ error: reply });
        }
    } catch (err) {
        res.status(500).json({ error: 'Database connection failed', details: err.message });
    }
});

app.get('/get/:key', async (req, res) => {
    const { key } = req.params;
    
    try {
        const reply = await queryDatabase(`GET ${key}`);
        if (reply.startsWith('VALUE ')) {
            const rawVal = reply.substring(6).replace(/\\n/g, '\n');
            let value;
            try {
                value = JSON.parse(rawVal);
            } catch {
                value = rawVal;
            }
            res.json({ key, value });
        } else if (reply === 'ERR NOT_FOUND') {
            res.status(404).json({ error: 'Key not found or expired' });
        } else {
            res.status(500).json({ error: reply });
        }
    } catch (err) {
        res.status(500).json({ error: 'Database connection failed', details: err.message });
    }
});

app.delete('/delete/:key', async (req, res) => {
    const { key } = req.params;
    
    try {
        const reply = await queryDatabase(`DEL ${key}`);
        if (reply === 'DELETED') {
            res.json({ status: 'success', message: `Key '${key}' deleted successfully.` });
        } else if (reply === 'ERR NOT_FOUND') {
            res.status(404).json({ error: 'Key not found' });
        } else {
            res.status(500).json({ error: reply });
        }
    } catch (err) {
        res.status(500).json({ error: 'Database connection failed', details: err.message });
    }
});

const PORT = 8000;
app.listen(PORT, () => {
    console.log(`Node.js API Gateway listening on http://localhost:${PORT}`);
});
