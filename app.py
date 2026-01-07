python
import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import quote
import os
import io
from PIL import Image
from datetime import datetime, timedelta

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="ALÉ 專業報價系統", page_icon="🚴", layout="wide")

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

# --- 5. 參數設定 (左側選單) ---
st.sidebar.success("✅ 已解鎖")
st.sidebar.markdown("---")

# 【新增功能】客戶資訊輸入區
st.sidebar.header("📝 客戶資訊 (填寫後會印在報價單)")
client_team = st.sidebar.text_input("隊名")
client_contact = st.sidebar.text_input("聯絡人")
client_phone = st.sidebar.text_input("電話")
client_address = st.sidebar.text_input("地址")

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

# --- 6. 執行計算與篩選 ---
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

# === Logo 顯示區塊 (網頁版) ===
logo_path_png = "images/logo-ale b.png"
logo_path_svg = "images/logo-ale b.svg"

final_logo_path = None
if os.path.exists(logo_path_png):
    final_logo_path = logo_path_png
elif os.path.exists(logo_path_svg):
    final_logo_path = logo_path_svg

if final_logo_path:
    c_logo, c_dummy = st.columns([1, 6])
    with c_logo:
        st.image(final_logo_path, width=200)

st.title("🛡️ 代理商專業報價系統")
st.divider()

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
        
        display_cols = ['Item_No', 'Description_CH', '10-15PCS']
        valid_cols = [c for c in display_cols if c in cart_df.columns]
        st.dataframe(cart_df[valid_cols], use_container_width=True)

        # 準備匯出 Excel
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                worksheet = workbook.add_worksheet('報價單')
                
                target_font = 'Noto Sans CJK TC' 
                
                # --- A. 定義格式 (Styles) ---
                fmt_title = workbook.add_format({
                    'bold': True, 'font_size': 20, 'align': 'center', 'valign': 'vcenter',
                    'font_name': target_font
                })
                fmt_date = workbook.add_format({
                    'bold': True, 'font_size': 12, 'align': 'right', 'valign': 'vcenter',
                    'font_name': target_font
                })
                # 客戶資訊 (自動換行，靠左)
                fmt_client_info = workbook.add_format({
                    'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter',
                    'font_name': target_font, 'text_wrap': False
                })
                fmt_header = workbook.add_format({
                    'bold': True, 'font_color': 'white', 'bg_color': '#2C3E50',
                    'align': 'center', 'valign': 'vcenter', 'border': 1,
                    'font_name': target_font
                })
                fmt_center = workbook.add_format({
                    'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'font_size': 11,
                    'font_name': target_font
                })
                fmt_left = workbook.add_format({
                    'align': 'left', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'font_size': 11,
                    'font_name': target_font
                })
                fmt_currency = workbook.add_format({
                    'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '$#,##0', 'font_size': 12, 'bold': True,
                    'font_name': target_font
                })
                fmt_footer = workbook.add_format({
                    'align': 'left', 'valign': 'top', 'text_wrap': True, 'font_size': 11,
                    'font_name': target_font
                })
                
                # --- B. 設定欄寬與列高參數 (修正: 正方形大格) ---
                # 36寬 x 180高 => 大約 250px x 240px 的正方形格子
                COL_WIDTH_EXCEL = 36  
                COL_WIDTH_PIXELS = 255
                
                ROW_HEIGHT_EXCEL = 180
                ROW_HEIGHT_PIXELS = 240
                
                worksheet.set_column('A:A', COL_WIDTH_EXCEL) 
                worksheet.set_column('B:B', 20)
                worksheet.set_column('C:C', 35)
                worksheet.set_column('D:F', 15)
                worksheet.set_column('G:G', 20)
                
                # --- C. 寫入頁首 (Header) ---
                
                worksheet.set_row(0, 20) # 頂部留白

                # Logo 獨立 (A2)
                logo_file = "images/logo-ale b.png"
                if os.path.exists(logo_file):
                    try:
                        with Image.open(logo_file) as img:
                            w, h = img.size
                            target_h = 75
                            scale = target_h / h
                            worksheet.insert_image('A2', logo_file, {
                                'x_scale': scale, 'y_scale': scale,
                                'x_offset': 5, 'y_offset': 5
                            })
                    except:
                        pass
                
                worksheet.set_row(1, 65) 

                # 標題 (B2:G2)
                worksheet.merge_range('B2:G2', 'ALÉ 訂製車衣報價單', fmt_title)
                
                # 報價日期 (A3:G3)
                quote_date_str = datetime.now().strftime("%Y/%m/%d")
                worksheet.merge_range('A3:G3', f"報價日期：{quote_date_str}", fmt_date)
                
                # 空白行
                worksheet.set_row(3, 10)
                
                # 【新功能】填入客戶資訊 (如果有輸入就填入，沒有就留底線)
                t_team = client_team if client_team else "__________________________________"
                t_contact = client_contact if client_contact else "____________________"
                t_phone = client_phone if client_phone else "__________________________________"
                t_addr = client_address if client_address else "___________________________________________"

                worksheet.write('A5', f'隊名：{t_team}', fmt_client_info)
                worksheet.write('C5', f'聯絡人：{t_contact}', fmt_client_info)
                
                # 空白行 (手寫行距)
                worksheet.set_row(5, 25)

                worksheet.write('A7', f'電話：{t_phone}', fmt_client_info)
                worksheet.write('C7', f'地址：{t_addr}', fmt_client_info)

                worksheet.set_row(7, 20)
                
                # --- D. 寫入表格 ---
                start_row = 8
                headers = ['產品圖片', '型號', '中文品名', '10-15PCS', '16-29PCS', '30-59PCS', '備註']
                for col_num, header in enumerate(headers):
                    worksheet.write(start_row, col_num, header, fmt_header)
                
                current_row = start_row + 1
                
                for i, item in enumerate(st.session_state.cart):
                    # 設定列高
                    worksheet.set_row(current_row, ROW_HEIGHT_EXCEL)
                    
                    # 1. 圖片處理 (強制滿版)
                    p_code = item.get('pic code_1', '')
                    if not p_code or str(p_code) == 'nan':
                        p_code = item.get('Item_No', '')
                        
                    img_path = find_image_robust(p_code)
                    
                    if img_path:
                        try:
                            with Image.open(img_path) as im:
                                orig_w, orig_h = im.size
                                
                                # 設定目標尺寸 (撐滿格線 98%)
                                target_w = COL_WIDTH_PIXELS * 0.98
                                target_h = ROW_HEIGHT_PIXELS * 0.98
                                
                                ratio_w = target_w / orig_w
                                ratio_h = target_h / orig_h
                                
                                # 使用較小的比例，確保完整放入
                                scale = min(ratio_w, ratio_h)
                                
                                final_w = orig_w * scale
                                final_h = orig_h * scale
                                
                                # 絕對置中
                                x_off = (COL_WIDTH_PIXELS - final_w) / 2
                                y_off = (ROW_HEIGHT_PIXELS - final_h) / 2
                                
                                worksheet.insert_image(current_row, 0, img_path, {
                                    'x_scale': scale, 
                                    'y_scale': scale,
                                    'x_offset': x_off, 
                                    'y_offset': y_off,
                                    'object_position': 1
                                })
                        except:
                            worksheet.write(current_row, 0, "圖片錯誤", fmt_center)
                    else:
                        worksheet.write(current_row, 0, "無圖片", fmt_center)

                    # 2. 文字資料
                    worksheet.write(current_row, 1, item.get('Item_No', ''), fmt_center)
                    worksheet.write(current_row, 2, item.get('Description_CH', ''), fmt_left)
                    
                    def get_price(key):
                        try: return float(item.get(key, 0))
                        except: return 0
                        
                    worksheet.write(current_row, 3, get_price('10-15PCS'), fmt_currency)
                    worksheet.write(current_row, 4, get_price('16-29PCS'), fmt_currency)
                    worksheet.write(current_row, 5, get_price('30-59PCS'), fmt_currency)
                    
                    note_txt = item.get('NOTE', '')
                    if pd.isna(note_txt): note_txt = ""
                    worksheet.write(current_row, 6, str(note_txt), fmt_center)
                    
                    current_row += 1

                # --- E. 寫入頁尾 (Footer) ---
                footer_row = current_row + 1
                valid_date = (datetime.now() + timedelta(days=30)).strftime("%Y/%m/%d")
                
                # 依指示更新文字與格式
                terms = (
                    f"▶ 報價已含 5% 營業稅\n"
                    f"▶ 報價有效期限：{valid_date}\n"
                    f"▶ 提供尺寸套量，預付套量押金 NT 5,000 元，退回套量後押金會退還或是轉作訂製訂金。\n\n"
                    f"【匯款資訊】\n"
                    f"銀行：彰化銀行 (代碼 009) 北屯分行\n"
                    f"帳號：4028-8601-6895-00\n"
                    f"戶名：禾宏文化資訊有限公司\n\n"
                    f"--------------------------------------------------\n"
                    f"禾宏文化資訊有限公司 | 聯絡人：徐郁芳 | TEL: 04-24369368 ext19 | Email: uma@hehong.com.tw"
                )
                
                worksheet.set_row(footer_row, 250) 
                worksheet.merge_range(footer_row, 0, footer_row, 6, terms, fmt_footer)

            excel_data = output.getvalue()

            st.download_button(
                label="📥 下載 Excel 報價單 (含客戶資訊)",
                data=excel_data,
                file_name="ALE_Quote.xlsx",
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
with st.expander("🛠️ 系統診斷報告 (Debug)"):
    if os.path.exists("images"):
        st.success("✅ 'images' 資料夾存在")
        has_png = os.path.exists("images/logo-ale b.png")
        if has_png: st.success("✅ PNG Logo (logo-ale b.png) 存在")
    else:
        st.error("❌ 找不到 'images' 資料夾！")

```
