FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install cron and required packages
RUN apt-get update && apt-get -y install cron && \
    apt-get clean && rm -rf /var/lib/apt/lists/* \
    apt-get install vim

# Install compatible versions of numpy and pandas
RUN pip install --no-cache-dir numpy==1.24.3
RUN pip install --no-cache-dir pandas==2.0.3 requests==2.31.0 beautifulsoup4==4.12.2 openpyxl==3.1.2
# Install additional dependencies for handling various Excel formats
RUN pip install --no-cache-dir odfpy xlrd xlwt

# Copy script and other files
COPY fb.py /app/fb.py
COPY fb.xlsx /app/fb.xlsx

# Create a cron job file with absolute path to Python
RUN echo "0 * * * * /usr/local/bin/python /app/fb.py >> /app/fb_poster.log 2>&1" > /etc/cron.d/fb-poster-cron
RUN chmod 0644 /etc/cron.d/fb-poster-cron
RUN chmod 0644 /app/fb.xlsx

# Apply cron job to crontab
RUN crontab /etc/cron.d/fb-poster-cron

# Create log file and set permissions
RUN touch /app/fb_poster.log && chmod 666 /app/fb_poster.log

# Create an entrypoint script
RUN echo '#!/bin/sh\nservice cron start\ntail -f /app/fb_poster.log' > /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run the entrypoint script when the container launches
CMD ["/app/entrypoint.sh"]