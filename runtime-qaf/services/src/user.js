'use strict';

const { createService, simulateWork } = require('./common');

const { app, start } = createService('user');

const users = Array.from({ length: 50 }, (_, i) => ({
  id: i + 1,
  name: `User ${i + 1}`,
  email: `user${i + 1}@example.com`,
}));

app.get('/users', async (req, res) => {
  await simulateWork(5, 20);
  res.json(users.slice(0, 20));
});

app.get('/users/:id', async (req, res) => {
  await simulateWork(2, 10);
  const user = users.find((u) => u.id === Number(req.params.id));
  if (!user) return res.status(404).json({ error: 'user not found' });
  return res.json(user);
});

start(Number(process.env.PORT) || 3001);
