'use strict';

const { createService, simulateWork } = require('./common');

const { app, start } = createService('product');

const products = Array.from({ length: 100 }, (_, i) => ({
  id: i + 1,
  name: `Product ${i + 1}`,
  price: Math.round((10 + Math.random() * 490) * 100) / 100,
  stock: 1000,
}));

app.get('/products', async (req, res) => {
  await simulateWork(10, 30);
  res.json(products.slice(0, 20));
});

app.get('/products/:id', async (req, res) => {
  await simulateWork(3, 12);
  const product = products.find((p) => p.id === Number(req.params.id));
  if (!product) return res.status(404).json({ error: 'product not found' });
  return res.json(product);
});

start(Number(process.env.PORT) || 3002);
