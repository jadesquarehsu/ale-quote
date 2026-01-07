import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import quote
import os
import io

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="ALÉ 專業報價系統", layout="wide")

# ==========================================
# 🔐 安全密碼鎖
# ==========================================
PASSWORD = "8017"

input_pass = st.sidebar.text_input("🔒 請輸入通關密碼", type="password")

if input_pass != PASSWORD:
    st.sidebar.warning("❌ 未輸入或密碼錯誤")
    st.markdown("## 🔒 系統已鎖定")
    st.info("⚠️ 請在左側輸入密碼以存取報價系統。")
    st.stop() 

# ==========================================
# 🔓 驗證通過區
# ==========================================

# --- 2. Google Sheet 設定 ---
SHEET_ID = "1LNaFoDOAr08LGxQ8cCRSSff7U7OU5ABH" 
SHEET_NAME = "Sheet1" 

try:
    encoded_sheet_name = quote(SHEET_NAME)
    SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
except:
    SHEET_URL = ""

# --- 3. 讀取資料 ---
@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8')
        # 資料清理：確保重要欄位是字串格式
        if 'Item_No' in df.columns:
            df['Item_No'] = df['Item_No'].astype(str).str.strip()
        
        # 預先處理圖片欄位
        for col in ['pic code_1', 'pic code_2']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            else:
                df[col] = "" # 如果沒這欄就補空
                
        return df
    except:
        return None

# --- 4. 計算邏輯 ---
FREIGHT_MAP = {'A': 45, 'B': 63, 'C': 103, 'D': 13, 'E': 22}

def calc_price(row, src_col, design, service, margin, rate):
    try:
        p_price = float(row[src_col])
        if pd.isna(p_price) or p_price <= 0: return 0.0
        
        f_code = str(row['freight']).strip().upper() if 'freight' in row and pd.notna(row['freight']) else 'A'
        ship = FREIGHT_MAP.get(f_code, 45)
        
        duty = 0.125 if (pd.notna(row['DYED']) and str(row['DYED']).strip()!="") else 0.105
        
        cost = (p_price * rate) * (1 + 0.05 + duty) + ship
        return round((cost + design + service) / (1 - margin))
    except:
        return 0.0

# 找圖功能的強力邏輯 (自動忽略大小寫、自動補副檔名)
def find_image_robust(filename):
    if not filename or str(filename).lower() == "nan" or str(filename).strip() == "":
        return None
    
    clean_name = str(filename).strip()
    
    # 嘗試分離主檔名 (例如 "A001.png" -> "A001")
    base_name = clean_name
    if "." in clean_name:
        base_name = clean_name.rsplit('.', 1)[0]
    
    # 所有可能的檔名組合
    candidates = [
        clean_name,                     # 原樣
        f"{clean_name}.png",            # 加小寫 png
        f"{clean_name}.PNG",            # 加大寫 PNG
        f"{clean_name}.jpg",            # 加小寫 jpg
        f"{clean_name}.JPG",            # 加大寫 JPG
        f"{base_name}.png",             # 只有檔名 + png
        f"{base_name}.PNG",             # 只有檔名 + PNG
        f"{base_name}.jpg",
        f"{base_name}.JPG"
    ]
    
    for c in candidates:
        path = f"images/{c}"
        if os.path.exists(path):
            return path # 找到了！
            
    return None

# 回呼函數
def add_to_cart_callback(item_dict):
    st.session_state.cart.append(item_dict)
    st.toast(f"✅ 已加入 {item_dict.get('Item_No', '產品')}")

# 載入資料
df_raw = load_data()

if df_raw is None:
    st.error("❌ 無法讀取資料，請檢查 Google Sheet 權限。")
    st.stop()

df_raw.columns = df_raw.columns.str.strip()

# --- 5. 參數設定面板 ---
st.sidebar.success("✅ 已解鎖")
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 參數設定")
rate = st.sidebar.number_input("當前匯率", value=35.0, step=0.1)

with st.sidebar.expander("📈 進階利潤率設定 (點擊展開)"):
    m1 = st.slider("10-15pcs (%)", 10, 60, 40) / 100
    m2 = st.slider("16-29pcs (%)", 10, 60, 35) / 100
    m3 = st.slider("30-59pcs (%)", 10, 60, 30) / 100

st.sidebar.markdown("---")
line_opt = ["全部"] + sorted(df_raw['Line_code'].dropna().unique().tolist()) if 'Line_code' in df_raw.columns else ["全部"]
cate_opt = ["全部"] + sorted(df_raw['Category'].dropna().unique().tolist()) if 'Category' in df_raw.columns else ["全部"]
gend_opt = ["全部"] + sorted(df_raw['Gender'].dropna().unique().tolist()) if 'Gender' in df_raw.columns else ["全部"]

sel_line = st.sidebar.selectbox("系列篩選", line_opt)
sel_cate = st.sidebar.selectbox("類型篩選", cate_opt)
sel_gend = st.sidebar.selectbox("性別篩選", gend_opt)
search_kw = st.sidebar.text_input("搜尋關鍵字")

# --- 6. 執行計算與過濾 ---
df = df_raw.copy()

df['10-15PCS'] = df.apply(lambda r: calc_price(r, '10-59', 300, 100, m1, rate), axis=1)
df['16-29PCS'] = df.apply(lambda r: calc_price(r, '10-59', 200, 62, m2, rate), axis=1)
df['30-59PCS'] = df.apply(lambda r: calc_price(r, '10-59', 150, 33, m3, rate), axis=1)

if sel_line != "全部": df = df[df['Line_code'] == sel_line]
if sel_cate != "全部": df = df[df['Category'] == sel_cate]
if sel_gend != "全部": df = df[df['Gender'] == sel_gend]
if search_kw: 
    df = df[
        df['Description_CH'].str.contains(search_kw, na=False, case=False) | 
        df['Item_No'].str.contains(search_kw, na=False)
    ]

# --- 7. 主畫面顯示 ---
st.title("🛡️ ALÉ 代理商專業報價系統")

if 'cart' not in st.session_state:
    st.session_state.cart = []

col_main, col_cart = st.columns([2, 1])

# === 左側：搜尋結果 ===
with col_main:
    st.subheader(f"📦 搜尋結果 ({len(df)} 筆)")
    if df.empty:
        st.info("查無產品")
    else:
        for _, row in df.head(50).iterrows():
            gender_label = f"({row['Gender']})" if 'Gender' in row and pd.notna(row['Gender']) else ""
            with st.expander(f"➕ {row['Item_No']} {gender_label} - {row['Description_CH']}"):
                
                # --- 圖片顯示區塊 (使用新邏輯) ---
                # 取得編號：優先用 pic code 欄位，沒有則用 Item_No
                code_1 = row['pic code_1'] if 'pic code_1' in row else row['Item_No']
                code_2 = row['pic code_2'] if 'pic code_2' in row else None
                
                path_front = find_image_robust(code_1)
                path_back = find_image_robust(code_2)

                if path_front and path_back:
                    c1, c2 = st.columns(2)
                    c1.image(path_front, caption="正面", use_container_width=True)
                    c2.image(path_back, caption="背面", use_container_width=True)
                elif path_front:
                    st.image(path_front, caption="正面", width=300)
                elif path_back:
                    st.image(path_back, caption="背面", width=300)
                else:
                    st.caption(f"🖼️ 無圖片 (嘗試搜尋: {code_1})")
                # ------------------------------

                # 顯示資訊
                note = row['NOTE'] if pd.notna(row['NOTE']) else "無"
                st.write(f"**備註：** {note}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("10-15pcs", f"${row['10-15PCS']:,}")
                c2.metric("16-29pcs", f"${row['16-29PCS']:,}")
                c3.metric("30-59pcs", f"${row['30-59PCS']:,}")
                
                st.button(
                    "加入報價單", 
                    key=f"btn_{row['Item_No']}",
                    on_click=add_to_cart_callback,
                    args=(row.to_dict(),)
                )

# === 右側：報價清單 ===
with col_cart:
    st.subheader(f"🛒 報價清單 ({len(st.session_state.cart)})")
    
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        
        display_cols = ['Item_No', 'Description_CH', '10-15PCS', '16-29PCS', '30-59PCS']
        valid_cols = [c for c in display_cols if c in cart_df.columns]
        
        st.dataframe(cart_df[valid_cols], use_container_width=True)

        # 匯出 Excel 功能
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                cart_df[valid_cols].to_excel(writer, index=False, sheet_name='報價單')
                worksheet = writer.sheets['報價單']
                worksheet.set_column('A:A', 15)
                worksheet.set_column('B:B', 30)
            
            excel_data = output.getvalue()

            st.download_button(
                label="📥 下載 Excel 報價單",
                data=excel_data,
                file_name="ALE_Quote.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Excel 匯出功能需安裝 xlsxwriter: {e}")

        st.divider()
        if st.button("🗑️ 清空全部"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("尚未選取任何產品")

# ==========================================
# 🛑 系統診斷區 (Debug Mode)
# ==========================================
st.divider()
with st.expander("🛠️ 系統診斷報告 (如果圖片沒出來請點我)"):
    st.write("檢查 images 資料夾狀態...")
    if os.path.exists("images"):
        st.success("✅ 'images' 資料夾存在！")
        files = os.listdir("images")
        st.write(f"📂 資料夾內共有 {len(files)} 個檔案")
        st.write("前 5 個檔案名稱：")
        st.code(files[:5])
    else:
        st.error("❌ 找不到 'images' 資料夾！請確認 GitHub 結構是否正確。")
        st.write("目前所在目錄的所有檔案：", os.listdir("."))
