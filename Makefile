.PHONY: help up down logs shell-api clean-pyc

help:  ## 显示帮助信息
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) 

up: ## 启动所有服务 (后台模式)
	docker-compose up -d --build

down: ## 停止并移除容器
	docker-compose down

logs: ## 查看实时日志
	docker-compose logs -f

migrate: ## 执行数据库迁移
	docker-compose exec api alembic upgrade head

shell-api: ## 进入 API 容器终端
	docker-compose exec api /bin/bash

test-x: ## 在容器内运行 X 采集测试
	docker-compose exec worker python -m tests.test_x_collector

clean-db: ## [危险] 清空数据库数据
	docker-compose down -v

