setup:
	docker-compose up -d --build
	docker-compose exec web python manage.py makemigrations
	docker-compose exec web python manage.py migrate
	docker-compose exec web python manage.py collectstatic --noinput

build:
	docker-compose up -d --build

run:
	docker-compose up -d

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

remove:
	docker-compose down -v --remove-orphans