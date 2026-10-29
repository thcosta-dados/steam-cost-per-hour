# TLS tunnel between Power BI and Supabase (see stunnel.conf).
FROM alpine:3.22

RUN apk add --no-cache stunnel

# Configuration and Supabase's public root CA go inside the image: nothing secret here
COPY stunnel.conf supabase-root-ca-2021.crt /etc/stunnel/

# No privileges needed: the tunnel only listens on a high port and opens outgoing connections
USER nobody

CMD ["stunnel", "/etc/stunnel/stunnel.conf"]
