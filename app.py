# ========================================================
                # 👇 超級容錯版：自動解決 .PNG/.png 大小寫問題
                # ========================================================
                
                def find_image_robust(filename):
                    if not filename or str(filename) == "nan": return None
                    clean_name = str(filename).strip()
                    
                    # 先把檔名和副檔名分開 (如果有)
                    base_name = clean_name
                    if "." in clean_name:
                        base_name = clean_name.rsplit('.', 1)[0]
                    
                    # 建立所有可能的檔名組合
                    candidates = [
                        clean_name,                     # 原始檔名
                        f"{clean_name}.png",            # 加小寫 png
                        f"{clean_name}.PNG",            # 加大寫 PNG
                        f"{clean_name}.jpg",            # 加小寫 jpg
                        f"{clean_name}.JPG",            # 加大寫 JPG
                        f"{base_name}.png",             # 去掉舊副檔名，加小寫 png
                        f"{base_name}.PNG"              # 去掉舊副檔名，加大寫 PNG
                    ]
                    
                    # 一個一個試，看哪個檔案真的存在
                    for c in candidates:
                        path = f"images/{c}"
                        if os.path.exists(path):
                            return path # 找到了！
                            
                    return None

                # 1. 執行搜尋
                code_1 = row['pic code_1'] if 'pic code_1' in row else row['Item_No']
                code_2 = row['pic code_2'] if 'pic code_2' in row else None
                
                path_front = find_image_robust(code_1)
                path_back = find_image_robust(code_2)

                # 2. 顯示圖片
                if path_front and path_back:
                    c1, c2 = st.columns(2)
                    c1.image(path_front, caption="正面", use_container_width=True)
                    c2.image(path_back, caption="背面", use_container_width=True)
                elif path_front:
                    st.image(path_front, caption="正面", width=300)
                elif path_back:
                    st.image(path_back, caption="背面", width=300)
                else:
                    # 還是找不到時，顯示一個灰底文字
                    st.caption(f"🖼️ 無法載入: {code_1}")
                
                # ========================================================
