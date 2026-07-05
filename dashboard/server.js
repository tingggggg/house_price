const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;
const TRENDS_PATH = path.join(__dirname, '..', 'data', 'processed', 'trends.json');

app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/trends', (req, res) => {
  fs.readFile(TRENDS_PATH, 'utf-8', (err, data) => {
    if (err) {
      res.status(503).json({ error: '趨勢資料尚未產生，請先執行 python 資料管線 (run_pipeline.py)' });
      return;
    }
    res.type('json').send(data);
  });
});

app.listen(PORT, () => {
  console.log(`台中房價趨勢儀表板已啟動：http://localhost:${PORT}`);
});
