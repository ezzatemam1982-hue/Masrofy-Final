import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import time
import base64
import requests

# ---------------------------------------------------------
# 1. إعدادات الصفحة
# ---------------------------------------------------------
ICON_FILE = "diamond_icon.png"
page_icon_obj = ICON_FILE if os.path.exists(ICON_FILE) else "💎"

st.set_page_config(page_title="مصروفي | Masrofy Cloud", page_icon=page_icon_obj, layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------
# 2. الرابط السحري (Google Apps Script URL)
# ---------------------------------------------------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwbXgGRGb6LyZ2_34JApbNXWqvVmQNKRmxaxTWI-GMPw4Wt_UIaegOH994J8owpI1tg/exec"

# ---------------------------------------------------------
# 3. CSS (التصميم)
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 4. دوال الاتصال (المخ)
# ---------------------------------------------------------
@st.cache_data(ttl=5) 
def load_data():
    try:
        response = requests.get(APPS_SCRIPT_URL)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                df["التاريخ"] = pd.to_datetime(df["التاريخ"])
                df["المبلغ"] = pd.to_numeric(df["المبلغ"])
                for col in ["النوع", "البند", "طريقة الدفع", "ملاحظات"]:
                    if col not in df.columns: df[col] = ""
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
# 5. القوائم والبيانات
# ---------------------------------------------------------
df = load_data()

INCOME_CATEGORIES = ["💰 راتب (نص الشهر)", "💰 راتب (اخر الشهر)", "🏠 إيراد إيجار شقة", "🏆 مكافأة أرباح سنوية", "🎁 مكافأة أخرى / إضافية", "💊 استرداد علاج", "💼 استرداد مأموريات عمل", "➕ أخرى"]
EXPENSE_CATEGORIES = ["🏠 إيجار شقة (سكن)", "🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم", "⚡ فواتير (كهرباء/غاز/مياه)", "🌐 إنترنت وموبايل", "🚗 بنزين ومواصلات", "🔧 صيانة سيارة", "💊 علاج ودواء", "👕 ملابس", "🎓 مصاريف تعليم ودروس", "🧸 مستلزمات الأبناء", "🎉 ترفيه وخروجات", "➕ أخرى"]
INSTALLMENT_TYPES = ["🏢 قسط الشقة الربع سنوي", "📦 أقساط مشتريات (أونلاين/أجهزة)", "🏊 قسط النادي", "➕ أخرى"]
PAYMENT_METHODS = ["💵 كاش", "💳 فيزا", "📱 محفظة", "🏦 بنك"]

# ---------------------------------------------------------
# 6. الواجهة الرسومية
# ---------------------------------------------------------
st.markdown(f"""<h1 style="text-align: center; color: #2ecc71;">مصروفي | Masrofy Cloud ☁️</h1>""", unsafe_allow_html=True)
if st.button("🔄 تحديث البيانات"): st.cache_data.clear(); st.rerun()

# --- إعدادات الفلترة وميزانية الطعام ---
today = datetime.now()
# قائمة السنوات المتاحة (الحالية + القادمة + اللي في الداتا)
years_available = sorted(list(set([today.year, today.year + 1] + (df["السنة"].tolist() if not df.empty else []))))

with st.expander("📅 إعدادات العرض وميزانية الطعام", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1: view_year = st.selectbox("عرض سنة", years_available, index=years_available.index(today.year) if today.year in years_available else 0)
    with c2: view_month = st.selectbox("عرض شهر", range(1, 13), index=today.month - 1)
    with c3: food_budget_limit = st.number_input("🍖 ميزانية الطعام", value=5000, step=100)

# التبويبات
tab1, tab2, tab3, tab4 = st.tabs(["📊 لوحة القيادة", "📝 تسجيل جديد", "✏️ تعديل / حذف", "📂 السجل"])

# =========================================================
# TAB 1: لوحة القيادة
# =========================================================
with tab1:
    if not df.empty:
        mask = (df["الشهر"] == view_month) & (df["السنة"] == view_year)
        m_df = df[mask]
        
        inc = m_df[m_df["النوع"]=="دخل"]["المبلغ"].sum()
        exp_only = m_df[m_df["النوع"].str.contains("مصروف", na=False)]["المبلغ"].sum()
        inst_only = m_df[m_df["النوع"].str.contains("قسط", na=False)]["المبلغ"].sum()
        total_out = exp_only + inst_only
        balance = inc - total_out
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 إجمالي الدخل", f"{inc:,.0f}")
        col2.metric("💸 المصروفات", f"{exp_only:,.0f}")
        col3.metric("📅 الأقساط", f"{inst_only:,.0f}")
        col4.metric("✅ الرصيد المتبقي", f"{balance:,.0f}", delta_color="normal" if balance >= 0 else "inverse")
        
        st.divider()
        
        food_spent = m_df[m_df["البند"].str.contains("طعام|سوبر ماركت|خضار|لحوم|بقال", na=False)]["المبلغ"].sum()
        food_progress = min(food_spent / food_budget_limit, 1.0) if food_budget_limit > 0 else 0
        st.write(f"**🍖 استهلاك الطعام:** {food_spent:,.0f} من {food_budget_limit:,.0f}")
        st.progress(food_progress)
        if food_spent > food_budget_limit: st.error("⚠️ لقد تجاوزت ميزانية الطعام!")
        
        st.divider()

        g1, g2 = st.columns(2)
        with g1:
            out_data = m_df[m_df["النوع"].str.contains("مصروف|قسط", na=False)]
            if not out_data.empty:
                st.subheader("توزيع المصاريف والأقساط")
                fig_pie = px.pie(out_data, values='المبلغ', names='البند', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            
        with g2:
            inc_data = m_df[m_df["النوع"] == "دخل"]
            if not inc_data.empty:
                st.subheader("مصادر الدخل")
                fig_bar = px.bar(inc_data, x="البند", y="المبلغ", color="البند")
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("لا توجد بيانات. ابدأ بإضافة عمليات.")

# =========================================================
# TAB 2: تسجيل جديد (مع تحديد شهر الميزانية)
# =========================================================
with tab2:
    st.subheader("إضافة عملية جديدة")
    
    # Session State للتهيئة
    if 'add_amount' not in st.session_state: st.session_state.add_amount = 0.0
    if 'add_note' not in st.session_state: st.session_state.add_note = ""
    if 'add_date' not in st.session_state: st.session_state.add_date = datetime.now()

    t_type = st.radio("النوع", ["مصروفات", "دخل", "قسط"], horizontal=True, key="radio_entry_type")
    
    if t_type == "دخل": current_cats = INCOME_CATEGORIES
    elif t_type == "قسط": current_cats = INSTALLMENT_TYPES
    else: current_cats = EXPENSE_CATEGORIES
    
    cat = st.selectbox("البند / التصنيف", current_cats)
    if "أخرى" in cat: cat = st.text_input("اكتب اسم البند هنا:")

    with st.form("entry_form"):
        # صف التاريخ والميزانية
        c_date, c_month, c_year = st.columns(3)
        date_val = c_date.date_input("تاريخ العملية", key="add_date")
        
        # ✅ هنا الجديد: تحديد شهر وسنة الميزانية يدوياً
        # بنخلي الافتراضي هو شهر وتاريخ العملية اللي اخترناها (أو اليوم)
        selected_month = c_month.selectbox("شهر الميزانية", range(1, 13), index=date_val.month - 1)
        selected_year = c_year.selectbox("سنة الميزانية", years_available, index=years_available.index(date_val.year) if date_val.year in years_available else 0)

        col_amt, col_pay = st.columns(2)
        amount_val = col_amt.number_input("المبلغ", min_value=0.0, step=10.0, key="add_amount")
        method_val = col_pay.selectbox("طريقة الدفع", PAYMENT_METHODS)
        
        note_val = st.text_input("ملاحظات / تفاصيل", key="add_note")
        
        submitted = st.form_submit_button("💾 حفظ وترحيل سحابي", use_container_width=True)

        if submitted:
            if amount_val > 0:
                backend_type = "income" if t_type == "دخل" else "expense"
                payload = {
                    "action": "add",
                    "transType": backend_type, 
                    "date": str(date_val),
                    "customMonth": selected_month, # ✅ إرسال الشهر المختار
                    "customYear": selected_year,   # ✅ إرسال السنة المختارة
                    "amount": amount_val,
                    "category": cat,
                    "subCategory": note_val,
                    "method": method_val,
                    "realType": t_type 
                }
                
                with st.spinner("جاري الحفظ..."):
                    ok, msg = send_to_google(payload)
                    if ok:
                        st.success(f"تم الحفظ في ميزانية شهر {selected_month}/{selected_year}!")
                        st.session_state.add_amount = 0.0
                        st.session_state.add_note = ""
                        st.session_state.add_date = datetime.now()
                        time.sleep(1)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("خطأ: " + msg)
            else:
                st.warning("يرجى إدخال مبلغ أكبر من صفر.")

# =========================================================
# TAB 3: تعديل / حذف (مع إمكانية تعديل شهر الميزانية)
# =========================================================
with tab3:
    st.subheader("إدارة العمليات")
    if not df.empty:
        filter_type = st.radio("فلتر بـ:", ["الكل", "مصروفات", "دخل", "قسط"], horizontal=True, key="filter_radio")
        
        if filter_type == "الكل": display_df = df
        elif filter_type == "قسط": display_df = df[df["النوع"].str.contains("قسط", na=False)]
        elif filter_type == "دخل": display_df = df[df["النوع"] == "دخل"]
        else: display_df = df[df["النوع"].str.contains("مصروف", na=False)]
        
        if not display_df.empty:
            display_df['label'] = display_df.apply(lambda x: f"{x['التاريخ'].date()} | {x['النوع']} | {x['البند']} | {x['المبلغ']} (شهر {x['الشهر']})", axis=1)
            selected_label = st.selectbox("اختر العملية:", display_df['label'].tolist())
            
            if selected_label:
                row = display_df[display_df['label'] == selected_label].iloc[0]
                
                with st.expander("✏️ تعديل البيانات", expanded=True):
                    # تعديل المبلغ والبند
                    c_edit1, c_edit2 = st.columns(2)
                    new_amount = c_edit1.number_input("تعديل المبلغ", value=float(row['المبلغ']))
                    
                    if "قسط" in row['النوع']: edit_cats = INSTALLMENT_TYPES
                    elif "دخل" in row['النوع']: edit_cats = INCOME_CATEGORIES
                    else: edit_cats = EXPENSE_CATEGORIES
                    try: c_ix = edit_cats.index(row['البند'])
                    except: c_ix = 0
                    new_cat = c_edit2.selectbox("تعديل البند", edit_cats, index=c_ix)

                    # ✅ تعديل شهر وسنة الميزانية
                    c_edit3, c_edit4 = st.columns(2)
                    new_month = c_edit3.selectbox("تعديل شهر الميزانية", range(1, 13), index=int(row['الشهر'])-1)
                    
                    curr_y = int(row['السنة'])
                    y_idx = years_available.index(curr_y) if curr_y in years_available else 0
                    new_year = c_edit4.selectbox("تعديل سنة الميزانية", years_available, index=y_idx)

                    new_note = st.text_input("تعديل الملاحظات", value=row['ملاحظات'])
                    
                    c_btn1, c_btn2 = st.columns(2)
                    
                    if c_btn1.button("تحديث"):
                        payload = {
                            "action": "edit",
                            "id": row['id'],
                            "transType": row['النوع'],
                            "date": str(row['التاريخ'].date()),
                            "customMonth": new_month, # ✅ إرسال التعديل
                            "customYear": new_year,   # ✅ إرسال التعديل
                            "amount": new_amount,
                            "category": new_cat,
                            "subCategory": new_note,
                            "method": row['طريقة الدفع']
                        }
                        with st.spinner("جاري التعديل..."):
                            ok, msg = send_to_google(payload)
                            if ok: st.success("تم التحديث!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                            else: st.error("فشل التعديل")

                    if c_btn2.button("🗑️ حذف", type="primary"):
                        payload = {"action": "delete", "id": row['id']}
                        with st.spinner("جاري الحذف..."):
                            ok, msg = send_to_google(payload)
                            if ok: st.success("تم الحذف!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                            else: st.error("فشل الحذف")
        else: st.info("لا توجد عمليات بهذا النوع.")
    else: st.info("لا توجد بيانات.")

# =========================================================
# TAB 4: السجل
# =========================================================
with tab4:
    if not df.empty:
        st.dataframe(df.drop(columns=['id', 'label'], errors='ignore').sort_values(by="التاريخ", ascending=False), use_container_width=True)
    else:
        st.info("السجل فارغ.")

st.markdown("---")
st.caption("Masrofy v1.1 | Budget Control Edition 🚀")
