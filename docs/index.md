---
marp: true
title: Из слона (PostgreSQL) муху (баги)
description: Мониторинг, анализ и оптимизация SQL-запросов
theme: vtb
template: gaia
paginate: true
_paginate: false

---

<!-- _class: lead2
_footer: 'Cсылка на [слайды](https://polarnik.github.io/pg-sql-query-performance/), ссылка [на проект](https://github.com/polarnik/pg-sql-query-performance)'
-->

![bg](img/first.svg)

<!--




История ускорения системы.
Про три месяца оформления и исправления дефектов большой системы,
которую можно услышать за тридцать минут и прожить за десять.

Как известно, инструмент подбирается под задачу.
Но для задачи визуализации статистики по SQL-запросам с точностью до минуты (или секунды, при желании) инструмента не было,
так чтобы инструмент работал в закрытой сети, работал под максимально высокой нагрузкой, не требовал модификаций PostgreSQL.
Инструмент был собран из открытых компонент: Telegraf, InfluxDB, Grafana. И отлично показал себя на проекте.
Позволив оформлять и исправлять дефекты в течение трех месяцев не отвлекаясь ни на что другое.
Что позволило достаточно быстро ускорить систему.

А если нужна детальная статистика с учетом значений параметров запроса, то это тоже возможно. За счет простого логирования и анализа лога.

Расскажу об опыте применения двух подходов к сбору и визуализации статистики, 
о том какие есть альтернативные подходы, которые не дали результата,
о том какие есть альтернативные решения, которыми вдохновлялся,
о том какие новые и полезные решения есть и появляются сейчас.

Аудитория и уровень

Доклад будет интересен инженерам по производительности и мониторингу систем, имеющим дело с PostgreSQL. Тем, кто стремиться не только тестировать и мониторить, но и оптимизировать, как саму систему так и механизм мониторинга.

Опыт оптимизации не требуется, но представление о том, что такое Java, SQL, PostgreSQL и Time Series Database нужно иметь.
-->

---

<!-- _class: title-->

# Тестирую и ускоряю ДБО для юридических лиц в банке ВТБ
## __Развиваю @qa_load__

![bg cover](img/omsk.jpg)

<!-- 
Повышаю качество более десяти лет. Занимаюсь системой дистанционного банковского обслуживания юридических лиц. Основной профиль моей работы — тестирование производительности. Развиваю сообщество инженеров по тестированию производительности, помогая коллегам в telegram чате «QA — Load & Performance».
-->

---
<!-- _class: main 
-->

# О чем доклад 

---
<!-- _class: head 
-->
![bg](#000)
![](#fff)
# О мониторинге и оптимизации SQL-запросов и ...

1) Как не раздуть из мухи слона в анализе производительности
2) Как написать дефект, от которого можно посчитать эффект

3) Отображение за секунду месячной статистики по SQL

4) Зачем и как выполнять трассировку SQL-запросов

---
<!-- _class: head 
-->
![bg](#000)
![](#fff)
## __Как не раздуть из мухи слона в анализе производительности__

- О моих ошибках, как инженера по тестированию производительности

## __Как написать дефект, от которого можно посчитать эффект__

- Ускорение долгих запросов и Active state 
- Долгие транзакции и Idle in transaction 
- Нехватка подключений и Idle state
- Блокировки и Blocked state 

## __Отображение за секунду месячной статистики по SQL__

## __Зачем и как выполнять трассировку SQL-запросов__

- Пошаговое ускорения одного SQL-запроса и роль трассировки

---
![bg](#000)
![](#fff)
> «Ценность любой практики зависит от ее контекста»

Джем Канер, Джеймс Бах, Брайан Марик и Брет Петтичорд

> «The value of any practice depends on its context»

Cem Kaner, James Bach, Brian Marick, Bret Pettich



![bg right](img/A-Context-Driven-Approach.jpg)


---
<!-- _class: main 
-->

# Контекст

---

<!-- _class: title -->

# 100 JVM работающих друг с другом и базой
## __На тестовом стенде__
![bg](#000)
![](#fff)
![bg right:40% h:700px](img/monitoring-5.svg)

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Узким местом была база данных

- База данных выросла и стала узким местом, замедлилась

- Утилизация CPU на сервере PostgreSQL близка к 100%
- Микросервисам не хватает пула подключений
- Подключений к PostgreSQL уже 2 000
- Много ошибок в логах сервисов
- Медленные ответы сервисов

---
![bg](#000)
![](#fff)
![bg w:95% h:80%](img/sql-bottleneck.svg)

---
![bg](#000)
![](#fff)
![bg w:95% h:80%](img/cpu.svg)

![bg w:95% h:80%](img/sql-bottleneck.svg)

---

![bg](#000)
![](#fff)

![bg w:95% h:75%](img/load.2.png)

---

![bg](#000)
![](#fff)

![bg w:95% h:75%](img/load.6.png)


---

![bg](#000)
![](#fff)

![bg w:95% h:75%](img/sql-step.svg)

---
![bg](#000)
![](#fff)
![bg w:95% h:75%](img/sql-step-2.svg)




---
<!-- _class: head -->

![bg](#000)
![](#fff)
# Стал нужен источник метрик по SQL-запросам

## __Но не просто срез статистики для ручного сравнения и анализа, а ...__

- с удобным сравнением: запрос ускорился на X процентов

- с хранением статистики за длительный интервал
- с гибким выбором интервалов для сравнения
- с высокой точностью сбора метрик
- с быстрым отображением данных
- с отображением интенсивности

---
![bg](#000)
![](#fff)

![bg w:95% h:75%](img/sql-step-3.svg)

---
<!-- _class: main 
-->

# Что получилось

---


![bg](img/pgstat.1.png)


---

<!-- _class: title -->

# Статистика по запросам в виде таблиц

## __С фильтрами по всем полям__

![bg brightness:0.5](img/pgstat.2.png)

---

<!-- _class: title -->

# Детальная статистика по выбранному запросу

## __И не только это__

![bg brightness:0.5](img/pgstat.3.png)

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Demo-стенд

- PostgreSQL

- InfluxDB
- Grafana
- Telegraf
- JMeter

github.com/polarnik/pg-sql-query-performance

![bg right:35% h:60% ](img/sql-qrcode.svg)




---
<!-- _class: main 
-->

# Как не раздуть из мухи слона в анализе производительности



---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Иногда приходится тестировать на заглушках

![bg w:90% h:70%](img/sql-mock.svg)

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Если тестировать на заглушках

## __Мы найдем дефекты производительности__

- В одном компоненте, при быстрых ответах от окружения
- При большом масштабировании компонента

## __Мы упустим__

* Многие сценарии использования
* Дефекты взаимодействия
* Другие компоненты

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Иногда приходится тестировать на пустых БД

![bg w:90% h:70%](img/sql-empty.db.svg)

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Если тестировать на пустых базах данных
## __Мы найдем дефекты производительности__

- Дефекты взаимодействия при быстрых ответах от базы данных
- Очень частые SQL-запросы, что можно кешировать
- Утечки подключений, файлов, ...

## __Мы упустим__

* Многие сценарии использования
* Большую часть медленных SQL-запросов и блокировок
* Расходы памяти на большие данные
* Обработку больших коллекций



---

<!-- _class: title 
_footer: 'Изображение с сайта <a href="https://i.imgur.com/VuyIVW0.jpg">imgur.com</a>'
-->

# Есть много способов найти дефекты производительности

## __Которых не будет в продуктиве__

![bg](img/freedom-4903175_1920.jpg)



---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Сделать лишнюю работу или получить отказ

## __Что может услышать инженер__

> _Мы что-то поправили, проверь_

> _Дефект когда-нибудь проанализируем_

> _Дефект больше не воспроизводится — закрываем_

---

<!-- _class: title 

_footer: 'Изображение c сайта <a href="https://cdn.wallpapersafari.com/23/35/RA5mfj.jpg">wallpapersafari.com</a>'
-->

# Тут легко сделать из мухи слона


![bg ](img/elefant1.jpg)





---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Повышая приоритет непроверенных дефектов

## __Инженер:__

> «Прошу проанализировать и исправить дефект, <strike>эффект уже проверен</strike>»
> «Дефект важен, ускорение будет, <strike>для ключевой операции на 70%</strike>»

## __Команда:__

> «Поправили, __но на DEV-стенде нет эффекта__»
> «Проверь на нагрузочном стенде»

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Но есть проверенный способ изменить ситуацию

## __Что может сделать и сказать инженер__

> _Поправить предлагаю так, уже проверено_

> _Ускорение ключевой операции на 70%_

> _Влияния на функциональность нет_

---

<!-- _class: title 

_footer: 'Изображение с сайта <a href="https://i.imgur.com/VuyIVW0.jpg">imgur.com</a>'

-->

# Можно сделать из <br>слона (PostgreSQL)<br>муху (дефекты)

## __Проверенные дефекты__

![bg ](img/butterphant.jpg)

---
![bg](#000)
![](#fff)
![bg h:90%](img/sql-t-shape.svg)

---
![bg](#000)
![](#fff)
![bg h:90%](img/sql-t-shape-dev.svg)

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Используя непустые базы данных
## __Есть доклад по генерации данных: https://o.codefest.ru/lecture/1674__

![ width:1220px ](img/MakeTestData.CodeFest-2020.1.jpg)


---
<!-- _class: head -->
![bg](#000)
![](#fff)
# И оптимизируя SQL-запросы на тестовом стенде

## __Стенд нагрузки (большая БД с данными) позволяет оптимизировать__

- __долгие запросы (active) с предсказуемыми планами__
- долгие транзакции (idle in transaction)
- нехватка подключений (idle)
- блокировки (blocked)

## __А стенд разработки (малая БД на контейнерах) не позволяет, ведь__

- планы запросов парадоксальные: __sequnce scan__ вместо __index scan__
- таблицы маленькие
- запросы быстрые




---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Эффект будет и для дела и для репутации

## __Инженер:__

> «Дефект поправить предлагаю так, **эффект уже проверен**»
> «Дефект важен, ускорение будет, **для ключевой операции на 70%**»

## __Команда:__

> «Поправили, **есть эффект даже на DEV-стенде**»
> «**Спасибо!**»


---
<!-- _class: main 
-->

# Как написать дефект, от которого можно посчитать эффект

---

![bg](img/effect.png)

---

![bg ](img/effect.2.png)

---

<!-- _class: title -->

# Очень важен выбор метрик, которые будем измерять

## __По ним оценим эффект__

![bg  brightness:0.5](img/effect.2.png)

---

<!-- _class: main 
-->

# Долгие запросы и Active state

<!--

* Выбор наиболее медленных SQL-запросов

* Анализ интенсивности SQL-запроса
* Среднее и максимальное время
* Другие важные метрики

-->

---

![bg](img/top.png)

---

![bg](img/pgstat.2.png)



---

![bg](img/top.4.png)

---

<!-- _class: title -->

# Длительность за выбранный в Grafana период

![bg brightness:0.5](img/top.4.png)

---

![bg](img/top.5.png)

---

<!-- _class: title -->

# Запросы дольше<br> 10-100 мсек можно попробовать ускорить


![bg brightness:0.5](img/top.5.png)


---

<!-- _class: head -->

# Колонка QueryID — ссылка на детали по запросу

![bg](img/top.6.png)

---

<!-- _class: title -->

# Детали по запросу, не только в табличном виде, но с графиками

![bg brightness:0.5](img/query.png)


---

![bg](img/query.2.png)


---

![bg](img/query.4.png)


---

<!-- _class: title -->

# Использую DBeaver для работы с PostgreSQL

## __explain (analyse, buffers) ...__

![bg  brightness:0.5](img/explain.png)

---


![bg](img/explain.png)

---

<!-- _class: title -->

# План запроса — один из возможных планов выполнения SQL

![bg brightness:0.5](img/explain.png)

---

<!-- _class: title -->

# Собираю планы запроса с разными параметрами

## __Сохраняю их в комментариях__

![bg  brightness:0.5](img/explain.2.png)

---

![bg](img/explain.2.png)

---

<!-- _class: title -->

# https://explain.tensor.ru/ помогает понять и визуализировать план

## __Полезный сайт__

![bg](img/explain.3.png)

---

<!-- _class: head -->

# После оптимизации перепроверяю под нагрузкой

![bg](img/active.recheck.png)

---


<!-- _class: head -->

# ⬇️ Средняя длительность (Mean time) снизится

## __Сравнить показатели до и после правки, при сходной нагрузке__

![bg](img/effect.3.png)

---

<!-- _class: head -->

# ⬇️ Shared Blk Hit, Shared Blk Read снизятся

## __Параметры важны для SELECT-запросов__

![bg](img/effect.4.png)

---

<!-- _class: head -->
# А что с Total Time и Calls по запросу?

![bg](img/effect.5.png)

---

<!-- _class: head -->

# На Total Time и Calls по запросу не смотрим

## __🔀 Calls при ускорении может расти, Total Time тоже, а должен падать__

![bg](img/effect.5.png)

---

<!-- _class: main 
-->

# Долгие транзакции и Idle in transaction state


<!--
* Выбор SQL-запросов в долгих транзакциях

* Поиск кода, вызывающего SQL-запрос
* Анализ причин зависания
-->

---

![bg](img/idle.in.transaction.dev.png)

---

<!-- _class: head -->

# Такой код приведет к долгой транзакции

## __Будет подключение к БД в статусе Idle in transaction__

![bg](img/idle.in.transaction.dev.png)

---

![bg](img/idle.in.transaction.3.png)

---

<!-- _class: head -->

# Доска PostgreSQL Activity в Grafana покажет TOP 

## __После какого SQL-запроса транзакция не закрывалась долго__
![bg](img/idle.in.transaction.3-2.png)

---

<!-- _class: head -->

# Колонка Sum только для сортировки 

![bg](img/idle.in.transaction.3-2.png)

---

<!-- _class: head -->

# Выбирем признаки для поиска в исходниках

## __По базе данных и логину выбираем сервис, а по SQL - место в коде__

![bg](img/idle.in.transaction.4.png)

---

<!-- _class: head -->

# Иногда текста запроса нет или он не помогает

## __Тогда придется перечитать все исходники с учетом pg_stat_statements__

![bg](img/idle.in.transaction.4-2.png)

---

<!-- _class: head -->

# Пусть у нас есть уникальный запрос и логин

## __qpt_transaction_user: SELECT * FROM aircrafts_data WHERE range > 3000__

![bg](img/idle.in.transaction.4.png)


---

<!-- _class: head -->

# По тексту запроса и логину находим исходники

![bg](img/idle.in.transaction.png)

---

<!-- _class: head -->

# По исходникам определяем, что не так

![bg](img/idle.in.transaction.dev.png)

---

<!-- _class: title -->

# Переписываем код: просим убрать из транзакции ожидание

## __Или сокращаем ожидание__

![bg brightness:0.5](img/idle.in.transaction.dev.png)

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Сокращаем ожидание, если транзакция нужна

```java
sqlClient.transactionBegin();
try {
    sqlClient.exec("INSERT INTO table_name ...");
    // Внутри транзакции: HTTP, JMS, MQTT (Kafka), ...
    httpClient.Send("http://load.qa/ADD"); // Ускоряем
} finally {
    if ( ... )
        sqlClient.transactionCommit(); 
    else
        sqlClient.transactionRollback();
}
```

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Переписываем код, если есть возможность

## __До переписывания: длительный вызов внутри транзакции__

```java
sqlClient.transactionBegin();
try {
    // Внутри транзакции: HTTP, JMS, MQTT (Kafka), ...
    httpClient.Send("http://load.qa/ADD"); // Переписываем
    sqlClient.exec("INSERT INTO table_name ...");
} finally {
    if ( ... )
        sqlClient.transactionCommit(); 
    else
        sqlClient.transactionRollback();
}
```

---
![bg](#000)
![](#fff)
<!-- _class: head -->

# Переписываем код, если есть возможность

## __После переписывания: длительный вызов вне транзакции__

```java
// Вне транзакции
httpClient.Send("http://load.qa/ADD"); // Переписали

if (...) {
    sqlClient.transactionBegin();
    sqlClient.exec("INSERT INTO table_name ...");
    sqlClient.transactionCommit();
}
```

---
![bg](#000)
![](#fff)
<!-- _class: head -->

# Настраиваем более короткие подключения к БД

## __maxLifetime по умолчанию 1800000 (30 минут)__

Например, 3 минуты вместо 30-ти минут:

```yml
ConfigMap:
    spring.datasource.hikari:
        maxLifetime: 180000
```

---

<!-- _class: head -->

# ⬇️ Эффект оценим по статусам подключений

![bg](img/idle.in.transaction.5.png)

---

<!-- _class: head -->

# ⬇️ По суммарной длительности состояния


![bg](img/idle.in.transaction.3-2.png)

---

<!-- _class: main 
-->

# Нехватка подключений и Idle state


<!--
* Выбор сервисов с неиспользуемыми подключениями

* Справедливое распределение подключений

* Настройки времени жизни подключений
-->

---
![bg](#000)
![](#fff)

![bg w:90%](img/sql-idle.svg)

---
![bg](#000)
![](#fff)

<!-- _class: head -->

# spring.datasource.hikari.maximumPoolSize=10...50

## __для server.tomcat.threads.max = 200__

![bg w:90% brightness:0.1](img/sql-idle.svg)

Проблема: 
* В Tomcat по умолчанию  maxThreads = __200__ (потоков обработки)
* А HikariPool по умолчанию __10__ (потоков подключения к БД)
* Подключений не хватает под нагрузкой, в логах ошибки
* Разработчик старается сделать HikariPool побольше, 50
* Если 250 сервисов со Scale 2 установят по 50 сразу:
    * ```250 x 2 x 50 = 25 000``` (подключений к PostgreSQL)
* А подключений всего пусть 4000




---
![bg](#000)
![](#fff)

<!-- _class: head -->

# Задача — сократить пулы потоков

## __и spring.datasource.hikari.maximumPoolSize и server.tomcat.threads.max__

![bg w:90% brightness:0.1](img/sql-idle.svg)

Чтобы соединения быстрее возвращались в пул потоков HikariPool:

- Ускоряем медленные запросы (Active)
- Исправляем долгие транзакции (Idle in transaction)

А далее смотрим, кто не использует свои подключения и уменьшаем 
```yml
spring.datasource.hikari:
    maximumPoolSize: 50     # было увеличено
    minimumIdle: 10         # по умолчанию
    idleTimeout: 600000     # (10 minutes)
```

---

![bg](img/idle.duration.png)

---

![bg](img/idle.count.png)

---

<!-- _class: title -->

# Выделяем фаворитов и уменьшаем им пул

## __В индивидуальном порядке__

![bg brightness:0.5](img/idle.count.png)

---

![bg](img/total_time.png)


---

<!-- _class: title -->

# Перераспределяем пул пропорционально Total Time

## __Каждому по потребностям__

![bg brightness:0.5](img/total_time.png)

---

<!-- _class: main 
-->

# Блокировки и Blocked state

---
<!-- _class: head -->

# Как правило, причина в долгих запросах

## __Ускоряем медленные запросы — решаются блокировки__

![bg](img/top.4.png)

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Детализацию хорошо показывает [PASH Viewer](https://github.com/dbacvetkov/PASH-Viewer)

## __Аналог ASH Viewer, но только для PostgreSQL__

![bg h:70%](img/pash-viewer-screenshot-01.png)

---
<!-- _class: main 
-->

# Отображение за секунду месячной статистики по SQL


---
<!-- _class: head -->
![bg](#000)
![](#fff)
# В InfluxDB все теги индексируются сразу

## __И основная задача в уменьшении этих индексов__

```sql
CREATE CONTINUOUS QUERY query_md5_10min ON telegraf_pg_demo
BEGIN
    SELECT
        sum("duration") AS duration_sum,
        sum(calls) AS calls_sum
    INTO
        telegraf_pg_demo.autogen.pg_stat_statements_query_md5_10min
    FROM
        telegraf_pg_demo."7d".pg_stat_statements_diff
    WHERE
        time >= now() - 20m AND calls > 0
    GROUP BY host, usename, datname, queryid, query_md5, time(10m)
END;
```

---

<!-- _class: title -->
![bg](#000)
![](#fff)
# За счет Continious Query Influxdb cтатистика  отдельно

## __А Query Text тоже отдельно__

![bg right:45% w:90%](img/sql-cont-query.svg)

---

![bg](#000)
![](#fff)

![bg h:90% w:90%](img/sql-cont-query.svg)

---

<!-- _class: title -->
![bg](#000)
![](#fff)
# https://github.com/ polarnik/pg-sql-query-performance

## __Проект с демонстрацией__

![bg right:45% h:70% ](img/sql-qrcode.svg)

---

<!-- _class: head -->
![bg](#000)
![](#fff)
# Как запустить проект

```bash
# Отдельно поднять сервер баз данных
docker-compose up db

# Остановить поднятый сервер БД
# <Ctrl+C> или командой
docker stop sql_monitor_postgres

# А теперь поднять все компоненты
docker-compose up

# Открыть Grafana
open 'http://localhost:3000'

```

![bg right:45% h:70% ](img/sql-qrcode.svg)

---
<!-- _class: main 
-->

# Для чего и как выполнять трассировку SQL-запросов

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Partial-индексы и вот это вот все

```sql
select 
    concat('{"m":"', message, '"}') body 
from web_message
where
    user_id = '0eaab87d-5977-4a3a-af9f-6f5f424140f5'
    and status = 'NEW'
    and category in ('NOTIFICATION')
    and channel = 'WEB_POPUP'
    and (   expiration_time is null 
            or expiration_time >= now())
order by created_at desc
limit 10;
```


---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Запрос в статистике

```sql
select 
    concat($1, message, $2) body 
from ntn_web.web_message msg
where
    user_id = $3
    and status = $4
    and category in ($5)
    and channel = $6
    and (   expiration_time is null 
            or expiration_time >= $7)
order by created_at desc
limit $8;
```
---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Первое предположение: добавить в индекс все

```sql
select 
    concat($1, message, $2) body 
from ntn_web.web_message msg
where
    user_id = $3                      -- в индекс
    and status = $4                   -- в индекс
    and category in ($5)              -- в индекс
    and channel = $6                  -- в индекс
    and (   expiration_time is null  
            or expiration_time >= $7) -- в индекс
order by created_at desc              -- в индекс
limit $8;
```

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Большой индекс, который не будет использован

```sql
select concat($1, message, $2) body from web_message
where user_id = $3 and status = $4
  and category in ($5) and channel = $6
  and ( expiration_time is null or expiration_time >= $7 )  
order by created_at desc limit $8;

------ В индекс включены все поля
create index fix_web_message_idx_1 on web_message
using btree(user_id, status, category, channel,
   expiration_time, created_at DESC);
```

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Меньший индекс, который будет использован

```sql
select concat($1, message, $2) body from web_message
where user_id = $3 and status = $4
  and category in ($5) and channel = $6
  and ( expiration_time is null or expiration_time >= $7 )  
order by created_at desc limit $8;

------ Из индекса исключены неподходящие строки
create index fix_web_message_idx_2 on web_message
using btree(user_id, expiration_time, 
  created_at DESC)
where status = 'NEW'
  and category in ('NOTIFICATION')
  and channel = 'WEB_POPUP';
```

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Для заданных параметров фильтрации годится

```sql
select concat($1, message, $2) body from web_message
where user_id = $3 and status = 'NEW'
  and category in ('NOTIFICATION') and channel = 'WEB_POPUP'
  and ( expiration_time is null or expiration_time >= $7 )
order by created_at desc limit $8;

------ Из индекса исключены неподходящие строки
create index fix_web_message_idx_2 on web_message
using btree(user_id, expiration_time, 
  created_at DESC)
where status = 'NEW'
  and category in ('NOTIFICATION')
  and channel = 'WEB_POPUP';
```

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Немного перепишем запрос


```sql
select concat($1, message, $2) body from web_message
where user_id = $3 and status = 'NEW'
  and category in ('NOTIFICATION') and channel = 'WEB_POPUP'
--and ( expiration_time is null or expiration_time >= $7 )
  and coalesce( expiration_time, '3000-01-01' ) >= now()
order by created_at desc limit $8;
-- TODO: успеть актуализировать запрос до 3000-го года
```

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Немного перепишем запрос


```sql
select concat($1, message, $2) body from web_message
where user_id = $3 and status = 'NEW'
  and category in ('NOTIFICATION') and channel = 'WEB_POPUP'
  and coalesce( expiration_time, '3000-01-01' ) >= now()
order by created_at desc limit $8;
-- TODO: успеть актуализировать запрос до 3000-го года
```

## __Код будет работать до 3000-го года корректно__

А потом мы что-нибудь придумаем

---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Функцию coalesce тоже можно индексировать

```sql
select concat($1, message, $2) body from web_message
where user_id = $3 and status = 'NEW'
  and category in ('NOTIFICATION') and channel = 'WEB_POPUP'
  and coalesce( expiration_time, '3000-01-01' ) >= now()
order by created_at desc limit $8;

------ В индекс добавлен результат выполнения coalesce
create index fix_web_message_idx_3 on web_message
using btree(user_id, coalesce(expiration_time,'3000-01-01'),
  created_at DESC)
where status = 'NEW'
  and category in ('NOTIFICATION')
  and channel = 'WEB_POPUP';
```


---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Сделаем из индекса аналог View

```sql
select concat($1, message, $2) body from web_message
where user_id = $3 and status = 'NEW'
  and category in ('NOTIFICATION') and channel = 'WEB_POPUP'
  and coalesce( expiration_time, '3000-01-01' ) >= now()
order by created_at desc limit $8;

------ В индекс добавлена колонка message
create index fix_web_message_idx_4 on web_message
using btree(user_id, coalesce(expiration_time,'3000-01-01'),
  message, created_at DESC)
where status = 'NEW'
  and category in ('NOTIFICATION')
  and channel = 'WEB_POPUP';
```


---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Результат функции concat можно индексировать

```sql
select concat($1, message, $2) body from web_message
where user_id = $3 and status = 'NEW'
  and category in ('NOTIFICATION') and channel = 'WEB_POPUP'
  and coalesce( expiration_time, '3000-01-01' ) >= now()
order by created_at desc limit $8;

------ В индекс добавлен результат выполнения concat
create index fix_web_message_idx_4 on web_message
using btree(user_id, coalesce(expiration_time,'3000-01-01'),
  concat('{"m":"', message, '"}'), created_at DESC)
where status = 'NEW'
  and category in ('NOTIFICATION')
  and channel = 'WEB_POPUP';
```


---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Все это стало возможно при знании параметров

```sql
select concat('{"m":"', message, '"}') body from web_message
where user_id = $3 and status = 'NEW'
  and category in ('NOTIFICATION') and channel = 'WEB_POPUP'
  and coalesce( expiration_time, '3000-01-01' ) >= now()
order by created_at desc limit $8;

------ В индекс добавлен результат выполнения concat
create index fix_web_message_idx_4 on web_message
using btree(user_id, coalesce(expiration_time,'3000-01-01'),
  concat('{"m":"', message, '"}'), created_at DESC)
where status = 'NEW'
  and category in ('NOTIFICATION')
  and channel = 'WEB_POPUP';
```


---
<!-- _class: head -->
![bg](#000)
![](#fff)
# Чтобы узнать параметры запроса

## __Нужна трассировка приложения, интуиция или знания__

* Смотрим исходники

* Угадываем параметры (UI, БД)

* Параметры из __профилирования JVM__ ([JProfiler](https://www.ej-technologies.com/products/jprofiler/overview.html), [YourKit](https://www.yourkit.com/java/profiler/features/))

* Параметры из логов трассировки JDBC

* Параметры из логов трассировки Hibernate

* Параметры из логов планов запросов PostgreSQL

* Перехват параметров с JDBC Proxy

---
<!-- _class: main 
-->

# Приложение: инструменты


---
<!-- _class: head -->
# Трассировка (с параметрами)
![bg](#000)
![](#fff)
- Коммерческие профайлеры [JProfiler](https://www.ej-technologies.com/products/jprofiler/overview.html), [YourKit](https://www.yourkit.com/java/profiler/features/)

- [TRACE-логи](https://jdbc.postgresql.org/documentation/head/logging.html) PostgreSQL JDBC Driver
- [TRACE-логи](https://stackoverflow.com/questions/1710476/how-to-print-a-query-string-with-parameter-values-when-using-hibernate) для org.hibernate.type и DEBUG-логи для org.hibernate.sql
- [CSV Log](https://www.postgresql.org/docs/10/runtime-config-logging.html#RUNTIME-CONFIG-LOGGING-CSVLOG) + [debug_print_parse](https://www.postgresql.org/docs/10/runtime-config-logging.html#RUNTIME-CONFIG-LOGGING-WHAT), debug_print_plan, debug_pretty_print
- Расширение [auto_explain](https://www.postgresql.org/docs/10/auto-explain.html) и анализ логов PostgreSQL
- Логирование с Side Effect Injection: [AspectJ](https://www.eclipse.org/aspectj/), [Byteman](https://byteman.jboss.org/), [jMint](https://github.com/Toparvion/jmint)
- JDBC Proxy [P6Spy](https://github.com/p6spy) (нужно встраивать в сервис)

---
<!-- _class: head -->
# Мониторинг
![bg](#000)
![](#fff)
- APM, Application Performance Monitoring-системы New Relic, Dynatrace
- ELK + [логи приложения](https://www.playframework.com/documentation/2.8.x/AccessingAnSQLDatabase#How-to-configure-SQL-log-statement) с медленными SQL-запросами
- [PgBadger](https://pgbadger.darold.net/) + [логи PostgreSQL](https://pgbadger.darold.net/documentation.html#POSTGRESQL-CONFIGURATION) с медленными SQL-запросами
- Утилита [PASH Viewer](https://github.com/dbacvetkov/PASH-Viewer) и системы мониторинга: okmeter.io
- [pg_stats_statements](https://www.postgresql.org/docs/10/pgstatstatements.html) и Prometheus [exporter](https://github.com/prometheus-community/postgres_exporter) или [Telegraf](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/postgresql_extensible) + InfluxDB
- [pg_profile](https://github.com/zubkov-andrei/pg_profile) для сравнительных [отчетов](https://pgconf.ru/media/2020/02/04/%D0%90%D0%BD%D0%B4%D1%80%D0%B5%D0%B9%20%D0%97%D1%83%D0%B1%D0%BA%D0%BE%D0%B2%20-%20pg_profile.pdf)

- [pg_stat_monitor](https://github.com/percona/pg_stat_monitor) для PostgreSQL 11+ или [pg_stat_plans](https://github.com/2ndQuadrant/pg_stat_plans) и доступ к статистике через SQL

---
<!-- 
_class: lead2
_footer: 'Cсылка на [слайды](https://polarnik.github.io/pg-sql-query-performance/), ссылка [на проект](https://github.com/polarnik/pg-sql-query-performance)'
-->

![bg](img/last.svg)



