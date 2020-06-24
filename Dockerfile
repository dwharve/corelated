FROM python
ENV PYTHONUNBUFFERED=0
RUN mkdir /opt/correlated
WORKDIR /opt/correlated
COPY . .
RUN apt-get update && apt-get -y install vim && pip3 install -Iv elasticsearch==6.3.1 pyyaml

CMD python3 -u correlate.py 4
