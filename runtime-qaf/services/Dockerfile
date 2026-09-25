FROM node:22-alpine

WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund
COPY src ./src

ENV NODE_ENV=production
# SERVICE selects which microservice to run: user | product | order | payment
CMD ["sh", "-c", "node src/${SERVICE}.js"]
