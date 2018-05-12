# Органайзер-каталог для карт Heroes III

[https://habr.com/post/353484/](https://habr.com/post/353484/)

# Установка

1. Установить [Docker](https://www.docker.com/community-edition) и [Docker Compose](https://docs.docker.com/compose/install/)
2. `git clone https://github.com/Alexmod/heroes3manager-maps.git`
3. `cd heroes3manager-maps`
4. `docker-compose up -d`
5. Docker скачает все зависимости, соберет контейнеры и запустит сервисы. Займет это пару минут. Затем приложение будет запущено на localhost на порте 8000: [http://localhost:8000/](http://localhost:8000/)

Если ОС Windows или OS X и четвертый шаг `docker-compose up -d` выполняется с ошибкой, попробуйте `docker-compose -f docker-compose-windows.yml up -d`. Дело в том, что Mongo не поддерживает механизм монтирования папок, который использует Docker на этих системах:

> WARNING (Windows & OS X): The default Docker setup on Windows and OS X uses a VirtualBox VM to host the Docker daemon. Unfortunately, the mechanism VirtualBox uses to share folders between the host system and the Docker container is not compatible with the memory mapped files used by MongoDB (see vbox bug, docs.mongodb.org and related jira.mongodb.org bug). This means that it is not possible to run a MongoDB container with the data directory mapped to the host.

В docker-compose.yml монтируется папка `./db`, куда сладываются файлы Mongo. В docker-compose-windows.yml этого не происходит. Это нормально, просто не так удобно. Так же в этом случае при удалении контейнера база данных так же будет удалена.

Файлы карт находятся в папке `./static/Maps`.

