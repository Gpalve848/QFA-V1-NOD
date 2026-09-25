'use strict';

const { createService, callService, simulateWork } = require('./common');

const { app, start } = createService('order');

const USER_URL = process.env.USER_URL || 'http://localhost:3001';
const PRODUCT_URL = process.env.PRODUCT_URL || 'http://localhost:3002';
const PAYMENT_URL = process.env.PAYMENT_URL || 'http://localhost:3004';

const orders = new Map();
let nextId = 1;

// Order creation fans out to user, product and payment services, so faults in
// any dependency propagate here -- useful for observing quality degradation.
app.post('/orders', async (req, res) => {
  const { userId, productId, quantity = 1 } = req.body || {};
  if (!userId || !productId) {
    return res.status(400).json({ error: 'userId and productId are required' });
  }
  try {
    const [user, product] = await Promise.all([
      callService(USER_URL, `/users/${userId}`),
      callService(PRODUCT_URL, `/products/${productId}`),
    ]);
    const id = nextId++;
    const amount = Math.round(product.price * Number(quantity) * 100) / 100;
    const payment = await callService(PAYMENT_URL, '/payments', {
      method: 'POST',
      body: JSON.stringify({ orderId: id, amount }),
    });
    await simulateWork(5, 15);
    const order = { id, userId: user.id, productId: product.id, quantity: Number(quantity), amount, paymentId: payment.id };
    orders.set(id, order);
    if (orders.size > 10000) orders.delete(orders.keys().next().value);
    return res.status(201).json(order);
  } catch (err) {
    return res.status(err.status || 500).json({ error: err.message });
  }
});

app.get('/orders/:id', (req, res) => {
  const order = orders.get(Number(req.params.id));
  if (!order) return res.status(404).json({ error: 'order not found' });
  return res.json(order);
});

start(Number(process.env.PORT) || 3003);
