# Quarto 1.11.9, orange-book 0.7.1, Source Serif 4, Inter, and Poppler.
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    HOME=/root \
    LANG=C.UTF-8 \
    XDG_CACHE_HOME=/opt/cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl fontconfig unzip poppler-utils \
    && curl -fsSL -o /tmp/quarto.deb https://github.com/quarto-dev/quarto-cli/releases/download/v1.11.9/quarto-1.11.9-linux-amd64.deb \
    && apt-get install -y /tmp/quarto.deb \
    && rm -f /tmp/quarto.deb \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/source-serif.zip https://github.com/adobe-fonts/source-serif/releases/download/4.005R/source-serif-4.005_Desktop.zip \
    && curl -fsSL -o /tmp/inter.zip https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip \
    && unzip -q /tmp/source-serif.zip -d /tmp/fonts-source \
    && unzip -q /tmp/inter.zip -d /tmp/fonts-inter \
    && mkdir -p /usr/local/share/fonts \
    && find /tmp/fonts-source /tmp/fonts-inter -type f \( -iname '*.otf' -o -iname '*.ttf' \) -exec cp {} /usr/local/share/fonts/ \; \
    && fc-cache -f \
    && rm -rf /tmp/source-serif.zip /tmp/inter.zip /tmp/fonts-source /tmp/fonts-inter

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY physics_studio ./physics_studio
COPY fixtures ./fixtures
COPY scripts ./scripts
COPY tests ./tests

# Compile the real template once so orange-book is cached and the show rule is known to build.
RUN cd /app && PYTHONPATH=/app python /app/scripts/warm_template.py /opt/warm \
    && cd /opt/warm \
    && quarto render --to typst \
    && test -f /opt/warm/_render/physics.pdf \
    && rm -rf /opt/warm

EXPOSE 8080
CMD ["python", "-m", "physics_studio"]
