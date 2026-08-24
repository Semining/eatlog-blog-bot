import base64
import json
import io
import anthropic
from PIL import Image
from prompts import SYSTEM_PROMPT, PHOTO_ANALYSIS_PROMPT, BLOG_GENERATION_PROMPT

MODEL = "claude-sonnet-4-6"


def _to_base64(image_file) -> tuple[str, str]:
    """업로드된 파일을 base64 JPEG로 변환. 최대 1000px, quality 65로 압축."""
    if hasattr(image_file, "read"):
        img_bytes = image_file.read()
        image_file.seek(0)
    else:
        buf = io.BytesIO()
        image_file.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

    img = Image.open(io.BytesIO(img_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 긴 변 기준 1000px로 리사이즈
    img.thumbnail((1000, 1000), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=65)
    data = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return data, "image/jpeg"


def analyze_photos(api_key: str, image_files: list) -> list[dict]:
    """사진들을 Claude Vision으로 분석. 최대 5장, 한 번에 전송."""
    if not image_files:
        return []

    client = anthropic.Anthropic(api_key=api_key)

    # 최대 5장으로 제한
    files = image_files[:5]

    content = [{"type": "text", "text": PHOTO_ANALYSIS_PROMPT}]
    for img_file in files:
        data, media_type = _to_base64(img_file)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        })

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return []


def generate_blog(api_key: str, restaurant_info: dict, photo_analysis: list[dict]) -> str:
    """식당 정보 + 사진 분석 결과로 블로그 포스팅 생성"""
    client = anthropic.Anthropic(api_key=api_key)

    info_text = "\n".join(f"- {k}: {v}" for k, v in restaurant_info.items() if v)

    if photo_analysis:
        lines = [
            f"[사진 {item.get('index', 0) + 1}] 유형: {item.get('type', '기타')} / {item.get('description', '')}"
            for item in photo_analysis
        ]
        analysis_text = "\n".join(lines)
    else:
        analysis_text = "사진 정보 없음 (텍스트 정보만으로 작성)"

    user_prompt = BLOG_GENERATION_PROMPT.format(
        restaurant_info=info_text,
        photo_analysis=analysis_text,
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text
