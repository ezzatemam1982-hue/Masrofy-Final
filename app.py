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

# --- 1. إعداد الصفحة (لازم تكون أول حاجة) ---
ICON_FILE = "diamond_icon.png"
page_icon_obj = ICON_FILE if os.path.exists(ICON_FILE) else "💎"

st.set_page_config(
    page_title="مصروفي | Masrofy",
    page_icon=page_icon_obj,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. تعريف المسارات والمتغيرات ---
LOCAL_DATA_FILE = "finance_data_v28.csv"
ATTACHMENTS_DIR = "attachments"
SHEET_NAME = "Masrofy_DB"
CREDS_FILE = "credentials.json"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# إنشاء مجلد للمرفقات لو مش موجود
if not os.path.exists(ATTACHMENTS_DIR): os.makedirs(ATTACHMENTS_DIR)

# متغير لحفظ الحالة (Mode)
if 'current_mode' not in st.session_state: st.session_state['current_mode'] = "مصروفات"
def update_mode(): st.session_state['current_mode'] = st.session_state.mode_selector

# --- 3. تحسين المظهر (CSS) ---
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
    
    /* تنسيق زر التحميل في القائمة الجانبية */
    .stDownloadButton button {
        width: 100%;
        background-color: #f1c40f !important;
        color: black !important;
        border: none;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. الدوال المساعدة (Load/Save/Sync) ---

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def load_data_local():
    """تحميل البيانات من الملف المحلي مع معالجة الأخطاء وتوحيد الأسماء"""
    if os.path.exists(LOCAL_DATA_FILE):
        try:
            df = pd.read_csv(LOCAL_DATA_FILE)
            
            # تصحيح اسم العمود لو كان "السعر" بدلاً من "المبلغ"
            if "السعر" in df.columns and "المبلغ" not in df.columns:
                df.rename(columns={"السعر": "المبلغ"}, inplace=True)
                
            if "التاريخ" in df.columns:
                df["التاريخ"] = pd.to_datetime(df["التاريخ"], errors='coerce')
                df["المبلغ"] = pd.to_numeric(df["المبلغ"], errors='coerce').fillna(0.0)
                # تنظيف النصوص من الـ NaN
                for col in ["النوع", "البند", "طريقة الدفع", "ملاحظات", "المرفق"]:
                    if col in df.columns:
                        df[col] = df[col].astype(str).replace('nan', '')
                return df
        except: pass
    # لو الملف مش موجود أو بايظ، رجع جدول فاضي
    return pd.DataFrame(columns=["التاريخ", "السنة", "الشهر", "النوع", "البند", "طريقة الدفع", "المبلغ", "ملاحظات", "المرفق"])

def save_data_local(df):
    df.to_csv(LOCAL_DATA_FILE, index=False)

def sync_to_google_background(row_dict):
    """دالة الرفع لجوجل شيت (تعمل في الخلفية)"""
    print(f"🔍 بدء عملية الرفع لجوجل... المسار: {os.path.abspath(CREDS_FILE)}")
    if os.path.exists(CREDS_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope=SCOPE)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            
            # ترتيب البيانات زي ما هي في الشيت
            values = [
                str(row_dict.get("التاريخ").date()), 
                str(row_dict.get("السنة")), 
                str(row_dict.get("الشهر")), 
                str(row_dict.get("النوع")), 
                str(row_dict.get("البند")), 
                str(row_dict.get("طريقة الدفع")), 
                str(row_dict.get("المبلغ")), 
                str(row_dict.get("ملاحظات", "")), 
                "تطبيق كامل"
            ]
            sheet.append_row(values)
            print("✅ تم الرفع لجوجل بنجاح!")
        except Exception as e:
            print(f"❌ خطأ في جوجل شيت: {e}")
    else:
        print("⚠️ ملف credentials.json غير موجود!")

# --- 5. قوائم البيانات (التصنيفات) ---
INCOME_CATEGORIES = ["💰 راتب (نص الشهر)", "💰 راتب (اخر الشهر)", "🏠 إيراد إيجار شقة", "🏆 مكافأة أرباح سنوية", "🎁 مكافأة أخرى / إضافية", "💊 استرداد علاج", "💼 استرداد مأموريات عمل", "➕ أخرى"]
EXPENSE_CATEGORIES = ["🏠 إيجار شقة (سكن)", "🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم", "⚡ فواتير (كهرباء/غاز/مياه)", "🌐 إنترنت وموبايل", "🚗 بنزين ومواصلات", "🔧 صيانة سيارة", "💊 علاج ودواء", "👕 ملابس", "🎓 مصاريف تعليم ودروس", "🧸 مستلزمات الأبناء", "🎉 ترفيه وخروجات", "➕ أخرى"]
INSTALLMENT_TYPES = ["🏢 قسط الشقة الربع سنوي", "📦 أقساط مشتريات (أونلاين/أجهزة)", "🏊 قسط النادي", "➕ أخرى"]
PAYMENT_INCOME = ["💵 كاش", "🏦 تحويل بنكي / راتب", "📱 محفظة إلكترونية"]
PAYMENT_SPENDING = ["💵 كاش", "💳 Credit Card End 8298", "💳 Credit Card End 6016", "📱 محفظة البنك الأهلي", "📱 محفظة CIB", "📱 فودافون كاش"]

# تحميل البيانات عند البدء
df = load_data_local()

# --- 6. واجهة التطبيق ---

# الهيدر واللوجو
img_base64_small = get_base64_image(ICON_FILE)
header_logo = f'<img src="data:image/png;base64,{img_base64_small}" width="90" style="vertical-align: middle;">' if img_base64_small else '<span style="font-size: 60px;">💎</span>'

st.markdown(f"""
<div style="display: flex; align-items: center; justify-content: center; direction: rtl; margin-bottom: 20px;">
    <div style="margin-left: 15px;">{header_logo}</div>
    <h1 style="color: #2ecc71; margin: 0; font-size: 2.5rem;">مصروفي | Masrofy</h1>
</div>
""", unsafe_allow_html=True)

# --- القائمة الجانبية (إدارة البيانات) ---
if os.path.exists(ICON_FILE): st.sidebar.image(ICON_FILE, width=100)
else: st.sidebar.title("💎")

with st.sidebar.expander("⚙️ إدارة قاعدة البيانات (CSV)", expanded=True):
    # زر التصدير (حفظ)
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 حفظ نسخة احتياطية",
        data=csv_data,
        file_name=f"Masrofy_Backup_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    
    # زر الاستيراد (استرجاع)
    uploaded_file = st.file_uploader("📂 استرجاع ملف بيانات") 
    if uploaded_file is not None:
        if st.button("⚠️ تأكيد الاستبدال"):
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                # التأكد من صحة الملف
                required = ["التاريخ", "النوع"] # شروط مخففة
                if any(col in uploaded_df.columns for col in required):
                    # تصحيح تلقائي لو العمود اسمه السعر
                    if "السعر" in uploaded_df.columns: uploaded_df.rename(columns={"السعر": "المبلغ"}, inplace=True)
                    
                    uploaded_df.to_csv(LOCAL_DATA_FILE, index=False)
                    st.success("✅ تم استرجاع قاعدة البيانات!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ الملف لا يحتوي على بيانات صحيحة.")
            except Exception as e:
                st.error(f"خطأ في الملف: {e}")

# --- الفلاتر العلوية ---
today = datetime.now()
years_list = list(range(today.year - 1, today.year + 4))
default_year_ix = years_list.index(today.year) if today.year in years_list else 1

with st.expander("📅 إعدادات الفلترة", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1: view_year = st.selectbox("السنة", years_list, index=default_year_ix)
    with c2: view_month = st.selectbox("الشهر", range(1, 13), index=today.month - 1)
    with c3: food_budget_limit = st.number_input("ميزانية الطعام", value=5000, step=100)

# --- التبويبات الرئيسية ---
tab1, tab2, tab3 = st.tabs(["📊 لوحة القيادة", "📝 تسجيل جديد", "📂 السجل"])

# === التبويب 1: لوحة القيادة ===
with tab1:
    if not df.empty and "التاريخ" in df.columns:
        # فلترة البيانات حسب السنة والشهر المختارين
        mask = (df["الشهر"] == int(view_month)) & (df["السنة"] == int(view_year))
        month_df = df[mask]
        
        # الحسابات
        total_income = month_df[month_df["النوع"] == "دخل"]["المبلغ"].sum()
        total_expense = month_df[month_df["النوع"].str.contains("مصروف", na=False)]["المبلغ"].sum()
        total_installments = month_df[month_df["النوع"] == "قسط"]["المبلغ"].sum()
        balance = total_income - (total_expense + total_installments)
        
        # عرض الأرقام
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 الدخل", f"{total_income:,.0f}")
        c2.metric("💸 المصاريف", f"{total_expense:,.0f}")
        c3.metric("📅 الأقساط", f"{total_installments:,.0f}")
        c4.metric("✅ الرصيد", f"{balance:,.0f}", delta_color="normal" if balance >= 0 else "inverse")
        
        st.divider()
        
        # الرسومات البيانية
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("توزيع المصاريف")
            outgoing = month_df[month_df["النوع"].str.contains("مصروف|قسط", regex=True, na=False)]
            if not outgoing.empty: 
                fig1 = px.pie(outgoing, values='المبلغ', names='البند', hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
            else: st.info("لا توجد مصاريف هذا الشهر.")
            
        with col_chart2:
            st.subheader("مصادر الدخل")
            income_data = month_df[month_df["النوع"] == "دخل"]
            if not income_data.empty: 
                fig2 = px.bar(income_data, x="البند", y="المبلغ", color="البند")
                st.plotly_chart(fig2, use_container_width=True)
            else: st.info("لا يوجد دخل مسجل هذا الشهر.")
            
    else: st.info("👋 مرحباً! السجل فارغ، ابدأ بتسجيل عملياتك.")

# === التبويب 2: تسجيل جديد ===
with tab2:
    st.subheader("➕ إضافة معاملة")
    options = ["مصروفات", "دخل", "قسط"]
    
    # اختيار النوع
    t_type = st.radio("نوع المعاملة:", options, horizontal=True, index=options.index(st.session_state['current_mode']), key="mode_selector", on_change=update_mode)
    
    # تحديد القوائم بناءً على النوع
    if t_type == "دخل": cat_l, pay_l = INCOME_CATEGORIES, PAYMENT_INCOME
    elif t_type == "قسط": cat_l, pay_l = INSTALLMENT_TYPES, PAYMENT_SPENDING
    else: cat_l, pay_l = EXPENSE_CATEGORIES, PAYMENT_SPENDING
    
    # التصنيف
    c_s1, c_s2 = st.columns([1,1])
    with c_s1: cat_sel = st.selectbox("التصنيف:", cat_l)
    cust_cat = ""
    
    # حقل إضافي لو اختار "أخرى"
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
        
        # المرفقات (صور وكاميرا فقط)
        with st.expander("📎 إرفاق صورة الفاتورة (اختياري)"):
            upl = st.file_uploader("التقاط صورة أو اختيار ملف", type=["png", "jpg", "jpeg", "pdf"])

        # زر الحفظ
        if st.form_submit_button("💾 حفظ البيانات", use_container_width=True):
            # تحديد اسم البند النهائي
            fin_cat = cust_cat.strip() if ("أخرى" in cat_sel and cust_cat) else cat_sel
            fp = ""
            
            # حفظ المرفق
            if upl:
                fp = os.path.join(ATTACHMENTS_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{upl.name}")
                with open(fp, "wb") as f: f.write(upl.getbuffer())

            # تجهيز الصف
            row_dict = {
                "التاريخ": pd.to_datetime(dv), 
                "السنة": int(ty), 
                "الشهر": int(tm), 
                "النوع": t_type, 
                "البند": fin_cat, 
                "طريقة الدفع": pay, 
                "المبلغ": float(amt), 
                "ملاحظات": dsc, 
                "المرفق": fp
            }
            
            # 1. حفظ محلي
            df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
            save_data_local(df)
            
            # 2. رفع لجوجل (في الخلفية)
            bg_thread = threading.Thread(target=sync_to_google_background, args=(row_dict,))
            bg_thread.start()
            
            st.toast(f"✅ تم الحفظ بنجاح: {fin_cat}", icon="🚀")
            time.sleep(0.5); st.rerun()

# === التبويب 3: السجل ===
with tab3:
    if not df.empty and "التاريخ" in df.columns:
        # عرض الجدول
        st.dataframe(
            df.sort_values(by="التاريخ", ascending=False), 
            use_container_width=True, 
            column_config={"المرفق": st.column_config.TextColumn("مسار المرفق")}
        )
        
        st.divider()
        
        # حذف عملية
        with st.expander("🗑️ حذف عملية (محلياً فقط)", expanded=False):
            df_disp = df.copy().sort_values(by="التاريخ", ascending=False)
            del_opts = df_disp.apply(lambda x: f"م{x.name}: {x['التاريخ'].date()} | {x['البند']} | {x['المبلغ']}ج", axis=1)
            sel_del = st.selectbox("اختر العملية للحذف:", del_opts, index=None)
            
            if sel_del and st.button("🗑️ تأكيد الحذف", type="primary"):
                idx = int(sel_del.split(":")[0].replace("م", ""))
                df = df.drop(idx)
                save_data_local(df)
                st.toast("تم الحذف من الجهاز!", icon="🗑️")
                time.sleep(0.5); st.rerun()
                
        # عرض صور الفواتير
        if "المرفق" in df.columns:
            files_df = df[df["المرفق"].notna() & (df["المرفق"] != "")]
            if not files_df.empty:
                st.markdown("---")
                st.subheader("🖼️ عرض الفواتير")
                opts = files_df.apply(lambda x: f"{x['التاريخ'].date()} - {x['البند']} ({x['المبلغ']})", axis=1)
                sel = st.selectbox("اختر فاتورة للعرض:", opts.unique())
                if sel:
                    row = files_df[files_df.apply(lambda x: f"{x['التاريخ'].date()} - {x['البند']} ({x['المبلغ']})", axis=1) == sel].iloc[0]
                    if os.path.exists(row["المرفق"]): 
                        st.image(row["المرفق"], caption=f"فاتورة: {row['البند']}", width=400)
                    else:
                        st.warning("⚠️ ملف الصورة غير موجود على الجهاز.")
    else: st.info("السجل فارغ.")

st.markdown("---")
st.caption("Masrofy App v3.0 | Developed by Ezzat Emam")
