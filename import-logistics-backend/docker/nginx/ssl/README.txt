Put your TLS certificate here (never commit it):
    fullchain.pem   certificate + intermediates
    privkey.pem     private key

For a quick local test, a self-signed certificate (browsers will warn once):
    openssl req -x509 -nodes -newkey rsa:2048 -days 30 -keyout privkey.pem -out fullchain.pem -subj "/CN=localhost"

For a real domain use Let's Encrypt (certbot) and point these two files at the issued certificate.
