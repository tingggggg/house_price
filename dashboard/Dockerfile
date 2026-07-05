FROM node:20-slim

WORKDIR /app/dashboard

COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm install --omit=dev

COPY dashboard/ ./

EXPOSE 3000

CMD ["npm", "start"]
