# کلیدهای API و تنظیمات — GradMatch AI

این سند دقیقاً می‌گوید چه کلیدی لازم است، از کجا بگیری، کجای کد بگذاری و چطور مطمئن شوی کار می‌کند.

## خلاصه در یک نگاه

| # | سرویس | اجباری؟ | برای چه کاری | متغیر در `backend/.env` | لینک گرفتن کلید |
|---|-------|---------|---------------|--------------------------|------------------|
| ۱ | **OpenAlex** | برای «جستجوی زنده» بله | پیدا کردن استاد و مقالات اخیر از هر دانشگاهی | `OPENALEX_API_KEY` | <https://openalex.org/settings/api> |
| ۲ | **LLM** (OpenAI / DeepSeek / OpenRouter / Groq / Ollama) | خیر | نوشتن ایمیل شخصی‌سازی‌شده به‌جای متن آماده | `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` | <https://platform.openai.com/api-keys> |
| ۳ | **SMTP** | خیر | ارسال لینک بازیابی رمز عبور | `SMTP_HOST` … `SMTP_FROM` | <https://ethereal.email/> یا Gmail |
| ۴ | **Sentence-Transformers** | خیر | جایگزینی TF-IDF با مدل ترنسفورمر (کیفیت بهتر، کندتر) | `EMBEDDING_BACKEND=sbert` | بدون کلید — <https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2> |

> **مهم:** نسخهٔ فعلی **بدون هیچ کلیدی هم کار می‌کند**. اگر `OPENALEX_API_KEY` خالی باشد، برنامه روی «دیتاست نمونه» (۶۴ استاد و ۳۰۶ مقاله از OpenAlex در دانشگاه‌های تورنتو، آمستردام و TUM) اجرا می‌شود. این حالت مخصوص همین دمو و ویدیوی دفاع است. برای اینکه جستجو روی مک‌گیل یا UBC هم کار کند، کلید OpenAlex لازم است.

---

## ۱) OpenAlex — تنها کلیدی که واقعاً «لازم» است

**چرا:** کل استخراج استاد و مقاله از این API می‌آید. بدون کلید، فقط سه دانشگاه دیتاست نمونه جواب می‌دهند.

**مراحل گرفتن کلید (۲ دقیقه):**

1. برو به <https://openalex.org/settings/api>
2. با ایمیل خودت وارد شو (اگر حساب نداری همان‌جا بساز؛ رایگان است).
3. روی **Create API key** (یا دکمهٔ مشابه) بزن.
4. رشته‌ای شبیه `aBcD1234...` می‌گیری؛ کامل کپی کن.

**کجا بگذارم:** در فایل `backend/.env` خط زیر را پر کن:

```env
OPENALEX_API_KEY=aBcD1234...
```

**سهمیه:** در پلن رایگان روزانه سقف مشخصی وجود دارد (در زمان نوشتن این سند ۱۰۰٬۰۰۰ اعتبار در روز). برنامه برای همین سقف دارد:

- `MAX_UNIVERSITIES_PER_RUN=5` — حداکثر ۵ دانشگاه در هر جستجو
- `CACHE_TTL_DAYS=7` — نتایج هر (دانشگاه، موضوع) هفت روز کش می‌شود، پس جستجوی دوم هزینه‌ای ندارد
- `MAX_CANDIDATES_PER_UNIVERSITY=25`

**چطور مطمئن شوم شناسایی شد؟**

- در برنامه: صفحهٔ **Keys & data** → کارت OpenAlex باید «configured» شود و بالا «OpenAlex live» بنویسد.
- در API: `GET http://localhost:8000/api/meta/integrations`
- یا `GET http://localhost:8000/api/health` و مقدار `openalex_key_configured: true`.

> بعد از هر تغییر در `.env`، بک‌اند را متوقف و دوباره اجرا کن (uvicorn بدون `--reload` فایل env را دوباره نمی‌خواند).

---

## ۲) LLM برای نوشتن ایمیل (اختیاری ولی برای ویدیو جذاب)

**چرا:** دکمهٔ «AI version» در پنجرهٔ پیش‌نویس ایمیل، متن آماده را با یک مدل زبانی بازنویسی می‌کند و دقیقاً از همان شواهد مچ (موضوع مشترک + مقاله) استفاده می‌کند. اگر کلید نگذاری، همان متن قالب‌بندی‌شده نمایش داده می‌شود و برنامه خطا نمی‌دهد.

هر سرویس سازگار با OpenAI کار می‌کند. یکی را انتخاب کن:

| سرویس | لینک کلید | `LLM_BASE_URL` | `LLM_MODEL` نمونه | هزینه |
|-------|-----------|----------------|-------------------|-------|
| OpenAI | <https://platform.openai.com/api-keys> | `https://api.openai.com/v1` | `gpt-4o-mini` | بسیار کم (هر ایمیل < ۰.۱ سنت) |
| DeepSeek | <https://platform.deepseek.com/api_keys> | `https://api.deepseek.com/v1` | `deepseek-chat` | ارزان |
| OpenRouter | <https://openrouter.ai/keys> | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini` | متغیر |
| Groq | <https://console.groq.com/keys> | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | سخاوتمندانه رایگان |
| Ollama (محلی) | بدون کلید | `http://localhost:11434/v1` | `llama3.1` | رایگان |

**در `backend/.env`:**

```env
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

برای Ollama (کاملاً آفلاین، بدون کلید) کافی است:

```env
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1
```

**تست:** در صفحهٔ Shortlist روی «Draft email» بزن و تب «AI version» را انتخاب کن. اگر کار نکند، برنامه به‌جای خطا همان قالب را با یک پیام توضیح برمی‌گرداند (fail-safe برای دمو).

---

## ۳) SMTP برای بازیابی رمز (اختیاری)

فقط برای لینک «فراموشی رمز» استفاده می‌شود؛ در دمو لازم نیست.

**ساده‌ترین راه برای تست:** <https://ethereal.email/> — یک ایمیل تست رایگان می‌دهد، همان host/user/pass را در `.env` بگذار.

**Gmail:** در حساب گوگل «App Password» بساز (نیاز به ۲FA دارد):

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=app-password-16-chars
SMTP_FROM=you@gmail.com
SMTP_STARTTLS=true
```

---

## ۴) Sentence-Transformers (بدون کلید)

کیفیت مچ را از «شباهت واژگانی» به «شباهت معنایی» ارتقا می‌دهد:

```powershell
cd backend
.\.venv\Scripts\pip.exe install -r requirements-sbert.txt
```

```env
EMBEDDING_BACKEND=sbert
SBERT_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

اولین اجرا مدل (~۹۰ مگابایت) را از Hugging Face دانلود می‌کند؛ بعد از آن آفلاین کار می‌کند. برای دمو توصیه می‌شود روی `tfidf` بمانی تا سرعت بالا و ریسک دانلود صفر باشد.

---

## امنیت (مهم برای گیت‌هاب)

- فایل `backend/.env` در `.gitignore` هست؛ **هرگز** آن را کامیت نکن.
- در ویدیو، پنل Keys را نشان بده ولی روی مقدار کلید زوم نکن.
- اگر کلیدی لو رفت، از همان سایت revoke کن و کلید جدید بساز.
- `SECRET_KEY` را با این دستور بساز و در `.env` بگذار:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## هزینهٔ کل دمو

| مورد | هزینه |
|------|-------|
| OpenAlex | رایگان (با کلید) |
| LLM (۵ ایمیل نمونه با gpt-4o-mini) | کمتر از ۱ سنت |
| Hugging Face / SMTP | رایگان |
| سرور محلی | رایگان |

یعنی برای ضبط ویدیو، تنها هزینهٔ واقعی می‌تواند چند سنت LLM باشد — و آن هم اختیاری است.
