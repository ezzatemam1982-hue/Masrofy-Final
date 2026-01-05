import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import time
import base64
import requests

# ---------------------------------------------------------
# إعدادات الصفحة
# ---------------------------------------------------------
ICON_FILE = "diamond_icon.png"
page_icon_obj = ICON_FILE if os.path.exists(ICON_FILE) else "💎"

st.set_page_config(page_title="مصروفي | Masrofy", page_icon=page_icon_obj, layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------
# الرابط (تأكد من تحديث Apps Script وعمل New Version)
# ---------------------------------------------------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwbXgGRGb6LyZ2_34JApbNXWqvVmQNKRmxaxTWI-GMPw4Wt_UIaegOH994J8owpI1tg/exec"

# ---------------------------------------------------------
# دوال الاتصال (Brain)
# ---------------------------------------------------------
@st.cache_data(ttl=5) # تقليل وقت الكاش عشان التعديل يظهر بسرعة
def load_data():
    try:
        response = requests.get(APPS_SCRIPT_URL)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                df["التاريخ"] = pd.to_datetime(df["التاريخ"])
                df["المبلغ"] = pd.to_numeric(df["المبلغ"])
                return df
    except: pass
    return pd.DataFrame(columns=["id", "التاريخ", "السنة", "الشهر", "النوع", "البند", "طريقة الدفع", "المبلغ", "ملاحظات"])

def send_to_google(payload):
    try:
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

# ---------------------------------------------------------
# الواجهة
# ---------------------------------------------------------
# CSS
st.markdown("""
<style>
    .main {direction: rtl;}
    h1, h2, h3, h4, p, div, label, .stSelectbox, .stNumberInput, .stDateInput, .stTextInput, .stRadio, .stMarkdown, .stTabs, .stDataFrame {
        text-align: right !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 10px; color: #000; font-weight: bold; flex: 1; }
    .stTabs [aria-selected="true"] { background-color: #2ecc71 !important; color: white !important; }
    div[data-testid="stMetric"] { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; border: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# التحميل
if 'refresh_trigger' not in st.session_state: st.session_state.refresh_trigger = 0
df = load_data()

# القوائم
INCOME_CATEGORIES = ["💰 راتب (نص الشهر)", "💰 راتب (اخر الشهر)", "🏠 إيراد إيجار شقة", "🏆 مكافأة أرباح سنوية", "🎁 مكافأة أخرى / إضافية", "💊 استرداد علاج", "💼 استرداد مأموريات عمل", "➕ أخرى"]
EXPENSE_CATEGORIES = ["🏠 إيجار شقة (سكن)", "🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم", "⚡ فواتير (كهرباء/غاز/مياه)", "🌐 إنترنت وموبايل", "🚗 بنزين ومواصلات", "🔧 صيانة سيارة", "💊 علاج ودواء", "👕 ملابس", "🎓 مصاريف تعليم ودروس", "🧸 مستلزمات الأبناء", "🎉 ترفيه وخروجات", "➕ أخرى"]
PAYMENT_METHODS = ["💵 كاش", "💳 فيزا", "📱 محفظة", "🏦 بنك"]

# الهيدر
st.markdown(f"""<h1 style="text-align: center; color: #2ecc71;">مصروفي | Masrofy Cloud ☁️</h1>""", unsafe_allow_html=True)
if st.button("🔄 تحديث البيانات"): st.cache_data.clear(); st.rerun()

# التبويبات
tab1, tab2, tab3, tab4 = st.tabs(["📊 لوحة القيادة", "📝 تسجيل جديد", "✏️ تعديل / حذف", "📂 السجل"])

# --- 1. لوحة القيادة ---
with tab1:
    if not df.empty:
        today = datetime.now()
        c1, c2 = st.columns(2)
        with c1: view_year = st.selectbox("السنة", sorted(df["السنة"].unique()), index=len(df["السنة"].unique())-1)
        with c2: view_month = st.selectbox("الشهر", range(1, 13), index=today.month - 1)
        
        mask = (df["الشهر"] == view_month) & (df["السنة"] == view_year)
        m_df = df[mask]
        
        inc = m_df[m_df["النوع"]=="دخل"]["المبلغ"].sum()
        exp = m_df[m_df["النوع"]=="مصروفات"]["المبلغ"].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("الدخل", f"{inc:,.0f}")
        col2.metric("المصروفات", f"{exp:,.0f}")
        col3.metric("المتبقي", f"{inc-exp:,.0f}")
        
        if not m_df.empty:
            exp_data = m_df[m_df["النوع"]=="مصروفات"]
            if not exp_data.empty:
                st.plotly_chart(px.pie(exp_data, values='المبلغ', names='البند', hole=0.4), use_container_width=True)
    else:
        st.info("لا توجد بيانات. ابدأ بإضافة عمليات.")

# --- 2. تسجيل جديد ---
with tab2:
    st.subheader("إضافة عملية جديدة")
    c1, c2 = st.columns(2)
    with c1: t_type = st.radio("النوع", ["مصروفات", "دخل"], horizontal=True)
    with c2: 
        cats = INCOME_CATEGORIES if t_type == "دخل" else EXPENSE_CATEGORIES
        cat = st.selectbox("البند", cats)
    
    col_a, col_b = st.columns(2)
    with col_a: date_val = st.date_input("التاريخ", datetime.now())
    with col_b: amount_val = st.number_input("المبلغ", min_value=1.0, step=10.0)
    
    col_c, col_d = st.columns(2)
    with col_c: method_val = st.selectbox("طريقة الدفع", PAYMENT_METHODS)
    with col_d: note_val = st.text_input("ملاحظات / تفاصيل")
    
    if st.button("💾 حفظ العملية", use_container_width=True):
        payload = {
            "action": "add",
            "transType": "income" if t_type == "دخل" else "expense",
            "date": str(date_val),
            "amount": amount_val,
            "category": cat,
            "subCategory": note_val,
            "method": method_val
        }
        with st.spinner("جاري الحفظ في جوجل شيت..."):
            ok, msg = send_to_google(payload)
            if ok:
                st.success("تم الحفظ!"); time.sleep(1); st.cache_data.clear(); st.rerun()
            else:
                st.error("خطأ: " + msg)

# --- 3. تعديل / حذف (الجديد) ---
with tab3:
    st.subheader("إدارة العمليات (تعديل أو حذف)")
    if not df.empty:
        # اختيار العملية
        # بنعمل قايمة شكلها حلو عشان تختار منها
        df['label'] = df.apply(lambda x: f"{x['التاريخ'].date()} | {x['النوع']} | {x['البند']} | {x['المبلغ']}", axis=1)
        selected_label = st.selectbox("اختر العملية للتعديل أو الحذف:", df['label'].tolist())
        
        # استخراج بيانات العملية المختارة
        if selected_label:
            row = df[df['label'] == selected_label].iloc[0]
            st.info(f"العملية المحددة: {selected_label}")
            
            # فورم التعديل
            with st.expander("✏️ تعديل البيانات", expanded=True):
                new_amount = st.number_input("تعديل المبلغ", value=float(row['المبلغ']))
                cats_edit = INCOME_CATEGORIES if row['النوع'] == "دخل" else EXPENSE_CATEGORIES
                
                # محاولة تحديد الفهرس الصحيح، لو مش موجود نختار الأول
                try: cat_index = cats_edit.index(row['البند'])
                except: cat_index = 0
                    
                new_cat = st.selectbox("تعديل البند", cats_edit, index=cat_index)
                new_note = st.text_input("تعديل الملاحظات", value=row['ملاحظات'])
                
                c_edit, c_del = st.columns(2)
                
                # زر التعديل
                if c_edit.button("تحديث البيانات"):
                    payload = {
                        "action": "edit",
                        "id": row['id'], # ده الرقم السري بتاع الصف
                        "transType": "income" if row['النوع'] == "دخل" else "expense", # للحفاظ على التوافق
                        "date": str(row['التاريخ'].date()), # التاريخ يظل كما هو
                        "amount": new_amount,
                        "category": new_cat,
                        "subCategory": new_note,
                        "method": row['طريقة الدفع']
                    }
                    with st.spinner("جاري التعديل..."):
                        ok, msg = send_to_google(payload)
                        if ok: st.success("تم التعديل!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                        else: st.error("فشل التعديل")

                # زر الحذف
                if c_del.button("🗑️ حذف نهائي", type="primary"):
                    payload = {
                        "action": "delete",
                        "id": row['id']
                    }
                    with st.spinner("جاري الحذف..."):
                        ok, msg = send_to_google(payload)
                        if ok: st.success("تم الحذف!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                        else: st.error("فشل الحذف")
    else:
        st.warning("لا توجد عمليات لتعديلها.")

# --- 4. السجل ---
with tab4:
    if not df.empty:
        st.dataframe(df.drop(columns=['id', 'label'], errors='ignore').sort_values(by="التاريخ", ascending=False), use_container_width=True)
    else:
        st.info("السجل فارغ.")

st.markdown("---")
st.caption("Masrofy v5.0 | Full Cloud Control")
