FROM playground-nix:latest

ENV DD_FETCH=1
ENV DD_CUDD=1

WORKDIR /deps

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN pysmt-install --msat --confirm-agreement
RUN patch -i constants.patch $(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")/theorydd/constants.py
RUN python pysmt-postinstall.py

CMD ["sleep" "infinity"]
