FROM python:latest
RUN apt-get update && apt-get install -y apt-utils gcc python3-dev libldap2-dev libsasl2-dev libssl-dev libffi-dev
WORKDIR /app
COPY . /app/
CMD mkdir -p /var/log/ftp-web-client
RUN pip install --no-cache-dir -r /app/requirements.txt
CMD python web_admin.py