FROM python:3.13

RUN apt update -y
RUN apt install curl -y
RUN curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install linux \
  --determinate \
  --init none \
  --no-confirm
ENV PATH="${PATH}:/nix/var/nix/profiles/default/bin"

WORKDIR /flake

COPY ./flake .

RUN --mount=type=secret,id=nix-config,env=NIX_CONFIG \
  nix profile add .#bundle \
  && nix-collect-garbage -d

WORKDIR /deps

COPY ./python .

RUN pip install --no-cache-dir -r requirements.txt
RUN pysmt-install --msat --confirm-agreement
RUN patch -i constants.patch $(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")/theorydd/constants.py
RUN python pysmt-postinstall.py

CMD ["bash"]
