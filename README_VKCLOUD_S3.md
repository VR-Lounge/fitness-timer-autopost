# 🚀 Настройка публичного доступа к S3-бакету VK Cloud

## 📋 Параметры подключения

- **S3 Endpoint URL**: `hb.ru-msk.vkcloud-storage.ru`
- **Access Key ID**: `5QFbmJmX45AzvRGs3gzwDD`
- **Secret Key**: ⚠️ **Нужно вставить из буфера обмена** (был скопирован при создании)
- **Bucket Name**: `tabatatimer`

---

## 🎯 Быстрая настройка

### Вариант 1: Автоматический скрипт (рекомендуется)

```bash
cd "/Users/LOBANOFF-PRO/Documents/TABATATIMER.RU/С MediaPipe/fitness-timer-autopost"
./setup_vkcloud_s3.sh YOUR_SECRET_KEY
```

**Где `YOUR_SECRET_KEY`** — это Secret Key, который был скопирован в буфер обмена при создании Access Key.

### Вариант 2: Ручная настройка

#### 1. Настройка credentials:
```bash
aws configure set aws_access_key_id 5QFbmJmX45AzvRGs3gzwDD --profile vkcloud
aws configure set aws_secret_access_key YOUR_SECRET_KEY --profile vkcloud
aws configure set region ru-msk --profile vkcloud
```

#### 2. Создание bucket-policy.json:
```bash
cat > /tmp/bucket-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::tabatatimer/*"
    }
  ]
}
EOF
```

#### 3. Применение bucket policy:
```bash
aws s3api put-bucket-policy \
  --bucket tabatatimer \
  --policy file:///tmp/bucket-policy.json \
  --endpoint-url https://hb.ru-msk.vkcloud-storage.ru \
  --profile vkcloud
```

#### 4. Проверка доступа:
```bash
curl https://tabatatimer.hb.ru-msk.vkcloud-storage.ru/index.html
```

Должен вернуться HTML-код сайта вместо `AccessDenied`.

---

## ✅ Что будет после настройки

1. ✅ `www.tabatatimer.ru` будет работать **в России без VPN**
2. ✅ Все файлы сайта будут публично доступны через VK Cloud
3. ✅ Музыкальные треки и tracks.json будут загружаться
4. ⚠️ `tabatatimer.ru` (без www) пока будет показывать ошибку DNS — для него нужен отдельный редирект на www

---

## 🔍 Полезные команды

### Проверка bucket policy:
```bash
aws s3api get-bucket-policy \
  --bucket tabatatimer \
  --endpoint-url https://hb.ru-msk.vkcloud-storage.ru \
  --profile vkcloud
```

### Список файлов в бакете:
```bash
aws s3 ls s3://tabatatimer/ \
  --endpoint-url https://hb.ru-msk.vkcloud-storage.ru \
  --profile vkcloud
```

### Загрузка файла в бакет:
```bash
aws s3 cp file.txt s3://tabatatimer/ \
  --endpoint-url https://hb.ru-msk.vkcloud-storage.ru \
  --profile vkcloud
```

### Загрузка всей папки:
```bash
aws s3 sync ./public_html/ s3://tabatatimer/ \
  --endpoint-url https://hb.ru-msk.vkcloud-storage.ru \
  --profile vkcloud \
  --delete
```

---

## ⚠️ Важно

- **Secret Key** был скопирован в буфер обмена при создании Access Key — сохрани его в безопасном месте!
- После применения bucket policy может потребоваться несколько минут для активации
- Убедись, что бакет содержит файлы перед проверкой доступа

---

## 🆘 Решение проблем

### Ошибка "AccessDenied"
- Проверь, что bucket policy применена корректно
- Убедись, что используешь правильный Access Key и Secret Key
- Проверь настройки CORS в панели VK Cloud

### Ошибка "NoSuchBucket"
- Убедись, что бакет `tabatatimer` существует
- Проверь правильность endpoint URL

### Ошибка "InvalidAccessKeyId"
- Проверь правильность Access Key ID
- Убедись, что используешь правильный профиль (`--profile vkcloud`)

