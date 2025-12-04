FROM python:3.13

RUN apt update -y
RUN apt install curl -y
RUN --mount=type=secret,id=GITHUB_TOKEN,env=GITHUB_TOKEN \
  curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install linux \
  --determinate \
  --init none \
  --extra-conf "access-tokens = github.com=${GITHUB_TOKEN}"\
  --no-confirm
ENV PATH="${PATH}:/nix/var/nix/profiles/default/bin"

WORKDIR /flake

COPY ./flake .

RUN nix profile add .#bundle

ENV DD_FETCH=1
ENV DD_CUDD=1

WORKDIR /deps

COPY ./python .

RUN pip install --no-cache-dir -r requirements.txt
RUN pysmt-install --msat --confirm-agreement
RUN patch -i constants.patch $(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")/theorydd/constants.py
RUN python pysmt-postinstall.py

CMD ["bash"]
