import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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

# --- 2. تعريف المسارات والمتغيرات ---
LOCAL_DATA_FILE = "finance_data_v28.csv"
ATTACHMENTS_DIR = "attachments"
SHEET_NAME = "Masrofy_DB"
CREDS_FILE = "credentials.json"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if not os.path.exists(ATTACHMENTS_DIR): os.makedirs(ATTACHMENTS_DIR)

if 'current_mode' not in st.session_state: st.session_state['current_mode'] = "مصروفات"
def update_mode(): st.session_state['current_mode'] = st.session_state.mode_selector

# --- 3. CSS ---
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

# --- 4. الدوال المساعدة ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    return None

def load_data_local():
    if os.path.exists(LOCAL_DATA_FILE):
        try:
            df = pd.read_csv(LOCAL_DATA_FILE)
            if "السعر" in df.columns: df.rename(columns={"السعر": "المبلغ"}, inplace=True)
            if "التاريخ" in df.columns:
                df["التاريخ"] = pd.to_datetime(df["التاريخ"], errors='coerce')
                df["المبلغ"] = pd.to_numeric(df["المبلغ"], errors='coerce').fillna(0.0)
                for col in ["النوع", "البند", "طريقة الدفع", "ملاحظات", "المرفق"]:
                    if col in df.columns: df[col] = df[col].astype(str).replace('nan', '')
                return df
        except: pass
    return pd.DataFrame(columns=["التاريخ", "السنة", "الشهر", "النوع", "البند", "طريقة الدفع", "المبلغ", "ملاحظات", "المرفق"])

def save_data_local(df):
    df.to_csv(LOCAL_DATA_FILE, index=False)

# دالة الرفع المباشر (Synchronous)
def sync_to_google_direct(row_dict):
    if os.path.exists(CREDS_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope=SCOPE)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            values = [
                str(row_dict.get("التاريخ").date()), str(row_dict.get("السنة")), str(row_dict.get("الشهر")), 
                str(row_dict.get("النوع")), str(row_dict.get("البند")), str(row_dict.get("طريقة الدفع")), 
                str(row_dict.get("المبلغ")), str(row_dict.get("ملاحظات", "")), "تطبيق V3.1"
            ]
            sheet.append_row(values)
            return True, "تم الرفع بنجاح"
        except Exception as e:
            return False, str(e)
    else:
        return False, "ملف credentials.json غير موجود"

# --- 5. القوائم ---
INCOME_CATEGORIES = ["💰 راتب (نص الشهر)", "💰 راتب (اخر الشهر)", "🏠 إيراد إيجار شقة", "🏆 مكافأة أرباح سنوية", "🎁 مكافأة أخرى / إضافية", "💊 استرداد علاج", "💼 استرداد مأموريات عمل", "➕ أخرى"]
EXPENSE_CATEGORIES = ["🏠 إيجار شقة (سكن)", "🛒 سوبر ماركت وبقالة", "🥩 خضار ولحوم", "⚡ فواتير (كهرباء/غاز/مياه)", "🌐 إنترنت وموبايل", "🚗 بنزين ومواصلات", "🔧 صيانة سيارة", "💊 علاج ودواء", "👕 ملابس", "🎓 مصاريف تعليم ودروس", "🧸 مستلزمات الأبناء", "🎉 ترفيه وخروجات", "➕ أخرى"]
INSTALLMENT_TYPES = ["🏢 قسط الشقة الربع سنوي", "📦 أقساط مشتريات (أونلاين/أجهزة)", "🏊 قسط النادي", "➕ أخرى"]
PAYMENT_INCOME = ["💵 كاش", "🏦 تحويل بنكي / راتب", "📱 محفظة إلكترونية"]
PAYMENT_SPENDING = ["💵 كاش", "💳 Credit Card End 8298", "💳 Credit Card End 6016", "📱 محفظة البنك الأهلي", "📱 محفظة CIB", "📱 فودافون كاش"]

df = load_data_local()

# --- 6. الواجهة ---
img_base64_small = get_base64_image(ICON_FILE)
header_logo = f'<img src="data:image/png;base64,{img_base64_small}" width="90" style="vertical-align: middle;">' if img_base64_small else '<span style="font-size: 60px;">💎</span>'

st.markdown(f"""<div style="display: flex; align-items: center; justify-content: center; direction: rtl; margin-bottom: 20px;">
    <div style="margin-left: 15px;">{header_logo}</div><h1 style="color: #2ecc71; margin: 0; font-size: 2.5rem;">مصروفي | Masrofy</h1></div>""", unsafe_allow_html=True)

if os.path.exists(ICON_FILE): st.sidebar.image(ICON_FILE, width=100)
else: st.sidebar.title("💎")

with st.sidebar.expander("⚙️ إدارة البيانات", expanded=True):
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button("💾 حفظ نسخة احتياطية", csv_data, f"Backup_{datetime.now().date()}.csv", "text/csv")
    st.markdown("---")
    upl_file = st.file_uploader("📂 استرجاع ملف بيانات") 
    if upl_file and st.button("⚠️ تأكيد الاستبدال"):
        try:
            udf = pd.read_csv(upl_file)
            if "السعر" in udf.columns: udf.rename(columns={"السعر": "المبلغ"}, inplace=True)
            if any(c in udf.columns for c in ["التاريخ", "النوع"]):
                udf.to_csv(LOCAL_DATA_FILE, index=False)
                st.success("✅ تم الاسترجاع!"); time.sleep(1); st.rerun()
        except: st.error("❌ ملف غير صالح")

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
    else: st.info("السجل فارغ.")

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
    if "أخرى" in cat_sel: with c2: cust_cat = st.text_input("اسم المصروف:")
    
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
        
        upl = st.file_uploader("صورة الفاتورة (اختياري)", type=["png", "jpg", "jpeg", "pdf"])

        if st.form_submit_button("💾 حفظ وترحيل", use_container_width=True):
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
            
            # 1. الحفظ المحلي
            df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
            save_data_local(df)
            
            # 2. الرفع المباشر (Synchronous) - الحل الأكيد
            with st.spinner("⏳ جاري الحفظ في جوجل شيت..."):
                success, msg = sync_to_google_direct(row_dict)
                
            if success:
                st.success(f"✅ تم الحفظ محلياً وعلي جوجل! ({fin_cat})")
                time.sleep(1)
                st.rerun()
            else:
                st.warning(f"⚠️ تم الحفظ محلياً فقط. فشل جوجل: {msg}")
                time.sleep(3) # وقت عشان تقرأ الخطأ لو حصل

with tab3:
    if not df.empty:
        st.dataframe(df.sort_values(by="التاريخ", ascending=False), use_container_width=True, column_config={"المرفق": st.column_config.TextColumn("مسار المرفق")})
        st.divider()
        with st.expander("🗑️ حذف"):
            del_list = df.apply(lambda x: f"{x.name}: {x['التاريخ'].date()} | {x['البند']} | {x['المبلغ']}", axis=1)
            sel_del = st.selectbox("اختر للحذف:", del_list)
            if sel_del and st.button("تأكيد الحذف"):
                df = df.drop(int(sel_del.split(":")[0]))
                save_data_local(df)
                st.success("تم الحذف"); time.sleep(0.5); st.rerun()
    else: st.info("السجل فارغ")

st.markdown("---")
st.caption("Masrofy App v3.0 | Developed by Ezzat Emam")

