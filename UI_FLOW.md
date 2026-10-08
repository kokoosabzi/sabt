# UI Flow Specification

## 1. هدف

این سند جریان اصلی رابط کاربری SABT را تعریف می‌کند؛ به‌گونه‌ای که کاربر عملیاتی بتواند با کمترین رفت‌وبرگشت بین صفحه‌ها، نوبت، عملیات، قرارداد، اشخاص، ملک و اسناد را مدیریت کند.

این سند درباره رفتار و ساختار UX است، نه پیاده‌سازی HTML/CSS/JS.

## 2. اصول UX
- رابط اصلی فارسی و RTL است.
- زبان معماری i18n-ready است و متن فارسی نباید در منطق برنامه hard-code شود.
- فیلدهای فنی مانند شماره قرارداد، کدها و شناسه‌ها می‌توانند بر اساس محتوا LTR نمایش داده شوند.
- عملیات مهم باید وضعیت واضح و قابل ردگیری داشته باشند.
- کاربر نباید برای کارهای پرتکرار مجبور به بازگشت مکرر به Dashboard شود.
- وضعیت‌های نهایی و قفل‌شده باید از وضعیت‌های قابل ویرایش متمایز باشند.
- حذف فیزیکی، override و اقدامات حساس باید confirmation و permission مناسب داشته باشند.
- خطاهای اعتبارسنجی باید نزدیک همان فیلد یا مرحله نمایش داده شوند.
- فرم‌های طولانی باید Stepper و Quick Navigation داشته باشند.

## 3. Shell اصلی برنامه
- Header: پروژه فعال، کاربر جاری، اعلان‌ها/reminders، تنظیمات
- Navigation: خانه، نوبت‌ها، عملیات، قراردادها، اشخاص، املاک، اسناد، فرم‌ها و چاپ، محدودیت‌ها، پروژه‌ها، تنظیمات
- بخش‌های Users/Roles، Audit و Backup/Restore فقط در صورت permission نمایش داده شوند.
- Context indicator پروژه فعال و در صورت نیاز Operation/Contract جاری را نشان می‌دهد.

## 4. Dashboard / خانه
Dashboard نقطه شروع عملیاتی است، نه گزارش‌گیری سنگین.
- Today: نوبت‌های امروز و وضعیت Reserved/Present/No-Show/Cancelled/Done
- Calendar: نمای روزانه/هفتگی در صورت فعال‌سازی
- Quick Search: شماره قرارداد، شماره ثبت، شخص، ملک، شماره عملیات
- Recent Operations: عملیات اخیر با وضعیت و آخرین تغییر
- Quick Actions: ایجاد نوبت، عملیات، شخص، ملک و import محدودیت‌ها در صورت مجوز
Dashboard منبع حقیقت جداگانه نیست و داده‌ها را از entityهای اصلی می‌خواند.

## 5. جست‌وجوی سراسری
Global Search باید Operation، Contract، Person، Property، Appointment و در صورت مجوز Document را پیدا کند.
هر نتیجه باید نوع entity، شناسه/شماره مهم، وضعیت و اقدام سریع داشته باشد.
کنترل دسترسی نتایج باید در backend انجام شود؛ UI تنها لایه امنیت نیست.

## 6. Appointment Flow
### 6.1 Calendar
Slotها بر اساس configuration پروژه/نوع نوبت ساخته می‌شوند.
حالت‌ها: Free، Reserved، Present، No-Show، Cancelled، Done. Free می‌تواند state محاسباتی باشد.

### 6.2 Reserve
1. انتخاب Appointment Type
2. انتخاب تاریخ/slot
3. انتخاب یا ایجاد Personهای مرتبط
4. ثبت توضیحات لازم
5. بررسی conflict
6. ایجاد Appointment
7. Audit

### 6.3 Present
در Present، حضور و timestamp ثبت می‌شود. بر اساس Appointment Type، سیستم یا فقط حضور را ثبت می‌کند یا حضور را همراه با ایجاد/شروع Operation ثبت می‌کند.
این رفتار configurable است و نباید در UI hard-code شود.

### 6.4 No-Show / Cancel / Done
No-Show عدم حضور را ثبت می‌کند؛ Cancelled در صورت نیاز علت دارد؛ Done نوبت را پایان‌یافته می‌کند. تمام transitionها باید قواعد workflow و permission را رعایت کنند.

## 7. Operation Flow
### 7.1 Operation List
فیلترهای پایه: Project، Operation Type، State، Date range، Person، Property، Contract Number، Registration Number و Assigned user در صورت وجود.
لیست باید pagination داشته باشد.

### 7.2 Create Operation
Operation از Appointment یا به‌صورت مستقیم ایجاد می‌شود.
شروع شامل Project، Operation Type، اطلاعات اولیه، Partyها، Property در صورت نیاز و ایجاد working snapshot است.

### 7.3 Operation Workspace
Operation Workspace مرکز انجام کار است.
- Header: شناسه Operation، Type، State، Project و lock/concurrency indicator
- Stepper: اطلاعات پایه، اشخاص/Partyها، ملک، قرارداد، custom fields، اسناد، محدودیت‌ها، فرم/چاپ، Review، Finalize
- Quick Navigation: پرش مستقیم به مراحل با نشان completion/error/warning
- Activity/Audit summary در صورت مجوز

### 7.4 Working Snapshot
هنگام ایجاد Operation، داده‌های لازم از Person/Property به working snapshot منتقل می‌شوند. تغییر master نباید بدون rule مشخص snapshot کاری را خاموش تغییر دهد.

### 7.5 Review
پیش از Finalize باید required fields، required parties، required documents، workflow rules، restriction rules، numbering readiness و concurrency/version check بررسی شوند. خطاها باید به مرحله مربوطه لینک شوند.

### 7.6 Finalize
Finalize اقدام حساس است: خلاصه نهایی، هشدارها و تأیید کاربر نمایش داده می‌شوند؛ backend درخواست را پردازش می‌کند؛ سپس وضعیت نهایی، Registration Number در صورت وجود، Generated Documents و timestamp نمایش داده شده و workspace read-only می‌شود.

## 8. Correction Flow
Operation نهایی‌شده مستقیماً editable نیست.
مسیر: Finalized → Correction Request → Approval → New Version → Finalization
UI باید تفاوت نسخه فعلی و نسخه جدید را برای کاربر مجاز قابل فهم کند. درخواست اصلاح حداقل دلیل، requester، timestamp و approval status دارد.

## 9. Contract Flow
Contract در Operation Workspace مدیریت می‌شود.
- هر Operation حداکثر یک Contract دارد.
- Contract در V1 دقیقاً یک Property دارد.
- Contract Number دستی است.
- Registration Number در صورت policy مناسب تولید می‌شود.
- Contract Number کلید اصلی DB نیست.
صفحه Contract باید به Operation، Property، Partyها، Documents و Restrictions دسترسی سریع داشته باشد.

## 10. Person Flow
Person یک master record مرکزی است.
صفحه Person شامل اطلاعات پایه، راه‌های تماس، سوابق عملیات قابل مشاهده و در صورت مجوز پروژه‌ها و اسناد مرتبط است.
هنگام استفاده در Operation، snapshot عملیاتی طبق workflow ایجاد/به‌روزرسانی می‌شود. پس از Finalize، تغییر Person تاریخچه Operation را تغییر نمی‌دهد.

## 11. Property Flow
Property یک master record مرکزی است.
صفحه Property شامل مشخصات ملک، عملیات، قراردادها و اسناد مرتبط و در صورت مجوز پروژه‌هاست.
در Operation داده مورد نیاز به working/final snapshot منتقل می‌شود. تغییر master پس از Finalize تاریخچه نهایی را تغییر نمی‌دهد.

## 12. Document Flow
Document یک entity مستقل و قابل جست‌وجو است.
Attach: انتخاب Document Type → انتخاب فایل → validation → hash → ذخیره filesystem → metadata در DB → Audit.
Replace: فایل جدید supersede قبلی می‌شود؛ در V1 file-version history نگهداری نمی‌شود ولی replacement audit می‌شود.
Archive با audit انجام می‌شود و physical delete فقط برای Admin و طبق retention policy مجاز است.

## 13. Forms / Print Flow
Select Template → Preview → Validate Dynamic Fields → Generate PDF → Print
Template می‌تواند System logo، Project logo، Template-specific logo، Dynamic data و QR داشته باشد.
Designer با mm و engine داخلی PDF با point کار می‌کند.

## 14. QR Flow
در Preview/Generate، payload از داده‌های مجاز ساخته و checksum/signature تولید می‌شود؛ QR مطابق position/size قالب رندر می‌شود. V1 public verification URL ندارد.

## 15. Restriction Flow
Import: Upload/Paste → Map Columns → Validate → Preview → Commit → Audit
ورودی‌ها CSV، Excel و Clipboard/Paste هستند.
Runtime: Evaluate Rules → Warning/Block → Optional Override → Audit
Override فقط با permission مجاز و در صورت اجازه Rule انجام می‌شود.

## 16. User / Permission Flow
UI فقط قابلیت‌های مجاز را نمایش می‌دهد، اما enforcement نهایی در backend است.
Permissionها می‌توانند project، operation type، operation action، documents، correction approval، restriction override، audit و backup/restore را کنترل کنند.

## 17. Concurrency UX
در فرم‌های حساس lock indicator نمایش داده شود. Version mismatch باید واضح باشد. سیستم نباید تغییر کاربر دیگر را silently overwrite کند. در conflict، کاربر باید وضعیت جدید را ببیند و تصمیم آگاهانه بگیرد. lockهای موقت باید timeout/release policy داشته باشند.

## 18. Notifications / Reminders
Reminderها به‌صورت notification نمایش داده شوند: unread count، لیست reminder، link مستقیم به Appointment/Operation و mark as read. رخدادهای مهم در صورت policy audit شوند.

## 19. Responsive / Display
V1 desktop-first و مناسب شبکه داخلی است. صفحات پرتراکم مانند Operation Workspace برای نمایشگرهای اداری طراحی می‌شوند. Responsive behavior از ابتدا در CSS لحاظ شود، ولی V1 mobile-first نیست.

## 20. Error / Confirmation UX
سه سطح خطا: Field Error، Workflow Error و System/Conflict Error.
اقدامات حساس مانند Finalize، Correction Request، Approval، Restriction Override، Archive/Delete و Restore Backup باید confirmation داشته باشند.
پیام خطا باید actionable باشد.

## 21. Accessibility Baseline
- keyboard navigation برای فرم‌های اصلی
- focus قابل مشاهده
- label واقعی برای inputها
- پیام خطا قابل ارتباط با field
- رنگ تنها نشانه status نباشد
- statusها علاوه بر رنگ، text/icon داشته باشند

## 22. UX Invariants
- Appointment و Operation مستقل هستند.
- یک Appointment می‌تواند چند Operation داشته باشد.
- Operation می‌تواند بدون Appointment ایجاد شود.
- Operation حداکثر یک Contract دارد.
- Contract دقیقاً یک Property دارد.
- Contract Number دستی است.
- Registration Number از policy می‌آید.
- Finalized Operation عادی قابل ویرایش نیست.
- Correction با version جدید انجام می‌شود.
- Finalized snapshots مستقل از master records هستند.
- Permission enforcement در backend انجام می‌شود.
- SQLite مستقیماً از client باز نمی‌شود.