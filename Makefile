IMAGE_NAME ?= quay.io/carbonin/assisted-service-mcp
TAG ?= latest

.PHONY: build
build:
	podman build -t $(IMAGE_NAME):$(TAG) .

.PHONY: push
push:
	podman push $(IMAGE_NAME):$(TAG)

.PHONY: run
run:
	podman run --rm -p 8000:8000 $(IMAGE_NAME):$(TAG)

.PHONY: run-local
run-local:
	uv run server.py
