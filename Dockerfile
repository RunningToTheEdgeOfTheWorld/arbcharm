FROM pypy:3-6

# base
RUN cp -f /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo 'Asia/Shanghai' >/etc/timezone \
    && apt-get update -y \
    && pip install --upgrade pip

# project
COPY . /opt/project

WORKDIR /opt/project

RUN pip install /opt/project

CMD ["pypy3", "-m", "arbcharm"]
