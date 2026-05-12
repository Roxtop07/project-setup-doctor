const express = require('express');
const app = express();

const key = process.env.API_KEY;

app.get('/', (req, res) => {
  res.send('Hello from fullstack app');
});

app.listen(3000);
