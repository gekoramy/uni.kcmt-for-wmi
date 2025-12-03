FROM python:3.13

ARG GITHUB_TOKEN

RUN apt update -y
RUN apt install curl -y
RUN curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install linux \
  --determinate \
  --init none \
  --extra-conf "access-tokens = github.com=${GITHUB_TOKEN}"\
  --no-confirm
ENV PATH="${PATH}:/nix/var/nix/profiles/default/bin"

WORKDIR /flake

COPY . .

RUN nix profile add .#bundle

CMD ["bash"]
