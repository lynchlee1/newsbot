import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class ChromeDriver:
    def __init__(self, headless: bool = False, timers: dict = {
        "buffer_time": 0.3,
        "load_time": 10
    }):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.timers = timers

    def setup(self): 
        self.driver, self.wait = self._setup_driver(headless=self.headless)
    
    # Open url
    def open(self, url: str):
        try:
            self.driver.get(url)
            return True
        except: return False

    # Cleanup driver
    def cleanup(self): 
        if self.driver: self.driver.quit()

    # Switch to frame
    def switch_to_frame(self, frame_selector: str):
        try:
            frame = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, frame_selector)))
            self.driver.switch_to.frame(frame)
            return True
        except: return False
    
    # Switch to default content
    def switch_to_default(self):
        try: 
            self.driver.switch_to.default_content()
            return True
        except: return False

    # Click button
    def click_button(self, selector: str, frame: str=""):
        try:
            if frame: self.switch_to_frame(frame)
            
            button = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            self.driver.execute_script("arguments[0].click();", button)
            print(f"{selector} button clicked")
            time.sleep(self.timers["buffer_time"])

            if frame: self.switch_to_default()
            return True
        except:
            if frame: self.switch_to_default()
            return False

    # Click button by text
    def click_by_text(self, button_text: str, frame: str=""):
        try:
            if frame: self.switch_to_frame(frame)

            # normalize-space removes whitespace to match the text content
            xpath_patterns = [
                f"//button[normalize-space(string())='{button_text}']",
                f"//a[normalize-space(string())='{button_text}']",
            ]
            for partial_xpath in xpath_patterns:
                try:
                    element = self.driver.find_element(By.XPATH, partial_xpath)
                    self.driver.execute_script("arguments[0].click();", element)
                    print(f"{button_text} button clicked")

                    if frame: self.switch_to_default()
                    return True
                except: continue
            return False
        except:
            if frame: self.switch_to_default()
            return False

    # Fill input
    def fill_input(self, selector: str, value: str, frame: str=""):
        try:
            if frame: self.switch_to_frame(frame)        

            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            self.driver.execute_script("arguments[0].click();", element)
            time.sleep(self.timers["buffer_time"])

            element.clear()
            element.send_keys(value)
            time.sleep(self.timers["buffer_time"])

            if frame: self.switch_to_default()
            return True
        except: 
            if frame: self.switch_to_default()
            return False
    
    # Copy all data under selectors
    def copy(self, selectors: list[str], frame: str=""):
        results = []
        try:
            if frame: self.switch_to_frame(frame)
            for selector in selectors or []:
                try:
                    self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    roots = self.driver.find_elements(By.CSS_SELECTOR, selector)
                except: continue

                for root in roots:
                    try:
                        data = self.driver.execute_script( # define & run a JavaScript function
                        """
                        function serialize(node){
                          var obj = {};                                 // save basic node info
                          obj.tag = (node.tagName || '').toLowerCase(); // save tag name
                          obj.text = (node.textContent || '').trim();   // save trimmed text

                          obj.attributes = {};                          // save node attributes
                          if (node.attributes) {
                            for (var i=0;i<node.attributes.length;i++){
                              var a = node.attributes[i];
                              obj.attributes[a.name] = a.value;
                            }
                          }

                          var props = ['href','src','value','id','className','name','type']; // save non-HTML properties
                          for (var p of props){
                            try{
                              var v = node[p];
                              if (v !== undefined && v !== null && String(v) !== '') obj[p] = v;
                            }catch(e){}
                          }

                          obj.children = [];                        // save childrens as nested dictionaries
                          var kids = node.children || [];
                          for (var j=0;j<kids.length;j++){
                            obj.children.push(serialize(kids[j]));  // recursively save childrens
                          }
                          return obj;
                        }
                        return serialize(arguments[0]);             // call the function with the root node
                        """,
                        root,
                    )
                        results.append(data)
                    except: continue
        except: pass
        finally: 
            if frame: self.switch_to_default()
        return results

    # Setup driver
    def _setup_driver(self, headless):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Stability and crash prevention options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")
        chrome_options.add_argument("--data-path=/tmp/chrome-data")
        chrome_options.add_argument("--disk-cache-dir=/tmp/chrome-cache")
        chrome_options.add_argument("--remote-allow-origins=*")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-features=Translate,BackForwardCache,AcceptCHFrame,MediaRouter,OptimizationHints")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        
        # Memory and performance options
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        
        # Logging and notifications
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        chrome_options.add_argument("--window-size=1600,1000")

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(self.timers["load_time"])
        wait = WebDriverWait(driver, self.timers["load_time"])
        return driver, wait


class TableScraper(ChromeDriver):
    '''
    ChromeDriver with table scraping functions.
    '''
    def __init__(self, headless: bool = False, timers: dict = {
        "buffer_time": 0.3,
        "load_time": 10
    }):
        super().__init__(headless=headless, timers=timers)
    
    def extract_row_texts(self, row, display_only: bool = True):
        '''
        Single row extraction function.
        '''
        td_cells = row.find_elements(By.TAG_NAME, "td") # Get all td cells
        if not td_cells: return None # Skip if there are no td cells

        first_cell = td_cells[0] # Get the first cell
        if display_only and not first_cell.is_displayed(): return None # Skip if the first cell is not displayed (invisible row)

        values = self.driver.execute_script(
            """
            var result = [];
            for (var i = 0; i < arguments[0].length; i++) {
                result.push(arguments[0][i].textContent.trim());
            }
            return result;
            """,
            td_cells
        )
        return values

    def table_to_dicts(self, tbody_selector: str, row_to_dict):
        '''
        Parse a table body into a list of dictionaries using a provided row_to_dict mapper.
        '''
        tbody = self.driver.find_element(By.CSS_SELECTOR, tbody_selector)
        rows = tbody.find_elements(By.TAG_NAME, "tr")

        data_dicts = []
        for row in rows:
            values = self.extract_row_texts(row)
            if values is None: continue # Skip invalid row
            try:
                mapped = row_to_dict(values)
                if mapped: data_dicts.append(mapped)
            except Exception: continue # Skip if mapping failed
        return data_dicts, rows

    def get_page_key(self, rows):
        '''
        Generate a simple page key using first row's cell texts.
        '''
        if not rows: return None
        first_row = rows[0]
        td_cells = first_row.find_elements(By.TAG_NAME, "td")
        if not td_cells: return None
        values = self.driver.execute_script(
            """
            var result = [];
            for (var i = 0; i < arguments[0].length; i++) {
                result.push(arguments[0][i].textContent.trim());
            }
            return result;
            """,
            td_cells
        )
        return "|".join(values) if values else None
