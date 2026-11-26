# LearnWell Burnout — Single-Container Deploy (`v1` + `v2`)

Ця гілка (`deploy`) містить конфігурацію для тимчасового запуску **обох версій в одному Docker-контейнері**:

- **v1** (гілка `main`, ЛР4) → порт **`8001`** (`v1smart.dvkpowered.org`)
- **v2** (гілка `lab5`, ЛР5 + Evidently `/monitor`) → порт **`8002`** (`v2smart.dvkpowered.org`)

Гілки `main` та `lab5` залишаються без змін.

## 1. Запуск на сервері (`192.168.0.103`)

Або запустіть зі свого ПК:
```bash
SSH_USER=<твій_юзер_на_сервері> ./deploy-to-server.sh
```

Або вручну на сервері `192.168.0.103`:
```bash
git clone --branch deploy --single-branch https://github.com/Kukuliak-Dmytro/learnwell-burnout.git ~/learnwell-burnout-deploy
cd ~/learnwell-burnout-deploy
docker compose up -d --build
```

Перевірка:
```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
```

## 2. Налаштування піддоменів (`dvkpowered.org`)

1. У DNS `dvkpowered.org` додайте `A` (або `CNAME`) записи для:
   - `v1smart.dvkpowered.org`
   - `v2smart.dvkpowered.org`
2. У вашому reverse proxy (Nginx / Caddy / Nginx Proxy Manager / Cloudflare Tunnel) направте:
   - `v1smart.dvkpowered.org` → `http://127.0.0.1:8001`
   - `v2smart.dvkpowered.org` → `http://127.0.0.1:8002` (таймаут >= 120s для `/monitor`)

Якщо використовуєте системний Nginx, готовий конфіг лежить у `nginx-dvkpowered.conf`:
```bash
sudo cp nginx-dvkpowered.conf /etc/nginx/sites-available/learnwell-burnout.conf
sudo ln -sf /etc/nginx/sites-available/learnwell-burnout.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# За потреби HTTPS через Let's Encrypt:
sudo certbot --nginx -d v1smart.dvkpowered.org -d v2smart.dvkpowered.org
```

## 3. Після запуску

- `v1` Swagger: `https://v1smart.dvkpowered.org/docs`
- `v2` Swagger: `https://v2smart.dvkpowered.org/docs`
- `v2` Evidently Data Drift: `https://v2smart.dvkpowered.org/monitor`
- `v2` Evidently Data Quality: `https://v2smart.dvkpowered.org/monitor?report=quality`

Щоб увімкнути `POST /predict`, виконайте один раз `POST /train-model` на `v1` та `v2` (або через Swagger).

## 4. Видалення після використання

```bash
cd ~/learnwell-burnout-deploy
docker compose down -v
```
