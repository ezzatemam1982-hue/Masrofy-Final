import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import time
import base64
import requests

# ---------------------------------------------------------
# إعداد الصفحة
# ---------------------------------------------------------
ICON_FILE = "diamond_icon.png"
page_icon_obj = ICON_FILE if os.path.exists(ICON_FILE) else "💎"

st.set_page_config(
    page_title="مصروفي | Masrofy",
    page_icon=page_icon_obj,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# ✅ الرابط الجديد (تم تحديثه بالرابط الذي أرسلته للتو)
# ---------------------------------------------------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwbXgGRGb6LyZ2_34JApbNXWqvVmQNKRmxaxTWI-GMPw4Wt_UIaegOH994J8owpI1tg/exec"

# المسارات
current_dir = os.path.dirname(os.path.abspath(__file__))
ATTACHMENTS_DIR = os.path.join(current_dir, "attachments")
if not os.path.exists(ATTACHMENTS_DIR): os.makedirs(ATTACHMENTS_DIR)

# ---------------------------------------------------------
# التنسيقات CSS
# ---------------------------------------------------------
st.markdown("""
<style>
    .main {direction: rtl;}
    h1, h2, h3, h4, p, div, label, .stSelectbox, .stNumberInput, .stDateInput, .stTextInput, .stRadio, .stMarkdown, .stTabs {
        text-align: right !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 10px; color: #000; font-weight: bold; flex: 1; }
    .stTabs [aria-selected="true"] { background-color: #2ecc71 !important; color: white !important; }
    .stDownloadButton button { width: 100%; background-color: #f1c40f !important; color: black !important; border: none; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# دوال الاتصال بجوجل (المحرك الرئيسي)
# ---------------------------------------------------------

# 1. دالة سحب البيانات (doGet)
@st.cache_data(ttl=60) # تحديث كل دقيقة
def load_data_from_google():
    try:
        response = requests.get(APPS_SCRIPT_URL)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                # ضبط التنسيقات
                df["التاريخ"] = pd.to_datetime(df["التاريخ"])
                df["المبلغ"] = pd.to_numeric(df["المبلغ"])
                # التأكد من الأعمدة
                cols = ["النوع", "البند", "طريقة الدفع", "ملاحظات", "المرفق"]
                for c in cols:
                    if c not in df.columns: df[c] = ""
                return df
    except Exception as e:
        print(f"Error: {e}")
    
    # لو فشل الاتصال نرجع جدول فاضي عشان التطبيق ميقفش
    return pd.DataFrame(columns=["التاريخ", "السنة", "الشهر", "النوع", "البند", "طريقة الدفع", "المبلغ", "ملاحظات", "المرفق"])

# 2. دالة إرسال البيانات (doPost)
def sync_to_google_direct(row_dict):
    try:
        t_type = str(row_dict.get("النوع", ""))
        trans_type = "income" if "دخل" in t_type else "expense"
        
        payload = {
            "transType": trans_type,
            "date": str(row_dict.get("التاريخ").date()),
            "amount": float(row_dict.get("المبلغ")),
            "category": str(row_dict.get("البند")),
            "subCategory": str(row_dict.get("ملاحظات", "")),
            "method": str(row_dict.get("طريقة الدفع")),
            "note": "Cloud App v4"
        }
        
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        
        if response.status_code == 200:
            return True, "تم"
        return False, f"خطأ: {response.text}"
    except Exception as e:
        return False, f"خطأ اتصال: {str(e)}"

# ---------------------------------------------------------
# تشغيل التطبيق
# ---------------------------------------------------------

# سحب البيانات عند الفتح
df = load_data_from_google()

# القوائم
INCOME_CATEGORIES = ["💰 راتب (نص الشهر)", "💰 راتب (اخر الشهر)", "🏠 إيراد إيجار شقة", "🏆 مكافأة أرباح سنوية", "🎁 مكافأة أخرى / إضافية", "💊 استرداد علاج", "💼 استرداد مأموريات عمل", "➕ أخرى"]
EXPENSE_CATEGORIES = ["🏠 إيجار شقة (سكن)", "🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم", "⚡ فواتير (كهرباء/غاز/مياه)", "🌐 إنترنت وموبايل", "🚗 بنزين ومواصلات", "🔧 صيانة سيارة", "💊 علاج ودواء", "👕 ملابس", "🎓 مصاريف تعليم ودروس", "🧸 مستلزمات الأبناء", "🎉 ترفيه وخروجات", "➕ أخرى"]
INSTALLMENT_TYPES = ["🏢 قسط الشقة الربع سنوي", "📦 أقساط مشتريات (أونلاين/أجهزة)", "🏊 قسط النادي", "➕ أخرى"]
PAYMENT_INCOME = ["💵 كاش", "🏦 تحويل بنكي / راتب", "📱 محفظة إلكترونية"]
PAYMENT_SPENDING = ["💵 كاش", "💳 Credit Card End 8298", "💳 Credit Card End 6016", "📱 محفظة البنك الأهلي", "📱 محفظة CIB", "📱 فودافون كاش"]

if 'current_mode' not in st.session_state: st.session_state['current_mode'] = "مصروفات"
def update_mode(): st.session_state['current_mode'] = st.session_state.mode_selector

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    return None

img_base64_small = get_base64_image(ICON_FILE)
header_logo = f'<img src="data:image/png;base64,{img_base64_small}" width="90" style="vertical-align: middle;">' if img_base64_small else '<span style="font-size: 60px;">💎</span>'

st.markdown(f"""<div style="display: flex; align-items: center; justify-content: center; direction: rtl; margin-bottom: 20px;">
    <div style="margin-left: 15px;">{header_logo}</div><h1 style="color: #2ecc71; margin: 0; font-size: 2.5rem;">مصروفي | Masrofy</h1></div>""", unsafe_allow_html=True)

# زر التحديث اليدوي
if st.sidebar.button("🔄 تحديث البيانات (سحب من جوجل)"):
    st.cache_data.clear()
    st.rerun()

today = datetime.now()
years_list = list(range(today.year - 1, today.year + 4))
default_year_ix = years_list.index(today.year) if today.year in years_list else 1

with st.expander("📅 إعدادات الفلترة", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1: view_year = st.selectbox("السنة", years_list, index=default_year_ix)
    with c2: view_month = st.selectbox("الشهر", range(1, 13), index=today.month - 1)
    with c3: food_budget_limit = st.number_input("ميزانية الطعام", value=5000, step=100)

tab1, tab2, tab3 = st.tabs(["📊 لوحة القيادة", "📝 تسجيل جديد", "📂 السجل"])

with tab1:
    if not df.empty and "التاريخ" in df.columns:
        mask = (df["الشهر"] == int(view_month)) & (df["السنة"] == int(view_year))
        month_df = df[mask]
        total_inc = month_df[month_df["النوع"] == "دخل"]["المبلغ"].sum()
        total_exp = month_df[month_df["النوع"].str.contains("مصروف", na=False)]["المبلغ"].sum()
        total_inst = month_df[month_df["النوع"] == "قسط"]["المبلغ"].sum()
        bal = total_inc - (total_exp + total_inst)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 الدخل", f"{total_inc:,.0f}")
        c2.metric("💸 المصاريف", f"{total_exp:,.0f}")
        c3.metric("📅 الأقساط", f"{total_inst:,.0f}")
        c4.metric("✅ الرصيد", f"{bal:,.0f}", delta_color="normal" if bal >= 0 else "inverse")
        
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            out = month_df[month_df["النوع"].str.contains("مصروف|قسط", regex=True, na=False)]
            if not out.empty: st.plotly_chart(px.pie(out, values='المبلغ', names='البند', hole=0.4), use_container_width=True)
        with g2:
            inc = month_df[month_df["النوع"] == "دخل"]
            if not inc.empty: st.plotly_chart(px.bar(inc, x="البند", y="المبلغ", color="البند"), use_container_width=True)
    else:
        st.info("جاري الاتصال بقاعدة البيانات السحابية...")

with tab2:
    st.subheader("➕ إضافة معاملة")
    options = ["مصروفات", "دخل", "قسط"]
    t_type = st.radio("النوع:", options, horizontal=True, index=options.index(st.session_state['current_mode']), key="mode_selector", on_change=update_mode)
    
    if t_type == "دخل": cat_l, pay_l = INCOME_CATEGORIES, PAYMENT_INCOME
    elif t_type == "قسط": cat_l, pay_l = INSTALLMENT_TYPES, PAYMENT_SPENDING
    else: cat_l, pay_l = EXPENSE_CATEGORIES, PAYMENT_SPENDING
    
    c1, c2 = st.columns([1,1])
    with c1: cat_sel = st.selectbox("التصنيف:", cat_l)
    cust_cat = ""
    if "أخرى" in cat_sel: 
        with c2: cust_cat = st.text_input("اسم المصروف:")
    
    with st.form("entry", clear_on_submit=True):
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            tm = st.selectbox("شهر", range(1, 13), index=today.month - 1)
            ty = st.selectbox("سنة", years_list, index=default_year_ix)
            dv = st.date_input("يوم", datetime.today())
        with c2:
            amt = st.number_input("المبلغ", min_value=0.0, step=50.0)
            pay = st.selectbox("دفع", pay_l)
            dsc = st.text_input("ملاحظة")
        
        upl = st.file_uploader("صورة الفاتورة (للعرض فقط)", type=["png", "jpg", "jpeg", "pdf"])

        if st.form_submit_button("💾 حفظ سحابي", use_container_width=True):
            fin_cat = cust_cat.strip() if ("أخرى" in cat_sel and cust_cat) else cat_sel
            
            row_dict = {
                "التاريخ": pd.to_datetime(dv), "السنة": int(ty), "الشهر": int(tm), 
                "النوع": t_type, "البند": fin_cat, "طريقة الدفع": pay, 
                "المبلغ": float(amt), "ملاحظات": dsc
            }
            
            with st.spinner("⏳ جاري الإرسال لقاعدة البيانات..."):
                success, msg = sync_to_google_direct(row_dict)
                
            if success:
                st.success(f"✅ تم الحفظ بنجاح في جوجل شيت! ({fin_cat})")
                time.sleep(1)
                st.cache_data.clear() 
                st.rerun()
            else:
                st.error(f"❌ حدث خطأ: {msg}")

with tab3:
    if not df.empty:
        st.dataframe(df.sort_values(by="التاريخ", ascending=False), use_container_width=True)
    else: st.info("لا توجد بيانات متاحة حالياً.")

st.markdown("---")
st.caption("Masrofy App v4.0 (Cloud Edition) | Developed by Ezzat Emam")
