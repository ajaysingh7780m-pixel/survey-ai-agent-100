"""
Timebucks AI Agent - Automated Survey Filling
Fills Timebucks surveys automatically with intelligent AI-generated responses
Supports Toluna, Innovate, MXR, Qandi and other survey providers
"""

import os
import time
import logging
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('timebucks_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Gemini API
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    logger.error("❌ GEMINI_API_KEY not found in .env file")
    exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Global variables
TIMEBUCKS_URL = "https://timebucks.com/publishers/index.php?pg=earn&tab=all_surveys"
TOTAL_SURVEYS = 100
DELAY_BETWEEN_SURVEYS = 3  # seconds

class TimebucksAIAgent:
    def __init__(self):
        self.results = []
        self.failed_surveys = []
        self.driver = None
        self.completed_count = 0
        self.earnings = 0.0
        
    def setup_driver(self):
        """Initialize Selenium WebDriver with anti-detection features"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            logger.info("✅ Selenium WebDriver initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize WebDriver: {e}")
            raise
    
    def get_ai_response(self, question_text, context=""):
        """Generate intelligent response using Google Gemini"""
        try:
            prompt = f"""
            You are taking an online survey. Answer this question naturally and realistically.
            
            Question: {question_text}
            Context: {context}
            
            Requirements:
            - Be concise and professional
            - For rating questions, choose a reasonable number (e.g., 3-5 out of 5)
            - For text questions, provide a realistic 1-3 sentence answer
            - For multiple choice, pick the most reasonable option
            - If asked about age/gender, respond appropriately
            - Don't mention that you're an AI
            - Be consistent with typical survey responses
            
            Just provide the answer, nothing else.
            """
            
            response = model.generate_content(prompt)
            answer = response.text.strip()
            logger.debug(f"🤖 AI generated: {answer[:50]}...")
            return answer
        except Exception as e:
            logger.error(f"❌ Error generating AI response: {e}")
            return "Neutral"
    
    def fill_text_field(self, field, text):
        """Fill text input field"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", field)
            time.sleep(0.5)
            field.clear()
            field.send_keys(text)
            logger.debug(f"✏️ Filled text: {text[:30]}...")
        except Exception as e:
            logger.error(f"❌ Error filling text field: {e}")
    
    def select_dropdown(self, field):
        """Select random dropdown option"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", field)
            time.sleep(0.3)
            select = Select(field)
            options = select.options
            if len(options) > 1:
                select.select_by_index(1)
            logger.debug("✓ Selected dropdown option")
        except Exception as e:
            logger.error(f"❌ Error selecting dropdown: {e}")
    
    def click_radio_button(self, field):
        """Click radio button or checkbox"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", field)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", field)
            logger.debug("✓ Clicked radio/checkbox")
            return True
        except Exception as e:
            logger.error(f"❌ Error clicking field: {e}")
            return False
    
    def handle_survey_questions(self):
        """Handle different types of survey questions"""
        try:
            handled_count = 0
            
            # Handle radio buttons (most common in Toluna)
            try:
                radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                logger.info(f"Found {len(radios)} radio buttons")
                
                for radio in radios:
                    try:
                        label = radio.find_element(By.XPATH, "../..")
                        question_text = label.text or "Survey question"
                        
                        self.click_radio_button(radio)
                        handled_count += 1
                        time.sleep(0.5)
                    except:
                        self.click_radio_button(radio)
                        handled_count += 1
                        time.sleep(0.5)
            except Exception as e:
                logger.debug(f"No radios found: {e}")
            
            # Handle checkboxes
            try:
                checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                logger.info(f"Found {len(checkboxes)} checkboxes")
                
                for i, checkbox in enumerate(checkboxes[:3]):
                    try:
                        self.click_radio_button(checkbox)
                        handled_count += 1
                        time.sleep(0.5)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"No checkboxes found: {e}")
            
            # Handle dropdowns
            try:
                dropdowns = self.driver.find_elements(By.TAG_NAME, "select")
                logger.info(f"Found {len(dropdowns)} dropdowns")
                
                for dropdown in dropdowns:
                    try:
                        self.select_dropdown(dropdown)
                        handled_count += 1
                        time.sleep(0.5)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"No dropdowns found: {e}")
            
            # Handle text inputs
            try:
                text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                logger.info(f"Found {len(text_inputs)} text inputs")
                
                for text_input in text_inputs:
                    try:
                        placeholder = text_input.get_attribute('placeholder') or "response"
                        ai_response = self.get_ai_response(placeholder)
                        self.fill_text_field(text_input, ai_response)
                        handled_count += 1
                        time.sleep(0.5)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"No text inputs found: {e}")
            
            # Handle textareas
            try:
                textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                logger.info(f"Found {len(textareas)} textareas")
                
                for textarea in textareas:
                    try:
                        ai_response = self.get_ai_response("Please provide your feedback")
                        self.fill_text_field(textarea, ai_response)
                        handled_count += 1
                        time.sleep(0.5)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"No textareas found: {e}")
            
            logger.info(f"✅ Handled {handled_count} form fields")
            return handled_count
        
        except Exception as e:
            logger.error(f"❌ Error handling survey questions: {e}")
            return 0
    
    def find_and_click_next_button(self):
        """Find and click Next or Continue button"""
        try:
            selectors = [
                "//button[contains(text(), 'Next')]",
                "//button[contains(text(), 'next')]",
                "//button[contains(text(), 'Continue')]",
                "//button[contains(text(), 'continue')]",
                "//input[@type='button'][@value='Next']",
                "//div[@class='btn-next']//button",
                "//button[@class*='next']",
            ]
            
            for selector in selectors:
                try:
                    button = self.driver.find_element(By.XPATH, selector)
                    if button and button.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", button)
                        logger.info("✓ Clicked Next button")
                        return True
                except:
                    continue
            
            logger.debug("No Next button found")
            return False
        except Exception as e:
            logger.error(f"❌ Error finding Next button: {e}")
            return False
    
    def find_and_click_submit_button(self):
        """Find and click Submit button"""
        try:
            selectors = [
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'submit')]",
                "//button[contains(text(), 'Finish')]",
                "//button[contains(text(), 'Complete')]",
                "//input[@type='submit']",
                "//button[@type='submit']",
                "//button[@class*='submit']",
                "//button[@class*='finish']",
            ]
            
            for selector in selectors:
                try:
                    button = self.driver.find_element(By.XPATH, selector)
                    if button and button.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", button)
                        logger.info("✅ Clicked Submit button")
                        return True
                except:
                    continue
            
            logger.warning("⚠️ No Submit button found")
            return False
        except Exception as e:
            logger.error(f"❌ Error finding Submit button: {e}")
            return False
    
    def complete_survey(self, survey_number, start_url):
        """Complete a single survey"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"📋 Survey #{survey_number} - Opening...")
            logger.info(f"{'='*60}")
            
            self.driver.get(start_url)
            time.sleep(3)
            
            page_count = 0
            max_pages = 20
            
            while page_count < max_pages:
                page_count += 1
                logger.info(f"\n📄 Page {page_count}")
                
                fields_filled = self.handle_survey_questions()
                
                if fields_filled == 0:
                    logger.warning("⚠️ No fields found on this page")
                    break
                
                time.sleep(1)
                
                if not self.find_and_click_next_button():
                    if self.find_and_click_submit_button():
                        logger.info(f"✅ Survey #{survey_number} submitted!")
                        self.completed_count += 1
                        return True
                    else:
                        logger.warning("⚠️ Could not find Next or Submit button")
                        break
                
                time.sleep(2)
            
            logger.info(f"✅ Survey #{survey_number} completed (Pages: {page_count})")
            self.completed_count += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Error completing survey #{survey_number}: {e}")
            self.failed_surveys.append(survey_number)
            return False
    
    def save_results(self):
        """Save results to CSV and JSON"""
        try:
            with open('timebucks_results.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['survey_number', 'status', 'timestamp', 'duration'])
                writer.writeheader()
                writer.writerows(self.results)
            
            with open('timebucks_results.json', 'w') as f:
                json.dump(self.results, f, indent=2)
            
            logger.info(f"✅ Results saved to timebucks_results.csv and timebucks_results.json")
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
    
    def run(self):
        """Run the Timebucks agent"""
        logger.info("\n" + "="*60)
        logger.info("🚀 TIMEBUCKS AI AGENT STARTED")
        logger.info("="*60)
        logger.info(f"📊 Target: {TOTAL_SURVEYS} surveys")
        logger.info("="*60 + "\n")
        
        start_time = datetime.now()
        
        try:
            self.setup_driver()
            logger.info("👉 Open Timebucks manually and start surveys")
            logger.info("The agent will help fill them automatically")
            
            self.driver.get(TIMEBUCKS_URL)
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("🛑 WebDriver closed")

if __name__ == "__main__":
    agent = TimebucksAIAgent()
    agent.run()
