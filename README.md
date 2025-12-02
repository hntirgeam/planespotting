# ADS-B Aircraft Tracker

Логирование данных ADS-B от dump1090 в базу данных SQLite с помощью peewee ORM.

## Установка

```bash
pip install -r requirements.txt
```

## Использование

### Режим структурированного логирования (по умолчанию):
```bash
python main.py
```

### Режим красивого вывода (как раньше):
```bash
python main.py --pretty
```

### Дополнительные опции:
```bash
# Указать путь к JSON файлу dump1090
python main.py --json-file /path/to/aircraft.json

# Изменить интервал опроса (в секундах)
python main.py --interval 5

# Уровень логирования
python main.py --log-level DEBUG
```

## База данных

- База данных автоматически создаётся при первом запуске: `adsb_tracker.db`
- Все поля из dump1090 JSON сохраняются (включая опциональные)
- Каждая запись имеет timestamp

### Миграция в PostgreSQL

Для перехода с SQLite на PostgreSQL:
1. Измените в [models.py](models.py) строку: `db = PostgresqlDatabase('adsb_tracker', user='user', password='pass', host='localhost')`
2. Экспортируйте данные: `sqlite3 adsb_tracker.db .dump > backup.sql`, затем используйте pgloader или импортируйте вручную с корректировкой синтаксиса.

## Структура проекта

- [main.py](main.py) - основной скрипт с логикой опроса и логирования
- [models.py](models.py) - модели базы данных (peewee ORM)
- `adsb_tracker.db` - база данных SQLite (создаётся автоматически)

dump1090 --write-json /tmp/dump1090 --write-json-every 1 --net --lat 44.80247 --lon 20.46632 --metric --fix --quiet