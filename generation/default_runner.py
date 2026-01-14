"""Default video generation runner using Playwright and Nexabot."""
import os
import time
import re
import subprocess
from typing import Optional
from playwright.sync_api import sync_playwright
from generation.base_runner import BaseRunner
from core.models import GenerationConfig, ScenePrompt
from core.logger import Logger


class DefaultRunner(BaseRunner):
    """Default runner using Playwright to interact with Nexabot."""
    
    def __init__(self, config: GenerationConfig, logger: Logger, 
                 email: str, password: str, ffmpeg_path: str, timeout: int, use_extensions: bool = True):
        """Initialize default runner.
        
        Args:
            config: Generation configuration
            logger: Logger instance
            email: Login email
            password: Login password
            ffmpeg_path: Path to ffmpeg executable
            timeout: Timeout in seconds
            use_extensions: If True, load nexa_extension for captcha solving; if False, no extensions
        """
        super().__init__(config, logger)
        self.email = email
        self.password = password
        self.ffmpeg_path = ffmpeg_path
        self.timeout = timeout
        self.use_extensions = use_extensions
        self.context = None
        self.page = None
        self.playwright = None
    
    def initialize(self) -> bool:
        """Initialize browser and navigate to Video Generator."""
        try:
            target_generator_url = "https://nexabot.pro/dashboard/videogenerator"
            
            self.logger.log("🌐 Opening Browser...")
            self.playwright = sync_playwright().start()
            
            # Build browser launch arguments
            launch_args = {}
            if self.use_extensions:
                ext_path = os.path.abspath("nexa_extension")
                if os.path.exists(ext_path):
                    self.logger.log("🔌 Loading nexa_extension for captcha solving...")
                    launch_args['args'] = [
                        f"--disable-extensions-except={ext_path}", 
                        f"--load-extension={ext_path}"
                    ]
                else:
                    self.logger.log("⚠️ nexa_extension not found, continuing without extensions...")
            else:
                self.logger.log("ℹ️ Extensions disabled (Nexa mode)")
            
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir="user_data", 
                headless=False, 
                slow_mo=1000,
                **launch_args
            )
            self.context.set_default_timeout(self.timeout * 1000)
            self.page = self.context.new_page()
            
            # Try to login to extension
            try:
                if self.context.service_workers:
                    actual_ext_id = self.context.service_workers[0].url.split("/")[2]
                    self.page.goto(f"chrome-extension://{actual_ext_id}/popup.html")
                    email_f = self.page.locator("#emailInput")
                    if email_f.is_visible():
                        email_f.fill(self.email or "")
                        self.page.fill("#passwordInput", self.password or "")
                        self.page.keyboard.press("Enter")
                        time.sleep(2)
                        if self.page.locator("#startBtn").is_visible():
                            self.page.click("#startBtn")
            except Exception:
                pass
            
            # Navigate to Video Generator
            self.logger.log("➡️ Navigating directly to Video Generator...")
            self.page.goto(target_generator_url, wait_until="domcontentloaded")
            
            if not self._is_on_videogenerator(self.page):
                self.logger.log("ℹ️ Video Generator heading not visible — checking login form...")
                need_login = False
                try:
                    need_login = self.page.locator("#email").is_visible()
                except Exception:
                    need_login = True
                
                if need_login:
                    if not self._perform_login(self.page):
                        return False
                
                self.logger.log("➡️ Post-login — redirecting to Video Generator...")
                try:
                    self.page.goto(target_generator_url, wait_until="domcontentloaded")
                except Exception:
                    pass
            
            # Verify we're on the right page
            try:
                self.page = self._wait_for_url_in_any_page(
                    self.context, r".*/dashboard/videogenerator.*", self.timeout * 1000
                )
            except Exception:
                found = False
                for p2 in self.context.pages:
                    if self._is_on_videogenerator(p2):
                        self.page = p2
                        found = True
                        break
                if not found:
                    self.logger.log("❌ Could not reach Video Generator after login.")
                    return False
            
            if self._is_on_videogenerator(self.page):
                self.logger.log("✅ Video Generator ready after login.")
            else:
                self.logger.log("⚠️ Video Generator still not visible — attempting dashboard link fallback...")
                try:
                    self.page.click('a[href="/dashboard/videogenerator"]', timeout=self.timeout * 1000)
                    self.page = self._wait_for_url_in_any_page(
                        self.context, r".*/dashboard/videogenerator.*", self.timeout * 1000
                    )
                    if not self._is_on_videogenerator(self.page):
                        raise Exception("Heading not found after dashboard link.")
                    self.logger.log("✅ Video Generator opened via dashboard link.")
                except Exception as e:
                    self.logger.log(f"❌ Fallback failed: {e}")
                    return False
            
            self.is_running = True
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
    
    def generate_scene(self, scene: ScenePrompt, save_dir: str, 
                      last_frame_path: Optional[str] = None) -> Optional[str]:
        """Generate a single scene using Nexabot.
        
        Args:
            scene: Scene prompt data
            save_dir: Directory to save the generated video
            last_frame_path: Path to last frame from previous scene (for I2V)
        
        Returns:
            Path to generated video if successful, None otherwise
        """
        if not self.page or not self.is_running:
            return None
        
        try:
            gen_target = self.config.generator
            self.logger.log(f"🎬 Scene #{scene.index}: Selecting {gen_target}...")
            
            gen_grid = self.page.locator("div.grid-cols-3").first
            gen_grid.locator("button", has_text=gen_target).first.click(timeout=5000)
            
            # Handle Veo 3.1 Booster
            if gen_target == "Veo 3.1":
                booster_card = self.page.locator("div.rounded-xl").filter(has_text="Veo 3.1 Booster").last
                status_text = booster_card.inner_text(timeout=5000)
                if "Enabled" not in status_text:
                    if "Active" in status_text:
                        booster_card.click()
                        self.logger.log("⚡ Booster: Enabled")
                    else:
                        self.logger.log("🔄 Booster: Refreshing...")
                        self.page.locator("button:has-text('Refresh Status')").click()
                        time.sleep(5)
                        if "Active" in booster_card.inner_text():
                            booster_card.click()
            
            # Set aspect ratio
            ratio = "Vertical (9:16)" if self.config.mode == "Shorts" else "Landscape (16:9)"
            self.page.locator("button").filter(has_text=ratio).click()
            
            # Upload last frame for I2V if available
            if last_frame_path and os.path.exists(last_frame_path):
                self.logger.log("🖼️ I2V: Uploading start frame...")
                self.page.set_input_files("input[accept='image/*']", last_frame_path)
                time.sleep(2)
            
            # Fill prompt
            self.logger.log(f"✍️ Scene #{scene.index}: Filling prompt...")
            textarea = self.page.locator("textarea[placeholder*='Describe your video']")
            textarea.scroll_into_view_if_needed()
            textarea.fill(scene.prompt_text)
            
            # Generate
            self.logger.log(f"🎥 Scene #{scene.index}: Generating...")
            self.page.locator("button:has-text('Generate Video')").click()
            
            # Wait for result
            self.logger.log(f"⏳ Scene #{scene.index}: Waiting for result...")
            try:
                self.page.wait_for_selector("button:has-text('Download')", 
                                           timeout=self.timeout * 1000)
                with self.page.expect_download() as dl_info:
                    self.page.click("button:has-text('Download')")
                
                video_path = os.path.join(save_dir, f"{scene.index}.mp4")
                dl_info.value.save_as(video_path)
                self.logger.log(f"✅ Scene #{scene.index}: SUCCESS")
                
                # Extract last frame for next scene
                temp_frame = os.path.join(save_dir, f"last_frame_{scene.index}.jpg")
                subprocess.run([self.ffmpeg_path, '-sseof', '-1', '-i', video_path,
                               '-update', '1', '-q:v', '2', '-frames:v', '1',
                               temp_frame, '-y'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                
                # Clear card
                self.page.click('button[title="Delete video"]')
                self.page.wait_for_selector("button:has-text('Download')", state="hidden")
                self.logger.log(f"🗑️ Scene #{scene.index}: Card cleared")
                
                return video_path
                
            except Exception as e:
                self.logger.log(f"❌ Scene #{scene.index} FAILED: {str(e)[:150]}")
                self.logger.log("🧹 Timeout pada 'Download' — mencoba 'Clear Queue'...")
                self._clear_queue_if_present(self.page)
                self._wait_until_no_processing_cards(self.page, timeout_ms=15000)
                return None
                
        except Exception as e:
            self.logger.log(f"❌ Scene #{scene.index} FAILED: {str(e)[:100]}")
            return None
    
    def cleanup(self):
        """Close browser and cleanup resources."""
        if self.context is not None:
            try:
                self.context.close()
            except Exception:
                pass
        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass
        self.is_running = False
    
    # Helper methods
    def _is_on_videogenerator(self, page) -> bool:
        """Check if on Video Generator page."""
        try:
            return page.locator("h1", has_text="Video Generator").first.is_visible()
        except Exception:
            return False
    
    def _perform_login(self, page) -> bool:
        """Perform login on login page."""
        try:
            self.logger.log("🔐 Login required — filling credentials...")
            if page.locator("#email").is_visible():
                page.fill("#email", self.email or "")
                page.keyboard.press("Enter")
                page.wait_for_selector("#password", timeout=15000)
                page.fill("#password", self.password or "")
                page.keyboard.press("Enter")
                self.logger.log("✅ Login submitted.")
                return True
        except Exception as e:
            self.logger.log(f"❌ Login form error: {e}")
        return False
    
    def _wait_for_url_in_any_page(self, context, pattern, timeout_ms):
        """Wait for URL pattern in any page."""
        end = time.time() + timeout_ms / 1000.0
        compiled = re.compile(pattern)
        while time.time() < end:
            for p in context.pages:
                url = getattr(p, "url", "") or ""
                if compiled.search(url):
                    try:
                        p.bring_to_front()
                    except Exception:
                        pass
                    return p
            time.sleep(0.25)
        raise TimeoutError(f"No page matched URL pattern: {pattern}")
    
    def _clear_queue_if_present(self, page, timeout_ms=5000):
        """Clear queue if button is present."""
        try:
            def _accept_dialog(dialog):
                try:
                    dialog.accept()
                except Exception:
                    pass
            page.once("dialog", _accept_dialog)
            btn = page.locator("button:has-text('Clear Queue')").first
            if btn.is_visible():
                self.logger.log("🧹 Queue: tombol 'Clear Queue' terdeteksi — eksekusi...")
                btn.click(timeout=timeout_ms)
                time.sleep(1.0)
                self.logger.log("✅ Queue dibersihkan (dialog dikonfirmasi).")
                return True
            else:
                return False
        except Exception as e:
            self.logger.log(f"⚠️ Gagal klik 'Clear Queue': {str(e)[:120]}")
            return False
    
    def _wait_until_no_processing_cards(self, page, timeout_ms=15000):
        """Wait until no processing cards are visible."""
        end = time.time() + timeout_ms / 1000.0
        while time.time() < end:
            try:
                has_processing = False
                if page.locator(r"text=/Processing|In\s+Queue|Generating/i").is_visible():
                    has_processing = True
                if page.locator('[role="status"], [role="progressbar"], [aria-busy="true"]').is_visible():
                    has_processing = True
                if page.locator("button:has-text('Cancel'), button:has-text('Stop')").is_visible():
                    has_processing = True
                if not has_processing:
                    return True
            except Exception:
                return True
            time.sleep(0.5)
        return False
