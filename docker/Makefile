.PHONY: all build up down clean logs shell tests lint format rebuild help dt-build dt-clean

all: build

build: ## Build Docker images
	docker compose -f docker-compose.yml --env-file ../.env build

up: ## Start all containers in the background
	docker compose -f docker-compose.yml --env-file ../.env up --build -d

down: ## Stop and remove containers
	docker compose -f docker-compose.yml --env-file ../.env down

clean: ## Stop containers and remove volumes and images
	docker compose -f docker-compose.yml --env-file ../.env down -v --rmi all

logs: ## Tail container logs
	docker compose -f docker-compose.yml --env-file ../.env logs -f

shell: ## Open a shell inside the app container
	docker compose -f docker-compose.yml --env-file ../.env exec app bash

tests: ## Run backend and frontend tests inside the container
	docker compose -f docker-compose.yml --env-file ../.env exec app ./unit_tests.sh

lint: ## Run all linters inside the container
	docker compose -f docker-compose.yml --env-file ../.env exec app ./linter.sh

format: ## Run Prettier formatter inside the container
	docker compose -f docker-compose.yml --env-file ../.env exec app bash -c "cd ccs-response-planner-frontend && npm run format"

rebuild: ## Full rebuild (remove volumes, rebuild images, start)
	docker compose -f docker-compose.yml --env-file ../.env down -v
	docker compose -f docker-compose.yml --env-file ../.env up --build -d

dt-build: ## Build all digital twin images
	bash digital_twin/build.sh

dt-clean: ## Remove all digital twin images
	docker rmi ccs-dt-gateway ccs-dt-firewall ccs-dt-ids \
	    ccs-dt-server1 ccs-dt-server2 ccs-dt-server3 \
	    ccs-dt-server4 ccs-dt-server5 ccs-dt-server6 2>/dev/null || true

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
