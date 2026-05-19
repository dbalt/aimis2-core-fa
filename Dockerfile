FROM docker-dev.registry-ci.delta.sbrf.ru/ci04675739/ci04675739/minimal:9.6.2-se

USER root
RUN set -x && microdnf upgrade -y && microdnf install -y --nodocs python3.12 python3.12-pip && microdnf clean all 
#&& ln -s /usr/bin/python3.12 /usr/bin/python3 && ln -s /usr/bin/pip3.12 /usr/bin/pip3

ARG APP='app'
ARG TOKEN

WORKDIR /${APP}
RUN mkdir /tmp_bld 
COPY . /tmp_bld    

RUN microdnf install -y gcc gcc-c++ libffi-devel zlib-devel libjpeg-turbo-devel python3.12-devel make \
    && python3.12 -m ensurepip \
    && python3.12 -m pip install --upgrade pip \
    && python3.12 -m pip install patchelf nuitka --index-url=https://token:${TOKEN}@sberosc.sigma.sbrf.ru/repo/pypi/simple --trusted-host=sberosc.sigma.sbrf.ru \
    && python3.12 -m pip install --no-cache-dir -r /tmp_bld/requirements.txt --index-url=https://token:${TOKEN}@sberosc.sigma.sbrf.ru/repo/pypi/simple --trusted-host=sberosc.sigma.sbrf.ru \
    && python3.12 -m nuitka \
        --standalone \
        --output-dir=/app \
        --output-filename=run_fa_server.bin \
        --remove-output \
        --include-package=coredis \
        --include-package=pandas \
        --include-package=numpy \
        /tmp_bld/src/run__fa_server.py \
    && rm -rf /tmp_bld \
    && mv /app/run__fa_server.dist /app/cake \
    && rm -rf /usr/bin/python3.6 \
    && rm -rf /usr/bin/python3.12 \
    && rm -rf /usr/lib/python3.6/site-packages \
    && rm -rf /usr/lib/python3.12/site-packages \
    && rm -rf /usr/local/lib/python3.12/site-packages
    
# FROM docker-dev.registry-ci.delta.sbrf.ru/ci04675739/ci04675739/python-3.12:8.10.1-se #
# COPY --from=compiler /app/pybin/run_fa_server.dist/ /app/
WORKDIR /app/cake

CMD ./run_fa_server.bin
