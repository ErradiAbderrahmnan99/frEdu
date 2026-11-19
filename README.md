# frEdu — Ta3allom l-Fransiya b Darija (A2 ➜ B1) 🇲🇦🇫🇷

Système gratuit, serverless w bla 7ta chi masrouf bach t-t3ellem l-français men niveau A2 l-B1. Kolchi mbeṣṣet w mchrou7 b Darija mktouba b l-Latin (Arabizi: 3, 7, 9).

Had l-projet fih:
1. **Comprehensible Input (Krashen i+1)**: 30 9issa 9sira (150–200 kelma) fiha mawaḍi3 mn l-wa9i3 l-meghribi (l-khedma w l-7ayat l-yawmiya).
2. **Spaced Repetition (Moraja3a)**: L-kelmat li khtariti kay-rej3o lik f 1, 3, 7, 14, 30 yam bach ma tensahomch.
3. **Shadowing**: Tṣennat l-joumla, sjel sawtek b l-micro, w 9aren m3a n-not9 l-aṣli.
4. **Bot Telegram**: Kay-sift lik kol sba7 9issat lyoum w l-kelmat li 3ndek f r-révision.

---

## 🛠️ Kifach t-f33el l-projet khotwa b khotwa (Setup Guide)

### 1. Kifach t-creer bot f Telegram b @BotFather
1. 7el Telegram w 9elleb 3la `@BotFather`.
2. Sift lih l-commande: `/newbot`.
3. 3tih smiya l-lbot dyalek (mital: `Mon Prof Français`).
4. 3tih username kay-tsala b `bot` (mital: `mon_prof_fr_bot`).
5. @BotFather ghadi y3tik wa7ed **HTTP API Token** (fih ar9am w 7ourouf, mital: `7123456789:AAH...`). Khezzno mezyan w ma t-werrih l-7edd.

---

### 2. Sift `/start` l-lbot dyalek
1. Dkhol l-lbot li 3ad sayebti f Telegram.
2. Wrek 3la **Start** aw sift lih `/start`.
3. Had l-khotwa daroriya bach l-bot y9der y-sift lik l-messages.

---

### 3. Kifach tjbed Chat ID dyalek
1. 7el l-motasaffi7 (navigateur) w dkhol l-had l-lien (3ewwed `<TOKEN>` b l-token dyalek):
   ```text
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
2. Ghadi ytl3 lik JSON fih l-message li sifti. 9elleb 3la:
   ```json
   "chat": {
     "id": 123456789,
     "first_name": "..."
   }
   ```
3. Dak r-raqm li 7da `"id":` huwa **Chat ID** dyalek (mital: `123456789`). Khezzno 7ta huwa.

---

### 4. Zid l-3 Secrets f GitHub Repo
1. Dkhol l-repo dyalek f GitHub.
2. Mchi l-**Settings** ➜ **Secrets and variables** ➜ **Actions**.
3. Wrek 3la **New repository secret** w zid had l-3:
   - `TELEGRAM_BOT_TOKEN`: dak l-token li 3tak @BotFather.
   - `TELEGRAM_CHAT_ID`: dak r-raqm dyal chat id li jbedti.
   - `APP_URL`: l-lien dyal l-app f GitHub Pages (mital: `https://username.github.io/frEdu/`).

---

### 5. Actiwer GitHub Pages
1. F l-repo dyalek, dkhol l-**Settings** ➜ **Pages**.
2. F **Build and deployment** ➜ **Source**, khtar **Deploy from a branch**.
3. Khtar branch: `main` w dossier: `/ (root)`, w wrek 3la **Save**.
4. Men b3d d9i9a ghadi y3tik l-lien dyal l-app (huwa li ghadi t-7otto f `APP_URL`).

---

### 6. Khddem l-workflow l-merra l-lowla (Test Manual)
1. Dkhol l-onglet **Actions** f GitHub.
2. Wrek 3la workflow **Daily Telegram French Lesson** f l-issar.
3. Wrek 3la **Run workflow** ➜ khtar branch `main` ➜ wrek 3la z-zerre l-azraq **Run workflow**.
4. Ghadi y-tchekkaw l-unit tests, y-kheddem l-bot, w ghadi ywslek awwel message f Telegram!

---

### 7. Kifach t-beddel sa3a dyal l-message
L-bot kay-khdem kol nhar b GitHub Actions Cron.
1. 7el l-milaf [daily.yml](file:///.github/workflows/daily.yml).
2. Ghadi tl9a fih:
   ```yaml
   schedule:
     - cron: '0 8 * * *'
   ```
   `0 8 * * *` kat-3ni 08:00 UTC (li hiya 09:00 b waqt l-Meghrib f l-mouchta).
3. Ila bghiti y-wslek m3a 07:00 UTC (08:00 dyal l-Meghrib), beddelha l:
   ```yaml
   - cron: '0 7 * * *'
   ```
4. Dir commit w push.

---

### 8. Kifach t-zid 9isas jdad f `data/stories.json`
L-milaf [stories.json](file:///data/stories.json) fih 30 9issa. Ila kmmltihom w bghiti t-zid qisas khrin:
1. 7el [data/stories.json](file:///data/stories.json).
2. Zid objet jdid f la fin:
   ```json
   {
     "id": 31,
     "title": "Titre dyal l-9issa",
     "topic": "vie quotidienne",
     "text": "Nass l-kamel dyal l-9issa (bin 150 w 200 kelma)...",
     "glossary": [
       {
         "word": "emprunter",
         "darija": "tsellef",
         "example": "Je peux emprunter ton stylo ?"
       }
     ],
     "shadowing": [
       "Joumla 1 taken mn n-nass.",
       "Joumla 2 taken mn n-nass.",
       "Joumla 3 taken mn n-nass.",
       "Joumla 4 taken mn n-nass.",
       "Joumla 5 taken mn n-nass."
     ]
   }
   ```
3. Chourout:
   - Bin 150 w 200 kelma f l-`text`.
   - Bin 8 w 12 l-kelma f l-`glossary` (khess kol kelma tkoun kayna f l-`text`).
   - 5 d l-jomla f `shadowing` mkhoudin nichan mn n-nass.

---

## 📱 Kifach t-kheddem l-bot mn Telegram

F ayy waqt t9der t-sift l-bot had l-awamir:
- `/add word1, word2, word3` : Kay-9elleb 3lihom f l-glossaire dyal ga3 l-9isas. Ila l9ahom, kay-zidhom l-deck dyalek b l-ma3na b Darija. Ila ma l9ahomch, kay-goul lik sift: `/add mot = ma3na`.
- `/add mot = ma3na` : Kay-zid l-kelma nichan b l-ma3na li 3titih.
- `/hard mot` : Kay-rejje3 dik l-kelma l-Stage 0 bach t-raj3ha lyoum/ghedda.
- `/list` : Kay-sift lik l-liste kamla dyal l-deck dyalek m3a l-istapat (stages) dyal kol kelma.

---

## 🌐 L-App f l-Web (PWA & Offline)
- **Audio TTS**: Tṣennat l-l9issa b voice française (fr-FR), w t7ekkem f s-sor3a (0.6x ➜ 1.2x).
- **Sentence by sentence**: Wrek 3la ayy joumla bach t-9raha bou7dha m3a highlight f l-waqt.
- **Dictionaire Darija b l-klick**: Wrek 3la ayy kelma msettra bach ytl3 lik popup fih l-ma3na b Darija, mital, زر dyal s-sawt 🔊, w زر `➕ Zid l-révision`.
- **Shadowing**: Sjel sawtek b l-micro w 9arno m3a s-sawt l-aṣli.
- **Moraja3a (Flashcards)**: Wrek bach t-9leb l-wer9a, w khtar `3reftha` (kat-zid l-9dam: 1, 3, 7, 14, 30 yam) aw `ma3reftaach` (kat-rje3 l-Stage 0).
- **Offline**: L-app kat-kheddem offline 100% mn b3d awwel dkhla grâce l-Service Worker w Manifest PWA.
- **Sauvegarde**: T9der t-telechargi l-khezin dyal l-kelmat b JSON w t-rej3o f ayy weqt.

---

## 🧪 Tests w Dry Run f Terminal
Bach t-tester l-bot f l-ordinateur dyalek bla ma t-sift f Telegram:
```bash
# Test unitaires
python3 -m unittest bot/test_send.py

# Dry run (kay-werrik chno ghadi ytsift bla token)
python3 bot/send.py --dry-run
```
