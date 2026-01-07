import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import quote
import os
import io
from PIL import Image # 用來讀取圖片尺寸，進行完美縮放

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
        if 'Item_No' in df.columns:
            df['Item_No'] = df['Item_No'].astype(str).str.strip()
        
        for col in ['pic code_1', 'pic code_2']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            else:
                df[col] = "" 
                
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

# 找圖功能的強力邏輯
def find_image_robust(filename):
    if not filename or str(filename).lower() == "nan" or str(filename).strip() == "":
        return None
    
    clean_name = str(filename).strip()
    base_name = clean_name
    if "." in clean_name:
        base_name = clean_name.rsplit('.', 1)[0]
    
    candidates = [
        clean_name,
        f"{clean_name}.png", f"{clean_name}.PNG",
        f"{clean_name}.jpg", f"{clean_name}.JPG",
        f"{base_name}.png", f"{base_name}.PNG",
        f"{base_name}.jpg", f"{base_name}.JPG"
    ]
    
    for c in candidates:
        path = f"images/{c}"
        if os.path.exists(path):
            return path
            
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

# --- 5. 參數設定 ---
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

# --- 6. 執行計算 ---
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

# --- 7. 主畫面 ---
st.title("🛡️ ALÉ 代理商專業報價系統")

if 'cart' not in st.session_state:
    st.session_state.cart = []

col_main, col_cart = st.columns([2, 1])

# === 左側 ===
with col_main:
    st.subheader(f"📦 搜尋結果 ({len(df)} 筆)")
    if df.empty:
        st.info("查無產品")
    else:
        for _, row in df.head(50).iterrows():
            gender_label = f"({row['Gender']})" if 'Gender' in row and pd.notna(row['Gender']) else ""
            with st.expander(f"➕ {row['Item_No']} {gender_label} - {row['Description_CH']}"):
                
                # --- 圖片顯示 ---
                code_1 = row['pic code_1'] if 'pic code_1' in row else row['Item_No']
                code_2 = row['pic code_2'] if 'pic code_2' in row else None
                
                path_front = find_image_robust(code_1)
                path_back = find_image_robust(code_2)

                if path_front and path_back:
                    c1, c2 = st.columns(2)
                    c1.image(path_front, caption="正面", use_column_width=True)
                    c2.image(path_back, caption="背面", use_column_width=True)
                elif path_front:
                    st.image(path_front, caption="正面", width=300)
                elif path_back:
                    st.image(path_back, caption="背面", width=300)
                else:
                    st.caption(f"🖼️ 無圖片 (嘗試搜尋: {code_1})")
                
                note = row['NOTE'] if pd.notna(row['NOTE']) else "無"
                st.write(f"**備註：** {note}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("10-15pcs", f"${row['10-15PCS']:,}")
                c2.metric("16-29pcs", f"${row['16-29PCS']:,}")
                c3.metric("30-59pcs", f"${row['30-59PCS']:,}")
                
                st.button("加入報價單", key=f"btn_{row['Item_No']}", on_click=add_to_cart_callback, args=(row.to_dict(),))

# === 右側：進階 Excel 匯出功能 ===
with col_cart:
    st.subheader(f"🛒 報價清單 ({len(st.session_state.cart)})")
    
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        
        # 網頁上的簡易顯示
        display_cols = ['Item_No', 'Description_CH', '10-15PCS']
        valid_cols = [c for c in display_cols if c in cart_df.columns]
        st.dataframe(cart_df[valid_cols], use_container_width=True)

        # 準備匯出 Excel
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                worksheet = workbook.add_worksheet('報價單')
                
                # --- 定義美化格式 ---
                # 標題列格式：深藍底、白字、加粗、置中
                fmt_header = workbook.add_format({
                    'bold': True, 'font_color': 'white', 'bg_color': '#2C3E50',
                    'align': 'center', 'valign': 'vcenter', 'border': 1
                })
                # 一般文字格式：置中、邊框
                fmt_center = workbook.add_format({
                    'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True
                })
                # 金額格式：金錢符號、無小數點
                fmt_currency = workbook.add_format({
                    'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '$#,##0'
                })
                
                # --- 設定欄寬 ---
                worksheet.set_column('A:A', 18) # 圖片欄 (寬一點)
                worksheet.set_column('B:B', 20) # 型號
                worksheet.set_column('C:C', 35) # 品名 (最寬)
                worksheet.set_column('D:F', 15) # 價格欄位
                worksheet.set_column('G:G', 20) # 備註
                
                # --- 寫入標題列 ---
                headers = ['產品圖片', '型號', '中文品名', '10-15PCS', '16-29PCS', '30-59PCS', '備註']
                for col_num, header in enumerate(headers):
                    worksheet.write(0, col_num, header, fmt_header)
                
                # --- 逐筆寫入資料與圖片 ---
                # 設定圖片目標大小 (像素)
                TARGET_SIZE = 110 
                
                for i, item in enumerate(st.session_state.cart):
                    row_num = i + 1
                    # 設定列高 (為了放圖片，設高一點，單位是 points)
                    worksheet.set_row(row_num, 90)
                    
                    # 1. 處理圖片插入
                    # 優先找正面圖，沒有則找 Item_No
                    p_code = item.get('pic code_1', '')
                    if not p_code or str(p_code) == 'nan':
                        p_code = item.get('Item_No', '')
                        
                    img_path = find_image_robust(p_code)
                    
                    if img_path:
                        try:
                            # 讀取圖片原始大小來計算縮放比例
                            with Image.open(img_path) as im:
                                orig_w, orig_h = im.size
                                # 計算縮放比例，讓圖片塞進 110x110 的框框內
                                x_scale = TARGET_SIZE / orig_w
                                y_scale = TARGET_SIZE / orig_h
                                final_scale = min(x_scale, y_scale) # 維持長寬比
                                
                                worksheet.insert_image(row_num, 0, img_path, {
                                    'x_scale': final_scale, 
                                    'y_scale': final_scale,
                                    'x_offset': 5, 'y_offset': 5, # 留一點邊距
                                    'object_position': 1 # 隨儲存格移動
                                })
                        except:
                            worksheet.write(row_num, 0, "圖片錯誤", fmt_center)
                    else:
                        worksheet.write(row_num, 0, "無圖片", fmt_center)

                    # 2. 寫入文字資料
                    worksheet.write(row_num, 1, item.get('Item_No', ''), fmt_center)
                    worksheet.write(row_num, 2, item.get('Description_CH', ''), fmt_center)
                    
                    # 3. 寫入價格 (確保是數字，否則會變文字無法加總)
                    def get_price(key):
                        try: return float(item.get(key, 0))
                        except: return 0
                        
                    worksheet.write(row_num, 3, get_price('10-15PCS'), fmt_currency)
                    worksheet.write(row_num, 4, get_price('16-29PCS'), fmt_currency)
                    worksheet.write(row_num, 5, get_price('30-59PCS'), fmt_currency)
                    
                    note_txt = item.get('NOTE', '')
                    if pd.isna(note_txt): note_txt = ""
                    worksheet.write(row_num, 6, str(note_txt), fmt_center)

            excel_data = output.getvalue()

            st.download_button(
                label="📥 下載 Excel 報價單 (含圖片)",
                data=excel_data,
                file_name="ALE_Quote_With_Images.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Excel 匯出失敗: {e}")

        st.divider()
        if st.button("🗑️ 清空全部"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("尚未選取任何產品")

# ==========================================
# 🛑 系統診斷區
# ==========================================
st.divider()
with st.expander("🛠️ 系統診斷報告"):
    if os.path.exists("images"):
        st.success("✅ 'images' 資料夾存在！")
    else:
        st.error("❌ 找不到 'images' 資料夾！")
