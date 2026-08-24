import os
import streamlit as st
from dotenv import load_dotenv
from generator import analyze_photos, generate_blog

load_dotenv()


def _parse_sections(text: str) -> dict:
    section_markers = [
        "[제목]", "[도입]", "[가게 정보 및 외관]", "[가게외관]",
        "[가게내부 및 인테리어]", "[메뉴판]", "[음식 후기]", "[총평]", "[해시태그]",
    ]
    sections = {}
    current_section = None
    current_lines = []

    for line in text.split("\n"):
        matched = False
        for marker in section_markers:
            if marker in line:
                if current_section:
                    sections[current_section] = "\n".join(current_lines)
                current_section = marker
                current_lines = []
                matched = True
                break
        if not matched and current_section:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines)

    return sections


st.set_page_config(
    page_title="EatLog 블로그 자동화 봇",
    page_icon="🍽️",
    layout="wide",
)

st.title("🍽️ EatLog 맛집 블로그 자동화 봇")
st.caption("사진 + 기본 정보만 넣으면 '벨리완' 문체의 SEO 최적화 포스팅을 자동 생성해요!")

# ── API 키 설정 ───────────────────────────────────────────────────────────────
api_key = os.getenv("ANTHROPIC_API_KEY", "")
with st.expander("⚙️ API 설정", expanded=not bool(api_key)):
    st.markdown(
        "🔑 API 키 발급: [Anthropic Console](https://console.anthropic.com/settings/keys) "
        "→ 최소 $5 충전 후 사용 (블로그 수백 개 분량)"
    )
    api_key_input = st.text_input(
        "Anthropic API Key",
        value=api_key,
        type="password",
        placeholder="sk-ant-...",
    )
    if api_key_input:
        api_key = api_key_input

# ── 사이드바: 식당 정보 입력 ──────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 식당 정보 입력")

    st.subheader("필수 정보")
    restaurant_name = st.text_input("식당명 *", placeholder="예: 백양숯불갈비")
    region = st.text_input("지역 *", placeholder="예: 인제대, 홍대, 강남")
    visit_type = st.selectbox("방문 유형", ["커플/데이트", "친구/모임", "혼밥", "가족 외식", "회식"])

    st.subheader("선택 정보")
    address = st.text_input("주소", placeholder="예: 경남 김해시 인제로 139 2층")
    hours = st.text_input("영업시간", placeholder="예: 평일 17:00-24:00 (수요일 휴무)")
    parking = st.selectbox("주차", ["", "주차 가능", "주차 불가", "유료 주차"])
    reservation = st.selectbox("예약", ["", "예약 필수", "예약 가능", "예약 불필요"])
    facilities = st.text_input("편의시설", placeholder="예: 어린이놀이방, 주차장, 휴대폰 충전소")
    visit_count = st.number_input("방문 횟수", min_value=1, max_value=10, value=1)

    st.subheader("메뉴 정보")
    menu_input = st.text_area(
        "주문한 메뉴 (한 줄에 하나씩)",
        placeholder="생갈비(100g) / 4,500원\n양념갈비(100g) / 4,500원\n진국된장찌개 / 5,900원",
        height=120,
    )

    st.subheader("추가 메모")
    extra_notes = st.text_area(
        "특이사항 / 팁",
        placeholder="사장님이 생갈비부터 드시길 추천, 듀록돼지 사용, 셀프바 있음 등",
        height=80,
    )

# ── 메인 영역: 사진 업로드 ────────────────────────────────────────────────────
st.subheader("📸 사진 업로드")
uploaded_files = st.file_uploader(
    "식당 사진을 드래그하거나 선택하세요 (여러 장 가능)",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 5))
    for i, f in enumerate(uploaded_files[:5]):
        with cols[i]:
            st.image(f, width="stretch", caption=f.name)
    if len(uploaded_files) > 5:
        st.caption(f"+ {len(uploaded_files) - 5}장 더 업로드됨")

# ── 생성 버튼 ─────────────────────────────────────────────────────────────────
st.divider()
col1, col2 = st.columns([1, 3])
with col1:
    generate_btn = st.button("✍️ 포스팅 생성", type="primary", use_container_width=True)

if generate_btn:
    if not api_key:
        st.error("Gemini API Key를 입력해주세요!")
        st.stop()
    if not restaurant_name or not region:
        st.error("식당명과 지역은 필수 입력 항목이에요!")
        st.stop()

    restaurant_info = {
        "식당명": restaurant_name,
        "지역": region,
        "방문유형": visit_type,
        "주소": address or None,
        "영업시간": hours or None,
        "주차": parking or None,
        "예약": reservation or None,
        "편의시설": facilities or None,
        "방문횟수": f"{visit_count}차 방문" if visit_count > 1 else "첫 방문",
        "주문메뉴": menu_input or None,
        "추가메모": extra_notes or None,
    }

    with st.spinner("📸 사진 분석 중..."):
        try:
            photo_analysis = analyze_photos(api_key, uploaded_files) if uploaded_files else []
            if photo_analysis:
                st.success(f"사진 {len(photo_analysis)}장 분석 완료!")
        except Exception as e:
            st.warning(f"사진 분석 오류 (텍스트로만 생성합니다): {e}")
            photo_analysis = []

    with st.spinner("✍️ 블로그 포스팅 생성 중... (15~30초 소요)"):
        try:
            blog_content = generate_blog(api_key, restaurant_info, photo_analysis)
        except Exception as e:
            st.error(f"생성 실패: {e}")
            st.stop()

    st.success("포스팅 생성 완료! 🎉")

    # ── 결과 출력 ──────────────────────────────────────────────────────────────
    st.subheader("📝 생성된 포스팅")
    sections = _parse_sections(blog_content)

    if sections:
        for title, content in sections.items():
            with st.expander(title, expanded=True):
                st.text_area(
                    label=title,
                    value=content.strip(),
                    height=200,
                    label_visibility="collapsed",
                )
    else:
        st.text_area("전체 포스팅", value=blog_content, height=600)

    st.divider()
    st.subheader("📋 전체 복사")
    st.text_area(
        "전체 내용 (여기서 복사하세요)",
        value=blog_content,
        height=400,
    )

    if photo_analysis:
        with st.expander("🔍 사진 분석 결과 보기"):
            for item in photo_analysis:
                st.write(f"**사진 {item.get('index', 0) + 1}** [{item.get('type', '기타')}]")
                st.caption(item.get("description", ""))
