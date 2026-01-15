.PHONY: up-local up-remote down-local down-remote restart-local restart-remote clean-local clean-remote logs seed-force seed-status

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

seed-force:
	@echo "Forcing re-seed from AWS RDS..."
	@docker-compose --profile local run --rm seeder --force
	@echo ""
	@echo "Done! Local backup updated at apps/backend/data/seed_backup.sql.gz"

seed-status:
	@echo ""
	@echo "Local seed backup status:"
	@echo "========================="
	@if [ -f apps/backend/data/seed_backup.sql.gz ]; then \
		echo "  File: apps/backend/data/seed_backup.sql.gz"; \
		echo "  Size: $$(du -h apps/backend/data/seed_backup.sql.gz | cut -f1)"; \
		echo "  Modified: $$(stat -f '%Sm' apps/backend/data/seed_backup.sql.gz 2>/dev/null || stat -c '%y' apps/backend/data/seed_backup.sql.gz 2>/dev/null)"; \
		echo ""; \
		echo "  Next 'make up-local' will restore from this backup (fast)."; \
		echo "  Use 'make seed-force' to refresh from AWS RDS."; \
	else \
		echo "  No local backup found."; \
		echo ""; \
		echo "  Next 'make up-local' will fetch from AWS RDS and create backup."; \
	fi
	@echo ""
