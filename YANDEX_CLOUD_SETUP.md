# ⚙️ Настройка системы автоответов на Yandex Cloud

## 📋 АКТУАЛЬНЫЕ ДАННЫЕ

### Telegram:
- **Канал:** TABATA TIMER (@fitnesstimer)
  - ID: `-1003382880193`
- **Группа обсуждений:** TABATA TIMER | Обсуждения (@tabatatimer_ru)
  - ID: `-1003298580082`
- **Бот:** @fitnesstimer_bot
  - Token: `8228469773:AAF2_m6lyWDp4nqaIh7glXqd7PQ6uycXPfo`

### Email для отчётов:
- **Email:** `admin@tabatatimer.ru`
- **SMTP пароль:** `thyspickpikpnqdq`
- **SMTP сервер:** `smtp.yandex.ru`
- **SMTP порт:** `465`

### Личный Telegram для отчётов:
- **Username:** `@lobanoff_pro`
- **Chat ID:** `422372115`

---

## 🚀 УСТАНОВКА НА YANDEX CLOUD

### Вариант 1: Yandex Cloud Functions (РЕКОМЕНДУЕТСЯ)

#### 1. Создание функции:

```bash
# Установите Yandex Cloud CLI
yc init

# Создайте функцию
yc serverless function create --name telegram-auto-reply
```

#### 2. Загрузите код:

```bash
# Создайте ZIP архив с файлами
zip -r telegram-auto-reply.zip auto_reply.py statistics.py requirements.txt

# Загрузите функцию
yc serverless function version create \
  --function-name telegram-auto-reply \
  --runtime python311 \
  --entrypoint auto_reply.главная \
  --memory 256m \
  --execution-timeout 60s \
  --source-path telegram-auto-reply.zip \
  --environment \
    TELEGRAM_BOT_TOKEN=8228469773:AAF2_m6lyWDp4nqaIh7glXqd7PQ6uycXPfo,\
    TELEGRAM_CHAT_ID=-1003382880193,\
    DEEPSEEK_API_KEY=ваш_deepseek_key,\
    ADMIN_TELEGRAM_CHAT_ID=422372115,\
    SMTP_SERVER=smtp.yandex.ru,\
    SMTP_PORT=465,\
    SMTP_USER=admin@tabatatimer.ru,\
    SMTP_PASSWORD=thyspickpikpnqdq
```

#### 3. Настройте триггер (каждые 30 минут):

```bash
yc serverless trigger create timer \
  --function-name telegram-auto-reply \
  --cron-expression "*/30 * * * *"
```

---

### Вариант 2: Yandex Compute Cloud (VM с cron)

#### 1. Создайте виртуальную машину:

```bash
yc compute instance create \
  --name telegram-bot \
  --zone ru-central1-a \
  --network-interface subnet-name=default-ru-central1-a,nat-ip-version=ipv4 \
  --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2204-lts,size=10 \
  --ssh-key ~/.ssh/id_rsa.pub
```

#### 2. Подключитесь к VM:

```bash
ssh ubuntu@<IP_АДРЕС>
```

#### 3. Установите зависимости:

```bash
sudo apt update
sudo apt install -y python3 python3-pip git

# Клонируйте репозиторий или загрузите файлы
git clone <ваш_репозиторий> || scp -r fitness-timer-autopost/ ubuntu@<IP>:/home/ubuntu/

cd fitness-timer-autopost
pip3 install -r requirements.txt
```

#### 4. Создайте файл с переменными окружения:

```bash
cat > .env << EOF
TELEGRAM_BOT_TOKEN=8228469773:AAF2_m6lyWDp4nqaIh7glXqd7PQ6uycXPfo
TELEGRAM_CHAT_ID=-1003382880193
DEEPSEEK_API_KEY=ваш_deepseek_key
ADMIN_TELEGRAM_CHAT_ID=422372115  # @lobanoff_pro
SMTP_SERVER=smtp.yandex.ru
SMTP_PORT=465
SMTP_USER=admin@tabatatimer.ru
SMTP_PASSWORD=thyspickpikpnqdq
EOF
```

#### 5. Создайте скрипт запуска:

```bash
cat > run_auto_reply.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/fitness-timer-autopost
source .env
export $(cat .env | xargs)
python3 auto_reply.py >> /var/log/telegram-bot.log 2>&1
EOF

chmod +x run_auto_reply.sh
```

#### 6. Настройте cron (каждые 30 минут):

```bash
crontab -e

# Добавьте строку:
*/30 * * * * /home/ubuntu/fitness-timer-autopost/run_auto_reply.sh
```

---

### Вариант 3: Yandex Cloud Container Service (Docker)

#### 1. Создайте Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auto_reply.py statistics.py .

CMD ["python", "auto_reply.py"]
```

#### 2. Создайте docker-compose.yml:

```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    environment:
      - TELEGRAM_BOT_TOKEN=8228469773:AAF2_m6lyWDp4nqaIh7glXqd7PQ6uycXPfo
      - TELEGRAM_CHAT_ID=-1003382880193
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - ADMIN_TELEGRAM_CHAT_ID=${ADMIN_TELEGRAM_CHAT_ID}
      - SMTP_SERVER=smtp.yandex.ru
      - SMTP_PORT=465
      - SMTP_USER=admin@tabatatimer.ru
      - SMTP_PASSWORD=thyspickpikpnqdq
    restart: unless-stopped
```

#### 3. Запустите с cron-контейнером:

```bash
docker-compose up -d
```

---

## 🔧 НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ

### Обязательные переменные:

```bash
TELEGRAM_BOT_TOKEN=8228469773:AAF2_m6lyWDp4nqaIh7glXqd7PQ6uycXPfo
TELEGRAM_CHAT_ID=-1003382880193
DEEPSEEK_API_KEY=ваш_deepseek_key
```

### Для статистики и отчётов:

```bash
ADMIN_TELEGRAM_CHAT_ID=422372115  # @lobanoff_pro
SMTP_SERVER=smtp.yandex.ru
SMTP_PORT=465
SMTP_USER=admin@tabatatimer.ru
SMTP_PASSWORD=thyspickpikpnqdq
```

---

## ✅ ADMIN_TELEGRAM_CHAT_ID

**Уже настроено:**
- **Username:** `@lobanoff_pro`
- **Chat ID:** `422372115`

**✅ Готово к использованию!**

---

## 🧪 ТЕСТИРОВАНИЕ

### Локальный запуск:

```bash
export TELEGRAM_BOT_TOKEN=8228469773:AAF2_m6lyWDp4nqaIh7glXqd7PQ6uycXPfo
export TELEGRAM_CHAT_ID=-1003382880193
export DEEPSEEK_API_KEY=ваш_deepseek_key
export ADMIN_TELEGRAM_CHAT_ID=422372115  # @lobanoff_pro
export SMTP_SERVER=smtp.yandex.ru
export SMTP_PORT=465
export SMTP_USER=admin@tabatatimer.ru
export SMTP_PASSWORD=thyspickpikpnqdq

python3 auto_reply.py
```

### Проверка логов:

```bash
# Для VM с cron
tail -f /var/log/telegram-bot.log

# Для Docker
docker-compose logs -f telegram-bot

# Для Cloud Functions
yc serverless function logs telegram-auto-reply --tail
```

---

## 📁 СТРУКТУРА ФАЙЛОВ

```
fitness-timer-autopost/
├── auto_reply.py          # Основной скрипт
├── statistics.py          # Модуль статистики
├── requirements.txt       # Зависимости Python
├── .env                   # Переменные окружения (НЕ коммитить!)
├── .telegram_statistics.json  # Статистика (автоматически)
├── feedback_timer.md      # Отзывы (автоматически)
└── YANDEX_CLOUD_SETUP.md  # Эта инструкция
```

---

## 🔒 БЕЗОПАСНОСТЬ

### ⚠️ ВАЖНО:

1. **НЕ коммитьте** файлы с токенами и паролями в Git
2. Добавьте в `.gitignore`:
   ```
   .env
   .telegram_statistics.json
   feedback_timer.md
   .auto_reply_state.json
   .answered_messages.json
   ```
3. Используйте переменные окружения или секреты Yandex Cloud
4. Регулярно обновляйте пароли и токены

---

## 📝 МОНИТОРИНГ

### Проверка работы:

1. **Проверьте логи:**
   ```bash
   # VM
   tail -f /var/log/telegram-bot.log
   
   # Cloud Functions
   yc serverless function logs telegram-auto-reply --tail
   ```

2. **Проверьте статистику:**
   ```bash
   cat .telegram_statistics.json | jq
   ```

3. **Проверьте отзывы:**
   ```bash
   cat feedback_timer.md
   ```

4. **Проверьте email:**
   - Проверьте почту `admin@tabatatimer.ru` на наличие отчётов

5. **Проверьте Telegram:**
   - Проверьте личные сообщения от бота

---

## 🆘 УСТРАНЕНИЕ ПРОБЛЕМ

### Бот не отвечает:

1. Проверьте, что бот добавлен в группу обсуждений как администратор
2. Проверьте правильность `TELEGRAM_CHAT_ID` и `TELEGRAM_BOT_TOKEN`
3. Проверьте логи на наличие ошибок

### Отчёты не отправляются:

1. Проверьте `ADMIN_TELEGRAM_CHAT_ID` (должен быть `422372115` для @lobanoff_pro)
2. Проверьте SMTP настройки
3. Проверьте, что бот может отправлять вам сообщения (напишите боту)

### Статистика не собирается:

1. Проверьте, что модуль `statistics.py` доступен
2. Проверьте права на запись файлов
3. Проверьте логи на наличие ошибок

---

## 📞 ПОДДЕРЖКА

Если что-то не работает:
1. Проверьте логи
2. Проверьте все переменные окружения
3. Проверьте документацию: `STATISTICS_AND_REPORTS.md`

---

**Дата обновления:** 2025-01-06  
**Платформа:** Yandex Cloud  
**Канал:** @fitnesstimer

