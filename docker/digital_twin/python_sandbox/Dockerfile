FROM python:3.11-slim
RUN pip install --no-cache-dir \
    numpy scipy gymnasium stable-baselines3 \
    matplotlib pandas pytest
RUN mkdir -p /workspace
WORKDIR /workspace
CMD ["tail", "-f", "/dev/null"]
