import requests
import json
import os

# --- 설정 ---
# 아래 "YOUR_..." 부분에 본인의 실제 키를 직접 입력해주세요.
OPENWEATHERMAP_API_KEY = "319607f4dd50bcac6dbeeb8eda1663fa"
KAKAO_REST_API_KEY = "1cfef967cc8b70ee9b11af77775a712f"

REDIRECT_URI = "https://localhost"
TOKEN_FILE = "kakao_tokens.json"

# --- 함수 정의 ---

def get_weather_and_dust(city_name):
    """OpenWeatherMap API를 사용하여 날씨와 미세먼지 정보를 가져옵니다."""
    try:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=kr"
        weather_res = requests.get(weather_url)
        weather_res.raise_for_status()
        weather_data = weather_res.json()

        lat = weather_data['coord']['lat']
        lon = weather_data['coord']['lon']

        dust_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}"
        dust_res = requests.get(dust_url)
        dust_res.raise_for_status()
        dust_data = dust_res.json()
        return weather_data, dust_data
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None, None

def get_dust_status(aqi):
    if aqi == 1: return "좋음"
    elif aqi == 2: return "보통"
    elif aqi == 3: return "나쁨"
    elif aqi == 4: return "매우 나쁨"
    elif aqi == 5: return "최악"
    return "알 수 없음"

def translate_weather_description(description):
    translation_map = {"튼구름": "조각구름 많음", "온흐림": "흐림", "실 비": "이슬비", "가벼운 비": "약한 비"}
    return translation_map.get(description, description)

def format_message(weather_data, dust_data):
    if not weather_data or not dust_data:
        return "날씨 정보를 가져오는 데 실패했습니다."
    city_name = weather_data['name']
    temp = weather_data['main']['temp']
    original_desc = weather_data['weather'][0]['description']
    weather_desc = translate_weather_description(original_desc)
    feels_like = weather_data['main']['feels_like']
    aqi = dust_data['list'][0]['main']['aqi']
    dust_stat = get_dust_status(aqi)
    rain_info = ""
    if 'rain' in weather_data and '1h' in weather_data['rain']:
        rain_mm = weather_data['rain']['1h']
        rain_info = f" (시간당 {rain_mm}mm)"
    message = (
        f"🏙️ 오늘 {city_name} 날씨 리포트\n"
        f"--------------------------\n"
        f"🌡️ 현재 기온: {temp:.1f}°C (체감: {feels_like:.1f}°C)\n"
        f"☀️ 날씨: {weather_desc}{rain_info}\n"
        f"😷 미세먼지: {dust_stat}\n"
        f"--------------------------\n"
        f"오늘도 좋은 하루 보내세요! 😊"
    )
    return message

def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as fp:
        json.dump(tokens, fp)

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as fp:
            return json.load(fp)
    return None

def refresh_kakao_token(refresh_token):
    url = "https://kauth.kakao.com/oauth/token"
    data = {"grant_type": "refresh_token", "client_id": KAKAO_REST_API_KEY, "refresh_token": refresh_token}
    response = requests.post(url, data=data)
    tokens = response.json()
    if "error" in tokens:
        print(f"토큰 갱신 실패: {tokens}")
        return None
    if "refresh_token" not in tokens:
        tokens["refresh_token"] = refresh_token
    save_tokens(tokens)
    return tokens["access_token"]

def get_initial_kakao_token(auth_code):
    url = "https://kauth.kakao.com/oauth/token"
    data = {"grant_type": "authorization_code", "client_id": KAKAO_REST_API_KEY, "redirect_uri": REDIRECT_URI, "code": auth_code}
    response = requests.post(url, data=data)
    tokens = response.json()
    if "error" in tokens:
        raise ValueError(f"토큰 발급 실패: {tokens}")
    save_tokens(tokens)
    print("토큰이 성공적으로 발급되어 파일에 저장되었습니다.")
    return tokens["access_token"]

def send_kakao_to_me(access_token, message):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    template_object = {
        "object_type": "text", "text": message,
        "link": {"web_url": "https://weather.naver.com/", "mobile_web_url": "https://m.weather.naver.com/"},
        "button_title": "자세한 날씨 보기"
    }
    data = {"template_object": json.dumps(template_object)}
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
        access_token = refresh_kakao_token(tokens["refresh_token"])
    
    if not access_token:
        print("--- 최초 인증 절차 ---")
        auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_REST_API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code&scope=talk_message"
        print(f"1. 아래 URL에 접속하여 인증하세요:\n   {auth_url}")
        auth_code = input("2. 인증 후 받은 코드를 여기에 붙여넣으세요: ").strip()
        try:
            access_token = get_initial_kakao_token(auth_code)
        except ValueError as e:
            print(e)
            return

    if not access_token:
        print("액세스 토큰을 얻지 못했습니다. 프로그램을 종료합니다.")
        return
        
    # 날씨를 조회할 도시를 'Yongin'으로 고정합니다.
    city_to_check = "Yongin"
    print(f"지정된 도시: {city_to_check}의 날씨를 조회합니다.")
    weather_data, dust_data = get_weather_and_dust(city_to_check)
    
    message_text = format_message(weather_data, dust_data)
    send_kakao_to_me(access_token, message_text)

if __name__ == "__main__":
    main()

