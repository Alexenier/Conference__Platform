# Conference Platform

Распределённая платформа для управления научными конференциями — приём заявок, управление участниками, рецензирование и хранение материалов.

---

## Стек технологий

| Компонент | Технология |
|---|---|
| Backend API | FastAPI (Python 3.12) |
| База данных | PostgreSQL + SQLAlchemy 2.0 |
| Миграции | Alembic |
| Объектное хранилище | MinIO (S3-совместимое) |
| Контейнеризация | Docker / Docker Compose |
| Управление зависимостями | Poetry |

---

## Структура проекта

```
conference-platform/
├── app/
│   ├── api/                  # HTTP-маршруты (транспортный слой)
│   │   └── routes/
│   │       └── files.py      # Эндпоинты для работы с файлами
│   ├── core/
│   │   └── config.py         # Конфигурация через переменные окружения
│   ├── db/
│   │   ├── base.py           # Базовый класс ORM-моделей
│   │   └── session.py        # Подключение к БД, dependency injection
│   ├── models/               # ORM-модели (доменный слой)
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── user_role.py
│   │   ├── conference.py
│   │   ├── conference_group.py
│   │   ├── group.py
│   │   ├── group_member.py
│   │   └── submission.py
│   ├── schemas/              # Pydantic-схемы (валидация и сериализация)
│   │   └── file.py
│   ├── services/             # Бизнес-логика и интеграции
│   │   ├── storage.py        # Работа с S3/MinIO (boto3)
│   │   └── thesis_validation/ # Валидация тезисов (.docx)
│   └── main.py               # Точка входа приложения
├── migrations/               # Alembic-миграции
│   ├── env.py
│   └── versions/
├── Dockerfile
├── alembic.ini
└── pyproject.toml
```

---

## API

### Проверка работоспособности

```
GET /health
```

### Работа с файлами

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/files/ensure-bucket` | Создаёт S3-бакет, если он не существует |
| `POST` | `/files/upload` | Загружает файл в объектное хранилище |

**Пример загрузки файла:**

```bash
curl -X POST http://localhost:8000/files/upload \
  -F "file=@thesis.docx"
```

**Ответ:**
```json
{
  "ok": true,
  "bucket": "conference-files",
  "object_key": "uploads/550e8400-e29b-41d4-a716-446655440000-thesis.docx",
  "original_name": "thesis.docx",
  "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}
```

Полная документация API доступна по адресу http://localhost:8000/docs после запуска сервера.

---

## Доменная модель

Платформа работает со следующими сущностями:

- **User** — участник платформы с учётными данными и профилем
- **Role** — роль пользователя: `participant`, `org_committee`, `admin`
- **Conference** — научная конференция со сроком подачи заявок
- **Submission** — заявка на участие (доклад/тезисы) со статусом жизненного цикла
- **Group** — логическая группа пользователей (оргкомитет, рецензенты и т.д.)

---

## Миграции базы данных

```bash
# Применить все миграции
alembic upgrade head

# Создать новую миграцию (autogenerate)
alembic revision --autogenerate -m "описание изменений"

# Откатить последнюю миграцию
alembic downgrade -1

# Посмотреть историю миграций
alembic history
```

---

## Валидация тезисов

Модуль `app/services/thesis_validation` выполняет автоматическую проверку `.docx`-файлов тезисов на соответствие требованиям оформления:

- формат страницы A4, поля 20 мм
- шрифт Times New Roman 14 pt
- структура заголовочной части (название, авторы, организация)
- выравнивание, межстрочный интервал 1.15, абзацный отступ 1.25 см
- наличие блока «Література»
- объём 1–2 страницы

---

## Роли пользователей

| ID | Роль | Описание |
|---|---|---|
| 1 | `participant` | Участник конференции, подаёт заявки |
| 2 | `org_committee` | Организационный комитет |
| 3 | `admin` | Администратор платформы |
