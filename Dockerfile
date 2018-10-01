FROM prnet_http_server:base

WORKDIR /prnet_http_server
COPY prnet_wsgi.py /prnet_http_server/
COPY PRNet /prnet_http_server/PRNet
RUN ln -s PRNet/Data

ENTRYPOINT ["gunicorn", "prnet_wsgi:handle_request", "-b", ":8000"]
EXPOSE 8000
