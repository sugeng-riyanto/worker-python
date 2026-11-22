# Quarto 1.11.9, textbook fonts (Source Sans 3, Barlow Condensed, Source Serif 4, Inter), and Poppler.
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

# Static textbook fonts for Typst (variable fonts render poorly) plus WOFF2 for the HTML.
RUN mkdir -p /usr/local/share/fonts/textbook \
    && curl -fsSL -o /tmp/ss3.zip https://github.com/adobe-fonts/source-sans/releases/download/3.052R/OTF-source-sans-3.052R.zip \
    && curl -fsSL -o /tmp/ss3w.zip https://github.com/adobe-fonts/source-sans/releases/download/3.052R/WOFF2-source-sans-3.052R.zip \
    && unzip -q /tmp/ss3.zip -d /tmp/ss3 && unzip -q /tmp/ss3w.zip -d /tmp/ss3w \
    && for w in Regular It Semibold SemiboldIt Bold BoldIt Black; do cp /tmp/ss3/OTF/SourceSans3-$w.otf /usr/local/share/fonts/textbook/; done \
    && for w in Regular It Bold; do cp /tmp/ss3w/WOFF2/OTF/SourceSans3-$w.otf.woff2 /usr/local/share/fonts/textbook/SourceSans3-$w.woff2; done \
    && for w in Regular Medium SemiBold Bold ExtraBold; do curl -fsSL -o /usr/local/share/fonts/textbook/BarlowCondensed-$w.ttf https://github.com/google/fonts/raw/main/ofl/barlowcondensed/BarlowCondensed-$w.ttf; done \
    && curl -fsSL -o /usr/local/share/fonts/textbook/NotoSansMath-Regular.ttf https://github.com/google/fonts/raw/main/ofl/notosansmath/NotoSansMath-Regular.ttf \
    && fc-cache -f \
    && rm -rf /tmp/ss3.zip /tmp/ss3w.zip /tmp/ss3 /tmp/ss3w

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY physics_studio ./physics_studio
COPY fixtures ./fixtures
COPY scripts ./scripts
COPY tests ./tests

# Every palette must pass the WCAG AA contrast checks, and math / justification /
# scaffold / graph-paper filters must hold in every format, or the build fails.
RUN cd /app && python -m unittest -q tests.test_palettes tests.test_v142

# Compile the real template once so a broken template fails the build.
RUN cd /app && PYTHONPATH=/app python /app/scripts/warm_template.py /opt/warm \
    && cd /opt/warm \
    && quarto render --to typst \
    && test -f /opt/warm/_render/physics.pdf \
    && rm -rf /opt/warm

EXPOSE 8080
CMD ["python", "-m", "physics_studio"]
