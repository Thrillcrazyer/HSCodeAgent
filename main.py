import os
import time
import json
import base64
import requests
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd


class UnipassHSScraper:
    """관세청 UNIPASS 품목분류 국내사례 스크래퍼"""
    
    def __init__(self, output_dir: str = "scraped_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        self.pdf_dir = self.output_dir / "pdf"
        self.pdf_dir.mkdir(exist_ok=True)
        
        self.driver = None
        self.wait = None
        self.results = []
        
    def setup_driver(self):
        """Chrome WebDriver 설정 (PDF 저장 지원)"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # 필요시 헤드리스 모드
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--lang=ko-KR")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # PDF 저장을 위한 설정
        chrome_options.add_argument("--kiosk-printing")
        prefs = {
            "printing.print_preview_sticky_settings.appState": json.dumps({
                "recentDestinations": [{
                    "id": "Save as PDF",
                    "origin": "local",
                    "account": ""
                }],
                "selectedDestinationId": "Save as PDF",
                "version": 2,
                "isHeaderFooterEnabled": False,
                "isLandscapeEnabled": False,
                "isCssBackgroundEnabled": True,
                "mediaSize": {
                    "height_microns": 297000,
                    "width_microns": 210000,
                    "name": "ISO_A4"
                },
                "scalingType": 3,
                "scaling": "100"
            }),
            "savefile.default_directory": str(self.pdf_dir.absolute()),
            "download.default_directory": str(self.pdf_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        
    def close_driver(self):
        """WebDriver 종료"""
        if self.driver:
            self.driver.quit()
            
    def navigate_to_main_page(self):
        """메인 페이지로 이동"""
        url = "https://unipass.customs.go.kr/clip/index.do"
        self.driver.get(url)
        time.sleep(3)
        print("메인 페이지 로드 완료")
        
    def navigate_to_hs_classification(self):
        """세계 HS > 품목분류국내사례 메뉴로 이동"""
        try:
            # 메인 메뉴에서 '세계HS' 버튼 클릭 (span 태그로 되어있음)
            world_hs_menu = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '세계HS')]"))
            )
            world_hs_menu.click()
            time.sleep(1)
            print("세계HS 메뉴 클릭 완료")
            
            # 서브메뉴에서 '품목분류 국내사례' 클릭 (ID로 찾기)
            domestic_case_menu = self.wait.until(
                EC.element_to_be_clickable((By.ID, "LEFTMENU_LNK_M_ULS0807030051"))
            )
            domestic_case_menu.click()
            time.sleep(3)
            print("품목분류 국내사례 페이지로 이동 완료")
            
        except TimeoutException:
            print("메뉴를 찾을 수 없습니다. 직접 URL로 이동합니다.")
            # 직접 URL로 이동 시도
            self.driver.get("https://unipass.customs.go.kr/clip/index.do#702010100000")
            time.sleep(3)
            
    def set_search_date(self, start_year: int = 2016, start_month: int = 1):
        """시행일자 시작일 설정"""
        try:
            # 시작일자 달력 버튼 클릭
            calendar_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "(//a[@class='btn_calendar'])[1]"))
            )
            calendar_btn.click()
            time.sleep(1)
            print("달력 팝업 열기 완료")
            
            # 년도 선택 (select 드롭다운)
            year_select = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//select[@name='selectYear' and @title='시작일자 연도']"))
            )
            Select(year_select).select_by_value(str(start_year))
            time.sleep(0.5)
            print(f"시작 년도 선택: {start_year}년")
            
            # 날짜(1일) 클릭
            day_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'day') and contains(@class, 'toMonth') and text()='1']"))
            )
            day_element.click()
            time.sleep(0.5)
            print("날짜 선택: 1일")
            
            # 확인 버튼 클릭
            confirm_btn = self.driver.find_element(
                By.XPATH, "//button[@name='dateSelectBtn']"
            )
            confirm_btn.click()
            time.sleep(1)
            print(f"검색 시작일 설정 완료: {start_year}년 {start_month}월 1일")
            
        except Exception as e:
            print(f"날짜 설정 중 오류: {e}")
            
    def click_search(self):
        """조회 버튼 클릭"""
        try:
            search_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and @title='조회']"))
            )
            search_btn.click()
            time.sleep(3)
            print("조회 버튼 클릭 완료")
            
        except TimeoutException:
            # 다른 방법으로 조회 버튼 찾기
            try:
                search_btn = self.driver.find_element(By.XPATH, "//button//span[text()='조회']/parent::button")
                search_btn.click()
                time.sleep(3)
            except:
                print("조회 버튼을 찾을 수 없습니다.")
                
    def get_total_pages(self) -> int:
        """전체 페이지 수 확인"""
        try:
            # 페이지네이션에서 마지막 페이지 버튼 찾기
            # 마지막 페이지로 이동하는 버튼이나 페이지 정보 텍스트에서 추출
            page_info_elements = self.driver.find_elements(
                By.XPATH, "//div[contains(@class, 'paging')]//a | //div[contains(@class, 'pagination')]//a"
            )
            
            pages = []
            for elem in page_info_elements:
                try:
                    text = elem.text.strip()
                    if text.isdigit():
                        pages.append(int(text))
                except:
                    continue
                    
            if pages:
                return max(pages)
                
        except:
            pass
        
        # 전체 건수에서 페이지 수 계산 (10개씩)
        try:
            total_count_elem = self.driver.find_element(
                By.XPATH, "//*[contains(text(), '건') or contains(text(), '총')]"
            )
            text = total_count_elem.text
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                total_count = int(numbers[0])
                return (total_count + 9) // 10  # 10개씩, 올림
        except:
            pass
            
        return 1  # 기본값
        
    def get_case_count_on_page(self) -> int:
        """현재 페이지의 사례 수 확인"""
        try:
            # 품목분류사례 테이블에서 행 수 확인
            rows = self.driver.find_elements(
                By.XPATH, "//h2[contains(text(), '품목분류사례')]/following::table[1]//tbody//tr"
            )
            return len([r for r in rows if r.find_elements(By.TAG_NAME, "td")])
        except:
            return 0
        
    def click_case_by_index(self, index: int) -> bool:
        """인덱스로 사례 클릭 (0부터 시작)"""
        try:
            # 품목분류사례 테이블에서 품명 링크 클릭
            case_links = self.driver.find_elements(
                By.XPATH, "//h2[contains(text(), '품목분류사례')]/following::table[1]//tbody//tr//a"
            )
            
            if index < len(case_links):
                case_links[index].click()
                time.sleep(2)
                return True
            return False
            
        except Exception as e:
            print(f"    사례 클릭 오류: {e}")
            return False
        
    def download_image(self, img_url: str, filename: str) -> str:
        """이미지 다운로드"""
        try:
            if img_url.startswith("data:"):
                # Base64 인코딩된 이미지
                header, data = img_url.split(",", 1)
                img_data = base64.b64decode(data)
            else:
                # URL에서 다운로드
                if not img_url.startswith("http"):
                    img_url = "https://unipass.customs.go.kr" + img_url
                response = requests.get(img_url, timeout=10)
                img_data = response.content
                
            filepath = self.images_dir / filename
            with open(filepath, "wb") as f:
                f.write(img_data)
            return str(filepath)
            
        except Exception as e:
            print(f"이미지 다운로드 실패: {e}")
            return ""
    
    def click_print_button_and_save_pdf(self, case_index: int) -> str:
        """인쇄 버튼 클릭 후 PDF로 저장"""
        pdf_filename = f"case_{case_index}.pdf"
        pdf_path = self.pdf_dir / pdf_filename
        
        try:
            # 상세보기 영역 옆에 있는 인쇄 버튼 찾기
            print_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//button[@title='인쇄'] | //a[@title='인쇄'] | //button[contains(@onclick, 'print')] | "
                    "//a[contains(@onclick, 'print')] | //button[contains(text(), '인쇄')] | "
                    "//span[contains(text(), '인쇄')]/parent::button | //span[contains(text(), '인쇄')]/parent::a | "
                    "//img[contains(@alt, '인쇄')]/parent::a | //img[contains(@alt, '인쇄')]/parent::button"
                ))
            )
            
            # 현재 창 핸들 저장
            main_window = self.driver.current_window_handle
            
            # 인쇄 버튼 클릭
            print_btn.click()
            time.sleep(2)
            
            # 새 창으로 전환
            all_windows = self.driver.window_handles
            new_window = None
            for window in all_windows:
                if window != main_window:
                    new_window = window
                    break
            
            if new_window:
                self.driver.switch_to.window(new_window)
                time.sleep(2)
                
                # 새 창에서 PDF로 인쇄 (Chrome의 Print to PDF 기능 사용)
                # DevTools Protocol을 사용하여 PDF 생성
                result = self.driver.execute_cdp_cmd("Page.printToPDF", {
                    "printBackground": True,
                    "landscape": False,
                    "paperWidth": 8.27,  # A4 width in inches
                    "paperHeight": 11.69,  # A4 height in inches
                    "marginTop": 0.4,
                    "marginBottom": 0.4,
                    "marginLeft": 0.4,
                    "marginRight": 0.4
                })
                
                # Base64 디코딩하여 PDF 파일 저장
                pdf_data = base64.b64decode(result["data"])
                with open(pdf_path, "wb") as f:
                    f.write(pdf_data)
                
                print(f"    PDF 저장 완료: {pdf_path}")
                
                # 새 창 닫기
                self.driver.close()
                
                # 메인 창으로 돌아가기
                self.driver.switch_to.window(main_window)
                time.sleep(1)
                
                return str(pdf_path)
            else:
                # 새 창이 열리지 않은 경우, 현재 창에서 처리
                print("    새 창이 열리지 않음, 현재 창에서 PDF 저장 시도")
                
                # DevTools Protocol을 사용하여 PDF 생성
                result = self.driver.execute_cdp_cmd("Page.printToPDF", {
                    "printBackground": True,
                    "landscape": False,
                    "paperWidth": 8.27,
                    "paperHeight": 11.69,
                    "marginTop": 0.4,
                    "marginBottom": 0.4,
                    "marginLeft": 0.4,
                    "marginRight": 0.4
                })
                
                pdf_data = base64.b64decode(result["data"])
                with open(pdf_path, "wb") as f:
                    f.write(pdf_data)
                
                print(f"    PDF 저장 완료: {pdf_path}")
                return str(pdf_path)
                
        except Exception as e:
            print(f"    PDF 저장 중 오류: {e}")
            return ""
            
    def scrape_case_detail(self, case_index: int) -> dict:
        """개별 사례 상세 정보 스크래핑 (인쇄 버튼 → PDF 저장 방식)"""
        detail = {
            "index": case_index,
            "title": "",
            "hs_code": "",
            "description": "",
            "images": [],
            "classification_reason": "",
            "pdf_path": "",
            "scraped_at": datetime.now().isoformat()
        }
        
        try:
            # 상세보기 영역 대기
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), '상세보기')]"))
            )
            
            # 상세보기 테이블에서 기본 정보 추출 (제목, HS코드 등)
            detail_table = self.driver.find_element(
                By.XPATH, "//h2[contains(text(), '상세보기')]/following::table[1]"
            )
            
            # 모든 th-td 쌍에서 정보 추출
            rows = detail_table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                try:
                    th = row.find_element(By.TAG_NAME, "th")
                    td = row.find_element(By.TAG_NAME, "td")
                    header = th.text.strip()
                    value = td.text.strip()
                    
                    if "품명" in header:
                        detail["title"] = value
                    elif "HS" in header or "세번" in header:
                        detail["hs_code"] = value
                    elif "해설" in header or "내용" in header:
                        detail["description"] = value
                    elif "분류사유" in header or "결정사유" in header or "사유" in header:
                        detail["classification_reason"] = value
                        
                except NoSuchElementException:
                    continue
            
            # 인쇄 버튼 클릭 후 PDF 저장
            pdf_path = self.click_print_button_and_save_pdf(case_index)
            if pdf_path:
                detail["pdf_path"] = pdf_path
                
        except Exception as e:
            print(f"상세 정보 추출 중 오류: {e}")
            
        return detail
        
    def go_to_page(self, page_num: int):
        """특정 페이지로 이동 (품목분류사례와 상세보기 사이의 ul.pages 사용)"""
        try:
            # 품목분류사례(h2)와 상세보기(h2) 사이에 있는 ul.pages에서 페이지 번호 클릭
            # 구조: <ul class="pages"><li><a href="#2">2</a></li>...</ul>
            page_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    f"//h2[contains(text(), '품목분류사례')]/following::ul[@class='pages'][1]//a[normalize-space(text())='{page_num}']"
                ))
            )
            page_btn.click()
            time.sleep(2)
            print(f"  페이지 {page_num}으로 이동 완료")
            return True
        except Exception as e:
            print(f"  페이지 {page_num} 버튼 클릭 실패: {e}")
            return False
    
    def go_to_next_page_group(self) -> bool:
        """다음 10페이지 그룹으로 이동 (품목분류사례와 상세보기 사이)"""
        try:
            # 품목분류사례(h2)와 상세보기(h2) 사이에 있는 "다음10페이지" 버튼 찾기
            next_group_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//h2[contains(text(), '품목분류사례')]/following::span[contains(text(), '다음10페이지')][1]/parent::a | "
                    "//h2[contains(text(), '품목분류사례')]/following::a[contains(@title, '다음10페이지')][1]"
                ))
            )
            next_group_btn.click()
            time.sleep(2)
            print("  다음 10페이지 그룹으로 이동 완료")
            return True
        except Exception as e:
            print(f"  다음 10페이지 버튼 없음 (마지막 그룹): {e}")
            return False
                
    def scrape_all_cases(self, start_year: int = 2016, start_month: int = 1, max_pages: int = None):
        """모든 품목분류 사례 스크래핑"""
        try:
            self.setup_driver()
            self.navigate_to_main_page()
            self.navigate_to_hs_classification()
            
            # 날짜 설정 및 조회
            self.set_search_date(start_year, start_month)
            self.click_search()
            
            # 전체 페이지 수 확인
            total_pages = self.get_total_pages()
            if max_pages:
                total_pages = min(total_pages, max_pages)
            print(f"총 {total_pages} 페이지 스크래핑 예정")
            
            case_index = 0
            current_page = 1
            current_page_group = 1  # 현재 페이지 그룹 (1~10, 11~20, ...)
            
            while current_page <= total_pages:
                print(f"\n--- {current_page}/{total_pages} 페이지 처리 중 ---")
                
                # 현재 페이지의 사례 수 확인
                case_count = self.get_case_count_on_page()
                print(f"현재 페이지 사례 수: {case_count}")
                
                # 각 사례 순차적으로 클릭하며 스크래핑
                for i in range(case_count):
                    try:
                        case_index += 1
                        
                        # 사례 클릭
                        if not self.click_case_by_index(i):
                            print(f"  사례 {case_index}: 클릭 실패, 건너뜀")
                            continue
                            
                        print(f"  사례 {case_index}: 상세 정보 추출 중...")
                        
                        # 상세 정보 스크래핑
                        detail = self.scrape_case_detail(case_index)
                        self.results.append(detail)
                        
                        print(f"    제목: {detail.get('title', '')[:30]}...")
                        print(f"    HS코드: {detail.get('hs_code', '')}")
                        print(f"    PDF: {detail.get('pdf_path', '')}")
                        
                    except Exception as e:
                        print(f"    사례 {case_index} 처리 중 오류: {e}")
                        continue
                
                # 현재 페이지에서 10개 다운로드 완료
                print(f"  페이지 {current_page} 처리 완료 ({case_count}건)")
                
                # 다음 페이지로 이동
                current_page += 1
                if current_page <= total_pages:
                    # 현재 페이지 그룹 내에서 이동할 페이지 번호 계산
                    page_in_current_group = ((current_page - 1) % 10) + 1
                    
                    # 10페이지 그룹의 마지막 페이지였으면 (10, 20, 30...) 다음 그룹으로 이동
                    if page_in_current_group == 1 and current_page > 1:
                        # 다음 10페이지 그룹으로 이동
                        print(f"\n  === 다음 10페이지 그룹으로 이동 (페이지 {current_page}~) ===")
                        if not self.go_to_next_page_group():
                            print("  다음 페이지 그룹이 없습니다. 스크래핑 종료.")
                            break
                        current_page_group += 1
                    else:
                        # 같은 그룹 내에서 페이지 번호 버튼 클릭
                        if not self.go_to_page(current_page):
                            print(f"  페이지 {current_page} 이동 실패, 건너뜀")
                        
                # 중간 저장 (10페이지마다)
                if current_page % 10 == 1 and current_page > 1:
                    self.save_results()
                    print(f"중간 저장 완료 ({len(self.results)}건)")
                    
        except Exception as e:
            print(f"스크래핑 중 오류 발생: {e}")
            
        finally:
            self.save_results()
            self.close_driver()
            
    def save_results(self):
        """결과 저장"""
        if not self.results:
            print("저장할 데이터가 없습니다.")
            return
            
        # JSON 저장
        json_path = self.output_dir / "hs_classification_cases.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"JSON 저장 완료: {json_path}")
        
        # CSV 저장 (PDF 경로 포함)
        csv_data = []
        for result in self.results:
            row = {
                "index": result.get("index"),
                "title": result.get("title"),
                "hs_code": result.get("hs_code"),
                "description": result.get("description"),
                "classification_reason": result.get("classification_reason"),
                "pdf_path": result.get("pdf_path", ""),
                "images": "; ".join([img.get("local_path", "") for img in result.get("images", [])]),
                "scraped_at": result.get("scraped_at")
            }
            csv_data.append(row)
            
        df = pd.DataFrame(csv_data)
        csv_path = self.output_dir / "hs_classification_cases.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"CSV 저장 완료: {csv_path}")
        
        print(f"\n총 {len(self.results)}건의 품목분류 사례 저장 완료")
        print(f"PDF 파일 저장 위치: {self.pdf_dir}")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("관세청 UNIPASS 품목분류 국내사례 스크래퍼")
    print("=" * 60)
    
    scraper = UnipassHSScraper(output_dir="scraped_data")
    
    # 2016년 1월부터 조회 시작, 테스트용으로 max_pages 설정 가능
    scraper.scrape_all_cases(
        start_year=2016, 
        start_month=1,
        max_pages=None  # 전체 페이지 스크래핑 (테스트시 숫자로 제한 가능)
    )
    
    print("\n스크래핑 완료!")
    print(f"결과 저장 위치: {scraper.output_dir}")


if __name__ == "__main__":
    main()
