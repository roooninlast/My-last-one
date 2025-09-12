# Telegram → n8n JSON Bot (Arabic)

بوت تيليغرام بسيط: يأخذ وصف مهمة من المستخدم ويعيد **ملف JSON** جاهز للاستيراد في **n8n**،
مع **فحوصات صحة** أساسية للتأكد أن الأتمتة منطقية قدر الإمكان.

## التشغيل محليًا
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TG_BOT_TOKEN=ضع_توكن_البوت_هنا
export TIMEZONE=Africa/Algiers
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

اضبط Webhook:
```
https://api.telegram.org/bot<TG_BOT_TOKEN>/setWebhook?url=<PUBLIC_URL>/telegram
```

## النشر على Render (الخطة المجانية)
1) ارفع هذا المشروع إلى GitHub.
2) أنشئ خدمة Web جديدة في Render من المستودع.
3) اعتمد `render.yaml` أو اكتب الأوامر يدويًا:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4) أضف متغيرات البيئة:
   - `TG_BOT_TOKEN` (مطلوب)
   - `TIMEZONE` (اختياري، افتراضي Africa/Algiers)
5) بعد الإقلاع، اضبط الـ Webhook على عنوان الخدمة `/telegram`.

## كيف أعدّل الذكاء الاصطناعي؟
الملف `app/llm.py` يحتوي دالة `plan_from_text`.
حاليًا منطق تجريبي (بدون مزود LLM). استبدله بنداء فعلي لمزودك وأعد
بناء **WorkflowSpec**.

## ماذا يحدث بعد الاستيراد في n8n؟
- أنشئ Credential باسم **Telegram Account** واربطه بتوكن البوت.
- عرّف متغيّر البيئة `TELEGRAM_CHAT_ID` أو عدّل عقدة Telegram لوضع Chat ID مباشرة.
- اختبر العقدة خطوة بخطوة من n8n.

> هذا المستودع مخصص للانطلاق بسرعة. طوّره كما تشاء.


## ربط مزود LLM عبر OpenRouter (اختياري)
- أضف `OPENROUTER_API_KEY` و `OPENROUTER_MODEL` كمتغيرات بيئة في Render.
- اضبط `DEMO_MODE=false` لتفعيل النداء الحقيقي للموديل.
- الافتراضي يستخدم `anthropic/claude-3.5-sonnet`، ويمكن تغييره إلى أي موديل متاح على OpenRouter.
