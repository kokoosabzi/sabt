# Appointments and Reminders Specification

## 1. هدف

این سند رفتار دامنه نوبت‌دهی و Reminderها را مشخص می‌کند تا Calendar، Appointment، Operation و Notificationها بر اساس قواعد واحد پیاده‌سازی شوند.

Appointment یک entity مستقل از Operation است.

- Appointment می‌تواند بدون Operation وجود داشته باشد.
- Operation می‌تواند بدون Appointment ایجاد شود.
- یک Appointment می‌تواند به چند Operation متصل شود.
- Appointment Type تعیین می‌کند Present چه اثری بر Operation داشته باشد.

## 2. مفاهیم اصلی

### Project
تنظیمات نوبت‌دهی در context پروژه اعمال می‌شوند.

### Appointment Type
نوع نوبت رفتار آن را مشخص می‌کند، از جمله عنوان، مدت یا slot behavior، قواعد رزرو، رفتار Present و Reminder rules. Appointment Type می‌تواند global/base باشد و در Project فعال و پیکربندی شود.

### Appointment Slot
Slot یک بازه زمانی قابل رزرو است که از configuration پروژه/نوع نوبت تولید یا محاسبه می‌شود.
پارامترهای قابل تنظیم: start/end time، interval، working days، shift، capacity و در صورت نیاز تعطیلات/blocked periods.

## 3. Appointment States

وضعیت‌های اصلی:
- Reserved
- Present
- No-Show
- Cancelled
- Done

Free در Calendar وضعیت محاسباتی slot است و الزاماً رکورد Appointment ندارد.

### State Transition Baseline
- Reserved → Present
- Reserved → No-Show
- Reserved → Cancelled
- Present → Done
- Present → Cancelled در صورت مجاز بودن workflow

Transitionهای دیگر باید توسط workflow/permission کنترل شوند. هر transition مهم باید actor، timestamp و Audit داشته باشد.

## 4. Reservation Flow

1. انتخاب Project
2. انتخاب Appointment Type
3. انتخاب تاریخ
4. انتخاب slot
5. انتخاب/ایجاد Personهای مرتبط
6. تکمیل اطلاعات مورد نیاز
7. بررسی ظرفیت و conflict
8. ایجاد Appointment
9. ثبت Audit
10. فعال شدن Reminderهای مرتبط

رزرو باید transactionally امن باشد تا دو کاربر نتوانند یک ظرفیت واحد را همزمان تصاحب کنند.

## 5. Conflict و ظرفیت

Backend منبع حقیقت ظرفیت است. UI ممکن است slot را Free نشان دهد، اما هنگام Reserve باید availability دوباره بررسی شود.

در رقابت همزمان فقط یک درخواست مجاز به رزرو ظرفیت است و درخواست دیگر باید conflict قابل فهم دریافت کند. اگر ظرفیت slot بیشتر از 1 باشد، reservation تا رسیدن به capacity مجاز است.

ظرفیت configurable است و نباید مقدار ثابت در کد باشد.

## 6. Present

Present یعنی مراجعه/حضور واقعی ثبت شده است. حداقل داده‌ها: appointment، actor، timestamp و state transition و در صورت نیاز توضیح.

Appointment Type دارای behavior configurable است:

### Attendance Only
فقط حضور ثبت می‌شود.

### Attendance + Start Operation
حضور ثبت شده و Operation مربوط ایجاد یا شروع می‌شود.

در حالت دوم Appointment به Operation لینک می‌شود و یک Appointment می‌تواند چند Operation داشته باشد. ایجاد Operation باید transactionally امن باشد و failure نباید وضعیت مبهم ایجاد کند.

## 7. No-Show

No-Show زمانی ثبت می‌شود که مراجعه مورد انتظار انجام نشده باشد. UI باید ثبت سریع No-Show را از Calendar و Appointment Detail فراهم کند.

حداقل actor، timestamp، appointment و reason در صورت نیاز ثبت می‌شود. Reminderهای آینده طبق rule متوقف یا به‌روزرسانی می‌شوند.

## 8. Cancelled

لغو باید actor و timestamp داشته باشد و در صورت policy شامل reason و source باشد. Slot پس از Cancelled دوباره قابل رزرو است مگر policy دیگری تعیین شده باشد. Reminderهای آینده طبق rule لغو یا inactive می‌شوند.

## 9. Done

Done پایان lifecycle عملیاتی Appointment است. Done معمولاً پس از Present ثبت می‌شود. اگر Appointment چند Operation داشته باشد، Done بودن Appointment به معنی Finalized بودن همه Operationها نیست؛ دو lifecycle مستقل‌اند.

## 10. Calendar

Calendar حداقل نمای روزانه و در صورت نیاز هفتگی ارائه می‌کند. هر slot اطلاعات time، Appointment Type، status، شخص/افراد اصلی در صورت مجوز و Operation indicator در صورت وجود را نشان می‌دهد.

رنگ تنها نشانه status نیست و text/icon نیز لازم است.

## 11. Appointment Detail

Appointment Detail شامل زمان و نوع، افراد مرتبط، وضعیت، تاریخچه transition در صورت مجوز، Operationهای مرتبط، Reminderهای مرتبط، توضیحات و Audit summary در صورت permission است.

Quick Actions بر اساس state و permission: Reserve/Edit، Present، No-Show، Cancel، Done، Open Operation و Create Operation.

## 12. Operation Linking

رابطه Appointment و Operation یک‌به‌چند است. برای هر Operation مرتبط حداقل identifier، Operation Type، state و created_at قابل مشاهده باشد.

## 13. Reminder Engine

Reminder Engine rule-based است. Reminder یک notification/event است که بر اساس rule و زمان/شرط مشخص ایجاد می‌شود. منطق Reminder نباید برای یک Appointment Type به‌صورت hard-coded نوشته شود.

## 14. Reminder Rule

هر rule می‌تواند شامل name، active/inactive، scope، trigger، offset، conditions، target، delivery channel و deduplication policy باشد.

Scope می‌تواند Project، Appointment Type، Appointment و Operation Type باشد. V1 حداقل Project و Appointment Type را پشتیبانی می‌کند.

## 15. Triggerهای پایه

Triggerها configurable هستند، از جمله شروع shift، پایان روز کاری قبل از appointment، زمان مشخص قبل از appointment، هنگام Reserve، تغییر state، Present، No-Show، Cancel و نزدیک شدن deadline یک Operation. این فهرست extensible است.

## 16. Reminder Timing

Reminder می‌تواند relative یا event-based باشد.

Relative: مانند 24 ساعت، 2 ساعت یا 30 دقیقه قبل.

Event-Based: مانند بلافاصله بعد از Reserve یا هنگام Present/No-Show.

برای relative timing، timezone طبق سیاست نهایی timezone تفسیر می‌شود.

## 17. Reminder Recipient

Target می‌تواند ایجادکننده Appointment، کاربر مسئول، نقش مشخص در پروژه، گروه/Role یا کاربر مشخص باشد.

V1 می‌تواند delivery را به in-app notification محدود کند، اما مدل باید برای کانال‌های بعدی آماده باشد.

## 18. Notification Lifecycle

وضعیت‌های حداقلی: Pending، Delivered، Read، Dismissed، Cancelled.

در V1، Delivered می‌تواند به معنی ایجاد موفق notification داخل سیستم باشد. Read توسط کاربر ثبت می‌شود.

Reminder مربوط به Appointment لغوشده یا No-Show نباید بدون rule جدید notification تکراری تولید کند.

## 19. Deduplication

هر Reminder Rule باید از notification تکراری برای یک event جلوگیری کند.

Deduplication key پیشنهادی: rule + target + appointment/operation + scheduled trigger. این uniqueness باید در backend enforce شود.

## 20. Reminder Recalculation

با تغییر زمان Appointment، Appointment Type، Cancel، No-Show، recipient یا فعال/غیرفعال شدن Rule، Reminderهای آینده باید دوباره ارزیابی شوند.

## 21. Appointment Reschedule

اگر reschedule فعال باشد: permission check → بررسی slot جدید → conflict check → تغییر زمان → audit → recalculation reminderها.

Appointment حاضرشده نباید بدون workflow ویژه reschedule شود.

## 22. Audit Requirements

حداقل رخدادهای قابل Audit: created، updated، Reserved، Present، No-Show، Cancelled، Done، Rescheduled، Operation linked، Reminder rule changed، Reminder generated، Notification read و Reminder cancelled.

## 23. Permission Baseline

Permissionهای پیشنهادی:
- appointment.view
- appointment.create
- appointment.update
- appointment.reserve
- appointment.present
- appointment.no_show
- appointment.cancel
- appointment.done
- appointment.reschedule
- appointment.create_operation
- reminder.view
- reminder.manage
- reminder.read

Backend باید permission را enforce کند.

## 24. Concurrency Requirements

در Reserve و تغییرات حساس Appointment از optimistic locking، transaction برای allocation ظرفیت، conflict response قابل فهم و عدم silent overwrite استفاده شود.

## 25. Data Integrity Invariants

- Appointment مستقل از Operation است.
- Appointment می‌تواند صفر یا چند Operation داشته باشد.
- Operation می‌تواند بدون Appointment ایجاد شود.
- Free الزاماً رکورد Appointment نیست.
- Present باید actor و timestamp داشته باشد.
- Reservation باید capacity/conflict را در backend دوباره بررسی کند.
- Done کردن Appointment به معنی Finalize شدن Operation نیست.
- Reminderها باید قابل audit و deduplicate باشند.
- Cancel/No-Show باید Reminderهای آینده را طبق rule بازتنظیم کنند.
- Reminder Engine نباید منطق کسب‌وکار را به UI وابسته کند.

## 26. V1 Scope

V1 شامل Calendar، configurable slots/intervals، Appointment Types، Reserve، Present، No-Show، Cancel، Done، Appointment → multiple Operations، rule-based in-app reminders، reminder deduplication، audit و permission enforcement است.

V1 الزاماً شامل SMS، Email delivery، WhatsApp، external calendar synchronization یا public booking portal نیست؛ معماری باید امکان افزودن این کانال‌ها را بدون بازطراحی Appointment domain فراهم کند.
