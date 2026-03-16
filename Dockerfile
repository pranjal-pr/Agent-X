FROM node:20-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

USER node

ENV HOME=/home/node \
    PATH=/home/node/.local/bin:$PATH \
    NODE_ENV=space \
    PORT=7860 \
    PYTHON_EXECUTABLE=python3

WORKDIR $HOME/app

COPY --chown=node:node package.json package-lock.json requirements.txt ./

RUN npm ci --omit=dev \
    && python3 -m pip install --no-cache-dir --user -r requirements.txt

COPY --chown=node:node . .

EXPOSE 7860

CMD ["npm", "start"]
