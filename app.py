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

st.set_page_config(page_title="مصروفي | Masrofy Business", page_icon=page_icon_obj, layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------
# 2. الرابط السحري
# ---------------------------------------------------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwbXgGRGb6LyZ2_34JApbNXWqvVmQNKRmxaxTWI-GMPw4Wt_UIaegOH994J8owpI1tg/exec"

# ---------------------------------------------------------
# 3. CSS
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
# 4. دوال الاتصال
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
# 5. القوائم
# ---------------------------------------------------------
df = load_data()

INCOME_CATEGORIES = ["💰 راتب (نص الشهر)", "💰 راتب (اخر الشهر)", "🏠 إيراد إيجار شقة", "🏆 مكافأة أرباح سنوية", "🎁 مكافأة أخرى / إضافية", "💊 استرداد علاج", "💼 استرداد مأموريات عمل", "➕ أخرى"]
EXPENSE_CATEGORIES = ["🏠 إيجار شقة (سكن)", "🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم", "⚡ فواتير (كهرباء/غاز/مياه)", "🌐 إنترنت وموبايل", "🚗 بنزين ومواصلات", "🔧 صيانة سيارة", "💊 علاج ودواء", "👕 ملابس", "🎓 مصاريف تعليم ودروس", "🧸 مستلزمات الأبناء", "🎉 ترفيه وخروجات", "➕ أخرى"]
INSTALLMENT_TYPES = ["🏢 قسط الشقة الربع سنوي", "📦 أقساط مشتريات (أونلاين/أجهزة)", "🏊 قسط النادي", "➕ أخرى"]
PAYMENT_METHODS = ["💵 كاش", "💳 فيزا", "📱 محفظة", "🏦 بنك"]

# ---------------------------------------------------------
# 6. الواجهة
# ---------------------------------------------------------
st.markdown(f"""<h1 style="text-align: center; color: #2ecc71;">مصروفي | Masrofy Business 💼</h1>""", unsafe_allow_html=True)
if st.button("🔄 تحديث البيانات"): st.cache_data.clear(); st.rerun()

# --- إعدادات ---
today = datetime.now()
years_available = sorted(list(set([today.year, today.year + 1] + (df["السنة"].tolist() if not df.empty else []))))

with st.expander("📅 إعدادات العرض وميزانية الطعام", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1: view_year = st.selectbox("عرض سنة", years_available, index=years_available.index(today.year) if today.year in years_available else 0)
    with c2: view_month = st.selectbox("عرض شهر", range(1, 13), index=today.month - 1)
    with c3: food_budget_limit = st.number_input("🍖 ميزانية الطعام", value=5000, step=100)

tab1, tab2, tab3, tab4 = st.tabs(["📊 لوحة القيادة", "📝 تسجيل جديد", "✏️ إدارة / تحصيل", "📂 السجل"])

# =========================================================
# TAB 1: لوحة القيادة
# =========================================================
with tab1:
    if not df.empty:
        mask = (df["الشهر"] == view_month) & (df["السنة"] == view_year)
        m_df = df[mask]
        
        inc = m_df[m_df["النوع"]=="دخل"]["المبلغ"].sum()
        pending_total = df[df["النوع"]=="دخل منتظر"]["المبلغ"].sum()
        
        exp_only = m_df[m_df["النوع"].str.contains("مصروف", na=False)]["المبلغ"].sum()
        inst_only = m_df[m_df["النوع"].str.contains("قسط", na=False)]["المبلغ"].sum()
        balance = inc - (exp_only + inst_only)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 الدخل المحصل", f"{inc:,.0f}")
        c2.metric("💸 المصروفات", f"{exp_only:,.0f}")
        c3.metric("📅 الأقساط", f"{inst_only:,.0f}")
        c4.metric("⏳ دخل منتظر (كلي)", f"{pending_total:,.0f}", delta="فلوس ليك بره")
        
        st.metric("✅ الرصيد الحالي (المتاح)", f"{balance:,.0f}", delta_color="normal" if balance >= 0 else "inverse")
        
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            out_data = m_df[m_df["النوع"].str.contains("مصروف|قسط", na=False)]
            if not out_data.empty:
                st.subheader("توزيع المصاريف")
                st.plotly_chart(px.pie(out_data, values='المبلغ', names='البند', hole=0.4), use_container_width=True)
        with g2:
            inc_data = m_df[m_df["النوع"] == "دخل"]
            if not inc_data.empty:
                st.subheader("مصادر الدخل")
                st.plotly_chart(px.bar(inc_data, x="البند", y="المبلغ", color="البند"), use_container_width=True)
    else:
        st.info("لا توجد بيانات.")

# =========================================================
# TAB 2: تسجيل جديد (تم الإصلاح هنا) 🛠️
# =========================================================
with tab2:
    st.subheader("إضافة عملية جديدة")
    
    # 1. التحقق من نجاح العملية السابقة وتصفير الحقول (قبل رسم الخانات)
    if st.session_state.get('form_success_flag', False):
        st.session_state.add_amount = 0.0
        st.session_state.add_note = ""
        st.session_state.add_date = datetime.now()
        st.session_state.form_success_flag = False  # إطفاء العلامة
        # تم التصفير بنجاح لأننا لسه مسمناش الخانات تحت

    # تهيئة المتغيرات لأول مرة
    if 'add_amount' not in st.session_state: st.session_state.add_amount = 0.0
    if 'add_note' not in st.session_state: st.session_state.add_note = ""
    if 'add_date' not in st.session_state: st.session_state.add_date = datetime.now()

    t_type = st.radio("النوع", ["مصروفات", "دخل", "قسط", "دخل منتظر ⏳"], horizontal=True, key="radio_entry_type")
    
    if "دخل" in t_type: current_cats = INCOME_CATEGORIES
    elif t_type == "قسط": current_cats = INSTALLMENT_TYPES
    else: current_cats = EXPENSE_CATEGORIES
    
    cat = st.selectbox("البند / التصنيف", current_cats)
    if "أخرى" in cat: cat = st.text_input("اكتب اسم البند هنا:")

    with st.form("entry_form"):
        c_date, c_month, c_year = st.columns(3)
        date_val = c_date.date_input("تاريخ العملية", key="add_date")
        
        selected_month = c_month.selectbox("شهر الميزانية", range(1, 13), index=date_val.month - 1)
        selected_year = c_year.selectbox("سنة الميزانية", years_available, index=years_available.index(date_val.year) if date_val.year in years_available else 0)

        col_amt, col_pay = st.columns(2)
        amount_val = col_amt.number_input("المبلغ", min_value=0.0, step=10.0, key="add_amount")
        
        if "منتظر" in t_type:
            st.info("سيتم تسجيل الحالة: 'منتظر' تلقائياً")
            method_val = "منتظر"
        else:
            method_val = col_pay.selectbox("طريقة الدفع", PAYMENT_METHODS)
        
        note_val = st.text_input("ملاحظات / تفاصيل", key="add_note")
        
        submitted = st.form_submit_button("💾 حفظ وترحيل", use_container_width=True)

        if submitted:
            if amount_val > 0:
                backend_type = "income" if "دخل" in t_type else "expense"
                final_method = "منتظر" if "منتظر" in t_type else method_val
                
                payload = {
                    "action": "add",
                    "transType": backend_type, 
                    "date": str(date_val),
                    "customMonth": selected_month,
                    "customYear": selected_year,
                    "amount": amount_val,
                    "category": cat,
                    "subCategory": note_val,
                    "method": final_method,
                    "realType": t_type 
                }
                
                with st.spinner("جاري الحفظ..."):
                    ok, msg = send_to_google(payload)
                    if ok:
                        st.success(f"تم الحفظ!")
                        # 🔥 التعديل هنا: بدل ما نصفر مباشرة، نرفع العلم ونعمل ريستارت
                        st.session_state.form_success_flag = True 
                        time.sleep(1)
                        st.cache_data.clear()
                        st.rerun() # هذا سيعيد تشغيل الكود من السطر 1 ويصفر القيم هناك
                    else:
                        st.error("خطأ: " + msg)
            else:
                st.warning("المبلغ يجب أن يكون أكبر من صفر")

# =========================================================
# TAB 3: إدارة / تحصيل
# =========================================================
with tab3:
    st.subheader("💼 إدارة العمليات والتحصيل")
    
    if not df.empty:
        pending_df = df[df["النوع"] == "دخل منتظر"]
        if not pending_df.empty:
            st.warning(f"🔔 لديك {len(pending_df)} عمليات دخل منتظر بإجمالي {pending_df['المبلغ'].sum():,.0f}")
            for index, row in pending_df.iterrows():
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
                    c1.write(f"📅 {row['التاريخ'].date()}")
                    c2.write(f"🏷️ {row['البند']}")
                    c3.write(f"💰 {row['المبلغ']:,.0f}")
                    c4.write(f"📝 {row['ملاحظات']}")
                    if c5.button("✅ استلمت المبلغ", key=f"collect_{row['id']}"):
                        payload = {
                            "action": "edit",
                            "id": row['id'],
                            "transType": "income",
                            "date": str(datetime.now().date()),
                            "customMonth": datetime.now().month,
                            "customYear": datetime.now().year,
                            "amount": row['المبلغ'],
                            "category": row['البند'],
                            "subCategory": row['ملاحظات'] + " (تم التحصيل)",
                            "method": "كاش"
                        }
                        with st.spinner("جاري التحصيل..."):
                            ok, msg = send_to_google(payload)
                            if ok: st.success("تم!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                            else: st.error("حدث خطأ")
                st.divider()
        else:
            st.success("✨ لا يوجد دخل منتظر حالياً.")

        st.markdown("---")
        
        with st.expander("🛠️ تعديل أو حذف عمليات أخرى"):
            filter_type = st.radio("نوع العملية:", ["مصروفات", "دخل", "قسط"], horizontal=True)
            if filter_type == "قسط": display_df = df[df["النوع"].str.contains("قسط", na=False)]
            elif filter_type == "دخل": display_df = df[df["النوع"] == "دخل"]
            else: display_df = df[df["النوع"].str.contains("مصروف", na=False)]
            
            if not display_df.empty:
                display_df['label'] = display_df.apply(lambda x: f"{x['التاريخ'].date()} | {x['البند']} | {x['المبلغ']}", axis=1)
                selected_label = st.selectbox("اختر العملية:", display_df['label'].tolist())
                if selected_label:
                    row = display_df[display_df['label'] == selected_label].iloc[0]
                    new_amount = st.number_input("تعديل المبلغ", value=float(row['المبلغ']))
                    new_note = st.text_input("تعديل الملاحظات", value=row['ملاحظات'])
                    c_btn1, c_btn2 = st.columns(2)
                    if c_btn1.button("تحديث"):
                        payload = {
                            "action": "edit",
                            "id": row['id'],
                            "transType": row['النوع'],
                            "date": str(row['التاريخ'].date()),
                            "customMonth": row['الشهر'], 
                            "customYear": row['السنة'],
                            "amount": new_amount,
                            "category": row['البند'],
                            "subCategory": new_note,
                            "method": row['طريقة الدفع']
                        }
                        send_to_google(payload)
                        st.success("تم!"); st.cache_data.clear(); st.rerun()
                    if c_btn2.button("🗑️ حذف", type="primary"):
                        payload = {"action": "delete", "id": row['id']}
                        send_to_google(payload)
                        st.success("تم الحذف!"); st.cache_data.clear(); st.rerun()

# =========================================================
# TAB 4: السجل
# =========================================================
with tab4:
    if not df.empty:
        st.dataframe(df.drop(columns=['id', 'label'], errors='ignore').sort_values(by="التاريخ", ascending=False), use_container_width=True)
    else:
        st.info("السجل فارغ.")


st.markdown("---")
st.caption("Masrofy v2 | Business Edition by Ezzat Emam 💼")

