FROM debian:12-slim

ARG NOVNC_VERSION=1.5.0

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99

WORKDIR /opt/vnc-cloak

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xvfb \
        x11vnc \
        supervisor \
        openbox \
        websockify \
        socat \
        chromium \
        ffmpeg \
        curl \
        ca-certificates \
        x11-utils \
    && mkdir -p /usr/share/novnc \
    && curl -fsSL "https://github.com/novnc/noVNC/archive/refs/tags/v${NOVNC_VERSION}.tar.gz" \
        | tar -xz --strip-components=1 -C /usr/share/novnc \
    && ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/vnc-cloak/

RUN mkdir -p /profiles /var/log/supervisor \
    && if [ -f /opt/vnc-cloak/chromium-launch.sh ]; then chmod +x /opt/vnc-cloak/chromium-launch.sh; fi

EXPOSE 5900 6080 9222

CMD ["supervisord", "-c", "/opt/vnc-cloak/supervisord.conf"]
