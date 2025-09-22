import requests
import json
import os

# --- 설정 ---
# OpenWeatherMap API 키와 도시 ID를 설정하세요.
# API 키 발급: https://openweathermap.org/api
# 도시 ID 찾기: https://openweathermap.org/find?q=
OPENWEATHERMAP_API_KEY = "319607f4dd50bcac6dbeeb8eda1663fa"  # 본인의 OpenWeatherMap API 키로 변경
CITY_ID = "1835848"  # 서울의 City ID, 다른 도시는 위 링크에서 검색

# 카카오 API 설정
# 카카오 개발자 사이트에서 앱을 만들고 REST API 키를 발급받으세요.
# https://developers.kakao.com/
KAKAO_REST_API_KEY = "1cfef967cc8b70ee9b11af77775a712f"  # 본인의 카카오 REST API 키로 변경
REDIRECT_URI = "https://localhost"  # 카카오 개발자 설정에서 등록한 Redirect URI
TOKEN_FILE = "kakao_tokens.json"  # 토큰을 저장할 파일명

def get_weather_and_dust():
    """OpenWeatherMap API를 사용하여 날씨와 미세먼지 정보를 가져옵니다."""
    try:
        # 날씨 정보 요청 (섭씨온도: units=metric, 언어: lang=kr)
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?id={CITY_ID}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=kr"
        weather_res = requests.get(weather_url)
        weather_res.raise_for_status()
        weather_data = weather_res.json()

        lat = weather_data['coord']['lat']  # 위도
        lon = weather_data['coord']['lon']  # 경도

        # 미세먼지 정보 요청
        dust_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}"
        dust_res = requests.get(dust_url)
        dust_res.raise_for_status()
        dust_data = dust_res.json()

        return weather_data, dust_data

    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None, None

def get_dust_status(aqi):
    """AQI(대기질 지수) 값을 한글 상태로 변환합니다."""
    if aqi == 1:
        return "좋음"
    elif aqi == 2:
        return "보통"
    elif aqi == 3:
        return "나쁨"
    elif aqi == 4:
        return "매우 나쁨"
    elif aqi == 5:
        return "최악"
    return "알 수 없음"

def format_message(weather_data, dust_data):
    """API 데이터를 바탕으로 카카오톡 메시지 내용을 만듭니다."""
    if not weather_data or not dust_data:
        return "날씨 정보를 가져오는 데 실패했습니다."

    city_name = weather_data['name']
    temp = weather_data['main']['temp']
    weather_desc = weather_data['weather'][0]['description']
    feels_like = weather_data['main']['feels_like']
    
    aqi = dust_data['list'][0]['main']['aqi']
    dust_stat = get_dust_status(aqi)

    # 비 정보 (있을 경우)
    rain_info = ""
    if 'rain' in weather_data and '1h' in weather_data['rain']:
        rain_mm = weather_data['rain']['1h']
        rain_info = f" (시간당 {rain_mm}mm)"

    message = (
        f"🏙️ 오늘 {city_name} 날씨 리포트\n"
        f"--------------------------\n"
        f"🌡️ 현재 기온: {temp}°C (체감: {feels_like}°C)\n"
        f"☀️ 날씨: {weather_desc}{rain_info}\n"
        f"😷 미세먼지: {dust_stat}\n"
        f"--------------------------\n"
        f"오늘도 좋은 하루 보내세요! 😊"
    )
    return message

def save_tokens(tokens):
    """토큰을 파일에 저장합니다."""
    with open(TOKEN_FILE, "w") as fp:
        json.dump(tokens, fp)

def load_tokens():
    """파일에서 토큰을 불러옵니다."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as fp:
            return json.load(fp)
    return None

def refresh_kakao_token(refresh_token):
    """리프레시 토큰으로 액세스 토큰을 갱신합니다."""
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": refresh_token,
    }
    response = requests.post(url, data=data)
    tokens = response.json()
    
    if "error" in tokens:
        print(f"토큰 갱신 실패: {tokens}")
        return None
        
    # 새로운 리프레시 토큰이 발급되었으면 저장, 아니면 기존 것 유지
    if "refresh_token" not in tokens:
        tokens["refresh_token"] = refresh_token
        
    save_tokens(tokens)
    print("액세스 토큰이 성공적으로 갱신되었습니다.")
    return tokens["access_token"]

def get_initial_kakao_token(auth_code):
    """최초 인증 코드로 토큰을 발급받습니다."""
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
    }
    response = requests.post(url, data=data)
    tokens = response.json()

    if "error" in tokens:
        raise ValueError(f"토큰 발급 실패: {tokens}")

    save_tokens(tokens)
    print("토큰이 성공적으로 발급되어 파일에 저장되었습니다.")
    return tokens["access_token"]

def send_kakao_to_me(access_token, message):
    """'나에게 보내기' API를 사용하여 메시지를 전송합니다."""
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # 메시지 템플릿 생성
    template_object = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": "https://weather.naver.com/",
            "mobile_web_url": "https://m.weather.naver.com/"
        },
        "button_title": "자세한 날씨 보기"
    }

    data = {
        "template_object": json.dumps(template_object)
    }

    response = requests.post(url, headers=headers, data=data)
    if response.json().get("result_code") == 0:
        print("카카오톡 메시지를 성공적으로 보냈습니다.")
    else:
        print(f"메시지 보내기 실패: {response.json()}")

def main():
    """메인 실행 함수"""
    access_token = None
    tokens = load_tokens()

    if tokens:
        # 리프레시 토큰이 있으면 갱신 시도
        access_token = refresh_kakao_token(tokens["refresh_token"])
    
    # 토큰이 없거나 갱신에 실패한 경우, 수동 인증 필요
    if not access_token:
        print("--- 최초 인증 절차 ---")
        auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_REST_API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code&scope=talk_message"
        print("1. 아래 URL에 접속하여 카카오 로그인을 하고 '동의하고 계속하기'를 클릭하세요.")
        print(f"   {auth_url}")
        print("2. 로그인 후 리다이렉트된 URL에서 'code=' 뒷부분의 인증 코드를 복사하여 아래에 붙여넣으세요.")
        auth_code = input("인증 코드: ").strip()
        
        try:
            access_token = get_initial_kakao_token(auth_code)
        except ValueError as e:
            print(e)
            return

    if not access_token:
        print("액세스 토큰을 얻지 못했습니다. 프로그램을 종료합니다.")
        return
        
    # 날씨 및 미세먼지 정보 가져오기
    weather_data, dust_data = get_weather_and_dust()
    
    # 메시지 포맷팅
    message_text = format_message(weather_data, dust_data)
    
    # 카카오톡 메시지 전송
    send_kakao_to_me(access_token, message_text)


if __name__ == "__main__":
    main()
