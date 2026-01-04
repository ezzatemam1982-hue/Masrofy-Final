import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
import base64

# --- 1. إعداد الصفحة ---
ICON_FILE = "diamond_icon.png"
page_icon_obj = ICON_FILE if os.path.exists(ICON_FILE) else "💎"

st.set_page_config(
    page_title="مصروفي | Masrofy",
    page_icon=page_icon_obj,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. إعداد المتغيرات ---
LOCAL_DATA_FILE = "finance_data_v28.csv"
ATTACHMENTS_DIR = "attachments"
SHEET_NAME = "Masrofy_DB"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "credentials.json"

if not os.path.exists(ATTACHMENTS_DIR): os.makedirs(ATTACHMENTS_DIR)

if 'current_mode' not in st.session_state: st.session_state['current_mode'] = "مصروفات"
def update_mode(): st.session_state['current_mode'] = st.session_state.mode_selector

# --- 3. CSS (تحسين المظهر) ---
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
    
    .stDownloadButton button {
        width: 100%;
        background-color: #f1c40f !important;
        color: black !important;
        border: none;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. دوال المساعدة ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def load_data_local():
    if os.path.exists(LOCAL_DATA_FILE):
        try:
            df = pd.read_csv(LOCAL_DATA_FILE)
            if "التاريخ" in df.columns:
                df["التاريخ"] = pd.to_datetime(df["التاريخ"], errors='coerce')
                df["المبلغ"] = pd.to_numeric(df["المبلغ"], errors='coerce').fillna(0.0)
                for col in ["النوع", "البند", "طريقة الدفع", "ملاحظات", "المرفق"]:
                    if col in df.columns:
                        df[col] = df[col].astype(str).replace('nan', '')
                return df
        except: pass
    return pd.DataFrame(columns=["التاريخ", "السنة", "الشهر", "النوع", "البند", "طريقة الدفع", "المبلغ", "ملاحظات", "المرفق"])

def save_data_local(df):
    df.to_csv(LOCAL_DATA_FILE, index=False)

def sync_to_google_forced_task(row_dict):
    if os.path.exists(CREDS_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope=SCOPE)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            values = [
                str(row_dict.get("التاريخ").date()), str(row_dict.get("السنة")), str(row_dict.get("الشهر")), 
                str(row_dict.get("النوع")), str(row_dict.get("البند")), str(row_dict.get("طريقة الدفع")), 
                str(row_dict.get("المبلغ")), str(row_dict.get("ملاحظات", "")), "تطبيق"
            ]
            sheet.append_row(values)
        except Exception as e:
            print(f"Sync Error: {e}")

# --- 5. شاشة التحميل ---
if 'first_load' not in st.session_state: st.session_state['first_load'] = True
if st.session_state['first_load']:
    splash = st.empty()
    img_base64 = get_base64_image(ICON_FILE)
    logo_html = f'<img src="data:image/png;base64,{img_base64}" width="150" style="margin-bottom: 20px;">' if img_base64 else '<div style="font-size: 100px; margin-bottom: 20px;">💎</div>'
    with splash.container():
        st.markdown(f"""<div style="position:fixed;top:0;left:0;width:100vw;height:100vh;background:#fff;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;">
        {logo_html}<h1 style="color:#2ecc71;">مصروفي</h1></div>""", unsafe_allow_html=True)
        time.sleep(1.0)
        splash.empty()
        st.session_state['first_load'] = False

# --- 6. القوائم والبيانات ---
INCOME_CATEGORIES = ["💰 راتب (نص الشهر)", "💰 راتب (اخر الشهر)", "🏠 إيراد إيجار شقة", "🏆 مكافأة أرباح سنوية", "🎁 مكافأة أخرى / إضافية", "💊 استرداد علاج", "💼 استرداد مأموريات عمل", "➕ أخرى"]
EXPENSE_CATEGORIES = ["🏠 إيجار شقة (سكن)", "🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم", "⚡ فواتير (كهرباء/غاز/مياه)", "🌐 إنترنت وموبايل", "🚗 بنزين ومواصلات", "🔧 صيانة سيارة", "💊 علاج ودواء", "👕 ملابس", "🎓 مصاريف تعليم ودروس", "🧸 مستلزمات الأبناء", "🎉 ترفيه وخروجات", "➕ أخرى"]
INSTALLMENT_TYPES = ["🏢 قسط الشقة الربع سنوي", "📦 أقساط مشتريات (أونلاين/أجهزة)", "🏊 قسط النادي", "➕ أخرى"]
PAYMENT_INCOME = ["💵 كاش", "🏦 تحويل بنكي / راتب", "📱 محفظة إلكترونية"]
PAYMENT_SPENDING = ["💵 كاش", "💳 Credit Card End 8298", "💳 Credit Card End 6016", "📱 محفظة البنك الأهلي", "📱 محفظة CIB", "📱 فودافون كاش"]

df = load_data_local()

# --- 7. الواجهة الرئيسية ---
img_base64_small = get_base64_image(ICON_FILE)
header_logo = f'<img src="data:image/png;base64,{img_base64_small}" width="90" style="vertical-align: middle;">' if img_base64_small else '<span style="font-size: 60px;">💎</span>'

st.markdown(f"""
<div style="display: flex; align-items: center; justify-content: center; direction: rtl; margin-bottom: 20px;">
    <div style="margin-left: 15px;">{header_logo}</div>
    <h1 style="color: #2ecc71; margin: 0; font-size: 2.5rem;">مصروفي | Masrofy</h1>
</div>
""", unsafe_allow_html=True)

# --- القائمة الجانبية (خاصة بالداتا فقط) ---
if os.path.exists(ICON_FILE): st.sidebar.image(ICON_FILE, width=100)
else: st.sidebar.title("💎")

with st.sidebar.expander("⚙️ إدارة قاعدة البيانات (CSV)", expanded=True):
    # زر الحفظ
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(label="💾 حفظ نسخة احتياطية", data=csv_data, file_name=f"Masrofy_Backup_{datetime.now().strftime('%Y-%m-%d')}.csv", mime="text/csv")
    
    st.markdown("---")
    
    # زر الاسترجاع (للملفات النصية فقط)
    # ملاحظة: شلت الـ type restriction عشان يظهرلك كل الملفات وتختار الـ CSV براحتك لو كان باهت
    uploaded_file = st.file_uploader("📂 استرجاع ملف بيانات") 
    if uploaded_file is not None:
        if st.button("⚠️ تأكيد الاستبدال"):
            try:
                # محاولة قراءة الملف كـ CSV
                uploaded_df = pd.read_csv(uploaded_file)
                required = ["التاريخ", "النوع", "المبلغ"]
                if any(col in uploaded_df.columns for col in required):
                    uploaded_df.to_csv(LOCAL_DATA_FILE, index=False)
                    st.success("✅ تم استرجاع قاعدة البيانات!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ هذا ليس ملف بيانات صحيح (يجب أن يكون CSV).")
            except Exception as e:
                st.error("❌ خطأ: تأكد أنك تختار ملف CSV وليس صورة.")

# --- الفلاتر ---
today = datetime.now()
years_list = list(range(today.year - 1, today.year + 4))
default_year_ix = years_list.index(today.year) if today.year in years_list else 1

with st.expander("📅 إعدادات الفلترة", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1: view_year = st.selectbox("السنة", years_list, index=default_year_ix)
    with c2: view_month = st.selectbox("الشهر", range(1, 13), index=today.month - 1)
    with c3: food_budget_limit = st.number_input("ميزانية الطعام", value=5000, step=100)

# --- التبويبات ---
tab1, tab2, tab3 = st.tabs(["📊 لوحة القيادة", "📝 تسجيل جديد", "📂 السجل"])

# === التبويب 1: لوحة القيادة (تمت إعادة رسمة الدخل) ===
with tab1:
    if not df.empty and "التاريخ" in df.columns:
        mask = (df["الشهر"] == int(view_month)) & (df["السنة"] == int(view_year))
        month_df = df[mask]
        
        total_income = month_df[month_df["النوع"] == "دخل"]["المبلغ"].sum()
        total_expense = month_df[month_df["النوع"].str.contains("مصروف", na=False)]["المبلغ"].sum()
        total_installments = month_df[month_df["النوع"] == "قسط"]["المبلغ"].sum()
        balance = total_income - (total_expense + total_installments)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 الدخل", f"{total_income:,.0f}")
        c2.metric("💸 المصاريف", f"{total_expense:,.0f}")
        c3.metric("📅 الأقساط", f"{total_installments:,.0f}")
        c4.metric("✅ الرصيد", f"{balance:,.0f}", delta_color="normal" if balance >= 0 else "inverse")
        
        st.divider()
        
        # --- هنا التصحيح: إظهار الرسمتين (المصاريف والدخل) ---
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("توزيع المصاريف")
            outgoing = month_df[month_df["النوع"].str.contains("مصروف|قسط", regex=True, na=False)]
            if not outgoing.empty: 
                fig1 = px.pie(outgoing, values='المبلغ', names='البند', hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
            else: st.info("لا توجد مصاريف.")
            
        with col_chart2:
            st.subheader("مصادر الدخل")
            income_data = month_df[month_df["النوع"] == "دخل"]
            if not income_data.empty: 
                fig2 = px.bar(income_data, x="البند", y="المبلغ", color="البند")
                st.plotly_chart(fig2, use_container_width=True)
            else: st.info("لا يوجد دخل مسجل.")
            
    else: st.info("👋 مرحباً! السجل فارغ.")

# === التبويب 2: تسجيل جديد (المرفقات صور فقط) ===
with tab2:
    st.subheader("➕ إضافة معاملة")
    options = ["مصروفات", "دخل", "قسط"]
    if st.session_state['current_mode'] not in options: st.session_state['current_mode'] = "مصروفات"

    t_type = st.radio("نوع المعاملة:", options, horizontal=True, index=options.index(st.session_state['current_mode']), key="mode_selector", on_change=update_mode)
    
    if t_type == "دخل": cat_l, pay_l = INCOME_CATEGORIES, PAYMENT_INCOME
    elif t_type == "قسط": cat_l, pay_l = INSTALLMENT_TYPES, PAYMENT_SPENDING
    else: cat_l, pay_l = EXPENSE_CATEGORIES, PAYMENT_SPENDING
    
    c_s1, c_s2 = st.columns([1,1])
    with c_s1: cat_sel = st.selectbox("التصنيف:", cat_l)
    cust_cat = ""
    if "أخرى" in cat_sel: 
        with c_s2: cust_cat = st.text_input("اسم المصروف:")
    
    with st.form("entry", clear_on_submit=True):
        st.markdown("---")
        c_d, c_det = st.columns(2)
        with c_d:
            tm = st.selectbox("شهر", range(1, 13), index=today.month - 1)
            ty = st.selectbox("سنة", years_list, index=default_year_ix)
            dv = st.date_input("يوم", datetime.today())
        with c_det:
            amt = st.number_input("المبلغ", min_value=0.0, step=50.0)
            pay = st.selectbox("دفع", pay_l)
            dsc = st.text_input("ملاحظة")
        
        # --- هنا المنطق الصحيح: المرفقات صور وملفات PDF فقط ---
        with st.expander("📎 إرفاق صورة الفاتورة (اختياري)"):
            upl = st.file_uploader("التقاط صورة أو اختيار ملف", type=["png", "jpg", "jpeg", "pdf"])

        if st.form_submit_button("💾 حفظ البيانات", use_container_width=True):
            fin_cat = cust_cat.strip() if ("أخرى" in cat_sel and cust_cat) else cat_sel
            fp = ""
            if upl:
                fp = os.path.join(ATTACHMENTS_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{upl.name}")
                with open(fp, "wb") as f: f.write(upl.getbuffer())

            row_dict = {
                "التاريخ": pd.to_datetime(dv), "السنة": int(ty), "الشهر": int(tm), 
                "النوع": t_type, "البند": fin_cat, "طريقة الدفع": pay, 
                "المبلغ": float(amt), "ملاحظات": dsc, "المرفق": fp
            }
            
            df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
            save_data_local(df)
            bg_thread = threading.Thread(target=sync_to_google_forced_task, args=(row_dict,))
            bg_thread.start()
            
            st.toast(f"✅ تم الحفظ: {fin_cat}", icon="🚀")
            time.sleep(0.5); st.rerun()

# === التبويب 3 ===
with tab3:
    if not df.empty and "التاريخ" in df.columns:
        st.dataframe(df.sort_values(by="التاريخ", ascending=False), use_container_width=True, column_config={"المرفق": st.column_config.TextColumn("المرفق")})
        st.divider()
        with st.expander("🗑️ حذف عملية"):
            df_disp = df.copy().sort_values(by="التاريخ", ascending=False)
            del_opts = df_disp.apply(lambda x: f"م{x.name}: {x['التاريخ'].date()} | {x['البند']} | {x['المبلغ']}ج", axis=1)
            sel_del = st.selectbox("اختر للحذف:", del_opts, index=None)
            if sel_del and st.button("🗑️ حذف السطر", type="primary"):
                idx = int(sel_del.split(":")[0].replace("م", ""))
                df = df.drop(idx)
                save_data_local(df)
                st.toast("تم الحذف!", icon="🗑️")
                time.sleep(0.5); st.rerun()
    else: st.info("السجل فارغ.")

st.markdown("---")
st.caption("Masrofy App v1.0 | Developed by Ezzat Emam")
