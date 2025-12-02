# ADS-B Aircraft Tracker

Логирование данных ADS-B от dump1090 в базу данных PostgreSQL с помощью peewee ORM.

## Установка

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка PostgreSQL
Скопируйте `.env_template` в `.env` и укажите параметры вашей базы данных:

```bash
cp .env_template .env
```

Отредактируйте `.env`:
```bash
DB_NAME=adsb_tracker
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### 3. Создание базы данных
```bash
# Войдите в PostgreSQL
psql -U postgres

# Создайте базу данных
CREATE DATABASE adsb_tracker;

# Выйдите
\q
```

Таблицы будут созданы автоматически при первом запуске.

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

### Структура данных
- **Primary key**: UUID (автоматический `uuid.uuid4()`)
- **flight_session_id**: UUID для группировки последовательных наблюдений одного самолёта
- Все поля из dump1090 JSON сохраняются (включая опциональные)
- Каждая запись имеет timestamp
- **Поддержка метрической системы**: высота (altitude_m), скорость (speed_kmh) и вертикальная скорость (vert_rate_ms) автоматически конвертируются и сохраняются вместе с имперскими значениями

### Flight Session Tracking

Система автоматически группирует наблюдения самолётов в **сессии полётов** (`flight_session_id`). Это решает проблему разрывов траектории при построении графиков.

**Как работает:**
- Когда самолёт появляется в первый раз, создаётся новая сессия (новый UUID)
- Все последующие наблюдения этого самолёта получают тот же `flight_session_id`
- Если самолёт исчезает на **более чем 30 минут** (SESSION_TIMEOUT), следующее наблюдение получит новый session_id
- Это предотвращает соединение точек между разными пролётами одного самолёта

**Пример использования для визуализации:**
```python
# Получить все траектории конкретного самолёта
aircraft_hex = '4C01E2'
sessions = Aircraft.select().where(Aircraft.hex == aircraft_hex).order_by(Aircraft.timestamp)

# Группировать по session_id для построения отдельных траекторий
from itertools import groupby
for session_id, points in groupby(sessions, key=lambda x: x.flight_session_id):
    trajectory = [(p.lat, p.lon, p.altitude_m, p.timestamp) for p in points]
    # Строить график для каждой траектории отдельно
    plot_trajectory(trajectory)
```

## Структура проекта

- [main.py](main.py) - основной скрипт с логикой опроса и логирования
- [models.py](models.py) - модели базы данных (peewee ORM с PostgreSQL)
- [.env](.env) - конфигурация базы данных (не коммитится в git)
- [.env_template](.env_template) - шаблон конфигурации
- [requirements.txt](requirements.txt) - зависимости Python

### Запуск dump1090
```bash
dump1090 --write-json /tmp/dump1090 --write-json-every 1 --net --lat 44.80247 --lon 20.46632 --metric --fix --quiet
```