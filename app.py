import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import quote
import os
import io
import base64
from PIL import Image
from datetime import datetime, timedelta

# --- 1. 網頁基本設定 ---
favicon = "images/hh.svg" if os.path.exists("images/hh.svg") else "🚴"

st.set_page_config(
    page_title="ALÉ 專業報價系統", 
    page_icon=favicon, 
    layout="wide"
)

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
        
        # 確保讀取 code_1 和 code_2
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

# 圖片預處理：強制大小 + 透明轉白底 (Excel 與 HTML 共用)
def process_image(image_path, max_width=None, max_height=None):
    try:
        with Image.open(image_path) as img:
            # 1. 處理透明背景 -> 轉為白底
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGBA')
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 2. 如果有指定大小，進行縮放
            if max_width and max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # 3. 存入記憶體
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            
            return output, img.width, img.height
    except Exception:
        return None, 0, 0

# 將記憶體中的圖片轉為 Base64 字串 (給 HTML 顯示用)
def buffer_to_b64(buffer):
    return base64.b64encode(buffer.getvalue()).decode()

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

st.sidebar.header("📝 客戶資訊")
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

if 'cart' not in st.session_state:
    st.session_state.cart = []

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

col_main, col_cart = st.columns([2, 1])

# === 左側：搜尋結果 (修正：加入正面與背面圖片) ===
with col_main:
    st.subheader(f"📦 搜尋結果 ({len(df)} 筆)")
    
    if df.empty:
        st.info("查無產品")
    else:
        for _, row in df.head(50).iterrows():
            gender_label = f"({row['Gender']})" if 'Gender' in row and pd.notna(row['Gender']) else ""
            with st.expander(f"➕ {row['Item_No']} {gender_label} - {row['Description_CH']}"):
                
                # 讀取正面和背面代碼
                code_1 = row['pic code_1'] if 'pic code_1' in row else row['Item_No']
                code_2 = row['pic code_2'] if 'pic code_2' in row else None
                
                # 尋找圖片路徑
                path_front = find_image_robust(code_1)
                path_back = find_image_robust(code_2)

                # 顯示邏輯：如果有兩張就並排，只有一張就單獨顯示
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

# === 右側：報價單區 ===
with col_cart:
    st.subheader(f"🛒 報價清單 ({len(st.session_state.cart)})")
    
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        
        display_cols = ['Item_No', 'Description_CH', '10-15PCS']
        valid_cols = [c for c in display_cols if c in cart_df.columns]
        st.dataframe(cart_df[valid_cols], use_container_width=True)

        # -------------------------------------------
        # 功能 1：Excel 匯出
        # -------------------------------------------
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                worksheet = workbook.add_worksheet('報價單')
                worksheet.hide_gridlines(2)
                target_font = 'Noto Sans CJK TC' 
                
                fmt_title = workbook.add_format({'bold': True, 'font_size': 28, 'align': 'center', 'valign': 'vcenter', 'font_name': target_font})
                fmt_date = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'right', 'valign': 'vcenter', 'font_name': target_font})
                fmt_client_label = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'left', 'valign': 'vcenter', 'font_name': target_font})
                fmt_client_val = workbook.add_format({'bold': False, 'font_size': 16, 'align': 'left', 'valign': 'vcenter', 'font_name': target_font})
                fmt_client_base = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'font_name': target_font, 'font_size': 16})
                fmt_header = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#2C3E50', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': target_font})
                fmt_center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'font_size': 12, 'font_name': target_font})
                fmt_left = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'font_size': 12, 'font_name': target_font})
                fmt_currency = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '$#,##0', 'font_size': 12, 'bold': True, 'font_name': target_font})
                fmt_footer = workbook.add_format({'align': 'left', 'valign': 'top', 'text_wrap': True, 'font_size': 11, 'font_name': target_font})
                
                COL_WIDTH_EXCEL, CELL_W_PX = 26, 190
                ROW_HEIGHT_EXCEL, CELL_H_PX = 150, 200
                
                worksheet.set_column('A:A', COL_WIDTH_EXCEL) 
                worksheet.set_column('B:B', 20)
                worksheet.set_column('C:C', 35)
                worksheet.set_column('D:F', 15)
                worksheet.set_column('G:G', 20)
                
                worksheet.set_row(0, 20) 
                header_row_height = 100
                worksheet.set_row(1, header_row_height) 
                logo_file = "images/logo-ale b.png"
                if os.path.exists(logo_file):
                    logo_target_h = 80
                    logo_img_buffer, w, h = process_image(logo_file, 500, logo_target_h)
                    if logo_img_buffer:
                        y_offset = (133 - h) / 2 
                        worksheet.insert_image('A2', logo_file, {'image_data': logo_img_buffer, 'x_offset': 10, 'y_offset': y_offset})

                worksheet.merge_range('B2:G2', 'ALÉ 訂製車衣報價單', fmt_title)
                quote_date_str = datetime.now().strftime("%Y/%m/%d")
                worksheet.merge_range('A3:G3', f"報價日期：{quote_date_str}", fmt_date)
                worksheet.set_row(3, 10)
                
                t_team = client_team if client_team else "________________________"
                t_contact = client_contact if client_contact else "____________"
                t_phone = client_phone if client_phone else "________________________"
                t_addr = client_address if client_address else "_________________________________"

                worksheet.write_rich_string('A5', fmt_client_label, "隊名：", fmt_client_val, t_team, fmt_client_base)
                worksheet.write_rich_string('C5', fmt_client_label, "聯絡人：", fmt_client_val, t_contact, fmt_client_base)
                worksheet.set_row(5, 30)
                worksheet.write_rich_string('A7', fmt_client_label, "電話：", fmt_client_val, t_phone, fmt_client_base)
                worksheet.write_rich_string('C7', fmt_client_label, "地址：", fmt_client_val, t_addr, fmt_client_base)
                worksheet.set_row(7, 20)
                
                start_row = 8
                worksheet.set_row(start_row, 30)
                headers = ['產品圖片', '型號', '中文品名', '10-15PCS', '16-29PCS', '30-59PCS', '備註']
                for col_num, header in enumerate(headers):
                    worksheet.write(start_row, col_num, header, fmt_header)
                
                current_row = start_row + 1
                for i, item in enumerate(st.session_state.cart):
                    worksheet.set_row(current_row, ROW_HEIGHT_EXCEL)
                    worksheet.write_blank(current_row, 0, "", fmt_center)
                    p_code = item.get('pic code_1', '')
                    if not p_code or str(p_code) == 'nan': p_code = item.get('Item_No', '')
                    img_path = find_image_robust(p_code)
                    if img_path:
                        # 強制圖片 180x180 並去背轉白底
                        img_buffer, final_w, final_h = process_image(img_path, 180, 180)
                        if img_buffer:
                            x_off = (CELL_W_PX - final_w) / 2
                            y_off = (CELL_H_PX - final_h) / 2
                            worksheet.insert_image(current_row, 0, "img.png", {'image_data': img_buffer, 'x_offset': x_off, 'y_offset': y_off, 'object_position': 1})
                        else: worksheet.write(current_row, 0, "圖片錯誤", fmt_center)
                    else: worksheet.write(current_row, 0, "無圖片", fmt_center)

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

                footer_row = current_row + 1
                valid_date = (datetime.now() + timedelta(days=30)).strftime("%Y/%m/%d")
                terms = (f"▶ 報價已含 5% 營業稅\n▶ 報價有效期限：{valid_date}\n▶ 提供尺寸套量，預付套量押金 NT 5,000 元，退回套量後押金會退還或是轉作訂製訂金。\n\n【匯款資訊】\n銀行：彰化銀行 (代碼 009) 北屯分行\n帳號：4028-8601-6895-00\n戶名：禾宏文化資訊有限公司\n\n--------------------------------------------------\n禾宏文化資訊有限公司 | 聯絡人：徐郁芳 | TEL: 04-24369368 ext19 | Email: uma@hehong.com.tw")
                worksheet.set_row(footer_row, 250) 
                worksheet.merge_range(footer_row, 0, footer_row, 6, terms, fmt_footer)

            excel_data = output.getvalue()
            st.download_button(label="📥 下載 Excel 報價單", data=excel_data, file_name="ALE_Quote.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        except Exception as e:
            st.error(f"Excel 匯出失敗: {e}")

        # -------------------------------------------
        # 功能 2：網頁列印預覽 (Print to PDF)
        # -------------------------------------------
        st.divider()
        if st.button("📄 產生 PDF / 列印專用頁面"):
            # 準備 Logo (轉為白底+Base64)
            logo_b64 = ""
            if os.path.exists("images/logo-ale b.png"):
                logo_buf, _, _ = process_image("images/logo-ale b.png", 500, 80)
                if logo_buf:
                    logo_b64 = buffer_to_b64(logo_buf)

            date_str = datetime.now().strftime("%Y/%m/%d")
            valid_date = (datetime.now() + timedelta(days=30)).strftime("%Y/%m/%d")
            
            # 建立表格列的 HTML
            table_rows_html = ""
            for item in st.session_state.cart:
                # 處理圖片: 轉白底 -> 轉 Base64
                p_code = item.get('pic code_1', '')
                if not p_code or str(p_code) == 'nan': p_code = item.get('Item_No', '')
                img_path = find_image_robust(p_code)
                
                img_html = ""
                if img_path:
                    # 強制轉為白底圖片，確保列印時無灰底
                    img_buf, _, _ = process_image(img_path, 300, 300)
                    if img_buf:
                        img_b64 = buffer_to_b64(img_buf)
                        img_html = f'<img src="data:image/png;base64,{img_b64}" class="product-img">'
                
                # 處理價格
                def fmt_p(val):
                    try: return f"${float(val):,.0f}"
                    except: return "$0"

                table_rows_html += f"""
                    <tr>
                        <td>{img_html}</td>
                        <td>{item.get('Item_No', '')}</td>
                        <td style="text-align: left;">{item.get('Description_CH', '')}</td>
                        <td>{fmt_p(item.get('10-15PCS'))}</td>
                        <td>{fmt_p(item.get('16-29PCS'))}</td>
                        <td>{fmt_p(item.get('30-59PCS'))}</td>
                        <td>{item.get('NOTE', '') if pd.notna(item.get('NOTE')) else ''}</td>
                    </tr>
                """

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif; padding: 40px; color: #000; }}
    .header-table {{ width: 100%; margin-bottom: 20px; }}
    .logo {{ height: 80px; }}
    .title {{ font-size: 28px; font-weight: bold; text-align: center; }}
    .date {{ text-align: right; font-weight: bold; font-size: 14px; vertical-align: bottom; }}
    .info-table {{ width: 100%; margin-bottom: 20px; font-size: 16px; border-collapse: collapse; }}
    .info-table td {{ padding: 5px 0; }}
    .info-label {{ font-weight: bold; width: 80px; vertical-align: top; }}
    .info-val {{ border-bottom: 1px solid #ccc; padding-right: 20px; }}
    .quote-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 20px; }}
    .quote-table th {{ background-color: #2C3E50; color: white; padding: 10px; border: 1px solid #000; text-align: center; }}
    .quote-table td {{ border: 1px solid #000; padding: 10px; text-align: center; vertical-align: middle; }}
    .product-img {{ width: 150px; height: auto; display: block; margin: 0 auto; }}
    .footer {{ margin-top: 30px; font-size: 12px; line-height: 1.6; white-space: pre-line; }}
    
    @media print {{ 
        .no-print {{ display: none; }} 
        body {{ -webkit-print-color-adjust: exact; padding: 0; }}
        .quote-table th {{ background-color: #2C3E50 !important; color: white !important; }}
    }}
</style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 20px; padding: 15px; background: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; text-align: center;">
        ⚠️ <b>列印說明：</b> 請按 <b>Ctrl + P</b> (Mac: Cmd + P) 開啟列印視窗，目的地選擇 <b>「另存為 PDF」</b>。
        <br>若沒看到背景色，請在列印設定中勾選 <b>「背景圖形」</b>。
    </div>
    
    <table class="header-table">
        <tr>
            <td width="20%"><img src="data:image/png;base64,{logo_b64}" class="logo"></td>
            <td class="title">ALÉ 訂製車衣報價單</td>
            <td width="20%" class="date">報價日期：{date_str}</td>
        </tr>
    </table>

    <table class="info-table">
        <tr>
            <td class="info-label">隊名：</td><td class="info-val">{client_team}</td>
            <td width="20"></td>
            <td class="info-label">聯絡人：</td><td class="info-val">{client_contact}</td>
        </tr>
        <tr><td colspan="5" style="height: 10px;"></td></tr>
        <tr>
            <td class="info-label">電話：</td><td class="info-val">{client_phone}</td>
            <td></td>
            <td class="info-label">地址：</td><td class="info-val">{client_address}</td>
        </tr>
    </table>

    <table class="quote-table">
        <thead>
            <tr>
                <th width="20%">產品圖片</th>
                <th width="15%">型號</th>
                <th width="25%">中文品名</th>
                <th width="10%">10-15PCS</th>
                <th width="10%">16-29PCS</th>
                <th width="10%">30-59PCS</th>
                <th width="10%">備註</th>
            </tr>
        </thead>
        <tbody>
            {table_rows_html}
        </tbody>
    </table>

    <div class="footer">▶ 報價已含 5% 營業稅
▶ 報價有效期限：{valid_date}
▶ 提供尺寸套量，預付套量押金 NT 5,000 元，退回套量後押金會退還或是轉作訂製訂金。

<b>【匯款資訊】</b>
銀行：彰化銀行 (代碼 009) 北屯分行
帳號：4028-8601-6895-00
戶名：禾宏文化資訊有限公司

--------------------------------------------------
禾宏文化資訊有限公司 | 聯絡人：徐郁芳 | TEL: 04-24369368 ext19 | Email: uma@hehong.com.tw</div>
</body>
</html>
"""
            st.markdown(html_content, unsafe_allow_html=True)

        st.divider()
        if st.button("🗑️ 清空全部"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("尚未選取任何產品")

st.divider()
with st.expander("🛠️ 系統診斷報告"):
    if os.path.exists("images"):
        st.success("✅ 'images' 資料夾存在")
    else:
        st.error("❌ 找不到 'images' 資料夾！")
