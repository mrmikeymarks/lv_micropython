# Node.js application image
FROM node:20-alpine AS base

WORKDIR /usr/src/app

# Install dependencies first so this layer is cached until package files change
COPY package*.json ./
RUN npm install --omit=dev

COPY . .

# Data directory for the tally store; owning it as node before dropping
# privileges means a named volume mounted here inherits writable ownership.
RUN mkdir -p /usr/src/app/data && chown -R node:node /usr/src/app/data

# Run as the unprivileged user shipped with the official node image
USER node

ENV NODE_ENV=production \
    PORT=3000

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/health || exit 1

CMD ["node", "server.js"]
