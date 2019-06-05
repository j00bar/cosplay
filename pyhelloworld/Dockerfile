FROM fedora:30

RUN dnf -y install python3-pip && dnf clean all

ADD . /src

RUN cd /src; pip3 install -r requirements.txt

EXPOSE 8080

CMD ["/usr/bin/python3", "/src/index.py"]