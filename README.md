# pg-sql-query-performance
Мониторинг, анализ и оптимизация производительности SQL-запросов к PostgreSQL. Описание и демонстрация

## FAQ

Если при сборке проекта будет ошибка

> failed to solve with frontend dockerfile.v0: failed to create LLB definition: failed to authorize: ...

То надо в консоли (в bash) выполнить установку переменных окружения:

```bash
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
```

Источник ответа: https://stackoverflow.com/questions/64221861/failed-to-resolve-with-frontend-dockerfile-v0

DOCKER_BUILDKIT отключается, так как в данном проекте не планируется размещать 
контейнер sql_monitor_jmeter в приватном или публичном docker registry.
https://docs.docker.com/develop/develop-images/build_enhancements/

И при выполнении команды `docker build` просто соберется Docker-контейнер, без публикации куда-то.

COMPOSE_DOCKER_CLI_BUILD отключается, чтобы при выполнении docker-compose build также не выполнялась публикация куда-либо.
https://www.docker.com/blog/faster-builds-in-compose-thanks-to-buildkit-support/


