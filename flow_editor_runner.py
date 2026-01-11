# -*- coding: utf-8 -*-
"""
Flow Editor Runner - Ultra Robust Version (v11 - HTML Specific Fix)
---------------------------------------
Perbaikan Kritis:
1. FIX Delete Button Selector: Menggunakan 'opsi lainnya' dan 'more_vert' sesuai HTML user.
2. Fix 720p Download: Menangani menu pop-up resolusi.
3. Settings Timeout Fix: Lebih tahan banting saat setelan lambat loading.
4. Aggressive Cleanup: Memastikan canvas bersih dari card sisa.
"""

import os
import re
import time
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

BROWSER_FLAGS = [
    "--window-size=1920,1080",
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-web-security",
    "--allow-running-insecure-content",
    "--disable-features=IsolateOrigins,site-per-process,Translate,TranslateUI",
    "--disable-translate",
    "--no-default-browser-check",
    "--disable-features=DownloadBubble,DownloadBubbleV2",
    "--disable-gpu",
]

class FlowEditorRunner:
    def __init__(self, **kwargs):
        self.email = kwargs.get('email', "")
        self.password = kwargs.get('password', "")
        self.extensions_root = os.path.abspath(kwargs.get('extensions_root'))
        self.user_data_dir = os.path.abspath(kwargs.get('user_data_dir'))
        self.download_dir = os.path.abspath(kwargs.get('download_dir'))
        self.headless = kwargs.get('headless', False)
        self.account_idx = kwargs.get('start_account_index', 8)
        self.timeout_ms = kwargs.get('timeout_ms', 180000)
        self.log = kwargs.get('log_fn', print)
        self.context = None
        self.popup_page = None 
        self.dashboard_page = None 
        self.playwright = None
        self.editor_retry_count = 0
        self.current_zoom = 1.0

    def start_context(self):
        os.makedirs(self.user_data_dir, exist_ok=True)
        os.makedirs(self.download_dir, exist_ok=True)
        
        ext_paths = [os.path.join(self.extensions_root, d) 
                     for d in os.listdir(self.extensions_root) 
                     if os.path.isdir(os.path.join(self.extensions_root, d))]
        
        load_arg = ",".join(ext_paths)
        args = [f"--disable-extensions-except={load_arg}", 
                f"--load-extension={load_arg}"] + BROWSER_FLAGS
        
        self.log("🌐 Memulai Browser (Ultra Robust Mode)...")
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir, 
            headless=self.headless, 
            args=args,
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True,
            ignore_https_errors=True
        )
        
        def handle_download(download):
            try:
                save_path = os.path.join(self.download_dir, download.suggested_filename)
                download.save_as(save_path)
                self.log(f"✅ Download: {download.suggested_filename}")
            except Exception as e:
                self.log(f"⚠️ Download failed: {e}")
        
        self.context.on("download", handle_download)
        return self.context

    def kill_all_modals(self, page):
        """Aggressive modal/overlay killer"""
        try:
            page.on("dialog", lambda dialog: dialog.dismiss())
            for _ in range(5):
                page.keyboard.press("Escape")
                time.sleep(0.3)
            
            overlay_selectors = [
                "[role='dialog']", ".modal", ".overlay", "[class*='popup']", 
                "[class*='tooltip']", ".MuiDialog-root", "[data-testid*='modal']"
            ]
            
            for selector in overlay_selectors:
                try:
                    page.evaluate(f"document.querySelectorAll('{selector}').forEach(el => {{ el.remove(); }});")
                except:
                    pass
            time.sleep(1)
        except Exception as e:
            self.log(f"⚠️ Modal killer warning: {e}")

    def set_adaptive_zoom(self, page, zoom_level=0.8):
        try:
            page.evaluate(f"document.body.style.zoom = '{zoom_level}'")
            self.current_zoom = zoom_level
            self.log(f"🔍 Zoom set to {int(zoom_level*100)}%")
            time.sleep(0.5)
        except Exception as e:
            self.log(f"⚠️ Zoom setting failed: {e}")

    def open_extension_popup(self):
        if self.popup_page and not self.popup_page.is_closed():
            self.popup_page.bring_to_front()
            return self.popup_page

        ext_id = None
        for attempt in range(30):
            for worker in self.context.service_workers:
                if "chrome-extension://" in worker.url: 
                    ext_id = worker.url.split("/")[2]
                    break
            if ext_id: 
                break
            time.sleep(0.5)
        
        if not ext_id:
            raise RuntimeError("❌ Extension ID tidak terdeteksi setelah 30 detik")
        
        self.popup_page = self.context.new_page()
        self.popup_page.goto(f"chrome-extension://{ext_id}/popup.html", 
                             wait_until="domcontentloaded", timeout=30000)
        return self.popup_page

    def handle_login_prompt_if_any(self):
        """Smart Login: Cek apakah sudah login (ada list akun) sebelum mencoba login."""
        try:
            self.open_extension_popup()
            
            # Cek apakah sudah ada list akun (artinya sudah login)
            if self.popup_page.locator(".account-item").first.is_visible(timeout=3000):
                self.log("✅ Sudah login di Extension (Account List Detected). Skip login.")
                return

            # Jika belum, cari tombol login
            login_btn = self.popup_page.locator("button:has-text('LOGIN TO NEXABOT')").first
            if login_btn.is_visible(timeout=3000):
                self.log("🔐 Melakukan Login Nexabot...")
                with self.context.expect_page(timeout=60000) as info: 
                    login_btn.click(force=True)
                
                lp = info.value
                lp.wait_for_load_state("domcontentloaded")
                lp.fill("#email", self.email)
                lp.keyboard.press("Enter")
                lp.wait_for_selector("#password", timeout=30000)
                lp.fill("#password", self.password)
                lp.keyboard.press("Enter")
                time.sleep(8)
                lp.close()
                self.log("✅ Login completed")
        except Exception as e:
            self.log(f"ℹ️ Login prompt check: {e}")

    def launch_flow_dashboard(self, account_idx: int):
        self.open_extension_popup()
        try:
            self.popup_page.wait_for_selector(".account-item", timeout=30000)
            target = str(account_idx)
            
            sel = self.popup_page.locator(".account-item").filter(
                has=self.popup_page.locator(".account-num", has_text=re.compile(f"^{target}$"))
            ).first
            
            if not sel.is_visible(timeout=2000):
                self.log(f"⚠️ Account {account_idx} not found, using first available")
                sel = self.popup_page.locator(".account-item").first
            
            sel.click(force=True)
            time.sleep(2)
            
            with self.context.expect_page(timeout=60000) as info:
                self.popup_page.locator("button:has-text('Launch')").click(force=True)
            
            self.dashboard_page = info.value
            self.dashboard_page.wait_for_load_state("domcontentloaded")
            self.log(f"📄 Dashboard opened (Account {account_idx})")
            return self.dashboard_page
            
        except Exception as e:
            self.log(f"❌ Launch Dashboard failed: {e}")
            return None

    def rotate_account_and_reopen_editor(self):
        self.account_idx += 1
        self.editor_retry_count += 1
        self.log(f"🔄 Rotating to Account #{self.account_idx}")
        
        if self.dashboard_page and not self.dashboard_page.is_closed():
            self.dashboard_page.close()
        
        self.launch_flow_dashboard(self.account_idx)
        return self.open_project_and_wait_editor()

    def find_and_click_new_project_button(self, page):
        strategies = [
            {"name": "Text Match", "selector": "button:has-text('Project baru'), button:has-text('New project')", "use_js": False},
            {"name": "ARIA Label", "selector": "button[aria-label*='project'], button[aria-label*='proyek']", "use_js": True},
            {"name": "CSS Class", "selector": ".new-project, .create-project, .project-button", "use_js": True}
        ]
        
        for strategy in strategies:
            try:
                buttons = page.locator(strategy['selector'])
                if buttons.first.is_visible(timeout=5000):
                    self.log(f"✅ Found via {strategy['name']}")
                    if strategy['use_js']:
                        page.evaluate(f"document.querySelector('{strategy['selector']}').click()")
                    else:
                        buttons.first.click(force=True)
                    time.sleep(2)
                    return True
            except:
                continue
        return False

    def open_project_and_wait_editor(self):
        page = self.dashboard_page
        if not page or page.is_closed():
            self.log("❌ Dashboard page is closed")
            return None
        
        try:
            self.kill_all_modals(page)
            self.set_adaptive_zoom(page, 0.75)
            
            if "/project/" in page.url:
                try:
                    page.wait_for_selector("#PINHOLE_TEXT_AREA_ELEMENT_ID", state="visible", timeout=10000)
                    self.log("✅ Editor sudah siap (project terbuka)")
                    self.editor_retry_count = 0
                    return page
                except:
                    page.reload()
            
            if "labs.google" not in page.url:
                page.goto("https://labs.google/fx/id/tools/flow", wait_until="domcontentloaded")
            
            if "/project/" not in page.url:
                if not self.find_and_click_new_project_button(page):
                    page.reload()
                    if not self.find_and_click_new_project_button(page):
                        raise Exception("Failed to find New Project button")
            
            self.log("⏳ Waiting for editor to load...")
            try:
                page.wait_for_selector("#PINHOLE_TEXT_AREA_ELEMENT_ID", state="visible", timeout=60000)
                self.log("✅ Editor loaded")
                self.editor_retry_count = 0
                return page
            except:
                raise Exception("Editor text area not detected")
                
        except Exception as e:
            self.log(f"❌ Editor opening failed: {e}")
            if self.editor_retry_count < 3:
                self.log("🔄 Retrying...")
                return self.rotate_account_and_reopen_editor()
            return None

    def apply_one_time_settings(self, vertical: bool):
        page = self.dashboard_page
        try:
            self.log("⚙️ Applying video settings...")
            self.kill_all_modals(page)
            
            # Open Settings
            settings_btn = page.locator("button:has-text('Setelan'), button:has-text('Settings')").first
            settings_btn.wait_for(state="visible", timeout=10000)
            settings_btn.click(force=True)
            time.sleep(2)
            
            # Aspect Ratio
            ratio_text = "Potret" if vertical else "Lanskap"
            # Coba cari dengan text lebih spesifik
            ratio_btn = page.locator(f"button:has-text('{ratio_text}')").first
            if ratio_btn.is_visible():
                ratio_btn.click(force=True)
            else:
                self.log(f"⚠️ Button {ratio_text} not found, attempting generic selector...")
            time.sleep(1)
            
            # Output per prompt (Ini yang sering timeout di log Anda)
            out_btn = page.locator("button:has-text('Output per perintah'), button:has-text('Output per prompt')").first
            if out_btn.is_visible(timeout=5000):
                out_btn.click(force=True)
                time.sleep(1)
                
                # Gunakan selector yang lebih aman untuk opsi '1'
                opt_1 = page.locator("li:has-text('1'), [role='option']:has-text('1')").first
                if opt_1.is_visible(timeout=5000):
                    opt_1.click(force=True)
                else:
                    self.log("⚠️ Option '1' not visible, skipping output count setting.")
            else:
                self.log("⚠️ Settings button for output count not found.")
            
            time.sleep(1)
            page.keyboard.press("Escape")
            time.sleep(1)
            self.log("✅ Settings applied.")
            
        except Exception as e:
            self.log(f"⚠️ Settings warning (Non-fatal): {e}")
            page.keyboard.press("Escape")

    def ensure_no_cards_before_input(self, page):
        """
        Aggressive cleanup: Menghapus semua card video yang ada.
        Diperbaiki dengan Selector Spesifik dari HTML User: 'opsi lainnya' & 'more_vert'.
        """
        self.log("🧹 Memastikan canvas bersih (Deleting existing cards)...")
        max_attempts = 10
        cleaned = False
        
        for _ in range(max_attempts):
            try:
                # 1. Cek keberadaan tombol Download/Unduh (Indikator Card ada)
                dl_btn = page.locator("button:has-text('Download'), button:has-text('Unduh')").first
                if not dl_btn.is_visible(timeout=2000):
                    break  # Bersih, keluar loop
                
                cleaned = True
                self.log("🗑️ Found leftover card, deleting...")
                
                # 2. Klik tombol opsi (titik tiga)
                # Selector spesifik berdasarkan HTML user:
                # <button ...><i ...>more_vert</i><span ...>opsi lainnya</span></button>
                more_btn = page.locator("button:has-text('opsi lainnya'), button:has-text('more_vert')").last
                
                # Fallback ke selector generic jika spesifik gagal (jarang terjadi dgn html ini)
                if not more_btn.is_visible():
                    more_btn = page.locator("button[aria-label*='Opsi'], button[aria-label*='Options']").last

                more_btn.scroll_into_view_if_needed()
                more_btn.click(force=True)
                time.sleep(1) # Tunggu menu muncul
                
                # 3. Klik tombol 'Hapus' di dalam menu pop-up
                del_menu = page.locator("text='Hapus'").or_(page.locator("text='Delete'")).first
                
                if del_menu.is_visible(timeout=3000):
                    del_menu.click(force=True)
                    self.log("✅ Clicked Delete.")
                    time.sleep(3)
                else:
                    self.log("⚠️ Delete menu item not found. Closing menu.")
                    page.keyboard.press("Escape")
                    
            except Exception as e:
                self.log(f"⚠️ Delete attempt error: {str(e)[:50]}")
                page.keyboard.press("Escape") # Tutup menu jika error
                time.sleep(1)
        
        if cleaned:
            self.log("✨ Canvas cleaned.")

    def find_and_click_generation_button(self, page, scene_index: int):
        # Fallback cleanup just in case
        self.ensure_no_cards_before_input(page)
        
        button_texts = ['Teks ke Video', 'Text to Video', 'Bahan menjadi Video', 'Material to Video']
        for text in button_texts:
            btn = page.locator(f"button:has-text('{text}')").first
            if btn.is_visible(timeout=2000):
                self.log(f"✅ Button found: {text}")
                btn.click(force=True)
                return True
        
        # Last resort fallback
        try:
            btns = page.locator("button:has-text('Video')")
            if btns.count() > 0:
                for i in range(btns.count()):
                    if btns.nth(i).is_visible():
                        btns.nth(i).click(force=True)
                        return True
        except:
            pass
            
        return False

    def generate_scene(self, scene_index: int, prompt_text: str, 
                      guide_image: Optional[str], save_dir: str, 
                      max_retries: int = 3):
        page = self.dashboard_page
        target_path = os.path.abspath(os.path.join(save_dir, f"{scene_index}.mp4"))
        
        for attempt in range(1, max_retries + 1):
            try:
                self.log(f"🎬 Scene #{scene_index} - Attempt {attempt}/{max_retries}")
                self.kill_all_modals(page)
                
                # 1. Pastikan bersih DULU sebelum klik apapun
                self.ensure_no_cards_before_input(page)
                
                # 2. Klik tombol tipe generasi
                if not self.find_and_click_generation_button(page, scene_index):
                    raise Exception("Tombol generasi tidak ditemukan")
                time.sleep(1)

                # 3. Upload Image (Optional)
                if scene_index > 1 and guide_image and os.path.exists(guide_image):
                    self.log(f"🖼️ Uploading guide image...")
                    try:
                        page.locator("button:has-text('Add')").first.click(force=True)
                        time.sleep(1)
                        page.locator("input[type='file']").set_input_files(guide_image)
                        time.sleep(2)
                        # Handle crop
                        crop = page.locator("button:has-text('Pangkas'), button:has-text('Crop')")
                        if crop.is_visible(timeout=3000): crop.click(force=True)
                    except Exception as e:
                        self.log(f"⚠️ Image upload warning: {e}")

                # 4. Input Prompt
                prompt_area = page.locator("#PINHOLE_TEXT_AREA_ELEMENT_ID").first
                prompt_area.click(force=True)
                prompt_area.fill(prompt_text)
                time.sleep(1)
                
                # 5. Execute
                self.log(f"🎥 Starting generation...")
                page.keyboard.press("Enter")
                
                # 6. Wait & Download
                if self.wait_for_and_download_result(page, scene_index, target_path):
                    # Cleanup success card immediately
                    self.ensure_no_cards_before_input(page)
                    return target_path
                else:
                    raise Exception("Download failed/timeout")

            except Exception as e:
                self.log(f"❌ Error: {str(e)[:100]}")
                if attempt < max_retries:
                    time.sleep(5)
                    try:
                        page.reload()
                        self.open_project_and_wait_editor()
                    except: pass
                else:
                    self.log("❌ Scene failed completely")
        return None

    def wait_for_and_download_result(self, page, scene_index: int, target_path: str, timeout_sec: int = 600):
        self.log(f"⏳ Waiting for generation (timeout: {timeout_sec}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout_sec:
            try:
                elapsed = time.time() - start_time
                remaining = max(30000, (timeout_sec - elapsed) * 1000)
                
                # 1. Cari tombol download utama
                dl_btn = page.locator("button:has-text('Download'), button:has-text('Unduh')").first
                if dl_btn.is_visible(timeout=2000):
                    self.log("✅ Found download button, clicking to open menu...")
                    
                    # 2. Klik tombol utama untuk membuka menu (jangan expect_download dulu)
                    try:
                        dl_btn.click(force=True)
                        time.sleep(1) # Tunggu menu muncul
                        
                        # 3. Cari pilihan "Ukuran asli (720p)" atau "Original size"
                        # Kita gunakan 'text=' untuk mencakup ID dan EN
                        menu_720p = page.locator("text='Ukuran asli (720p)'").or_(page.locator("text='Original size (720p)'")).first
                        
                        if menu_720p.is_visible(timeout=5000):
                            self.log("✅ Menu detected. Selecting '720p'...")
                            
                            # 4. Klik menu item -> Ini yang memicu download
                            with page.expect_download(timeout=remaining) as dl_info:
                                menu_720p.click(force=True)
                            
                            # 5. Save File
                            self.log("⬇️ Downloading file...")
                            download = dl_info.value
                            download.save_as(target_path)
                            
                            if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                                self.log(f"✅ Scene #{scene_index} Saved.")
                                return True
                            else:
                                raise Exception("File downloaded but empty/missing")
                        else:
                            self.log("⚠️ Menu pop-up did not appear or '720p' option not found. Retrying...")
                            # Klik escape jaga-jaga kalau menu nyangkut tapi invisible
                            page.keyboard.press("Escape")
                            
                    except PWTimeoutError:
                        self.log("⚠️ Download event timeout (Clicked 720p but no file).")
                    except Exception as e:
                        self.log(f"⚠️ Error during click sequence: {e}")
                
                # Cek error status dari Flow
                if page.locator("text='Gagal'").is_visible(timeout=500):
                    self.log("❌ Generation Failed status detected")
                    return False
                    
                time.sleep(5)
            except:
                time.sleep(5)
        
        self.log("⏰ Timeout reached")
        return False

    def close(self):
        try:
            if self.context: self.context.close()
            if self.playwright: self.playwright.stop()
            self.log("👋 Closed")
        except: pass