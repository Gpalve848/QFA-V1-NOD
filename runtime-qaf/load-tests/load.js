// k6 workload for the experiments. Select the traffic level with -e PROFILE=low|medium|peak|spike
//   docker compose run --rm k6 run -e PROFILE=medium /scripts/load.js

import http from 'k6/http';
import { check, sleep } from 'k6';

const PROFILES = {
  low: [
    { duration: '30s', target: 5 },
    { duration: '4m', target: 5 },
    { duration: '15s', target: 0 },
  ],
  medium: [
    { duration: '30s', target: 25 },
    { duration: '4m', target: 25 },
    { duration: '15s', target: 0 },
  ],
  peak: [
    { duration: '1m', target: 100 },
    { duration: '4m', target: 100 },
    { duration: '15s', target: 0 },
  ],
  spike: [
    { duration: '1m', target: 10 },
    { duration: '10s', target: 150 },
    { duration: '1m', target: 150 },
    { duration: '10s', target: 10 },
    { duration: '2m', target: 10 },
    { duration: '10s', target: 0 },
  ],
};

const PROFILE = __ENV.PROFILE || 'low';
if (!PROFILES[PROFILE]) throw new Error(`Unknown PROFILE '${PROFILE}'`);

export const options = {
  stages: PROFILES[PROFILE],
  tags: { profile: PROFILE },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

const USER = __ENV.USER_URL || 'http://localhost:3001';
const PRODUCT = __ENV.PRODUCT_URL || 'http://localhost:3002';
const ORDER = __ENV.ORDER_URL || 'http://localhost:3003';

const rand = (n) => 1 + Math.floor(Math.random() * n);

// Traffic mix: 30% product listing, 20% product detail, 15% user lookup, 35% order checkout.
export default function () {
  const r = Math.random();
  let res;
  if (r < 0.3) {
    res = http.get(`${PRODUCT}/products`, { tags: { name: 'list-products' } });
  } else if (r < 0.5) {
    res = http.get(`${PRODUCT}/products/${rand(100)}`, { tags: { name: 'get-product' } });
  } else if (r < 0.65) {
    res = http.get(`${USER}/users/${rand(50)}`, { tags: { name: 'get-user' } });
  } else {
    res = http.post(
      `${ORDER}/orders`,
      JSON.stringify({ userId: rand(50), productId: rand(100), quantity: rand(3) }),
      { headers: { 'Content-Type': 'application/json' }, tags: { name: 'create-order' } },
    );
  }
  check(res, { 'status < 500': (x) => x.status < 500 });
  sleep(0.5 + Math.random());
}
