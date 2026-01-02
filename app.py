import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
import base64  # 👈 مكتبة جديدة لدمج الصورة في المقدمة

# --- 0. إعداد المتغيرات ---
ICON_FILE = "diamond_icon.png" 
LOCAL_DATA_FILE = "finance_data_v28.csv"
ATTACHMENTS_DIR = "attachments"
SHEET_NAME = "Masrofy_DB"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "credentials.json"

if not os.path.exists(ATTACHMENTS_DIR): os.makedirs(ATTACHMENTS_DIR)

# --- 1. إعداد الصفحة ---
page_icon_obj = ICON_FILE if os.path.exists(ICON_FILE) else "💎"

st.set_page_config(
    page_title="مصروفي | Masrofy",
    page_icon=page_icon_obj,
    layout="wide",
    initial_sidebar_state="collapsed"
)

if 'current_mode' not in st.session_state: st.session_state['current_mode'] = "مصروف"
def update_mode(): st.session_state['current_mode'] = st.session_state.mode_selector

# --- 2. ستايل CSS ---
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
    div[data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #2c3e50; }
    .stMetric { background-color: #fff; padding: 10px; border-radius: 10px; border-right: 5px solid #2ecc71; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    
    /* تنسيق المقدمة المثبتة */
    #splash-screen {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background-color: #ffffff;
        z-index: 9999999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. دوال المساعدة والبيانات ---

# دالة لتحويل الصورة إلى نص (Base64) لدمجها في HTML
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def load_data_local():
    if os.path.exists(LOCAL_DATA_FILE):
        try:
            df = pd.read_csv(LOCAL_DATA_FILE)
            df["التاريخ"] = pd.to_datetime(df["التاريخ"], errors='coerce')
            for col in ["الشهر_المالي", "السنة_المالية"]: 
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            df["المبلغ"] = pd.to_numeric(df["المبلغ"], errors='coerce').fillna(0.0)
            for col in ["النوع", "الفئة", "طريقة الدفع", "المرفق"]:
                 if col in df.columns: df[col] = df[col].astype(str).str.strip()
            return df
        except: pass
    return pd.DataFrame(columns=["التاريخ", "السنة_المالية", "الشهر_المالي", "النوع", "الفئة", "طريقة الدفع", "المبلغ", "الوصف", "المرفق"])

def save_data_local(df):
    df.to_csv(LOCAL_DATA_FILE, index=False)

def sync_to_google_forced_task(row_dict):
    if os.path.exists(CREDS_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            all_values = sheet.get_all_values()
            next_row = len(all_values) + 1
            headers = ["التاريخ", "السنة_المالية", "الشهر_المالي", "النوع", "الفئة", "طريقة الدفع", "المبلغ", "الوصف", "المرفق"]
            if len(all_values) == 0:
                sheet.update(range_name="A1", values=[headers])
                next_row = 2
            values = [str(row_dict.get("التاريخ")), str(row_dict.get("السنة_المالية")), str(row_dict.get("الشهر_المالي")), str(row_dict.get("النوع")), str(row_dict.get("الفئة")), str(row_dict.get("طريقة الدفع")), str(row_dict.get("المبلغ")), str(row_dict.get("الوصف", "")), "ملف محلي"]
            sheet.update(range_name=f"A{next_row}", values=[values])
        except: pass

# --- 4. شاشة الترحيب (الإصلاح الجذري) ---
if 'first_load' not in st.session_state: st.session_state['first_load'] = True
if st.session_state['first_load']:
    splash = st.empty()
    
    # تجهيز كود الصورة (إما صورة حقيقية أو إيموجي)
    img_base64 = get_base64_image(ICON_FILE)
    if img_base64:
        # عرض الصورة باستخدام Base64
        logo_html = f'<img src="data:image/png;base64,{img_base64}" width="150" style="margin-bottom: 20px;">'
    else:
        # عرض إيموجي كبديل
        logo_html = '<div style="font-size: 100px; margin-bottom: 20px;">💎</div>'

    # كود HTML واحد يجمع كل شيء (هذا يضمن الظهور)
    splash_html = f"""
    <div id="splash-screen">
        {logo_html}
        <h1 style="color: #2ecc71; font-family: 'Segoe UI'; font-size: 3rem; margin: 0;">مصروفي</h1>
        <h3 style="color: #7f8c8d; font-family: 'Segoe UI'; margin-top: 10px;">...جاري التحميل</h3>
    </div>
    """
    
    with splash.container():
        st.markdown(splash_html, unsafe_allow_html=True)
        time.sleep(2.0)
        splash.empty()
        st.session_state['first_load'] = False

# --- 5. القوائم ---
INCOME_CATEGORIES = ["💰 راتب (نص الشهر)", "💰 راتب (اخر الشهر)", "🏠 إيراد إيجار شقة", "🏆 مكافأة أرباح سنوية", "🎁 مكافأة أخرى / إضافية", "💊 استرداد علاج", "💼 استرداد مأموريات عمل", "➕ أخرى"]
EXPENSE_CATEGORIES = ["🏠 إيجار شقة (سكن)", "🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم", "⚡ فواتير (كهرباء/غاز/مياه)", "🌐 إنترنت وموبايل", "🚗 بنزين ومواصلات", "🔧 صيانة سيارة", "💊 علاج ودواء", "👕 ملابس", "🎓 مصاريف تعليم ودروس", "🧸 مستلزمات الأبناء", "🎉 ترفيه وخروجات", "➕ أخرى"]
INSTALLMENT_TYPES = ["🏢 قسط الشقة الربع سنوي", "📦 أقساط مشتريات (أونلاين/أجهزة)", "🏊 قسط النادي", "➕ أخرى"]
PAYMENT_INCOME = ["💵 كاش", "🏦 تحويل بنكي / راتب", "📱 محفظة إلكترونية"]
PAYMENT_SPENDING = ["💵 كاش", "💳 Credit Card End 8298", "💳 Credit Card End 6016", "📱 محفظة البنك الأهلي", "📱 محفظة CIB", "📱 فودافون كاش"]

# --- التحميل ---
df = load_data_local()

# --- 6. واجهة التطبيق ---
# عرض الشعار بجانب العنوان (نفس طريقة Base64 للضمان)
img_base64_small = get_base64_image(ICON_FILE)
header_logo = f'<img src="data:image/png;base64,{img_base64_small}" width="90" style="vertical-align: middle;">' if img_base64_small else '<span style="font-size: 60px;">💎</span>'

st.markdown(f"""
<div style="display: flex; align-items: center; justify-content: center; direction: rtl; margin-bottom: 20px;">
    <div style="margin-left: 15px;">{header_logo}</div>
    <h1 style="color: #2ecc71; margin: 0; font-size: 2.5rem;">مصروفي | Masrofy</h1>
</div>
""", unsafe_allow_html=True)

today = datetime.now()
years_list = list(range(today.year - 1, today.year + 4))
default_year_ix = years_list.index(today.year) if today.year in years_list else 1

with st.expander("📅 إعدادات الفلترة", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1: view_year = st.selectbox("السنة", years_list, index=default_year_ix)
    with c2: view_month = st.selectbox("الشهر", range(1, 13), index=today.month - 1)
    with c3: food_budget_limit = st.number_input("ميزانية الطعام", value=5000, step=100)

tab1, tab2, tab3 = st.tabs(["📊 لوحة القيادة", "📝 تسجيل جديد", "📂 السجل"])

# === التبويب 1 ===
with tab1:
    if not df.empty:
        mask = (df["الشهر_المالي"] == int(view_month)) & (df["السنة_المالية"] == int(view_year))
        month_df = df[mask]
        
        total_income = month_df[month_df["النوع"] == "دخل"]["المبلغ"].sum()
        total_expense = month_df[month_df["النوع"] == "مصروف"]["المبلغ"].sum()
        total_installments = month_df[month_df["النوع"] == "قسط"]["المبلغ"].sum()
        balance = total_income - (total_expense + total_installments)
        visa_spending = month_df[(month_df["طريقة الدفع"].str.contains("Credit Card", case=False, na=False)) & (month_df["النوع"].isin(["مصروف", "قسط"]))]["المبلغ"].sum()
        food_spent = month_df[month_df["الفئة"].isin(["🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم"])]["المبلغ"].sum()

        if food_spent > food_budget_limit: st.error(f"🚨 تجاوزت ميزانية الطعام: {food_spent - food_budget_limit:,.0f}")
        if balance < 0: st.error(f"💸 عجز مالي: {abs(balance):,.0f}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 الدخل", f"{total_income:,.0f}")
        c2.metric("💸 المصاريف", f"{total_expense:,.0f}")
        c3.metric("📅 الأقساط", f"{total_installments:,.0f}")
        c4.metric("✅ الرصيد", f"{balance:,.0f}", delta_color="normal" if balance >= 0 else "inverse")
        
        st.markdown("---")
        k1, k2 = st.columns(2)
        with k1: st.warning(f"💳 فيزا مستحقة: {visa_spending:,.0f}")
        with k2: st.info(f"🍖 طعام: {food_spent:,.0f}/{food_budget_limit:,.0f}"); st.progress(min(food_spent/food_budget_limit, 1.0))
        
        st.divider()
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader("توزيع المصاريف")
            outgoing = month_df[month_df["النوع"].isin(["مصروف", "قسط"])]
            if not outgoing.empty: st.plotly_chart(px.pie(outgoing, values='المبلغ', names='الفئة', hole=0.4), use_container_width=True)
            else: st.info("لا توجد مصاريف.")
        with col_chart2:
            st.subheader("مصادر الدخل")
            inc = month_df[month_df["النوع"] == "دخل"]
            if not inc.empty: st.plotly_chart(px.bar(inc, x="الفئة", y="المبلغ", color="الفئة"), use_container_width=True)
            else: st.info("لا يوجد دخل.")
    else: st.info("مرحباً بك! ابدأ بتسجيل أول عملية.")

# === التبويب 2 ===
with tab2:
    st.subheader("➕ إضافة معاملة")
    options = ["مصروف", "دخل", "قسط"]
    if st.session_state['current_mode'] not in options: st.session_state['current_mode'] = "مصروف"

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
        
        with st.expander("📷 المرفقات"):
            c_cam, c_upl = st.columns(2)
            with c_cam: pic = st.camera_input("التقاط صورة"); 
            with c_upl: upl = st.file_uploader("رفع ملف")

        if st.form_submit_button("💾 حفظ البيانات", use_container_width=True):
            fin_cat = cust_cat.strip() if ("أخرى" in cat_sel and cust_cat) else cat_sel
            fp = ""
            fo = pic if pic else upl
            if fo:
                fp = os.path.join(ATTACHMENTS_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{getattr(fo, 'name', 'cam.jpg')}")
                with open(fp, "wb") as f: f.write(fo.getbuffer())

            row_dict = {"التاريخ": pd.to_datetime(dv), "السنة_المالية": int(ty), "الشهر_المالي": int(tm), "النوع": t_type, "الفئة": fin_cat, "طريقة الدفع": pay, "المبلغ": float(amt), "الوصف": dsc, "المرفق": fp}
            
            df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
            save_data_local(df)
            
            row_google = row_dict.copy(); row_google["التاريخ"] = dv
            bg_thread = threading.Thread(target=sync_to_google_forced_task, args=(row_google,))
            bg_thread.start()
            
            st.toast(f"✅ تم الحفظ: {fin_cat}", icon="🚀")
            time.sleep(0.2); st.rerun()

# === التبويب 3 ===
with tab3:
    if not df.empty:
        st.dataframe(df.sort_values(by="التاريخ", ascending=False), use_container_width=True, column_config={"المرفق": st.column_config.TextColumn("مسار المرفق")})
        st.divider()
        with st.expander("🗑️ حذف عملية", expanded=False):
            st.warning("⚠️ الحذف هنا يحذف من جهازك فقط.")
            df_disp = df.copy().sort_values(by="التاريخ", ascending=False)
            del_opts = df_disp.apply(lambda x: f"م{x.name}: {x['التاريخ'].date()} | {x['الفئة']} | {x['المبلغ']}ج", axis=1)
            sel_del = st.selectbox("اختر للحذف:", del_opts, index=None)
            if sel_del:
                idx = int(sel_del.split(":")[0].replace("م", ""))
                if st.button(f"🗑️ حذف رقم {idx}", type="primary"):
                    lf = df.loc[idx, "المرفق"]
                    if lf and os.path.exists(lf): 
                        try: os.remove(lf); 
                        except: pass
                    df = df.drop(idx)
                    save_data_local(df)
                    st.toast("تم الحذف!", icon="🗑️")
                    time.sleep(0.5); st.rerun()
        st.divider()
        files_df = df[df["المرفق"].notna() & (df["المرفق"] != "")]
        if not files_df.empty:
            opts = files_df.apply(lambda x: f"{x['التاريخ'].date()} - {x['الفئة']} ({x['المبلغ']})", axis=1)
            sel = st.selectbox("عرض فاتورة:", opts.unique())
            if sel:
                row = files_df[files_df.apply(lambda x: f"{x['التاريخ'].date()} - {x['الفئة']} ({x['المبلغ']})", axis=1) == sel].iloc[0]
                if os.path.exists(row["المرفق"]): st.image(row["المرفق"], width=400)
    else: st.info("السجل فارغ.")

# تذييل
st.markdown("---")
st.caption("Masrofy App v1.0 | Developed by Ezzat Emam")