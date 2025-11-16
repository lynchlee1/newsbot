# utilitylib Reference

금융 데이터 수집 및 처리를 돕는 `utilitylib`의 사용법을 정리한 문서입니다.
<br> 터미널에 아래 커맨드를 입력해 필요 모듈을 설치하세요. 

```sh
pip install -r utilitylib/requirements.txt
```

---

## Package Overview

`utilitylib`은 다음 모듈을 포함합니다. 

| Module | Purpose |
| --- | --- |
| `.driver` | <b>Chrome Driver를 이용한 웹 데이터 수집을 보조하는 모듈입니다.</b> <br><br>  클라우드 환경에서는 정상적으로 동작하지 않아 스크립트 기반 프로그램 제작에 적합합니다. |
| `.finder` | <b>로컬 파일 및 Google Cloud Storage 파일의 읽기⋅쓰기를 보조하는 모듈입니다.</b> <br><br>로컬 기능을 지원해 편리하게 테스트 케이스를 다룰 수 있습니다. |
| `.planner` | <b>특정 시간에 함수를 실행하는 스케줄러 모듈입니다.</b> <br><br>시간대를 설정하여 정해진 시간에 작업을 수행할 수 있습니다. |
| `.telegram` | <b>Telegram 봇 API를 이용한 메시지 전송을 보조하는 모듈입니다.</b> <br><br>텔레그램 봇을 통해 메시지를 쉽게 보낼 수 있습니다. |

---

## `utilitylib.driver`

### Class `ChromeDriver`

Chrome Driver를 이용한 웹 자동화를 위한 기본 클래스입니다.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `headless` | `bool` | `False` | `True`인 경우 크롬 팝업 없이 백그라운드에서 실행됩니다. |
| `timers` | `dict` | ```{"buffer_time": 0.3, "load_time": 10}``` | `buffer_time` : 클릭과 클릭 사이의 전환 속도입니다. 짧을수록 실행이 빨라지지만, 기본값보다 작으면 드라이버가 버벅임에 따라 오류 가능성이 있습니다. 느린 컴퓨터에서는 `0.5`에서 `1.0` 사이를 권장합니다. <br><br> `load_time` : 해당 시간동안 크롬 드라이버가 켜지지 않았을 경우 오류를 반환합니다. |

#### Functions

- `setup()` : 크롬 드라이버를 초기화하고 설정합니다.  
    - 반환값 : 없음  
    - 사용 전 반드시 호출해야 합니다.

- `open(url)` : 지정된 URL로 이동합니다.  
    - `url`: 이동할 웹페이지 주소  
    - 반환값 : 성공시 `True`, 실패시 `False`

- `cleanup()` : 크롬 드라이버를 종료하고 리소스를 정리합니다.  
    - 반환값 : 없음  
    - 사용 후 반드시 호출하여 메모리 누수를 방지하세요.

- `switch_to_frame(frame_selector)` : 지정된 프레임으로 전환합니다.  
    - `frame_selector`: CSS 선택자로 지정한 프레임  
    - 반환값 : 성공시 `True`, 실패시 `False`  
    - iframe 내부 요소에 접근하기 전에 사용합니다.

- `switch_to_default()` : 기본 콘텐츠 영역으로 돌아갑니다.  
    - 반환값 : 성공시 `True`, 실패시 `False`  
    - 프레임 작업 후 원래 페이지로 돌아갈 때 사용합니다.

- `click_button(selector, frame="")` : CSS 선택자로 지정한 버튼을 클릭합니다.  
    - `selector`: 클릭할 버튼의 CSS 선택자  
    - `frame`: 프레임 내부 버튼인 경우 프레임 선택자 (선택사항)  
    - 반환값 : 성공시 `True`, 실패시 `False`  
    - JavaScript를 사용하여 안정적으로 클릭합니다.

- `click_by_text(button_text, frame="")` : 텍스트로 버튼을 찾아 클릭합니다.  
    - `button_text`: 버튼에 표시된 텍스트  
    - `frame`: 프레임 내부 버튼인 경우 프레임 선택자 (선택사항)  
    - 반환값 : 성공시 `True`, 실패시 `False`  
    - `<button>` 또는 `<a>` 태그에서 텍스트를 찾아 클릭합니다.

- `fill_input(selector, value, frame="")` : 입력 필드에 값을 입력합니다.  
    - `selector`: 입력 필드의 CSS 선택자  
    - `value`: 입력할 값  
    - `frame`: 프레임 내부 입력 필드인 경우 프레임 선택자 (선택사항)  
    - 반환값 : 성공시 `True`, 실패시 `False`  
    - 기존 값을 지우고 새 값을 입력합니다.

- `copy(selectors, frame="")` : 지정한 선택자들의 HTML 구조를 딕셔너리로 복사합니다.  
    - `selectors`: 복사할 요소들의 CSS 선택자 리스트  
    - `frame`: 프레임 내부 요소인 경우 프레임 선택자 (선택사항)  
    - 반환값 : 요소 정보가 담긴 딕셔너리 리스트  
    - 각 요소의 태그, 텍스트, 속성, 자식 요소를 재귀적으로 저장합니다.

---

### Class `TableScraper`

`ChromeDriver`를 상속받아 테이블 스크래핑 기능을 추가한 클래스입니다.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `headless` | `bool` | `False` | `True`인 경우 크롬 팝업 없이 백그라운드에서 실행됩니다. |
| `timers` | `dict` | ```{"buffer_time": 0.3, "load_time": 10}``` | `ChromeDriver`와 동일합니다. |

#### Functions

- `extract_row_texts(row, display_only=True)` : 테이블의 한 행에서 텍스트를 추출합니다.  
    - `row`: 추출할 행 요소 (Selenium WebElement)  
    - `display_only`: `True`인 경우 보이는 행만 추출합니다.  
    - 반환값 : 셀 텍스트 리스트 또는 `None` (행이 유효하지 않은 경우)

- `table_to_dicts(tbody_selector, row_to_dict)` : 테이블 본문을 딕셔너리 리스트로 변환합니다.  
    - `tbody_selector`: 테이블 본문(`<tbody>`)의 CSS 선택자  
    - `row_to_dict`: 행 데이터를 딕셔너리로 변환하는 함수  
    - 반환값 : `(data_dicts, rows)` 튜플  
    - `data_dicts`: 변환된 딕셔너리 리스트  
    - `rows`: 원본 행 요소 리스트

- `get_page_key(rows)` : 첫 번째 행의 셀 텍스트로 페이지 키를 생성합니다.  
    - `rows`: 행 요소 리스트  
    - 반환값 : 셀 텍스트를 `|`로 구분한 문자열 또는 `None`  
    - 페이지 변경 감지에 사용할 수 있습니다.

---

## `utilitylib.finder`

### Class `ScriptFinder`

스크립트 기반 프로그램에서 로컬 파일을 읽고 쓰는 클래스입니다.

| Parameter | Type | Description |
| --- | --- | --- |
| `filename` | `str` | 읽고 쓸 파일명 (상대 경로) |

#### Functions

- `get_resource_path(relative_path)` : 리소스 파일의 절대 경로를 반환합니다.  
    - `relative_path`: 상대 경로  
    - 반환값 : 절대 경로 문자열  
    - PyInstaller로 컴파일된 실행 파일에서도 정상 동작합니다.

- `load_data()` : JSON 파일을 읽어 딕셔너리로 반환합니다.  
    - 반환값 : 성공시 딕셔너리 데이터, 실패시 `False`

- `save_data(data)` : 딕셔너리를 JSON 파일로 저장합니다.  
    - `data`: 저장할 딕셔너리 데이터  
    - 반환값 : 성공시 `True`, 실패시 `False`

---

### Class `CloudFinder`

Google Cloud Storage에 저장된 파일을 읽고 쓸 수 있는 클래스입니다. 로컬 모드도 지원합니다.

| Parameter | Type | Description |
| --- | --- | --- |
| `bucket_name` | `str` | 사용할 클라우드 버킷명 |

#### Functions

- `save(data, blob_name, local=False)` : 파이썬 딕셔너리를 JSON 파일로 저장합니다.  
    - `data`: 저장할 데이터  
    - `blob_name`: 저장할 파일명  
    - `local`: `True`면 로컬, `False`면 클라우드에 저장  
    - 반환값 : 성공시 `True`, 실패시 `False`

- `load(local_file_name, blob_name="", local=False)` : 저장된 JSON 파일을 파이썬 딕셔너리로 불러옵니다.  
    - `local_file_name`: 로컬 파일명  
    - `blob_name`: 클라우드 파일명 (생략시 `local_file_name` 사용)  
    - `local`: `True`면 로컬, `False`면 클라우드에서 불러옴  
    - 반환값 : 성공시 딕셔너리 데이터, 실패시 `False`

### 주요 GCS(Google Cloud Storage) 명령어 안내

| 동작 | 명령어 |
|-|-|
| **로그인**   | `$ gcloud auth application-default login` |
| **파일 업로드** | `$ gcloud storage cp <local_file_name> gs://<bucket_name>/<blob_name>` |
| **업로드 확인**| `$ gcloud storage ls gs://<bucket_name>/<blob_name>` |
| **다운로드** | `$ gcloud storage cp gs://<bucket_name>/<blob_name> <local_file_name>` |

---

## `utilitylib.planner`

### Class `Planner`

특정 시간에 함수를 실행하는 스케줄러 클래스입니다.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `utc_time` | `int` | `0` | UTC 기준 시간대 오프셋입니다. 한국 시간대(KST)는 `9`를 사용합니다. |

#### Functions

- `add_plan(hour, minute, buffer, func, kwargs={})` : 실행할 계획을 추가합니다.  
    - `hour`: 실행할 시 (0-23)  
    - `minute`: 실행할 분 (0-59)  
    - `buffer`: 버퍼 시간(분). `[hour:minute, hour:minute+buffer]` 구간에 실행됩니다.  
    - `func`: 실행할 함수  
    - `kwargs`: 함수에 전달할 키워드 인자 딕셔너리  
    - 반환값 : 없음

- `run_schedule()` : 등록된 계획 중 현재 시간에 해당하는 함수를 실행합니다.  
    - 반환값 : 함수가 실행되었으면 `True`, 그렇지 않으면 `False`  
    - 여러 계획이 있어도 하나만 실행되고 종료됩니다.

---

## `utilitylib.telegram`

### Class `ChatBot`

Telegram 봇 API를 이용하여 메시지를 전송하는 클래스입니다.

| Parameter | Type | Description |
| --- | --- | --- |
| `bot_token` | `str` | Telegram 봇 토큰 |

#### Functions

- `send_message(chat_id, text, parse_mode="HTML")` : 텔레그램 채팅에 메시지를 전송합니다.  
    - `chat_id`: 메시지를 보낼 채팅 ID  
    - `text`: 전송할 메시지 텍스트  
    - `parse_mode`: 메시지 파싱 모드 (기본값: `"HTML"`)  
    - 반환값 : 없음  
    - 오류 발생시 예외를 발생시킵니다.  
    - 링크 미리보기는 기본적으로 비활성화됩니다.
