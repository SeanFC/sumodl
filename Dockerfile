FROM python:3.12-slim-bookworm

# All the libs here are for playwright
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates cron
    
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# Times are based on UK time, make sure the container knows about this
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app
COPY ./pyproject.toml /app/pyproject.toml
COPY ./uv.lock /app/uv.lock

RUN uv sync --locked
RUN uv run playwright install firefox 
RUN uv run playwright install-deps firefox 

COPY . /app

COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

# Run the system once and then start cron to keep running
CMD uv --directory /app run python -m sumodl && cron -f
