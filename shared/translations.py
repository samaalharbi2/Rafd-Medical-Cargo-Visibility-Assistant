"""Arabic display translations (airports, facilities, tracking events)."""
AIRPORT_AR = {"JED": "جدة", "RUH": "الرياض", "DMM": "الدمام", "MED": "المدينة المنورة"}
FACILITY_AR = {
    "Mina Emergency Hospital": "مستشفى منى للطوارئ",
    "Arafat (Namira) Field Hospital": "مستشفى عرفات الميداني (نمرة)",
    "Makkah Health Cluster": "تجمع مكة المكرمة الصحي",
    "Madinah Health Cluster": "تجمع المدينة المنورة الصحي",
    "MoH Hajj Logistics Depot": "مستودع لوجستيات الحج بوزارة الصحة",
    "Central Medical Warehouse - Riyadh": "المستودع الطبي المركزي - الرياض",
    "Prophet's Mosque Medical Center": "المركز الطبي بالمسجد النبوي",
    "Quba Health Center": "مركز قباء الصحي",
    "Jamarat Health Center": "مركز الجمرات الصحي",
    "Muzdalifah Medical Point": "نقطة مزدلفة الطبية",
    "King Abdullah Medical City - Makkah": "مدينة الملك عبدالله الطبية - مكة المكرمة",
}
EVENT_AR = {
    "Booked": "تم الحجز", "Accepted": "مقبولة في مطار المنشأ",
    "Departed": "غادرت مطار المنشأ", "Arrived Transit": "وصلت مطار العبور",
    "Arrived Destination": "وصلت مطار الوجهة",
    "SFDA Hold": "معلّقة لدى هيئة الغذاء والدواء",
    "SFDA Cleared": "تم التخليص من هيئة الغذاء والدواء",
    "Cold Chain Alert": "تنبيه سلسلة التبريد",
    "Delivered": "تم التسليم", "Delayed": "تأخير", "Cancelled": "ملغاة",
}
def ap(code, ar):  return AIRPORT_AR.get(code, code) if ar else code
def fac(name, ar): return FACILITY_AR.get(name, name) if ar else name
def evt(name, ar): return EVENT_AR.get(name, name) if ar else name
