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
                # التأكد من الأعمدة
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
INSTALLMENT_TYPES = ["🏢 قسط الشقة الربع سنوي", "📦 أقساط مشتريات (أونلاين/أجهزة)", "🏊 قسط النادي", "➕ أخرى"] # ✅ استرجاع الأقساط
PAYMENT_METHODS = ["💵 كاش", "💳 فيزا", "📱 محفظة", "🏦 بنك"]

# ---------------------------------------------------------
# 6. الواجهة الرسومية
# ---------------------------------------------------------
st.markdown(f"""<h1 style="text-align: center; color: #2ecc71;">مصروفي | Masrofy Cloud ☁️</h1>""", unsafe_allow_html=True)
if st.button("🔄 تحديث البيانات"): st.cache_data.clear(); st.rerun()

# --- إعدادات الفلترة وميزانية الطعام ---
with st.expander("📅 إعدادات وميزانية", expanded=False):
    c1, c2, c3 = st.columns(3)
    today = datetime.now()
    if not df.empty:
        years = sorted(df["السنة"].unique()) if "السنة" in df.columns else [today.year]
    else: years = [today.year]
    
    with c1: view_year = st.selectbox("السنة", years, index=len(years)-1)
    with c2: view_month = st.selectbox("الشهر", range(1, 13), index=today.month - 1)
    with c3: food_budget_limit = st.number_input("🍖 ميزانية الطعام الشهرية", value=5000, step=100) # ✅ استرجاع ميزانية الطعام

# التبويبات
tab1, tab2, tab3, tab4 = st.tabs(["📊 لوحة القيادة", "📝 تسجيل جديد", "✏️ تعديل / حذف", "📂 السجل"])

# =========================================================
# TAB 1: لوحة القيادة (Dashboard) - تم استرجاع الرسوم البيانية
# =========================================================
with tab1:
    if not df.empty:
        mask = (df["الشهر"] == view_month) & (df["السنة"] == view_year)
        m_df = df[mask]
        
        # 1. الحسابات (شاملة الأقساط)
        inc = m_df[m_df["النوع"]=="دخل"]["المبلغ"].sum()
        
        # المصروفات تشمل "مصروفات" وأيضاً لو النوع مش دخل ولا قسط (تحسباً)
        exp_only = m_df[m_df["النوع"].str.contains("مصروف", na=False)]["المبلغ"].sum()
        
        # حساب الأقساط
        inst_only = m_df[m_df["النوع"].str.contains("قسط", na=False)]["المبلغ"].sum()
        
        # إجمالي المصاريف + الأقساط
        total_out = exp_only + inst_only
        
        # الرصيد
        balance = inc - total_out
        
        # 2. عرض العدادات
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 إجمالي الدخل", f"{inc:,.0f}")
        col2.metric("💸 المصروفات", f"{exp_only:,.0f}")
        col3.metric("📅 الأقساط", f"{inst_only:,.0f}") # ✅ عداد الأقساط رجع
        col4.metric("✅ الرصيد المتبقي", f"{balance:,.0f}", delta_color="normal" if balance >= 0 else "inverse")
        
        st.divider()
        
        # 3. ميزانية الطعام
        food_spent = m_df[m_df["البند"].str.contains("طعام|سوبر ماركت|خضار|لحوم|بقال", na=False)]["المبلغ"].sum()
        food_progress = min(food_spent / food_budget_limit, 1.0) if food_budget_limit > 0 else 0
        st.write(f"**🍖 استهلاك الطعام:** {food_spent:,.0f} من {food_budget_limit:,.0f}")
        st.progress(food_progress)
        if food_spent > food_budget_limit: st.error("⚠️ لقد تجاوزت ميزانية الطعام!")
        
        st.divider()

        # 4. الرسوم البيانية (Charts)
        g1, g2 = st.columns(2)
        with g1:
            # رسمة المصروفات والأقساط
            out_data = m_df[m_df["النوع"].str.contains("مصروف|قسط", na=False)]
            if not out_data.empty:
                st.subheader("توزيع المصاريف والأقساط")
                fig_pie = px.pie(out_data, values='المبلغ', names='البند', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            else: st.info("لا توجد مصاريف لعرضها")
            
        with g2:
            # رسمة الدخل
            inc_data = m_df[m_df["النوع"] == "دخل"]
            if not inc_data.empty:
                st.subheader("مصادر الدخل") # ✅ استرجاع رسمة الدخل
                fig_bar = px.bar(inc_data, x="البند", y="المبلغ", color="البند")
                st.plotly_chart(fig_bar, use_container_width=True)
            else: st.info("لا يوجد دخل لعرضه")

    else:
        st.info("لا توجد بيانات. ابدأ بإضافة عمليات.")

# =========================================================
# TAB 2: تسجيل جديد (Entry) - تم استرجاع الأقساط
# =========================================================
with tab2:
    st.subheader("إضافة عملية جديدة")
    
    # اختيار النوع (أضفنا القسط مرة أخرى)
    c_type, c_rest = st.columns([1, 2])
    with c_type:
        t_type = st.radio("النوع", ["مصروفات", "دخل", "قسط"], horizontal=True) # ✅
    
    # قوائم التصنيف بناءً على النوع
    if t_type == "دخل": current_cats = INCOME_CATEGORIES
    elif t_type == "قسط": current_cats = INSTALLMENT_TYPES
    else: current_cats = EXPENSE_CATEGORIES
    
    with c_rest:
        cat = st.selectbox("البند / التصنيف", current_cats)
        if "أخرى" in cat:
             cat = st.text_input("اكتب اسم البند هنا:")

    col_a, col_b = st.columns(2)
    with col_a: date_val = st.date_input("التاريخ", datetime.now())
    with col_b: amount_val = st.number_input("المبلغ", min_value=0.0, step=10.0)
    
    col_c, col_d = st.columns(2)
    with col_c: method_val = st.selectbox("طريقة الدفع", PAYMENT_METHODS)
    with col_d: note_val = st.text_input("ملاحظات / تفاصيل")
    
    if st.button("💾 حفظ وترحيل سحابي", use_container_width=True):
        # تحديد النوع للكود الخلفي
        # في جوجل شيت، بنعتبر "القسط" زي "المصروف" عشان يتكتب في الشمال
        # بس بنسجل اسمه "قسط" عشان الفلترة
        backend_type = "income" if t_type == "دخل" else "expense"
        final_category = cat # الاسم اللي هيظهر في الشيت
        
        # لو هو قسط، ممكن نعدل النوع اللي رايح للشيت عشان نميزه، 
        # بس الأفضل نخليه expense ونعتمد ان البند هو اللي بيوضح او نبعت النوع كـ "قسط"
        # الكود في Apps Script بيحط income يمين والباقي شمال، فـ "قسط" هيروح شمال (صح)
        
        payload = {
            "action": "add",
            "transType": backend_type, 
            "date": str(date_val),
            "amount": amount_val,
            "category": final_category,
            "subCategory": note_val, # ممكن نحط كلمة قسط هنا لو حابب
            "method": method_val,
            "realType": t_type # بنبعت النوع الحقيقي عشان لو حبينا نستخدمه مستقبلاً
        }
        
        # تريك صغيرة: لو قسط، هنخلي Apps Script يكتب في عمود "النوع" كلمة "قسط" بدل "مصروفات"
        # ده محتاج تعديل بسيط في Apps Script؟ لا، لأن Apps Script بياخد النوع مننا
        # احنا في Apps Script بنحدد العمود بناء على income/expense
        # بس بنكتب القيمة اللي جاية. 
        
        # التعديل: هنبعت للقائمة في الشيت اسم النوع اللي اخترناه (قسط)
        # بس عشان Apps Script يفهم يحطه يمين ولا شمال، بنستخدم transType
        
        # الحل: نعدل payload عشان يظبط الداتا
        if t_type == "قسط":
             # هنخلي الـ category هو اللي "قسط - اسم البند" عشان يبان بوضوح؟
             # لا، خلينا نعتمد على اننا هنبعت transType = expense (عشان المكان)
             # وهنحاول نتحايل على Apps Script يكتب كلمة "قسط" في الخلية؟
             # الكود الحالي في Apps Script بياخد transType يحدد بيه المكان (if income -> I else -> A)
             # وبيكتبه هو هو في الخلية.
             # فلو بعتله "قسط"، هيروح في الـ else (شمال) ويكتب "قسط". وده المطلوب! ممتاز.
             payload["transType"] = "قسط" 
             pass
        
        with st.spinner("جاري الحفظ في جوجل شيت..."):
            ok, msg = send_to_google(payload)
            if ok:
                st.success("تم الحفظ!"); time.sleep(1); st.cache_data.clear(); st.rerun()
            else:
                st.error("خطأ: " + msg)

# =========================================================
# TAB 3: تعديل / حذف (Edit/Delete)
# =========================================================
with tab3:
    st.subheader("إدارة العمليات")
    if not df.empty:
        # فلتر لعرض العمليات عشان القائمة متبقاش طويلة اوي
        filter_type = st.radio("فلتر بـ:", ["الكل", "مصروفات", "دخل", "قسط"], horizontal=True)
        
        if filter_type == "الكل": display_df = df
        elif filter_type == "قسط": display_df = df[df["النوع"].str.contains("قسط", na=False)]
        elif filter_type == "دخل": display_df = df[df["النوع"] == "دخل"]
        else: display_df = df[df["النوع"].str.contains("مصروف", na=False)]
        
        if not display_df.empty:
            display_df['label'] = display_df.apply(lambda x: f"{x['التاريخ'].date()} | {x['النوع']} | {x['البند']} | {x['المبلغ']}", axis=1)
            selected_label = st.selectbox("اختر العملية:", display_df['label'].tolist())
            
            if selected_label:
                row = display_df[display_df['label'] == selected_label].iloc[0]
                
                with st.expander("✏️ تعديل البيانات", expanded=True):
                    new_amount = st.number_input("تعديل المبلغ", value=float(row['المبلغ']))
                    
                    # تحديد القائمة المناسبة للتعديل
                    if "قسط" in row['النوع']: edit_cats = INSTALLMENT_TYPES
                    elif "دخل" in row['النوع']: edit_cats = INCOME_CATEGORIES
                    else: edit_cats = EXPENSE_CATEGORIES
                    
                    try: c_ix = edit_cats.index(row['البند'])
                    except: c_ix = 0
                    
                    new_cat = st.selectbox("تعديل البند", edit_cats, index=c_ix)
                    new_note = st.text_input("تعديل الملاحظات", value=row['ملاحظات'])
                    
                    c_edit, c_del = st.columns(2)
                    
                    if c_edit.button("تحديث"):
                        payload = {
                            "action": "edit",
                            "id": row['id'],
                            "transType": row['النوع'], # نحافظ على النوع
                            "date": str(row['التاريخ'].date()),
                            "amount": new_amount,
                            "category": new_cat,
                            "subCategory": new_note,
                            "method": row['طريقة الدفع']
                        }
                        with st.spinner("جاري التعديل..."):
                            ok, msg = send_to_google(payload)
                            if ok: st.success("تم!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                            else: st.error("فشل التعديل")

                    if c_del.button("🗑️ حذف", type="primary"):
                        payload = {"action": "delete", "id": row['id']}
                        with st.spinner("جاري الحذف..."):
                            ok, msg = send_to_google(payload)
                            if ok: st.success("تم الحذف!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                            else: st.error("فشل الحذف")
        else: st.info("لا توجد عمليات بهذا النوع.")
    else: st.info("لا توجد بيانات.")

# =========================================================
# TAB 4: السجل (History)
# =========================================================
with tab4:
    if not df.empty:
        st.dataframe(df.drop(columns=['id', 'label'], errors='ignore').sort_values(by="التاريخ", ascending=False), use_container_width=True)
    else:
        st.info("السجل فارغ.")

st.markdown("---")
st.caption("Masrofy v6.0 | Ultimate Cloud Edition 🚀")
