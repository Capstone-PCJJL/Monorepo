.PHONY: up-local up-remote down-local down-remote restart-local restart-remote clean-local clean-remote logs

up-local:
	@docker-compose --profile local up -d
	@echo ""
	@echo "========================================="
	@echo "  Services are starting (Local DB)..."
	@echo "========================================="
	@echo ""
	@echo "  Frontend:   http://localhost:3000"
	@echo "  Backend:    http://localhost:8000"
	@echo "  API Docs:   http://localhost:8000/api/docs"
	@echo "  MySQL:      localhost:3306"
	@echo ""
	@echo "========================================="

up-remote:
	@docker-compose up backend frontend -d
	@echo ""
	@echo "========================================="
	@echo "  Services are starting (Remote DB)..."
	@echo "========================================="
	@echo ""
	@echo "  Frontend:   http://localhost:3000"
	@echo "  Backend:    http://localhost:8000"
	@echo "  API Docs:   http://localhost:8000/api/docs"
	@echo "  Database:   AWS RDS (see .env)"
	@echo ""
	@echo "========================================="

down-local:
	@docker-compose --profile local down

down-remote:
	@docker-compose stop backend frontend

restart-local:
	@docker-compose --profile local down
	@docker-compose --profile local up -d

restart-remote:
	@docker-compose stop backend frontend
	@docker-compose up backend frontend -d

clean-local:
	@docker-compose --profile local down -v
	@docker system prune -f

clean-remote:
	@docker-compose stop backend frontend
	@docker-compose rm -f backend frontend

logs:
	@docker-compose logs -f
