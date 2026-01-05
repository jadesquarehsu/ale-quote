import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import quote
import os
import io  # 新增：用於處理 Excel 檔案匯出

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
        # 資料清理：確保重要欄位是字串格式，避免報錯
        if 'Item_No' in df.columns:
            df['Item_No'] = df['Item_No'].astype(str).str.strip()
        
        # 預先處理圖片欄位，轉為字串並去除空白
        for col in ['pic code_1', 'pic code_2']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            else:
                df[col] = "" # 如果 Google Sheet 沒這欄，就補空字串
                
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

# 回呼函數 (加入購物車)
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

# === 左側：搜尋結果 (含雙圖片顯示) ===
with col_main:
    st.subheader(f"📦 搜尋結果 ({len(df)} 筆)")
    if df.empty:
        st.info("查無產品")
    else:
        for _, row in df.head(50).iterrows():
            gender_label = f"({row['Gender']})" if 'Gender' in row and pd.notna(row['Gender']) else ""
            with st.expander(f"➕ {row['Item_No']} {gender_label} - {row['Description_CH']}"):
                
                # --- [圖片顯示區塊：讀取 pic code_1 和 pic code_2] ---
                # 1. 取得檔名 (處理 nan 或空值)
                img_name_1 = row['pic code_1'] if row['pic code_1'] != "nan" else ""
                img_name_2 = row['pic code_2'] if row['pic code_2'] != "nan" else ""

                # 2. 組合路徑
                path_1 = f"images/{img_name_1}" if img_name_1 else None
                path_2 = f"images/{img_name_2}" if img_name_2 else None

                # 3. 檢查是否存在
                has_img_1 = path_1 and os.path.exists(path_1)
                has_img_2 = path_2 and os.path.exists(path_2)

                # 4. 顯示邏輯
                if has_img_1 and has_img_2:
                    c_img1, c_img2 = st.columns(2)
                    with c_img1: st.image(path_1, caption="正面", use_container_width=True)
                    with c_img2: st.image(path_2, caption="背面", use_container_width=True)
                elif has_img_1:
                    st.image(path_1, caption="正面", width=300)
                elif has_img_2:
                    st.image(path_2, caption="背面", width=300)
                else:
                    # 如果兩個指定欄位都沒圖，嘗試舊方法 (用 Item_No 找)
                    old_png = f"images/{row['Item_No']}.png"
                    old_jpg = f"images/{row['Item_No']}.jpg"
                    if os.path.exists(old_png):
                        st.image(old_png, width=300)
                    elif os.path.exists(old_jpg):
                        st.image(old_jpg, width=300)
                # ---------------------------------------------------

                # 顯示資訊
                note = row['NOTE'] if pd.notna(row['NOTE']) else "無"
                st.write(f"**備註：** {note}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("10-15pcs", f"${row['10-15PCS']:,}")
                c2.metric("16-29pcs", f"${row['16-29PCS']:,}")
                c3.metric("30-59pcs", f"${row['30-59PCS']:,}")
                
                # 加入按鈕
                st.button(
                    "加入報價單", 
                    key=f"btn_{row['Item_No']}",
                    on_click=add_to_cart_callback,
                    args=(row.to_dict(),)
                )

# === 右側：報價清單 (含 Excel 下載) ===
with col_cart:
    st.subheader(f"🛒 報價清單 ({len(st.session_state.cart)})")
    
    if st.session_state.cart:
        # 將購物車轉為 DataFrame
        cart_df = pd.DataFrame(st.session_state.cart)
        
        # 整理要匯出的欄位
        display_cols = ['Item_No', 'Description_CH', '10-15PCS', '16-29PCS', '30-59PCS', 'NOTE']
        valid_cols = [c for c in display_cols if c in cart_df.columns]
        
        # 顯示簡易表格
        st.dataframe(cart_df[valid_cols], use_container_width=True)

        # --- 新增功能：匯出 Excel ---
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                cart_df[valid_cols].to_excel(writer, index=False, sheet_name='報價單')
                
                # 自動調整欄寬
                workbook = writer.book
                worksheet = writer.sheets['報價單']
                worksheet.set_column('A:A', 15) # 料號
                worksheet.set_column('B:B', 30) # 品名
                
            excel_data = output.getvalue()

            st.download_button(
                label="📥 下載 Excel 報價單",
                data=excel_data,
                file_name="ALE_Quote.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Excel 產生失敗: {e}，請確認已安裝 xlsxwriter 套件")

        st.divider()
        if st.button("🗑️ 清空全部"):
            st.session_state.cart = []
            st.rerun()

    else:
        st.info("尚未選取任何產品")
        # ==========================================
# 🕵️‍♂️ 圖片偵錯模式 (確認圖片修復後可刪除)
# ==========================================
st.divider()
st.header("🕵️‍♂️ 系統檢測報告")

folder_path = "images"

if os.path.exists(folder_path):
    file_list = os.listdir(folder_path)
    st.success(f"✅ 成功找到 'images' 資料夾！裡面共有 {len(file_list)} 個檔案。")
    
    st.write("👇 這是系統抓到的前 5 個檔名 (請檢查跟 Excel 裡的一不一樣)：")
    st.code(file_list[:5]) # 顯示前5個
    
    # 幫你檢查有沒有副檔名大小寫問題
    jpg_count = sum(1 for f in file_list if f.lower().endswith('.jpg'))
    png_count = sum(1 for f in file_list if f.lower().endswith('.png'))
    st.info(f"📊 統計：JPG 檔 {jpg_count} 個 / PNG 檔 {png_count} 個")
else:
    st.error(f"❌ 系統找不到 '{folder_path}' 資料夾！")
    st.warning("請確認 GitHub 上的資料夾名稱是否全小寫，且位於專案最外層。")
    # 印出當前目錄下有什麼，幫你找位置
    st.write("目前所在的目錄檔案有：", os.listdir("."))
